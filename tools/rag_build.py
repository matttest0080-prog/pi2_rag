#!/usr/bin/env python3
"""Build a lightweight JSON search index for Pi2 hardware knowledge.

Uses only the Python standard library so it can run on Raspberry Pi 2-class
systems without local embedding models or a vector database.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\.]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def iter_markdown(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


def split_chunks(text: str, max_chars: int = 1600) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n(?=#{1,6}\s)|\n\s*\n", text) if b.strip()]
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def build_index(repo_root: Path, output: Path) -> dict:
    source_roots = [repo_root / "skills" / "raspberry-pi-hardware-control" / "references"]
    extra_files = [repo_root / "README.md", repo_root / "docs" / "ARCHITECTURE.md"]

    documents = []
    postings: dict[str, dict[str, int]] = defaultdict(dict)
    doc_freq = Counter()

    paths: list[Path] = []
    for root in source_roots:
        if root.exists():
            paths.extend(iter_markdown(root))
    paths.extend(path for path in extra_files if path.exists())

    for path in sorted(set(paths)):
        text = path.read_text(encoding="utf-8", errors="replace")
        for chunk_no, chunk in enumerate(split_chunks(text), start=1):
            tokens = tokenize(chunk)
            if not tokens:
                continue
            doc_id = str(len(documents))
            counts = Counter(tokens)
            rel = path.relative_to(repo_root).as_posix()
            title_match = re.search(r"^#{1,6}\s+(.+)$", chunk, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else rel
            documents.append(
                {
                    "id": doc_id,
                    "path": rel,
                    "chunk": chunk_no,
                    "title": title,
                    "text": chunk,
                    "length": len(tokens),
                }
            )
            for term, tf in counts.items():
                postings[term][doc_id] = tf
                doc_freq[term] += 1

    avg_len = (
        sum(doc["length"] for doc in documents) / len(documents) if documents else 0.0
    )
    index = {
        "version": 1,
        "engine": "stdlib-json-bm25",
        "documents": documents,
        "postings": postings,
        "doc_freq": doc_freq,
        "avg_doc_length": avg_len,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--out", default=".rag/index.json", help="output index path")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = (repo / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    index = build_index(repo, out)
    print(f"indexed {len(index['documents'])} chunks -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
