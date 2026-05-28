"""
corpus.py — read your own documents and chunk them for graph extraction.

This is the heart of the "feed it your own corpus" capability. Instead of
searching the web for an unfamiliar domain, the tool reads YOUR files (notes,
PDFs, book excerpts, transcripts) and builds a graph grounded in them — every
concept can point back to the exact passage it came from.

Supported: .txt .md .pdf .docx  (others read as plain text if decodable)
PDF/DOCX readers are optional deps; if missing, those files are skipped with a
clear message rather than crashing.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    id: str                 # e.g. "notes.md#3"
    doc: str                # source filename
    index: int              # chunk number within the doc
    text: str


def _read_txt(path: str) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _read_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # fallback name
        except ImportError:
            print(f"  [corpus] skipping {os.path.basename(path)}: install pypdf to read PDFs")
            return ""
    try:
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        print(f"  [corpus] PDF read error {os.path.basename(path)}: {e}")
        return ""


def _read_docx(path: str) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        print(f"  [corpus] skipping {os.path.basename(path)}: install python-docx to read .docx")
        return ""
    try:
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    except Exception as e:
        print(f"  [corpus] DOCX read error {os.path.basename(path)}: {e}")
        return ""


def read_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    return _read_txt(path)


def chunk_text(text: str, doc: str, target_chars: int = 2400) -> list[Chunk]:
    """Split on paragraph boundaries into ~target_chars chunks, keeping
    semantic units (paragraphs) intact so extraction has coherent context."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, n = [], "", 0
    for p in paras:
        if buf and len(buf) + len(p) > target_chars:
            chunks.append(Chunk(id=f"{doc}#{n}", doc=doc, index=n, text=buf.strip()))
            n += 1
            buf = p
        else:
            buf = (buf + "\n\n" + p) if buf else p
    if buf.strip():
        chunks.append(Chunk(id=f"{doc}#{n}", doc=doc, index=n, text=buf.strip()))
    return chunks


def load_corpus(paths: list[str], target_chars: int = 2400) -> list[Chunk]:
    """Read a list of files/dirs into a flat list of chunks."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for nm in names:
                    if not nm.startswith("."):
                        files.append(os.path.join(root, nm))
        elif os.path.isfile(p):
            files.append(p)
    all_chunks = []
    for fp in sorted(files):
        text = read_file(fp)
        if not text.strip():
            continue
        doc = os.path.basename(fp)
        cs = chunk_text(text, doc, target_chars)
        all_chunks.extend(cs)
        print(f"  [corpus] {doc}: {len(cs)} chunks ({len(text)} chars)")
    print(f"  [corpus] total: {len(all_chunks)} chunks from {len(files)} files")
    return all_chunks
