"""
HeartBeat Engine - Ingest CBA PDFs as Documents

Extract per-page text, detect articles, and generate semantic chunks
to align with the ontology-inspired document layer.

Outputs written to data/processed/reference/ as Parquet:
- cba_document_text.parquet   (document_id, page_number, text, char_count, token_estimate, article_hint, article_number)
- cba_articles.parquet        (document_id, article_number, article_title, start_page, end_page, content, char_count)
- cba_chunks.parquet          (chunk_id, document_id, section, page_start, page_end, text, token_estimate)

Run:
  python scripts/ingest_cba_documents.py
Then sync to GCS with:
  python scripts/sync_cba_to_gcs.py
Create/refresh BigQuery views with:
  bq query --project_id=heartbeat-474020 < scripts/create_cba_views.sql
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed" / "reference"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Known mapping from filenames to document IDs used in ontology
FILENAME_TO_DOCID = {
    "nhl_cba_2012.pdf": "CBA_2012",
    "nhl_mou_2020.pdf": "MOU_2020",
    "nhl_mou_2025.pdf": "MOU_2025",
}


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough token estimate; avoids hard dependency on tiktoken."""
    # Heuristic: ~4 chars per token for English legal text
    return max(1, int(len(text) / 4))


def _load_pdf_text_pages(pdf_path: Path) -> List[Tuple[int, str]]:
    """Extract (page_number, text) tuples from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required. Install with: pip install pymupdf"
        ) from e

    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc, start=1):
        try:
            text = page.get_text("text") or ""
        except Exception:
            text = ""
        pages.append((i, text))
    doc.close()
    return pages


def _detect_articles(pages: List[Tuple[int, str]]) -> List[Dict]:
    """Very simple article detector based on heading regex.

    Looks for lines like:
      - ARTICLE 50 – SALARY CAP ACCOUNTING
      - Article 13.4 – Waivers

    Returns list of dicts with article_number, article_title, start_page, end_page, content.
    """
    import re

    heading_re = re.compile(r"^(ARTICLE|Article)\s+([0-9A-Za-z\.]+)\s*[\-–—:]\s*(.+)$", re.MULTILINE)

    hits: List[Tuple[int, str, str]] = []  # (page, number, title)
    for page_no, text in pages:
        for m in heading_re.finditer(text):
            art_num = m.group(2).strip()
            title = m.group(3).strip()
            hits.append((page_no, art_num, title))

    if not hits:
        return []

    articles: List[Dict] = []
    for idx, (start_page, art_num, title) in enumerate(hits):
        end_page = pages[-1][0]
        if idx < len(hits) - 1:
            end_page = hits[idx + 1][0] - 1

        # Concatenate page texts
        content_parts = [t for p, t in pages if start_page <= p <= end_page]
        content = "\n".join(content_parts).strip()

        articles.append({
            "article_number": str(art_num),
            "article_title": title,
            "start_page": int(start_page),
            "end_page": int(end_page),
            "content": content,
            "char_count": len(content),
        })

    return articles


def _chunk_text_windows(text: str, window_chars: int = 2000, overlap_chars: int = 250) -> List[str]:
    """Chunk text into overlapping windows by character length."""
    chunks: List[str] = []
    if not text:
        return chunks
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + window_chars)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


# -----------------------------------------------------------------------------
# Main workflow
# -----------------------------------------------------------------------------

def ingest_documents(pdf_paths: Optional[List[Path]] = None) -> None:
    """Ingest configured CBA PDFs to Parquet artifacts."""
    if pdf_paths is None:
        pdf_paths = [
            PROJECT_ROOT / "nhl_cba_2012.pdf",
            PROJECT_ROOT / "nhl_mou_2020.pdf",
            PROJECT_ROOT / "nhl_mou_2025.pdf",
        ]

    page_rows: List[Dict] = []
    article_rows: List[Dict] = []
    chunk_rows: List[Dict] = []

    for path in pdf_paths:
        if not path.exists():
            logger.warning(f"Skipping missing PDF: {path}")
            continue

        filename = path.name
        document_id = FILENAME_TO_DOCID.get(filename)
        if not document_id:
            logger.warning(f"Unknown document_id for {filename}; skipping")
            continue

        logger.info(f"Processing {filename} -> {document_id}")
        pages = _load_pdf_text_pages(path)

        # Per-page rows
        for page_no, text in pages:
            page_rows.append({
                "document_id": document_id,
                "page_number": int(page_no),
                "text": text,
                "char_count": len(text),
                "token_estimate": _estimate_tokens(text),
                # Best-effort hints (filled later from article detection if possible)
                "article_hint": None,
                "article_number": None,
            })

        # Detect articles and fill rows
        articles = _detect_articles(pages)
        for art in articles:
            art_row = {"document_id": document_id, **art}
            article_rows.append(art_row)

        # Generate chunks from articles (or entire document if no article detected)
        if articles:
            for art in articles:
                section = f"Article {art['article_number']}: {art['article_title']}"
                windows = _chunk_text_windows(art["content"])  # default sizes
                for idx, win in enumerate(windows):
                    chunk_rows.append({
                        "chunk_id": f"{document_id}_A{art['article_number']}_{idx+1}",
                        "document_id": document_id,
                        "section": section,
                        "page_start": art["start_page"],
                        "page_end": art["end_page"],
                        "text": win,
                        "token_estimate": _estimate_tokens(win),
                    })

                # Backfill page article hints
                for pr in page_rows:
                    if pr["document_id"] == document_id and art["start_page"] <= pr["page_number"] <= art["end_page"]:
                        pr["article_hint"] = art["article_title"]
                        pr["article_number"] = art["article_number"]
        else:
            # No article headings found: chunk the entire document
            full_text = "\n".join(t for _, t in pages)
            windows = _chunk_text_windows(full_text)
            for idx, win in enumerate(windows):
                chunk_rows.append({
                    "chunk_id": f"{document_id}_DOC_{idx+1}",
                    "document_id": document_id,
                    "section": "Document",
                    "page_start": 1,
                    "page_end": pages[-1][0] if pages else 1,
                    "text": win,
                    "token_estimate": _estimate_tokens(win),
                })

    # Write Parquet outputs
    if page_rows:
        df_pages = pd.DataFrame(page_rows)
        out_pages = DATA_PROCESSED / "cba_document_text.parquet"
        df_pages.to_parquet(out_pages, compression="zstd", index=False)
        logger.info(f"✓ Wrote {len(df_pages)} rows -> {out_pages}")
    else:
        logger.warning("No page rows produced (no PDFs found?)")

    if article_rows:
        df_articles = pd.DataFrame(article_rows)
        out_articles = DATA_PROCESSED / "cba_articles.parquet"
        df_articles.to_parquet(out_articles, compression="zstd", index=False)
        logger.info(f"✓ Wrote {len(df_articles)} rows -> {out_articles}")
    else:
        logger.warning("No article headings detected; cba_articles.parquet not created")

    if chunk_rows:
        df_chunks = pd.DataFrame(chunk_rows)
        out_chunks = DATA_PROCESSED / "cba_chunks.parquet"
        df_chunks.to_parquet(out_chunks, compression="zstd", index=False)
        logger.info(f"✓ Wrote {len(df_chunks)} rows -> {out_chunks}")
    else:
        logger.warning("No chunks produced")


def main() -> None:
    logger.info("=" * 70)
    logger.info("CBA DOCUMENT INGESTION")
    logger.info("=" * 70)
    ingest_documents()
    logger.info("\nNext: python scripts/sync_cba_to_gcs.py")


if __name__ == "__main__":
    main()

