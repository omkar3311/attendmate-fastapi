import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime,date
load_dotenv()
import csv
from fastapi.responses import FileResponse,JSONResponse

key = os.getenv("key")
url = os.getenv("url")
supabase = create_client(url, key)
router = APIRouter()

UPLOAD_FOLDER = "known_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

def is_allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if not is_allowed(file.filename):
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG files are allowed")

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return JSONResponse(
        status_code=200,
        content={"message": "Image uploaded successfully"}
    )

@router.get("/export/csv")
def download_csv():
    filename = "attendance.csv"
    export_attendance_csv(filename)
    return FileResponse(filename, media_type="text/csv", filename=filename)

def save_slot_attendance(attendance_tracker, slot):
    today = date.today().isoformat()
    if today not in attendance_tracker:
        return
    if slot not in attendance_tracker[today]:
        return
    records = []
    for name, record in attendance_tracker[today][slot].items():
        minutes = int(record["total_time"] // 60)
        status = "Present" if minutes >= 1 else "Absent"
        records.append({
            "name": name,
            "date": today,
            "slot": slot,
            "minutes": minutes,
            "status": status
        })
    if records:
        try:
            supabase.table("attendance").upsert(records).execute()
        except Exception as e:
            print("Export failed:", e)

def export_attendance_csv(filename="attendance.csv"):
    try:
        response = supabase.table("attendance").select("name,date,slot,minutes,status").order("date", desc=True).execute()
        if not response.data:
            print("⚠ No attendance data found")
            return
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "date", "slot", "minutes", "status"]
            )
            writer.writeheader()
            writer.writerows(response.data)
        print(f"Attendance exported to {filename}")
    except Exception as e:
        print("Export failed:", e)
