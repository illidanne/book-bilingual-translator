# Book Bilingual Translator

Translate an English EPUB into:

- a Simplified Chinese edition
- a Chinese-English bilingual edition

This skill uses Codex for translation and local Python scripts for deterministic EPUB extraction, auditing, and rebuild.

## Repository Layout

- `SKILL.md`: Codex skill entrypoint
- `agents/openai.yaml`: optional agent metadata
- `scripts/prepare_book.py`: unpack EPUB and generate translation tasks
- `scripts/rebuild_book.py`: rebuild bilingual and Chinese-only EPUB files
- `scripts/audit_workspace.py`: audit completeness and suspicious English leftovers
- `references/workflow.md`: Codex translation workflow
- `references/pipeline.md`: EPUB preservation rules
- `references/release-checklist.md`: final delivery checklist

## Requirements

- Python 3.10+
- `lxml`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Quick Start

Prepare a workspace:

```bash
python3 scripts/prepare_book.py \
  --input "/abs/path/book.epub" \
  --workspace "/abs/path/book-job"
```

Translate each `tasks/batch_XXX.jsonl` file with Codex and write matching output files into `translated/`:

```json
{"id":"...", "translated_html":"..."}
```

Rebuild outputs:

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job"
```

Audit before release:

```bash
python3 scripts/audit_workspace.py \
  --workspace "/abs/path/book-job"

python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job" \
  --require-complete
```

## Notes

- This repository does not call an external translation API.
- The local scripts preserve EPUB structure; Codex performs the translation.
- Do not treat a successful rebuild as proof of completeness. Always run the audit.
