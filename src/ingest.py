from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

PEP_FILE_RE = re.compile(r"^pep-(\d{4})\.rst$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def load_raw_document(path: Path) -> dict:
    match = PEP_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"not a PEP file: {path}")
    return {
        "pep_number": int(match.group(1)),
        "text": normalize_text(path.read_text(encoding="utf-8")),
    }


def load_raw_documents(input_dir: str | Path = "data/raw") -> list[dict]:
    directory = Path(input_dir)
    files = sorted(
        p for p in directory.glob("*.rst") if PEP_FILE_RE.match(p.name)
    )
    return [load_raw_document(p) for p in files]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load raw PEP documents")
    parser.add_argument("--input", default="data/raw", help="directory of .rst files")
    parser.add_argument(
        "--output", default=None, help="optional JSON file to write raw documents to"
    )
    args = parser.parse_args(argv)

    documents = load_raw_documents(args.input)
    print(f"Loaded {len(documents)} raw PEP documents from {args.input}")
    for doc in documents:
        print(f"  PEP {doc['pep_number']}: {len(doc['text'])} chars")

    if args.output:
        Path(args.output).write_text(
            json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())