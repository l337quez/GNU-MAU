# GNU Mau en Podman (contenedor)

Guía para ejecutar la aplicación en un contenedor con datos persistentes.

## Requisitos

- Podman (con `podman compose`) o Docker con Compose.
- Sesión gráfica X11/Xwayland activa.
- `xhost` instalado (lo usa `start.sh`).

## Inicio rápido

```bash
./start.sh
```

El script:

1. Permite conexiones X11 locales (`xhost +local:`).
2. Crea los directorios persistentes `./.docker-data/config` y `./.docker-data/data`.
3. Construye la imagen si hace falta (`podman compose up -d --build`).

Detener la aplicación:

```bash
podman compose down
```

Ver registros:

```bash
podman compose logs -f
```

## Persistencia

| Dato | Ruta en el contenedor | Ruta por defecto en el host |
| :--- | :--- | :--- |
| Configuración (`config.json`) | `/config` | `./.docker-data/config` |
| Base de datos Mongita | `/data/mongita_data` | `./.docker-data/data/mongita_data` |
| Archivos de proyectos (`storage`) | `/data/storage` | `./.docker-data/data/storage` |

La aplicación decide estas rutas mediante las variables de entorno
`GNU_MAU_CONFIG_DIR` y `GNU_MAU_DATA_DIR` (ver `utils.py`). Fuera del
contenedor se mantienen los valores de siempre (`~/.myapp/config.json` y la
carpeta del proyecto).

Para reutilizar datos existentes, copia `.env.example` a `.env` y ajusta:

```bash
GNU_MAU_CONFIG_PATH=/mnt/ronal_disk/contenedores/gnu_mau_data/config
GNU_MAU_DATA_PATH=/mnt/ronal_disk/contenedores/gnu_mau_data
```

Después vuelve a ejecutar `./start.sh`.

## Bandeja del sistema

Dentro del contenedor no suele haber un host de bandeja (StatusNotifier).
En ese caso la aplicación lo detecta con
`QSystemTrayIcon.isSystemTrayAvailable()` y, al cerrar la ventana, termina el
proceso en lugar de quedarse oculta en segundo plano.

## Reconstruir tras cambiar el código

```bash
podman compose build --no-cache
./start.sh
```

Las dependencias se instalan desde `poetry.lock`; si cambias
`pyproject.toml`, regenera el lock antes de construir:

```bash
poetry lock
```

## Problemas frecuentes

- **No se abre la ventana**: comprueba `echo $DISPLAY` y ejecuta
  `xhost +local:` en la sesión gráfica.
- **Error de plugin `xcb`**: falta alguna librería Qt; reconstruye la imagen
  (el `Dockerfile` instala `libxcb-cursor0` y el resto de dependencias).
- **Datos vacíos tras actualizar la imagen**: revisa que los volúmenes
  `GNU_MAU_CONFIG_PATH` y `GNU_MAU_DATA_PATH` apunten a los mismos
  directorios que antes.
- **Permisos de los volúmenes**: los directorios del host deben ser
  escribibles por el usuario del contenedor (root por defecto).
