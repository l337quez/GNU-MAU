import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from markitdown import MarkItDown
from app.api.notes.service import NoteService
from app.api.notes.schemas import NoteCreate

router = APIRouter(prefix="/projects/{project_id}/tools", tags=["Tools"])

def get_note_service() -> NoteService:
    return NoteService()

class MarkdownResponse(BaseModel):
    markdown: str
    note_created: bool
    note_id: str | None = None

@router.post("/markitdown", response_model=MarkdownResponse, summary="Convert file to Markdown")
async def convert_to_markdown(
    project_id: str,
    file: UploadFile = File(...),
    create_note: bool = Form(False),
    note_service: NoteService = Depends(get_note_service)
):
    try:
        # Save upload to temporary file
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # Convert using markitdown
        md = MarkItDown()
        result = md.convert(temp_path)
        markdown_content = result.text_content
        
        # Clean up
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        note_created = False
        note_id = None
        
        if create_note:
            title = os.path.splitext(file.filename)[0] if file.filename else "Converted Document"
            payload = NoteCreate(
                title=title,
                content=markdown_content,
                status="draft"
            )
            try:
                note = note_service.create(project_id, payload)
                note_created = True
                note_id = note.id
            except Exception as e:
                # Si falla la creación de nota (ej: ya existe), ignoramos para al menos retornar el MD
                pass

        return MarkdownResponse(
            markdown=markdown_content,
            note_created=note_created,
            note_id=note_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting file: {str(e)}")
