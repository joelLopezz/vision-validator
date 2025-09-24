# scripts/test_validation.py
from vision_validator import ReportValidator
import os
from config import IMAGES_DIR

def test_specific_image():
    validator = ReportValidator()
    
    # Cambiar 'tu_imagen.jpg' por el nombre real de tu archivo
    image_name = 'tu_imagen.jpg'  # CAMBIAR ESTE NOMBRE
    image_path = os.path.join(IMAGES_DIR, image_name)
    
    if os.path.exists(image_path):
        print(f"Procesando: {image_name}")
        result = validator.process_report_image(image_path)
        return result
    else:
        print(f"Imagen no encontrada: {image_path}")
        print("Imágenes disponibles:")
        for f in os.listdir(IMAGES_DIR):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                print(f"  - {f}")

if __name__ == "__main__":
    test_specific_image()