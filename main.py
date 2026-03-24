import cv2
from fastapi import FastAPI,Request, Form
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import face_recognition
from ultralytics import YOLO
from datetime import datetime,date
from services import router,save_slot_attendance,known_faces, known_names, load_known_faces ,get_student_attendance,login_or_register_student,check_password,superkey,encrypt_password

app = FastAPI()
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
model = YOLO("yolov8n.pt")

load_known_faces()


recognized_faces = {}
TODAY = date.today().isoformat()
LAST_SLOT = None

attendance_tracker = {}
lecture_slots = [
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("12:45", "13:45"),
    ("13:45", "14:45"),
    ("15:00", "17:00")
]

def get_current_lecture_slot():
    now = datetime.now().time()
    for start, end in lecture_slots:
        s = datetime.strptime(start, "%H:%M").time()
        e = datetime.strptime(end, "%H:%M").time()
        if s <= now <= e:
            return f"{start}-{end}"
    return None

def generate_frames():
    camera = cv2.VideoCapture(0)
    while True:
        try:
            success, frame = camera.read()
            if not success:
                continue

            frame = cv2.flip(frame,1)
            today = date.today().isoformat()

            global LAST_SLOT
            current_slot = get_current_lecture_slot()
            if LAST_SLOT and current_slot != LAST_SLOT:
                pass
                save_slot_attendance(attendance_tracker,LAST_SLOT)
            LAST_SLOT = current_slot

            results = model.track(frame, conf=0.4, classes=[0],persist=True,tracker="bytetrack.yaml")
            for r in results:
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    if box.id is None:
                        continue
                    track_id = int(box.id[0])

                    if track_id not in recognized_faces:
                        # recognized_faces[track_id] = f"Person {track_id}"
                        recognized_faces[track_id] = None

                    name = recognized_faces[track_id]
                    
                    person_crop = frame[y1:y2, x1:x2]
                    if person_crop.size > 0:
                        rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_crop)
                        face_encodings = face_recognition.face_encodings(rgb_crop, face_locations)

                        for face_encoding in face_encodings:
                            matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.5)
                            if True in matches:
                                idx = matches.index(True)
                                recognized_faces[track_id] = known_names[idx]
                                name = known_names[idx]
                                break

                    if current_slot and name:
                        attendance_tracker.setdefault(today, {})
                        attendance_tracker[today].setdefault(current_slot, {})

                        if name not in attendance_tracker[today][current_slot]:
                            attendance_tracker[today][current_slot][name] = {
                                "last_seen": datetime.now(),
                                "total_time": 0
                            }
                        now = datetime.now()
                        last_seen = attendance_tracker[today][current_slot][name]["last_seen"]
                        delta = (now - last_seen).total_seconds()

                        if delta < 3:
                            attendance_tracker[today][current_slot][name]["total_time"] += delta
                        attendance_tracker[today][current_slot][name]["last_seen"] = now

                    name = recognized_faces[track_id] or "Unknown"
                    cv2.rectangle(frame, (x1, y1), (x2, y2),(0, 255, 0), 2)
                    cv2.putText(frame, name,(x1, y1 - 10),cv2.FONT_HERSHEY_SIMPLEX,0.7, (0, 255, 0), 2)

            _, buffer = cv2.imencode(".jpg", frame)
            
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )
        except Exception as e:
            print("VIDEO ERROR:", e)
            continue

@app.post("/login")
def login(
    request: Request,
    role: str = Form(...),

    name: str = Form(None),
    prn: str = Form(None),
    password: str = Form(None),

    teacher_id: str = Form(None),
    teacher_name: str = Form(None),
    teacher_password: str = Form(None),
):
    if role == "student":
        ok, message = login_or_register_student(name, prn, password)

        if not ok:
            return templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "error": message,
                    "open_login": True,
                    "active_role": "student"
                }
            )

        return RedirectResponse(
            url=f"/student/dashboard?name={name}",
            status_code=302
        )

    if role == "teacher":
        hashed_superkey = encrypt_password(superkey)
        if not check_password(teacher_id , hashed_superkey):
            return templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "error": "Invalid teacher ID"
                }
            )

        return RedirectResponse(
            url="/index",
            status_code=302
        )

@app.get("/")
def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request ,"error": None,
            "open_login": False})


@app.get("/index")
def teacher_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/student/dashboard")
def student_dashboard(request: Request, name: str):
    attendance = get_student_attendance(name)
    total_slots = 0
    present_count = 0

    for _, slots in attendance.items():
        for _, status in slots.items():
            total_slots += 1
            if status == "Present":
                present_count += 1

    absent_count = total_slots - present_count
    attendance_percent = (
        round((present_count / total_slots) * 100, 2)
        if total_slots > 0 else 0
    )

    return templates.TemplateResponse(
        "student.html",
        {
            "request": request,
            "attendance": attendance,
            "student_name": name,
            "present_days": present_count,
            "absent_days": absent_count,
            "attendance_percent": attendance_percent
        }
    )

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/live-attendance")
def live_attendance():
    data = {}
    for day, slots in attendance_tracker.items():
        data[day] = {}
        for slot, records in slots.items():
            data[day][slot] = {}
            for name, record in records.items():
                total_seconds = int(record["total_time"])
                minutes = total_seconds // 60
                data[day][slot][name] = {
                    "name": name,
                    "minutes": minutes,
                    "status": "Present" if minutes >= 1 else "Absent"
                }
    if not data:
        return { "no_slots": True }

    return data

@app.on_event("shutdown")
def shutdown_event():
    print("🔻 Server shutting down...")
    global LAST_SLOT
    if LAST_SLOT:
        print(f"💾 Saving attendance for slot: {LAST_SLOT}")
        save_slot_attendance(attendance_tracker, LAST_SLOT)
    else:
        print("⚠ No active slot to save")
