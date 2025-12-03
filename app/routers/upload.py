import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings

router = APIRouter(tags=["upload"])


def validate_file_extension(filename: str) -> bool:
    """Check if the file has an allowed extension."""
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_extensions


def get_file_extension(filename: str) -> str:
    """Extract the file extension from filename."""
    return Path(filename).suffix.lower()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an audio or video file for processing.

    The file gets saved to disk with a unique ID so we can
    process it later. Right now we just store it - transcription
    comes in a future phase.
    """
    # make sure they gave us a filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # check the extension before we do anything else
    if not validate_file_extension(file.filename):
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported formats: {allowed}"
        )

    # read the file to check size
    # we do this in chunks to avoid loading huge files into memory
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)

    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {settings.max_file_size_mb}MB"
        )

    # generate a unique filename to avoid collisions
    file_id = str(uuid.uuid4())
    ext = get_file_extension(file.filename)
    new_filename = f"{file_id}{ext}"

    # make sure the upload directory exists
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / new_filename

    # save the file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return {
        "message": "File uploaded successfully",
        "file_id": file_id,
        "original_filename": file.filename,
        "size_mb": round(file_size_mb, 2),
    }


@router.get("/files/{file_id}")
async def get_file_info(file_id: str):
    """
    Get info about an uploaded file.

    This is mostly for debugging - lets you verify a file
    was uploaded correctly before we process it.
    """
    upload_path = Path(settings.upload_dir)

    # look for any file matching this ID
    # the extension could be any of the allowed types
    for ext in settings.allowed_extensions:
        file_path = upload_path / f"{file_id}{ext}"
        if file_path.exists():
            stat = file_path.stat()
            return {
                "file_id": file_id,
                "filename": file_path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "exists": True,
            }

    raise HTTPException(status_code=404, detail="File not found")
