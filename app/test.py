import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KNOWN_IMAGES_DIR = os.path.join(BASE_DIR, "known_images")
print(KNOWN_IMAGES_DIR)