"""Local document loader for v0.1 RAG ingestion.

The loader accepts only local `.md` and `.txt` files from the configured docs
directory. It returns normalized dictionaries that preserve source metadata for
later evidence citations.
"""

from hashlib import sha1
from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt"}


def load_documents(path: Path | str) -> list[dict]:
    """Load supported local documents from a directory.

    Args:
        path: Directory containing local company or demo documents.

    Returns:
        A list of document dictionaries with stable document IDs, source path,
        source filename, and normalized text.

    v0.1 limitation:
        PDF, office documents, permissions, and connectors are not supported.
    """

    docs_dir = Path(path)
    documents: list[dict] = []

    if not docs_dir.exists():
        return documents

    files = [
        candidate
        for candidate in docs_dir.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    for file_path in sorted(files):
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        relative_path = file_path.relative_to(docs_dir).as_posix()
        # The ID is path-stable so re-indexing unchanged files preserves citation
        # prefixes even when Chroma is refreshed.
        document_id = f"doc-{sha1(relative_path.encode('utf-8')).hexdigest()[:12]}"
        documents.append(
            {
                "document_id": document_id,
                "source_path": str(file_path),
                "source_filename": file_path.name,
                "text": text,
            }
        )

    return documents
