# scripts/config.py
import os

# Configuración del proyecto
PROJECT_ID = "document-ai-project-473112"
VISION_KEY_PATH = r"C:\Users\irisc\Documents\vision-validator\keys\vision-key.json"

# Configurar variable de entorno para Google Cloud
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = VISION_KEY_PATH

# Carpetas del proyecto
BASE_DIR = r"C:\Users\irisc\Documents\vision-validator"
IMAGES_DIR = os.path.join(BASE_DIR, "images")
RESULTS_DIR = os.path.join(BASE_DIR, "results")