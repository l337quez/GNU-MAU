from datetime import datetime, timedelta
import jwt
import base64
from fastapi import HTTPException, status
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity, 
    RegistrationResponse, 
    AuthenticationResponse, 
    AttestedCredentialData
)
from fido2.cose import CoseKey
from fido2 import cbor
from app.core.config import get_settings
from app.api.auth.models import UserModel, CredentialModel

settings = get_settings()

class AuthService:
    def __init__(self, db):
        self.db = db
        # 1. Configurar el RP (Relying Party)
        rp = PublicKeyCredentialRpEntity(id=settings.RP_ID, name=settings.RP_NAME)
        
        # 2. Configurar callback de verificación de origen
        def verify_origin(origin: str) -> bool:
            allowed = [settings.ORIGIN]
            if settings.DEBUG:
                allowed.extend([
                    "http://localhost:9000",
                    "http://127.0.0.1:9000",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ])
            return origin in allowed

        # 3. Inicializar el Fido2Server de Yubico
        self.server = Fido2Server(rp, verify_origin=verify_origin)

    def get_registration_options(self, username: str, display_name: str) -> dict:
        # Generar un ID de usuario en bytes (usamos UUID para usuarios nuevos)
        user_doc = self.db.users.find_one({"username": username})
        if user_doc:
            user_id = user_doc["_id"]
            if isinstance(user_id, str):
                user_id_bytes = user_id.encode("utf-8")
            else:
                user_id_bytes = str(user_id).encode("utf-8")
        else:
            import uuid
            user_id_bytes = uuid.uuid4().bytes

        user_entity = {
            "id": user_id_bytes,
            "name": username,
            "displayName": display_name,
        }

        # Generar opciones FIDO2 con Yubico Fido2Server
        options, state = self.server.register_begin(user_entity, user_verification="preferred")

        # Guardar el reto/estado temporal en la colección temporal
        self.db.auth_states.update_one(
            {"state_id": username},
            {"$set": {
                "state": state,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )

        return self._serialize_options(options)

    def verify_registration(self, username: str, display_name: str, credential_dict: dict) -> dict:
        state_doc = self.db.auth_states.find_one({"state_id": username})
        if not state_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay un reto de registro activo para este usuario."
            )
        
        state = state_doc["state"]
        self.db.auth_states.delete_one({"state_id": username})

        try:
            # Deserializar respuesta FIDO2 recibida del cliente
            credential_response = RegistrationResponse.from_dict(credential_dict)
            
            # Completar validación criptográfica en Fido2Server
            auth_data = self.server.register_complete(state, credential_response)
            
            # Extraer credencial y guardarla en formato compatible con BSON
            cred_data = auth_data.credential_data
            cred_id_bytes = cred_data.credential_id
            public_key_obj = cred_data.public_key # CoseKey
            
            cred_id_str = base64.urlsafe_b64encode(cred_id_bytes).decode("utf-8").rstrip("=")
            public_key_cbor = cbor.encode(public_key_obj)
            public_key_str = base64.urlsafe_b64encode(public_key_cbor).decode("utf-8").rstrip("=")
            
            # sign_count inicial
            sign_count = getattr(auth_data, "sign_count", 0)

            credential_data_model = {
                "credential_id": cred_id_str,
                "public_key": public_key_str,
                "sign_count": sign_count
            }
            
            user_doc = self.db.users.find_one({"username": username})
            if user_doc:
                self.db.users.update_one(
                    {"username": username},
                    {"$push": {"credentials": credential_data_model}}
                )
            else:
                new_user = UserModel(
                    username=username,
                    display_name=display_name,
                    credentials=[CredentialModel(**credential_data_model)]
                )
                self.db.users.insert_one(new_user.model_dump())
                
            return {"status": "success", "message": "Dispositivo registrado con éxito"}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fallo en verificación FIDO2: {str(e)}"
            )

    def get_login_options(self, username: str) -> dict:
        user_doc = self.db.users.find_one({"username": username})
        if not user_doc or not user_doc.get("credentials"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El usuario no existe o no tiene dispositivos FIDO2 registrados."
            )

        credentials = []
        for cred in user_doc["credentials"]:
            cred_id_bytes = base64.urlsafe_b64decode(self._pad_base64(cred["credential_id"]))
            public_key_bytes = base64.urlsafe_b64decode(self._pad_base64(cred["public_key"]))
            cose_key = CoseKey.parse(cbor.decode(public_key_bytes))
            
            cred_data = AttestedCredentialData(b"\x00" * 16, cred_id_bytes, cose_key)
            credentials.append(cred_data)

        # Generar opciones para login
        options, state = self.server.authenticate_begin(credentials, user_verification="preferred")

        # Guardar reto temporal
        self.db.auth_states.update_one(
            {"state_id": username},
            {"$set": {
                "state": state,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )

        return self._serialize_options(options)

    def verify_login(self, username: str, credential_dict: dict) -> dict:
        user_doc = self.db.users.find_one({"username": username})
        if not user_doc or not user_doc.get("credentials"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El usuario no existe o no tiene credenciales registradas."
            )

        state_doc = self.db.auth_states.find_one({"state_id": username})
        if not state_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró un reto de inicio de sesión activo."
            )
        
        state = state_doc["state"]
        self.db.auth_states.delete_one({"state_id": username})

        credentials = []
        for cred in user_doc["credentials"]:
            cred_id_bytes = base64.urlsafe_b64decode(self._pad_base64(cred["credential_id"]))
            public_key_bytes = base64.urlsafe_b64decode(self._pad_base64(cred["public_key"]))
            cose_key = CoseKey.parse(cbor.decode(public_key_bytes))
            cred_data = AttestedCredentialData(b"\x00" * 16, cred_id_bytes, cose_key)
            credentials.append(cred_data)

        try:
            credential_response = AuthenticationResponse.from_dict(credential_dict)
            
            # Completar autenticación
            auth_data = self.server.authenticate_complete(state, credentials, credential_response)
            
            used_cred_id_bytes = auth_data.credential_data.credential_id
            used_cred_id_str = base64.urlsafe_b64encode(used_cred_id_bytes).decode("utf-8").rstrip("=")
            
            # Actualizar sign_count
            new_sign_count = getattr(auth_data, "sign_count", 0)
            
            self.db.users.update_one(
                {"username": username, "credentials.credential_id": used_cred_id_str},
                {"$set": {"credentials.$.sign_count": new_sign_count}}
            )

            # Generar token JWT de sesión
            token = self.generate_jwt_token(username)
            return {"access_token": token, "token_type": "bearer"}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Fallo de verificación de FIDO2: {str(e)}"
            )

    def login_with_password(self, username: str, plain_password: str) -> dict:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user_doc = self.db.users.find_one({"username": username})
        
        # Si el login es con email en lugar de username
        if not user_doc:
            user_doc = self.db.users.find_one({"email": username})
            
        if not user_doc or not user_doc.get("hashed_password"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas o usuario no registrado con contraseña"
            )
            
        if not pwd_context.verify(plain_password, user_doc["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
            
        token = self.generate_jwt_token(user_doc["username"])
        return {"access_token": token, "token_type": "bearer"}

    def generate_jwt_token(self, username: str) -> str:
        payload = {
            "sub": username,
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def verify_jwt_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload["sub"]
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )

    def _pad_base64(self, s: str) -> str:
        return s + "=" * (4 - len(s) % 4)

    def _serialize_options(self, options) -> dict:
        from fido2.utils import websafe_encode
        from collections.abc import Mapping
        
        def prepare(data):
            if isinstance(data, bytes):
                return websafe_encode(data)
            elif isinstance(data, (str, int, float, bool)) or data is None:
                return data
            elif isinstance(data, Mapping):
                return {k: prepare(v) for k, v in data.items()}
            elif isinstance(data, (list, tuple, set)):
                return [prepare(v) for v in data]
            elif hasattr(data, "to_dict"):
                return prepare(data.to_dict())
            elif hasattr(data, "__dict__"):
                return prepare(data.__dict__)
            else:
                try:
                    return prepare(dict(data))
                except (TypeError, ValueError):
                    return str(data)
                    
        if hasattr(options, "publicKey"):
            return prepare(options.publicKey)
        elif isinstance(options, Mapping) and "publicKey" in options:
            return prepare(options["publicKey"])
        else:
            return prepare(options)
