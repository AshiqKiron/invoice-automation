import pymupdf
import pytesseract
from PIL import Image
import io


class OCREngine:
    """Handles text extraction from both text-layer PDFs and scanned images."""

    def extract_text(self, file_path: str) -> str:
        if file_path.lower().endswith(".pdf"):
            return self._extract_from_pdf(file_path)
        return self._extract_from_image_file(file_path)

    def _extract_from_pdf(self, file_path: str) -> str:
        doc = pymupdf.open(file_path)
        text_parts = []
        has_text_layer = False

        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                has_text_layer = True
                text_parts.append(page_text)

        if has_text_layer:
            doc.close()
            return "\n".join(text_parts)

        # No text layer → scanned PDF → render pages to images and OCR
        ocr_parts = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            custom_config = r"--oem 3 --psm 6 -l jpn"
            page_text = pytesseract.image_to_string(image, config=custom_config)
            ocr_parts.append(page_text)

        doc.close()
        return "\n".join(ocr_parts)

    def _extract_from_image_file(self, file_path: str) -> str:
        """OCR for JPG/PNG/image files."""
        try:
            image = Image.open(file_path)
            custom_config = r"--oem 3 --psm 6 -l jpn"
            return pytesseract.image_to_string(image, config=custom_config)
        except Exception as e:
            print(f"  ⚠️  OCR failed on {file_path}: {e}")
            return ""
