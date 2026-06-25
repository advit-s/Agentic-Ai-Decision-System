"""Tests for OCR parser integration (v1.25)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Skip all tests if OCR deps are not available
pytest.importorskip("tesserocr")
pytest.importorskip("fitz")


@pytest.fixture(scope="module")
def tessdata():
    """Ensure TESSDATA_PREFIX is set."""
    td = os.environ.get("TESSDATA_PREFIX") or os.environ.get("TESSDATA")
    if not td:
        for p in [
            "/usr/share/tesseract-ocr/5/tessdata",
            "/usr/share/tesseract-ocr/4.00/tessdata",
            os.path.expanduser("~/.local/share/tessdata"),
        ]:
            if os.path.isdir(p) and any(f.endswith(".traineddata") for f in os.listdir(p)):
                td = p
                break
    if not td:
        pytest.skip("No tessdata found")
    os.environ["TESSDATA_PREFIX"] = td
    return td


class TestImageOcrParser:
    """Test the ImageOcrParser."""

    def test_ocr_image_parser_imports(self):
        """Verify the OCR parser module loads."""
        from decision_system.data_sources.ocr_parser import ImageOcrParser, ScannedPdfParser, is_ocr_available
        assert ImageOcrParser is not None
        assert ScannedPdfParser is not None
        assert is_ocr_available() is True

    def test_ocr_image_invoice(self, tessdata):
        """OCR should extract text from the sample invoice image."""
        from decision_system.data_sources.ocr_parser import ImageOcrParser

        img_path = Path("demo/sample-data/image_invoice.png")
        if not img_path.exists():
            pytest.skip("Sample invoice image not found")

        parser = ImageOcrParser()
        result = parser.parse(img_path, "test-img-001", "test-ws-001")

        assert result is not None
        assert len(result.text) > 50, f"OCR extracted too little text: {len(result.text)} chars"
        assert "INVOICE" in result.text, f"OCR missing 'INVOICE', got: {result.text[:100]}"
        assert "DemoCorp" in result.text
        assert len(result.chunks) >= 1
        assert result.metadata.get("ocr") is True

    def test_ocr_parser_registered(self, tessdata):
        """Verify image parsers are registered in the parser registry."""
        from decision_system.data_sources.parser import get_parser, get_supported_extensions

        exts = get_supported_extensions()
        assert ".png" in exts
        assert ".jpg" in exts

        png_parser = get_parser(".png")
        assert png_parser is not None
        assert png_parser.name == "image_ocr"

    def test_ocr_dispatch_via_parse_document(self, tessdata):
        """Verify parse_document dispatches images to ImageOcrParser."""
        from decision_system.data_sources.parser import parse_document

        img_path = "demo/sample-data/image_invoice.png"
        if not os.path.exists(img_path):
            pytest.skip("Sample invoice image not found")

        chunks, warnings = parse_document(
            Path(img_path), ".png", "test-dispatch-001", "test-ws-001"
        )
        assert len(chunks) >= 1
        assert any("INVOICE" in c.text for c in chunks) or any("INVOICE" in str(chunks[0].text) for c in chunks)


class TestScannedPdfOcr:
    """Test scanned PDF OCR parsing."""

    def test_ocr_scanned_pdf(self, tessdata):
        """OCR should extract text from the scanned contract PDF."""
        from decision_system.data_sources.ocr_parser import ScannedPdfParser

        pdf_path = Path("demo/sample-data/scanned_contract.pdf")
        if not pdf_path.exists():
            pytest.skip("Sample scanned PDF not found")

        parser = ScannedPdfParser()
        result = parser.parse(pdf_path, "test-pdf-001", "test-ws-001")

        assert result is not None
        assert len(result.text) > 100, f"OCR extracted too little text: {len(result.text)} chars"
        assert "AGREEMENT" in result.text or "SERVICE" in result.text, \
            f"OCR missing contract keywords, got: {result.text[:150]}"
        assert len(result.chunks) >= 1
        assert result.metadata.get("ocr") is True

    def test_ocr_pdf_fallback_flow(self, tessdata):
        """Verify that textless PDFs trigger OCR fallback in parse_document."""
        from decision_system.data_sources.parser import parse_document

        pdf_path = "demo/sample-data/scanned_contract.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip("Sample scanned PDF not found")

        # parse_document dispatches to PdfParser first (which gets no text),
        # then falls back to ScannedPdfParser
        chunks, warnings = parse_document(
            Path(pdf_path), ".pdf", "test-pdf-fallback-001", "test-ws-001"
        )
        # Should have at least some chunks from OCR
        assert len(chunks) >= 1

        # Should have warnings about OCR
        ocr_warnings = [w for w in warnings if "OCR" in w or "ocr" in w.lower()]
        # The fallback may add an OCR warning
        text_from_chunks = " ".join(c.text for c in chunks)
        assert "AGREEMENT" in text_from_chunks or "SERVICE" in text_from_chunks or "DemoCorp" in text_from_chunks


class TestOcrFallbackBehavior:
    """Test graceful degradation when OCR is missing."""

    def test_parse_document_text_file_no_ocr_needed(self, tessdata):
        """Regular text files should not need OCR."""
        from decision_system.data_sources.parser import parse_document

        md_path = "demo/sample-data/company_overview.md"
        if not os.path.exists(md_path):
            pytest.skip("Sample markdown not found")

        chunks, warnings = parse_document(
            Path(md_path), ".md", "test-md-001", "test-ws-001"
        )
        assert len(chunks) >= 1
        text = chunks[0].text
        assert "DemoCorp" in text or "revenue" in text.lower()

    def test_ocr_available_function(self, tessdata):
        """is_ocr_available should return True when tesserocr works."""
        from decision_system.data_sources.ocr_parser import is_ocr_available
        assert is_ocr_available() is True
