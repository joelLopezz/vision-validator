# scripts/vision_validator.py
"""
Validador de Cálculos en Reportes usando Google Cloud Vision API
Proyecto: Tecnologías Emergentes - Unidad 2
Autor: [Tu nombre]
"""

import sys
import os
import re
from typing import List, Dict, Tuple, Optional
from google.cloud import vision
from PIL import Image
import numpy as np
from config import PROJECT_ID, IMAGES_DIR, RESULTS_DIR

class ReportValidator:
    def __init__(self):
        """Inicializa el validador con Vision API client"""
        self.client = vision.ImageAnnotatorClient()
        self.project_id = PROJECT_ID
        
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extrae texto de una imagen usando Vision API
        
        Args:
            image_path: Ruta a la imagen
            
        Returns:
            str: Texto extraído de la imagen
        """
        try:
            # Leer imagen
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Crear objeto Image para Vision API
            image = vision.Image(content=content)
            
            # Llamar a Vision API para detección de texto
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f'Error de Vision API: {response.error.message}')
            
            # Extraer texto completo
            texts = response.text_annotations
            if texts:
                return texts[0].description  # Primer resultado contiene todo el texto
            else:
                return ""
                
        except Exception as e:
            print(f"❌ Error extrayendo texto: {e}")
            return ""
    
    def clean_extracted_text(self, text: str) -> List[str]:
        """
        Limpia y organiza el texto extraído en líneas útiles
        
        Args:
            text: Texto extraído de la imagen
            
        Returns:
            List[str]: Líneas de texto limpias
        """
        if not text:
            return []
        
        # Dividir en líneas y limpiar
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Limpiar espacios extra y caracteres especiales
            cleaned_line = re.sub(r'\s+', ' ', line.strip())
            if cleaned_line and len(cleaned_line) > 1:  # Ignorar líneas muy cortas
                cleaned_lines.append(cleaned_line)
        
        return cleaned_lines
    
    def extract_numbers_from_text(self, text: str) -> List[float]:
        """
        Extrae todos los números de una línea de texto
        
        Args:
            text: Línea de texto
            
        Returns:
            List[float]: Lista de números encontrados
        """
        # Patrón para encontrar números (incluye decimales y negativos)
        number_pattern = r'-?\d+\.?\d*'
        matches = re.findall(number_pattern, text)
        
        numbers = []
        for match in matches:
            try:
                # Convertir a float si es posible
                num = float(match)
                numbers.append(num)
            except ValueError:
                continue
        
        return numbers
    
    def detect_table_structure(self, lines: List[str]) -> Dict:
        """
        Detecta la estructura de tabla en las líneas de texto
        
        Args:
            lines: Líneas de texto extraídas
            
        Returns:
            Dict: Información sobre la estructura detectada
        """
        table_data = {
            'headers': [],
            'data_rows': [],
            'total_row': None,
            'summary': {}
        }
        
        # Buscar encabezados (líneas con pocas o ningún número)
        headers_found = False
        for i, line in enumerate(lines):
            numbers = self.extract_numbers_from_text(line)
            
            # Si la línea tiene pocas números y contiene palabras, probablemente es encabezado
            if len(numbers) <= 1 and any(char.isalpha() for char in line):
                if not headers_found:
                    table_data['headers'].append(line)
                    headers_found = True
                elif "total" in line.lower() or "suma" in line.lower():
                    table_data['total_row'] = line
                    break
            else:
                # Líneas con múltiples números son filas de datos
                if len(numbers) >= 2:
                    table_data['data_rows'].append({
                        'text': line,
                        'numbers': numbers
                    })
        
        # Buscar fila de total al final
        for line in reversed(lines):
            if ("total" in line.lower() or "suma" in line.lower() or 
                line.strip().isdigit()):
                table_data['total_row'] = line
                break
        
        return table_data
    
    def validate_calculations(self, table_data: Dict) -> Dict:
        """
        Valida los cálculos encontrados en la tabla
        
        Args:
            table_data: Estructura de tabla detectada
            
        Returns:
            Dict: Resultados de la validación
        """
        results = {
            'valid': False,
            'calculations': [],
            'errors': [],
            'summary': {}
        }
        
        if not table_data['data_rows']:
            results['errors'].append("No se encontraron filas de datos para validar")
            return results
        
        # Extraer todos los números de las filas de datos
        all_numbers = []
        for row in table_data['data_rows']:
            all_numbers.extend(row['numbers'])
        
        if not all_numbers:
            results['errors'].append("No se encontraron números para calcular")
            return results
        
        # Calcular suma total
        calculated_sum = sum(all_numbers)
        
        # Buscar el total reportado
        reported_total = None
        if table_data['total_row']:
            total_numbers = self.extract_numbers_from_text(table_data['total_row'])
            if total_numbers:
                # Tomar el número más grande como total reportado
                reported_total = max(total_numbers)
        
        # Si no encontramos total en fila específica, buscar en todas las líneas
        if reported_total is None:
            # El número más grande podría ser el total
            if all_numbers:
                potential_total = max(all_numbers)
                # Verificar si este número podría ser suma de los otros
                others = [n for n in all_numbers if n != potential_total]
                if others and abs(sum(others) - potential_total) < 0.01:
                    reported_total = potential_total
                    calculated_sum = sum(others)
        
        # Validar el cálculo
        if reported_total is not None:
            difference = abs(calculated_sum - reported_total)
            is_valid = difference < 0.01  # Tolerancia para errores de redondeo
            
            results.update({
                'valid': is_valid,
                'calculated_sum': calculated_sum,
                'reported_total': reported_total,
                'difference': difference,
                'numbers_used': all_numbers,
                'summary': {
                    'status': '✅ CÁLCULO CORRECTO' if is_valid else '❌ ERROR EN CÁLCULO',
                    'message': f'Suma calculada: {calculated_sum}, Total reportado: {reported_total}'
                }
            })
        else:
            results['errors'].append("No se pudo identificar el total reportado")
            results['summary'] = {
                'status': '⚠️ NO SE PUDO VALIDAR',
                'message': f'Números encontrados: {all_numbers}, Suma: {calculated_sum}'
            }
        
        return results
    
    def process_report_image(self, image_path: str, save_results: bool = True) -> Dict:
        """
        Función principal para procesar una imagen de reporte completa
        
        Args:
            image_path: Ruta a la imagen del reporte
            save_results: Si guardar resultados en archivo
            
        Returns:
            Dict: Resultados completos del procesamiento
        """
        print(f"\n📸 Procesando reporte: {os.path.basename(image_path)}")
        print("=" * 50)
        
        # Paso 1: Extraer texto
        print("🔍 Extrayendo texto con Vision API...")
        raw_text = self.extract_text_from_image(image_path)
        
        if not raw_text:
            return {'error': 'No se pudo extraer texto de la imagen'}
        
        # Paso 2: Limpiar texto
        print("🧹 Limpiando y organizando texto...")
        cleaned_lines = self.clean_extracted_text(raw_text)
        
        # Paso 3: Detectar estructura de tabla
        print("📊 Detectando estructura de tabla...")
        table_data = self.detect_table_structure(cleaned_lines)
        
        # Paso 4: Validar cálculos
        print("🔢 Validando cálculos...")
        validation_results = self.validate_calculations(table_data)
        
        # Compilar resultados completos
        results = {
            'file_path': image_path,
            'raw_text': raw_text,
            'cleaned_lines': cleaned_lines,
            'table_structure': table_data,
            'validation': validation_results,
            'timestamp': str(np.datetime64('now'))
        }
        
        # Mostrar resumen
        self.print_results_summary(results)
        
        # Guardar resultados si se solicita
        if save_results:
            self.save_results_to_file(results)
        
        return results
    
    def print_results_summary(self, results: Dict):
        """Imprime un resumen de los resultados"""
        print("\n📋 RESUMEN DE RESULTADOS")
        print("=" * 50)
        
        validation = results.get('validation', {})
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        if validation.get('summary'):
            print(f"Estado: {validation['summary']['status']}")
            print(f"Detalle: {validation['summary']['message']}")
            
        if validation.get('calculated_sum') is not None:
            print(f"\n📊 Detalles del cálculo:")
            print(f"   Números encontrados: {validation.get('numbers_used', [])}")
            print(f"   Suma calculada: {validation.get('calculated_sum', 0)}")
            print(f"   Total reportado: {validation.get('reported_total', 0)}")
            print(f"   Diferencia: {validation.get('difference', 0)}")
        
        if validation.get('errors'):
            print(f"\n⚠️ Errores encontrados:")
            for error in validation['errors']:
                print(f"   - {error}")
    
    def save_results_to_file(self, results: Dict):
        """Guarda los resultados en un archivo de texto"""
        try:
            filename = f"resultado_{os.path.basename(results['file_path'])}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("REPORTE DE VALIDACIÓN DE CÁLCULOS\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"Archivo procesado: {results['file_path']}\n")
                f.write(f"Timestamp: {results['timestamp']}\n\n")
                
                validation = results.get('validation', {})
                if validation.get('summary'):
                    f.write(f"RESULTADO: {validation['summary']['status']}\n")
                    f.write(f"DETALLE: {validation['summary']['message']}\n\n")
                
                f.write("TEXTO EXTRAÍDO:\n")
                f.write("-" * 20 + "\n")
                f.write(results.get('raw_text', 'No disponible'))
                
            print(f"💾 Resultados guardados en: {filepath}")
            
        except Exception as e:
            print(f"⚠️ Error guardando resultados: {e}")

def main():
    """Función principal de ejemplo"""
    validator = ReportValidator()
    
    # Ejemplo de uso
    print("🚀 VALIDADOR DE REPORTES CON VISION API")
    print("=" * 50)
    print("Para usar este validador:")
    print("1. Coloca tus imágenes en la carpeta 'images'")
    print("2. Ejecuta: validator.process_report_image('ruta/a/imagen.jpg')")
    print("3. Los resultados se mostrarán en pantalla y se guardarán")
    
    # Buscar imágenes en la carpeta images
    if os.path.exists(IMAGES_DIR):
        image_files = [f for f in os.listdir(IMAGES_DIR) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        if image_files:
            print(f"\n📁 Imágenes encontradas en {IMAGES_DIR}:")
            for i, img in enumerate(image_files, 1):
                print(f"   {i}. {img}")
            
            # Procesar la primera imagen como ejemplo
            if len(image_files) > 0:
                sample_image = os.path.join(IMAGES_DIR, image_files[0])
                print(f"\n🔍 Procesando imagen de muestra: {image_files[0]}")
                validator.process_report_image(sample_image)
        else:
            print(f"\n📁 No se encontraron imágenes en {IMAGES_DIR}")
            print("   Coloca archivos .jpg, .png, etc. en esa carpeta")

if __name__ == "__main__":
    main()