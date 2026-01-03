import os
import shutil
import face_recognition
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
    load_known_faces()

known_faces = []
known_names = []
folder = "known_images"
def load_known_faces():
    known_faces.clear()
    known_names.clear()
    for file in os.listdir(folder):
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(folder, file)
            name = os.path.splitext(file)[0]
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_faces.append(encodings[0])
                known_names.append(name)

def add_new_face(image_path, name):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        raise ValueError("No face found")

    known_faces.append(encodings[0])
    known_names.append(name)


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
    for name, record in attendance_tracker[today][slot].items():
        session_minutes = int(record["total_time"] // 60)

        try:
            existing = (
                supabase.table("attendance")
                .select("minutes")
                .eq("name", name)
                .eq("date", today)
                .eq("slot", slot)
                .limit(1)
                .execute()
            )

            if existing.data:
                total_minutes = (existing.data[0]["minutes"] or 0) + session_minutes
                status = "Present" if total_minutes >= 1 else "Absent"

                supabase.table("attendance").update({
                    "minutes": total_minutes,
                    "status": status
                }).eq("name", name).eq("date", today).eq("slot", slot).execute()

            else:
                status = "Present" if session_minutes >= 1 else "Absent"

                supabase.table("attendance").insert({
                    "name": name,
                    "date": today,
                    "slot": slot,
                    "minutes": session_minutes,
                    "status": status
                }).execute()

        except Exception as e:
            print("Attendance save failed:", e)

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
