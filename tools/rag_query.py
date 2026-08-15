#!/usr/bin/env python3
"""Query the lightweight Pi2 hardware knowledge index."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\.]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def score(index: dict, query: str, k1: float = 1.5, b: float = 0.75):
    terms = tokenize(query)
    docs = index["documents"]
    postings = index["postings"]
    doc_freq = index["doc_freq"]
    avg_len = index.get("avg_doc_length") or 1.0
    n_docs = max(len(docs), 1)
    scores: dict[int, float] = {}

    for term in terms:
        posting = postings.get(term)
        if not posting:
            continue
        df = doc_freq.get(term, len(posting))
        idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
        for doc_id, tf in posting.items():
            doc = docs[int(doc_id)]
            dl = doc.get("length", 1)
            denom = tf + k1 * (1.0 - b + b * dl / avg_len)
            scores[int(doc_id)] = scores.get(int(doc_id), 0.0) + idf * tf * (k1 + 1.0) / denom

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="hardware/RAG query")
    parser.add_argument("--index", default=".rag/index.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit(f"index not found: {index_path}; run tools/rag_build.py first")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    ranked = score(index, args.query)[: max(args.top_k, 1)]

    results = []
    for doc_id, relevance in ranked:
        doc = index["documents"][doc_id]
        results.append(
            {
                "score": round(relevance, 4),
                "path": doc["path"],
                "chunk": doc["chunk"],
                "title": doc["title"],
                "text": doc["text"],
            }
        )

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if not results:
        print("no matching knowledge chunks")
        return 1

    for i, result in enumerate(results, start=1):
        print(f"[{i}] score={result['score']} {result['path']}#chunk-{result['chunk']}")
        print(f"    {result['title']}")
        snippet = " ".join(result["text"].split())
        print(f"    {snippet[:500]}{'...' if len(snippet) > 500 else ''}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
