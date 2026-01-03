import cv2
from fastapi import FastAPI,Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import face_recognition
from ultralytics import YOLO
from datetime import datetime,date
from services import router,save_slot_attendance,known_faces, known_names, load_known_faces

app = FastAPI()
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
model = YOLO("yolov8n.pt")

load_known_faces()

camera = cv2.VideoCapture(0)
recognized_faces = {}
TODAY = date.today().isoformat()
LAST_SLOT = None

attendance_tracker = {}
lecture_slots = [
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("12:45", "13:45"),
    ("13:45", "14:45"),
    ("15:00", "17:00"),
    ("17:00", "18:00") #demo
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
    person_counter = 0
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
                save_slot_to_supabase(attendance_tracker,LAST_SLOT)
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
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    
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
