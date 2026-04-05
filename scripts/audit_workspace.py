#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(r"https?://\S+")
ENGLISH_RUN_RE = re.compile(r"\b[A-Za-z][A-Za-z'/-]*\b")
LONG_ENGLISH_PHRASE_RE = re.compile(
    r"\b[A-Za-z][A-Za-z'/-]*"
    r"(?:\s+[A-Za-z][A-Za-z'/-]*){4,}\b"
)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ascii_ratio(text: str) -> float:
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    ascii_letters = [ch for ch in visible if ch.isascii() and ch.isalpha()]
    return len(ascii_letters) / len(visible)


def plain_text(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    text = URL_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def looks_suspicious(source_html: str, translated_html: str, threshold: float) -> tuple[bool, float]:
    if translated_html.strip() == source_html.strip():
        return True, 1.0

    plain = plain_text(translated_html)
    ratio = ascii_ratio(plain)
    english_runs = ENGLISH_RUN_RE.findall(plain)
    long_phrase = LONG_ENGLISH_PHRASE_RE.search(plain)

    if long_phrase:
        return True, ratio
    if not has_cjk(plain) and len(english_runs) >= 6:
        return True, ratio
    if has_cjk(plain) and ratio >= threshold and len(english_runs) >= 8:
        return True, ratio
    return False, ratio


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a book translation workspace before final rebuild.")
    parser.add_argument("--workspace", required=True, help="Workspace created by prepare_book.py")
    parser.add_argument(
        "--ascii-threshold",
        type=float,
        default=0.18,
        help="Flag translated blocks whose ASCII-letter ratio exceeds this threshold",
    )
    parser.add_argument(
        "--show-suspects",
        type=int,
        default=20,
        help="How many suspicious records to print",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    tasks_dir = workspace / "tasks"
    translated_dir = workspace / "translated"

    task_rows: dict[str, dict] = {}
    batch_task_counts: dict[str, int] = {}
    for rel_path in manifest["batch_files"]:
        task_path = workspace / rel_path
        rows = load_jsonl(task_path)
        batch_task_counts[task_path.name] = len(rows)
        for row in rows:
            task_rows[row["id"]] = row

    translated_rows: dict[str, tuple[str, str]] = {}
    batch_translated_counts: dict[str, int] = {}
    duplicate_ids: list[str] = []
    for path in sorted(translated_dir.glob("*.jsonl")):
        rows = load_jsonl(path)
        batch_translated_counts[path.name] = len(rows)
        for row in rows:
            row_id = row["id"]
            translated_html = row["translated_html"]
            if row_id in translated_rows:
                duplicate_ids.append(row_id)
            translated_rows[row_id] = (path.name, translated_html)

    missing_ids = sorted(set(task_rows) - set(translated_rows))
    extra_ids = sorted(set(translated_rows) - set(task_rows))
    missing_batches = sorted(set(batch_task_counts) - set(batch_translated_counts))
    incomplete_batches = sorted(
        name
        for name, count in batch_task_counts.items()
        if batch_translated_counts.get(name, 0) < count
    )

    suspicious: list[dict] = []
    for row_id, task_row in task_rows.items():
        translated = translated_rows.get(row_id)
        if translated is None:
            continue
        batch_name, translated_html = translated
        source_html = task_row["source_html"]
        flagged, ratio = looks_suspicious(source_html, translated_html, args.ascii_threshold)
        if flagged:
            suspicious.append(
                {
                    "id": row_id,
                    "batch": batch_name,
                    "ratio": round(ratio, 4),
                    "translated_html": plain_text(translated_html),
                }
            )

    summary = {
        "workspace": str(workspace),
        "task_count": len(task_rows),
        "translated_count": len(translated_rows),
        "missing_count": len(missing_ids),
        "extra_count": len(extra_ids),
        "duplicate_count": len(duplicate_ids),
        "missing_batches": missing_batches,
        "incomplete_batches": incomplete_batches,
        "suspicious_count": len(suspicious),
    }

    if args.json:
        payload = {
            "summary": summary,
            "missing_ids": missing_ids,
            "extra_ids": extra_ids,
            "duplicate_ids": duplicate_ids,
            "suspicious": suspicious[: args.show_suspects],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if (missing_ids or extra_ids or duplicate_ids or suspicious) else 0

    print("Workspace:", workspace)
    print("Tasks:", len(task_rows))
    print("Translated:", len(translated_rows))
    print("Missing ids:", len(missing_ids))
    print("Extra ids:", len(extra_ids))
    print("Duplicate ids:", len(duplicate_ids))
    print("Missing translated batch files:", ", ".join(missing_batches) or "none")
    print("Incomplete batches:", ", ".join(incomplete_batches) or "none")
    print("Suspicious translated blocks:", len(suspicious))

    if missing_ids:
        print("\nMissing ids:")
        for row_id in missing_ids[: args.show_suspects]:
            print("-", row_id)

    if suspicious:
        print("\nSuspicious blocks:")
        for item in suspicious[: args.show_suspects]:
            preview = re.sub(r"\s+", " ", item["translated_html"]).strip()[:160]
            print(f"- {item['id']} [{item['batch']}] ratio={item['ratio']}: {preview}")

    return 1 if (missing_ids or extra_ids or duplicate_ids or suspicious) else 0


if __name__ == "__main__":
    raise SystemExit(main())
