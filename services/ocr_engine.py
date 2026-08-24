import fitz  # PyMuPDF
import pytesseract
from PIL import Image

class OCREngine:
    def extract_text(self, file_path):
        """Extract text from PDF or Image."""
        if file_path.lower().endswith('.pdf'):
            return self._extract_from_pdf(file_path)
        else:
            return self._extract_from_image(file_path)

    def _extract_from_pdf(self, file_path):
        doc = fitz.open(file_path)
        text = ""
        has_text_layer = False
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                has_text_layer = True
                text += page_text + "\n"
        doc.close()
        
        # If no text layer, treat as scanned image
        if not has_text_layer:
            return self._extract_from_image(file_path)
        return text

    def _extract_from_image(self, file_path):
        """Use Tesseract for Japanese OCR."""
        try:
            image = Image.open(file_path)
            # --psm 6: Assume a single uniform block of text
            # -l jpn: Japanese language model
            custom_config = r'--oem 3 --psm 6 -l jpn'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text
        except Exception as e:
            print(f"OCR Error on {file_path}: {e}")
            return ""