from supabase import create_client
import os 
import face_recognition
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("key")
url = os.getenv("url")
supabase = create_client(url, key)

folder = "known_images"
for file in os.listdir(folder):
    if file.lower().endswith((".jpg", ".png", ".jpeg")):
        path = os.path.join(folder, file)
        name = os.path.splitext(file)[0]
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            encoding = encodings[0].tolist()
            supabase.table("encoding").insert(
                {"name" : name , "encoding" : encoding}).execute()
            print("encoded :" + name)