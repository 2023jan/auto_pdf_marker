"""
PDF handling utilities for PyMuPDF operations.
"""
import fitz  # PyMuPDF
import io
import base64
from typing import List, Dict, Tuple, Optional


def load_pdf(file_path: str) -> fitz.Document:
    """Load a PDF document from file path or bytes."""
    return fitz.open(file_path)


def render_page_to_image(doc: fitz.Document, page_num: int, dpi: int = 300) -> bytes:
    """
    Render a PDF page to a PNG image.

    Args:
        doc: PyMuPDF document
        page_num: 0-based page index
        dpi: resolution for rendering

    Returns:
        PNG image bytes
    """
    page = doc.load_page(page_num)
    # Calculate zoom factor based on DPI (default PDF DPI is 72)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes(output="png")


def write_toc(
    doc: fitz.Document,
    toc: List[Dict[str, int]],
    page_offset: int = 0,
    output_path: str = None
) -> Optional[bytes]:
    """
    Write table of contents to PDF and save or return bytes.

    Args:
        doc: PyMuPDF document (will be modified)
        toc: List of entries with 'title', 'page', 'level'
        page_offset: Offset to add to extracted page numbers
        output_path: If provided, save to file; otherwise return bytes

    Returns:
        PDF bytes if output_path is None, else None
    """
    # Convert toc to PyMuPDF format: list of [level, title, page, ...]
    # PyMuPDF expects: [level, title, page, ...] where page is 1-based
    fitz_toc = []
    for entry in toc:
        level = entry.get('level', 1)
        title = entry.get('title', '')
        page = entry.get('page', 1) + page_offset
        # Ensure page is at least 1 and within document bounds
        if page < 1:
            page = 1
        if page > doc.page_count:
            page = doc.page_count
        fitz_toc.append([level, title, page])

    # Set the table of contents
    doc.set_toc(fitz_toc)

    if output_path:
        doc.save(output_path, garbage=4, deflate=True)
        return None
    else:
        # Return PDF bytes
        return doc.write()


def get_page_count(doc: fitz.Document) -> int:
    """Return total number of pages."""
    return doc.page_count