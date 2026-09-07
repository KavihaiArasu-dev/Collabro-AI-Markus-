"""
Markus AI — Rebuild RAG Vector Store from all .md files

Usage:
    cd markus
    python scripts/rebuild_rag.py

This script:
  1. Discovers all .md files across the project (excluding venv, node_modules, .git, __pycache__)
  2. Clears the existing vector store
  3. Copies every .md file into data/documents/ (flat, with prefixed names to avoid collisions)
  4. Re-ingests all documents into the RAG vector store
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Ensure the markus package is importable
MARKUS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MARKUS_DIR))

PROJECT_ROOT = MARKUS_DIR.parent  # Markus_AI root
DOCUMENTS_DIR = MARKUS_DIR / "data" / "documents"

EXCLUDE_DIRS = {
    "venv", "node_modules", ".git", "__pycache__",
    ".pytest_cache", ".agents", ".vscode",
}


def discover_md_files(root: Path) -> list[Path]:
    """Walk the project tree and collect all .md files, excluding irrelevant dirs."""
    md_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            if fname.lower().endswith(".md"):
                md_files.append(Path(dirpath) / fname)
    return md_files


def safe_dest_name(md_path: Path, root: Path) -> str:
    """Create a flat, collision-free filename by joining relative path parts with underscores."""
    try:
        rel = md_path.relative_to(root)
    except ValueError:
        rel = Path(md_path.name)
    return "_".join(rel.parts).replace(" ", "_")


def main():
    print("=" * 60)
    print("  MARKUS AI — RAG Vector Store Rebuild")
    print("=" * 60)

    # 1. Discover all .md files
    md_files = discover_md_files(PROJECT_ROOT)
    # Filter out trivially small files (< 100 bytes) like placeholder READMEs
    md_files = [f for f in md_files if f.stat().st_size >= 100]

    print(f"\n[FOUND] {len(md_files)} .md files to ingest:\n")
    for f in md_files:
        rel = f.relative_to(PROJECT_ROOT)
        size_kb = f.stat().st_size / 1024
        print(f"   - {rel}  ({size_kb:.1f} KB)")

    # 2. Prepare documents directory
    if DOCUMENTS_DIR.exists():
        shutil.rmtree(DOCUMENTS_DIR)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[CLEAN] Cleaned and recreated: {DOCUMENTS_DIR.relative_to(PROJECT_ROOT)}")

    # 3. Copy all .md files into data/documents/
    for md_path in md_files:
        dest_name = safe_dest_name(md_path, PROJECT_ROOT)
        dest = DOCUMENTS_DIR / dest_name
        shutil.copy2(md_path, dest)
    print(f"[COPY]  Copied {len(md_files)} files into data/documents/")

    # 4. Clear and rebuild vector store
    # Change cwd to markus/ so relative paths (data/vector_store.json) work
    os.chdir(MARKUS_DIR)

    from rag.vector_store import vector_store
    from rag.document_loader import document_loader

    old_count = len(vector_store.chunks)
    vector_store.clear()
    print(f"\n[CLEAR] Cleared old vector store ({old_count} chunks removed)")

    total_chunks = document_loader.ingest_directory(str(DOCUMENTS_DIR))

    # 5. Summary
    doc_names = vector_store.get_document_names()
    print(f"\n[DONE]  Rebuild complete!")
    print(f"   Documents indexed: {len(doc_names)}")
    print(f"   Total chunks:      {total_chunks}")
    print(f"\n   Indexed documents:")
    for name in sorted(doc_names):
        print(f"      - {name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
