import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

UPLOAD_FOLDER = "known_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

def is_allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if not is_allowed(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG files are allowed"
        )

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "Image saved successfully",
        "filename": file.filename
    }
