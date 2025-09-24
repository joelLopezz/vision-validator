# scripts/financial_validator.py
"""
Validador Mejorado para Reportes Financieros
Especializado en detectar números monetarios y totales
"""

import sys
import os
import re
from typing import List, Dict, Tuple, Optional
from google.cloud import vision
from config import PROJECT_ID, IMAGES_DIR, RESULTS_DIR

class FinancialReportValidator:
    def __init__(self):
        """Inicializa el validador financiero"""
        self.client = vision.ImageAnnotatorClient()
        self.project_id = PROJECT_ID
        
    def extract_text_from_image(self, image_path: str) -> str:
        """Extrae texto usando Vision API"""
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f'Error de Vision API: {response.error.message}')
            
            texts = response.text_annotations
            if texts:
                return texts[0].description
            else:
                return ""
                
        except Exception as e:
            print(f"❌ Error extrayendo texto: {e}")
            return ""
    
    def extract_financial_amounts(self, text: str) -> List[Dict]:
        """
        Extrae cantidades monetarias del texto
        Maneja formatos como $120,000, 350,000, o $8,400
        """
        financial_data = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Buscar cantidades monetarias con múltiples patrones
            amounts = []
            
            # Patrón 1: Con símbolo $ (ej: $120,000)
            money_with_dollar = re.findall(r'\$[\d,]+\.?\d*', line)
            for match in money_with_dollar:
                clean_amount = re.sub(r'[$,]', '', match)
                try:
                    amount = float(clean_amount)
                    if amount > 0:
                        amounts.append(amount)
                except ValueError:
                    continue
            
            # Patrón 2: Solo números con comas (ej: 350,000) - SOLO si parece contexto financiero
            if not amounts:  # Solo si no encontramos números con $
                # Buscar números grandes con comas
                plain_numbers = re.findall(r'\b[\d,]+\.?\d*\b', line)
                for match in plain_numbers:
                    # Verificar si es un número financiero significativo
                    clean_amount = re.sub(r'[,]', '', match)
                    try:
                        amount = float(clean_amount)
                        # Solo incluir si es >= 1000 (números financieros significativos)
                        if amount >= 1000:
                            amounts.append(amount)
                    except ValueError:
                        continue
            
            # ELIMINAR DUPLICADOS - tomar solo valores únicos
            amounts = list(set(amounts))
            
            # Si encontramos cantidades, guardar información de la línea
            if amounts:
                # Detectar si es línea de total (buscar "total" en línea anterior o actual)
                is_total_line = False
                
                # Verificar línea actual
                if any(keyword in line.lower() for keyword in ['total', 'suma', 'subtotal']):
                    is_total_line = True
                
                # Verificar línea anterior si existe
                elif line_num > 0:
                    prev_line = lines[line_num-1].lower()
                    if any(keyword in prev_line for keyword in ['total', 'suma', 'subtotal']):
                        is_total_line = True
                
                financial_data.append({
                    'line_number': line_num,
                    'text': line,
                    'amounts': amounts,
                    'is_total': is_total_line,
                    'max_amount': max(amounts) if amounts else 0
                })
        
        return financial_data
    
    def identify_data_rows_and_total(self, financial_data: List[Dict]) -> Dict:
        """
        Separa las filas de datos del total con mejor lógica
        """
        data_rows = []
        total_rows = []
        
        # Buscar el número más grande (probable total)
        if financial_data:
            largest_amount = max(item['max_amount'] for item in financial_data)
            largest_item = None
            
            for item in financial_data:
                if item['max_amount'] == largest_amount:
                    largest_item = item
                    break
            
            # Verificar si el número más grande podría ser el total
            if largest_item:
                other_amounts = []
                for other_item in financial_data:
                    if other_item != largest_item:
                        other_amounts.extend(other_item['amounts'])
                
                # Calcular suma de otros números
                calculated_sum = sum(other_amounts)
                difference = abs(calculated_sum - largest_amount)
                
                print(f"🔍 Análisis de total:")
                print(f"   Número más grande: ${largest_amount:,.2f}")
                print(f"   Suma de otros números: ${calculated_sum:,.2f}")
                print(f"   Diferencia: ${difference:,.2f}")
                
                # Si la diferencia es significativa, reportar error
                # Si la diferencia es pequeña, es el total correcto
                total_rows.append({
                    **largest_item,
                    'is_total': True,
                    'detected_as_total': True,
                    'calculation_matches': difference <= 10
                })
                
                # Los demás son filas de datos
                for item in financial_data:
                    if item != largest_item:
                        data_rows.append(item)
            
            else:
                # Fallback: todos son datos si no encontramos patrón claro
                data_rows = financial_data
        
        return {
            'data_rows': data_rows,
            'total_rows': total_rows
        }
    
    def validate_financial_calculations(self, data_rows: List[Dict], total_rows: List[Dict]) -> Dict:
        """
        Valida los cálculos financieros
        """
        results = {
            'valid': False,
            'data_amounts': [],
            'calculated_sum': 0,
            'reported_total': 0,
            'difference': 0,
            'details': {},
            'summary': {}
        }
        
        # Extraer cantidades de las filas de datos
        data_amounts = []
        for row in data_rows:
            if row['amounts']:
                amount = max(row['amounts'])  # Tomar el número más grande de cada línea
                data_amounts.append(amount)
                print(f"   {row['text'][:50]}... → ${amount:,.2f}")
        
        if not data_amounts:
            results['summary'] = {
                'status': '❌ ERROR',
                'message': 'No se encontraron cantidades de datos para sumar'
            }
            return results
        
        # Calcular suma
        calculated_sum = sum(data_amounts)
        print(f"\n💰 Suma calculada: ${calculated_sum:,.2f}")
        
        # Buscar total reportado
        reported_total = 0
        if total_rows:
            total_amounts = []
            for row in total_rows:
                total_amounts.extend(row['amounts'])
            if total_amounts:
                reported_total = max(total_amounts)
                print(f"📊 Total reportado: ${reported_total:,.2f}")
        
        # Validar
        difference = abs(calculated_sum - reported_total)
        is_valid = difference <= 10  # Tolerancia de $10
        
        # Determinar el mensaje apropiado
        if difference == 0:
            status_msg = '✅ CÁLCULO CORRECTO'
            detail_msg = 'La suma coincide exactamente con el total reportado'
        elif difference <= 10:
            status_msg = '✅ CÁLCULO CORRECTO (diferencia mínima)'
            detail_msg = f'Diferencia menor a $10 (${difference:.2f}) - probablemente redondeo'
        else:
            status_msg = '❌ ERROR EN CÁLCULO DETECTADO'
            detail_msg = f'La suma no coincide con el total. Diferencia: ${difference:,.2f}'
        
        results.update({
            'valid': is_valid,
            'data_amounts': data_amounts,
            'calculated_sum': calculated_sum,
            'reported_total': reported_total,
            'difference': difference,
            'details': {
                'data_rows_count': len(data_rows),
                'total_rows_count': len(total_rows),
                'individual_amounts': data_amounts
            },
            'summary': {
                'status': status_msg,
                'message': detail_msg
            }
        })
        
        return results
    
    def process_financial_report(self, image_path: str) -> Dict:
        """
        Procesa un reporte financiero completo
        """
        print(f"\n💰 Procesando reporte financiero: {os.path.basename(image_path)}")
        print("=" * 60)
        
        # Extraer texto
        print("🔍 Extrayendo texto con Vision API...")
        raw_text = self.extract_text_from_image(image_path)
        
        if not raw_text:
            return {'error': 'No se pudo extraer texto de la imagen'}
        
        print("🔍 Texto extraído:")
        print("-" * 30)
        print(raw_text)
        print("-" * 30)
        
        # Extraer cantidades monetarias
        print("\n💵 Extrayendo cantidades monetarias...")
        financial_data = self.extract_financial_amounts(raw_text)
        
        if not financial_data:
            return {'error': 'No se encontraron cantidades monetarias'}
        
        print("Cantidades detectadas:")
        for item in financial_data:
            amounts_str = ", ".join([f"${amt:,.2f}" for amt in item['amounts']])
            total_flag = " (TOTAL)" if item['is_total'] else ""
            print(f"  {item['text'][:40]}... → {amounts_str}{total_flag}")
        
        # Separar datos y totales
        print("\n📊 Identificando estructura...")
        structure = self.identify_data_rows_and_total(financial_data)
        
        print(f"Filas de datos: {len(structure['data_rows'])}")
        print(f"Filas de total: {len(structure['total_rows'])}")
        
        # Validar cálculos
        print("\n🔢 Validando cálculos...")
        print("Sumando:")
        validation = self.validate_financial_calculations(
            structure['data_rows'], 
            structure['total_rows']
        )
        
        # Mostrar resultados
        print(f"\n📋 RESULTADO: {validation['summary']['status']}")
        print(f"💬 {validation['summary']['message']}")
        if validation['difference'] > 0:
            print(f"🔍 Diferencia: ${validation['difference']:,.2f}")
        
        # Compilar resultados
        results = {
            'file_path': image_path,
            'raw_text': raw_text,
            'financial_data': financial_data,
            'structure': structure,
            'validation': validation
        }
        
        # Guardar resultados
        self.save_results(results)
        
        return results
    
    def save_results(self, results: Dict):
        """Guarda resultados en archivo"""
        try:
            filename = f"reporte_financiero_{os.path.basename(results['file_path'])}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("VALIDACIÓN DE REPORTE FINANCIERO\n")
                f.write("=" * 40 + "\n\n")
                
                validation = results['validation']
                f.write(f"RESULTADO: {validation['summary']['status']}\n")
                f.write(f"DETALLE: {validation['summary']['message']}\n")
                f.write(f"DIFERENCIA: ${validation['difference']:,.2f}\n\n")
                
                f.write("CANTIDADES SUMADAS:\n")
                for i, amount in enumerate(validation['data_amounts'], 1):
                    f.write(f"{i}. ${amount:,.2f}\n")
                
                f.write(f"\nSUMA CALCULADA: ${validation['calculated_sum']:,.2f}\n")
                f.write(f"TOTAL REPORTADO: ${validation['reported_total']:,.2f}\n")
                
                f.write(f"\n\nTEXTO ORIGINAL:\n{results['raw_text']}")
            
            print(f"💾 Resultados guardados en: {filepath}")
            
        except Exception as e:
            print(f"⚠️ Error guardando: {e}")

def main():
    """Función principal"""
    validator = FinancialReportValidator()
    
    # Buscar imágenes
    if os.path.exists(IMAGES_DIR):
        image_files = [f for f in os.listdir(IMAGES_DIR) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        if image_files:
            print("💰 VALIDADOR DE REPORTES FINANCIEROS")
            print("=" * 50)
            print(f"📁 Imágenes encontradas:")
            for i, img in enumerate(image_files, 1):
                print(f"   {i}. {img}")
            
            # Procesar primera imagen
            sample_image = os.path.join(IMAGES_DIR, image_files[0])
            validator.process_financial_report(sample_image)
        else:
            print("📁 No se encontraron imágenes en la carpeta images/")

if __name__ == "__main__":
    main()