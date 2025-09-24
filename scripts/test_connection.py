# scripts/test_connection.py
import sys
sys.path.append('.')

from config import PROJECT_ID
from google.cloud import vision

def test_vision_api():
    try:
        client = vision.ImageAnnotatorClient()
        print(f"✅ Conexión exitosa con Vision API")
        print(f"✅ Proyecto: {PROJECT_ID}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_vision_api()