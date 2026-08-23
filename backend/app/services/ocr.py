from pathlib import Path
from pypdf import PdfReader

async def extract(path:str)->str:
    p=Path(path)
    if p.suffix.lower()==".pdf":
        try:
            txt="\n".join((x.extract_text() or "") for x in PdfReader(path).pages)
            if txt.strip(): return txt.strip()
        except Exception: pass
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:
        return ""
