import cv2
from fastapi import FastAPI,Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import face_recognition
from ultralytics import YOLO

app = FastAPI()
templates = Jinja2Templates(directory="templates")
model = YOLO("yolov8n.pt")

known_faces = []
known_names = []
folder = "known_images"
for file in os.listdir(folder):
    if file.lower().endswith((".jpg", ".png", ".jpeg")):
        path = os.path.join(folder, file)
        name = os.path.splitext(file)[0]
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_faces.append(encodings[0])
            known_names.append(name)

camera = cv2.VideoCapture(0)
recognized_faces = {}

def generate_frames():
    person_counter = 0
    while True:
        success, frame = camera.read()
        if not success:
            continue

        frame = cv2.flip(frame,1)
        results = model.track(frame, conf=0.4, classes=[0],persist=True,tracker="bytetrack.yaml")
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                if box.id is None:
                    continue
                track_id = int(box.id[0])

                # Default label
                if track_id not in recognized_faces:
                    recognized_faces[track_id] = f"Person {track_id}"

                name = recognized_faces[track_id]

                # ---- FACE RECOGNITION ----
                person_crop = frame[y1:y2, x1:x2]
                if person_crop.size > 0:
                    rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_crop)
                    face_encodings = face_recognition.face_encodings(
                        rgb_crop, face_locations
                    )

                    for face_encoding in face_encodings:
                        matches = face_recognition.compare_faces(
                            known_faces, face_encoding, tolerance=0.5
                        )
                        if True in matches:
                            idx = matches.index(True)
                            recognized_faces[track_id] = known_names[idx]
                            name = known_names[idx]
                            break
                cv2.rectangle(frame, (x1, y1), (x2, y2),
                              (0, 255, 0), 2)
                cv2.putText(frame, name,(x1, y1 - 10),cv2.FONT_HERSHEY_SIMPLEX,0.7, (0, 255, 0), 2)

        _, buffer = cv2.imencode(".jpg", frame)
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
