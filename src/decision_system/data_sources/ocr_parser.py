"""OCR-based parser for scanned PDFs and images.

Uses tesserocr (C extension, no tesseract binary required) and PyMuPDF
for rendering PDF pages to images. Falls back gracefully if dependencies
are not installed.

This module is part of the local-first OCR integration for v1.25.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .models import DataSourceChunk, ParseResult
from .parser import BaseParser

# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

_HAS_TESSEROCR: bool = False
_HAS_PDF_RENDER: bool = False

try:
    import tesserocr  # noqa: F401

    _HAS_TESSEROCR = True
except ImportError:
    pass

try:
    import fitz  # PyMuPDF  # noqa: F401

    _HAS_PDF_RENDER = True
except ImportError:
    pass


def is_ocr_available() -> bool:
    """Return True if tesserocr is available and a tessdata path can be found."""
    if not _HAS_TESSEROCR:
        return False
    try:
        import tesserocr

        # Try to find tessdata
        tessdata = os.environ.get("TESSDATA_PREFIX") or os.environ.get("TESSDATA")
        if not tessdata:
            # Check well-known paths
            for p in [
                "/usr/share/tesseract-ocr/5/tessdata",
                "/usr/share/tesseract-ocr/4.00/tessdata",
                "/usr/share/tesseract-ocr/tessdata",
                "/usr/local/share/tessdata",
                os.path.expanduser("~/.local/share/tessdata"),
            ]:
                if os.path.isdir(p) and any(f.endswith(".traineddata") for f in os.listdir(p)):
                    tessdata = p
                    break
        if not tessdata:
            return False
        # Quick validation
        import tesserocr as tr
        api = tr.PyTessBaseAPI()
        api.End()
        return True
    except Exception:
        return False


def _get_tessdata_path() -> str | None:
    """Find a valid tessdata directory."""
    tessdata = os.environ.get("TESSDATA_PREFIX") or os.environ.get("TESSDATA")
    if tessdata and os.path.isdir(tessdata):
        return tessdata
    for p in [
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/usr/local/share/tessdata",
        os.path.expanduser("~/.local/share/tessdata"),
    ]:
        if os.path.isdir(p) and any(f.endswith(".traineddata") for f in os.listdir(p)):
            return p
    return None


# ---------------------------------------------------------------------------
# Image OCR parser
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


class ImageOcrParser(BaseParser):
    """Parse images using OCR (tesserocr)."""

    name = "image_ocr"
    version = "tesserocr"
    supported_extensions = list(SUPPORTED_IMAGE_EXTENSIONS)
    supported_mime_types = [
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/bmp",
    ]

    def parse(
        self,
        path: Path,
        source_id: str,
        workspace_id: str,
    ) -> ParseResult:
        if not _HAS_TESSEROCR:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[
                    "OCR parser requires tesserocr. Install with: "
                    "pip install tesserocr  # or use [ocr] extras"
                ],
                parser_name=self.name,
            )

        tessdata = _get_tessdata_path()
        if not tessdata:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[
                    "OCR tessdata not found. Install Tesseract language data "
                    "(e.g., /usr/share/tesseract-ocr/5/tessdata/eng.traineddata) "
                    "or set TESSDATA_PREFIX."
                ],
                parser_name=self.name,
            )

        warnings: list[str] = []
        from PIL import Image

        try:
            img = Image.open(path)
        except Exception as e:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[f"Failed to open image: {e}"],
                parser_name=self.name,
            )

        try:
            import tesserocr as tr

            old_prefix = os.environ.get("TESSDATA_PREFIX")
            os.environ["TESSDATA_PREFIX"] = tessdata
            api = tr.PyTessBaseAPI()
            api.SetImage(img)
            text = api.GetUTF8Text().strip()
            api.End()
            if old_prefix is None:
                os.environ.pop("TESSDATA_PREFIX", None)
            else:
                os.environ["TESSDATA_PREFIX"] = old_prefix
        except Exception as e:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[f"OCR processing failed: {e}"],
                parser_name=self.name,
            )

        if not text:
            warnings.append("OCR produced no text from this image.")

        chunks = self.chunk(
            text,
            source_id,
            workspace_id,
            source_metadata={"source_name": path.name, "ocr": True},
        )

        return ParseResult(
            source_id=source_id,
            workspace_id=workspace_id,
            text=text,
            pages=[{"page_number": 1, "text": text, "char_count": len(text)}],
            metadata={"source_type": "image", "ocr": True, "format": path.suffix},
            warnings=warnings,
            parser_name=self.name,
            parser_version="tesserocr",
            chunks=chunks,
        )


# ---------------------------------------------------------------------------
# Scanned PDF parser (falls back to OCR when pypdf yields no text)
# ---------------------------------------------------------------------------

class ScannedPdfParser(BaseParser):
    """Parse scanned/image PDFs by rendering pages and running OCR.

    This parser should be tried when the standard PdfParser returns
    little or no extractable text. It requires tesserocr and PyMuPDF.
    """

    name = "scanned_pdf_ocr"
    version = "tesserocr+fitz"
    supported_extensions = [".pdf"]
    supported_mime_types = ["application/pdf"]

    def parse(
        self,
        path: Path,
        source_id: str,
        workspace_id: str,
    ) -> ParseResult:
        if not _HAS_TESSEROCR:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[
                    "Scanned PDF OCR requires tesserocr. Install with: "
                    "pip install tesserocr"
                ],
                parser_name=self.name,
            )
        if not _HAS_PDF_RENDER:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[
                    "Scanned PDF OCR requires PyMuPDF. Install with: "
                    "pip install PyMuPDF"
                ],
                parser_name=self.name,
            )

        tessdata = _get_tessdata_path()
        if not tessdata:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[
                    "OCR tessdata not found. Install Tesseract language data "
                    "or set TESSDATA_PREFIX."
                ],
                parser_name=self.name,
            )

        try:
            import fitz
        except ImportError as e:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[f"PyMuPDF import failed: {e}"],
                parser_name=self.name,
            )

        try:
            pdf = fitz.open(path)
        except Exception as e:
            return ParseResult(
                source_id=source_id,
                workspace_id=workspace_id,
                warnings=[f"Failed to open PDF with PyMuPDF: {e}"],
                parser_name=self.name,
            )

        import tesserocr as tr
        from PIL import Image

        warnings: list[str] = []
        pages_parsed: list[dict[str, Any]] = []
        full_text_parts: list[str] = []
        all_chunks: list[DataSourceChunk] = []
        page_count = len(pdf)
        ocr_errors = 0

        for page_num in range(page_count):
            page = pdf[page_num]
            try:
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(img_data)
                    tmp_path = tmp.name
                page_img = Image.open(tmp_path)
                os.unlink(tmp_path)
            except Exception as e:
                warnings.append(f"Page {page_num + 1} render failed: {e}")
                ocr_errors += 1
                continue

            try:
                old_prefix = os.environ.get("TESSDATA_PREFIX")
                os.environ["TESSDATA_PREFIX"] = tessdata
                api = tr.PyTessBaseAPI()
                api.SetImage(page_img)
                page_text = api.GetUTF8Text().strip()
                api.End()
                if old_prefix is None:
                    os.environ.pop("TESSDATA_PREFIX", None)
                else:
                    os.environ["TESSDATA_PREFIX"] = old_prefix
            except Exception as e:
                warnings.append(f"Page {page_num + 1} OCR failed: {e}")
                ocr_errors += 1
                continue

            if not page_text:
                warnings.append(f"Page {page_num + 1} OCR produced no text")
                continue

            pages_parsed.append({
                "page_number": page_num + 1,
                "text": page_text,
                "char_count": len(page_text),
            })
            full_text_parts.append(page_text)
            chunks = self.chunk(
                page_text,
                source_id,
                workspace_id,
                source_metadata={"source_name": path.name, "ocr": True},
                page_number=page_num + 1,
            )
            all_chunks.extend(chunks)

        pdf.close()
        full_text = "\n\n".join(full_text_parts)
        total_ocr_pages = page_count - ocr_errors

        if not full_text.strip():
            warnings.append(
                "OCR produced no text from this scanned PDF. "
                "The PDF may be encrypted, damaged, or contain only images "
                "without recognizable text."
            )

        return ParseResult(
            source_id=source_id,
            workspace_id=workspace_id,
            text=full_text,
            pages=pages_parsed,
            metadata={
                "page_count": page_count,
                "ocr_pages": total_ocr_pages,
                "ocr_errors": ocr_errors,
                "ocr": True,
                "parser": "scanned_pdf_ocr",
            },
            warnings=warnings,
            parser_name=self.name,
            parser_version="tesserocr+fitz",
            chunks=all_chunks,
        )
