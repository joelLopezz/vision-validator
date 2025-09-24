# scripts/batch_validator.py
"""
Validador por Lotes - Procesa todas las imágenes en la carpeta images/
Genera reporte consolidado para presentación
"""

import os
import glob
from datetime import datetime
from financial_validator import FinancialReportValidator
from config import IMAGES_DIR, RESULTS_DIR

class BatchValidator:
    def __init__(self):
        self.validator = FinancialReportValidator()
        self.results = []
        
    def find_all_images(self):
        """Encuentra todas las imágenes en la carpeta images/"""
        if not os.path.exists(IMAGES_DIR):
            print(f"❌ Carpeta no encontrada: {IMAGES_DIR}")
            return []
        
        # Buscar archivos de imagen
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
        image_files = []
        
        for extension in image_extensions:
            pattern = os.path.join(IMAGES_DIR, extension)
            image_files.extend(glob.glob(pattern))
            # También buscar en mayúsculas
            pattern_upper = os.path.join(IMAGES_DIR, extension.upper())
            image_files.extend(glob.glob(pattern_upper))
        
        return sorted(image_files)
    
    def process_all_images(self):
        """Procesa todas las imágenes encontradas"""
        image_files = self.find_all_images()
        
        if not image_files:
            print("❌ No se encontraron imágenes en la carpeta images/")
            return
        
        print("🚀 VALIDADOR POR LOTES - REPORTES FINANCIEROS")
        print("=" * 60)
        print(f"📁 Carpeta: {IMAGES_DIR}")
        print(f"📸 Imágenes encontradas: {len(image_files)}")
        print("-" * 60)
        
        # Procesar cada imagen
        for i, image_path in enumerate(image_files, 1):
            filename = os.path.basename(image_path)
            print(f"\n[{i}/{len(image_files)}] 📋 Procesando: {filename}")
            
            try:
                # Procesar imagen (sin guardar resultados individuales para limpiar output)
                result = self.validator.process_financial_report(image_path)
                
                # Guardar resultado resumido
                summary = self.extract_summary(result, filename)
                self.results.append(summary)
                
                print(f"    ✅ Procesado: {summary['status']}")
                
            except Exception as e:
                error_summary = {
                    'filename': filename,
                    'status': '❌ ERROR',
                    'message': f'Error procesando imagen: {str(e)}',
                    'calculated_sum': 0,
                    'reported_total': 0,
                    'difference': 0,
                    'valid': False
                }
                self.results.append(error_summary)
                print(f"    ❌ Error: {str(e)}")
        
        # Generar reporte consolidado
        self.generate_consolidated_report()
    
    def extract_summary(self, result, filename):
        """Extrae resumen de un resultado individual"""
        if 'error' in result:
            return {
                'filename': filename,
                'status': '❌ ERROR',
                'message': result['error'],
                'calculated_sum': 0,
                'reported_total': 0,
                'difference': 0,
                'valid': False
            }
        
        validation = result.get('validation', {})
        summary_info = validation.get('summary', {})
        
        return {
            'filename': filename,
            'status': summary_info.get('status', '⚠️ DESCONOCIDO'),
            'message': summary_info.get('message', 'No disponible'),
            'calculated_sum': validation.get('calculated_sum', 0),
            'reported_total': validation.get('reported_total', 0),
            'difference': validation.get('difference', 0),
            'valid': validation.get('valid', False),
            'data_amounts': validation.get('data_amounts', [])
        }
    
    def generate_consolidated_report(self):
        """Genera reporte consolidado de todos los resultados"""
        print("\n" + "=" * 80)
        print("📊 REPORTE CONSOLIDADO - VALIDACIÓN DE REPORTES FINANCIEROS")
        print("=" * 80)
        
        # Estadísticas generales
        total_images = len(self.results)
        valid_reports = sum(1 for r in self.results if r['valid'])
        invalid_reports = sum(1 for r in self.results if not r['valid'] and '❌ ERROR' not in r['status'])
        error_reports = sum(1 for r in self.results if '❌ ERROR' in r['status'])
        
        print(f"📈 ESTADÍSTICAS GENERALES:")
        print(f"   Total de reportes procesados: {total_images}")
        print(f"   ✅ Reportes con cálculos correctos: {valid_reports}")
        print(f"   ❌ Reportes con errores de cálculo: {invalid_reports}")
        print(f"   🔧 Errores de procesamiento: {error_reports}")
        print(f"   📊 Tasa de éxito: {(valid_reports/total_images)*100:.1f}%")
        
        # Detalles por reporte
        print(f"\n📋 DETALLES POR REPORTE:")
        print("-" * 80)
        
        for i, result in enumerate(self.results, 1):
            print(f"{i:2d}. 📄 {result['filename']}")
            print(f"    Estado: {result['status']}")
            
            if result['valid'] or '❌ ERROR' not in result['status']:
                print(f"    Suma calculada: ${result['calculated_sum']:,.2f}")
                print(f"    Total reportado: ${result['reported_total']:,.2f}")
                if result['difference'] > 0:
                    print(f"    Diferencia: ${result['difference']:,.2f}")
            
            if not result['valid'] and '❌ ERROR' not in result['status']:
                print(f"    ⚠️ PROBLEMA DETECTADO: {result['message']}")
            elif '❌ ERROR' in result['status']:
                print(f"    🔧 Error técnico: {result['message']}")
            
            print()
        
        # Resumen de errores encontrados
        financial_errors = [r for r in self.results if not r['valid'] and '❌ ERROR' not in r['status']]
        if financial_errors:
            print("🔍 ANÁLISIS DE ERRORES FINANCIEROS DETECTADOS:")
            print("-" * 50)
            total_error_amount = sum(r['difference'] for r in financial_errors)
            print(f"Total en discrepancias detectadas: ${total_error_amount:,.2f}")
            
            for result in financial_errors:
                error_percentage = (result['difference'] / result['reported_total'] * 100) if result['reported_total'] > 0 else 0
                print(f"• {result['filename']}: ${result['difference']:,.2f} ({error_percentage:.1f}% error)")
        
        # Guardar reporte en archivo
        self.save_consolidated_report()
        
        print("\n" + "=" * 80)
        print("✅ PROCESO COMPLETADO")
        print("=" * 80)
    
    def save_consolidated_report(self):
        """Guarda el reporte consolidado en archivo"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_consolidado_{timestamp}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("REPORTE CONSOLIDADO - VALIDACIÓN DE REPORTES FINANCIEROS\n")
                f.write("=" * 60 + "\n")
                f.write(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de reportes: {len(self.results)}\n\n")
                
                # Estadísticas
                valid_count = sum(1 for r in self.results if r['valid'])
                f.write("ESTADÍSTICAS:\n")
                f.write(f"  Correctos: {valid_count}\n")
                f.write(f"  Con errores: {len(self.results) - valid_count}\n")
                f.write(f"  Tasa de éxito: {(valid_count/len(self.results)*100):.1f}%\n\n")
                
                # Detalles
                f.write("DETALLES POR REPORTE:\n")
                f.write("-" * 40 + "\n")
                
                for i, result in enumerate(self.results, 1):
                    f.write(f"{i}. {result['filename']}\n")
                    f.write(f"   Estado: {result['status']}\n")
                    f.write(f"   Calculado: ${result['calculated_sum']:,.2f}\n")
                    f.write(f"   Reportado: ${result['reported_total']:,.2f}\n")
                    f.write(f"   Diferencia: ${result['difference']:,.2f}\n")
                    f.write(f"   Válido: {'Sí' if result['valid'] else 'No'}\n\n")
            
            print(f"💾 Reporte guardado en: {filepath}")
            
        except Exception as e:
            print(f"⚠️ Error guardando reporte: {e}")

def main():
    """Función principal"""
    batch_validator = BatchValidator()
    batch_validator.process_all_images()

if __name__ == "__main__":
    main()