# scripts/test_financial.py
from financial_validator import FinancialReportValidator
import os
from config import IMAGES_DIR

validator = FinancialReportValidator()
image_path = os.path.join(IMAGES_DIR, "imagen3.png")  # Tu imagen
result = validator.process_financial_report(image_path)