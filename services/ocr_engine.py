import fitz  # PyMuPDF
import pytesseract
from PIL import Image


class OCREngine:
    """Handles text extraction from both text-layer PDFs and scanned images."""

    def extract_text(self, file_path: str) -> str:
        if file_path.lower().endswith(".pdf"):
            return self._extract_from_pdf(file_path)
        return self._extract_from_image(file_path)

    def _extract_from_pdf(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        text_parts = []
        has_text_layer = False

        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                has_text_layer = True
                text_parts.append(page_text)

        doc.close()

        if not has_text_layer:
            # Scanned PDF → treat as image
            return self._extract_from_image(file_path)

        return "\n".join(text_parts)

    def _extract_from_image(self, file_path: str) -> str:
        try:
            image = Image.open(file_path)
            custom_config = r"--oem 3 --psm 6 -l jpn"
            return pytesseract.image_to_string(image, config=custom_config)
        except Exception as e:
            print(f"  ⚠️  OCR failed on {file_path}: {e}")
            return ""