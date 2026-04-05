---
name: book-bilingual-translator
description: Turn English EPUB books into a Chinese-only edition and a Chinese-English bilingual edition using a Codex-driven translation workflow that preserves chapter order, images, links, and as much formatting as possible.
---

# Book Bilingual Translator

Use this skill when the user wants an English book translated into:

- a Simplified Chinese edition
- a Chinese-English bilingual edition

This skill is optimized for `.epub` input and uses Codex itself for translation. The local scripts do extraction and rebuild work only.

## What To Read

- For the Codex-driven workflow, read [references/workflow.md](references/workflow.md).
- For preservation rules and EPUB structure, read [references/pipeline.md](references/pipeline.md).
- Before final delivery, read [references/release-checklist.md](references/release-checklist.md).

## Recommended Model

- `gpt-5.4` for the final translation pass
- `gpt-5.4-mini` for smoke tests and batch trials

## Workflow

### 1. Prepare the book

Run:

```bash
python3 scripts/prepare_book.py \
  --input "/abs/path/book.epub" \
  --workspace "/abs/path/book-job"
```

This creates:

- an unpacked EPUB workspace
- JSONL task batches containing XHTML fragments to translate
- a manifest file for rebuild

### 2. Translate task batches with Codex

For each JSONL file in `tasks/`:

- preserve `id`, `file`, `tag`, and `source_html`
- translate `source_html` into Simplified Chinese HTML
- write a JSONL file in `translated/` with one object per line:

```json
{"id":"...", "translated_html":"..."}
```

Rules:

- preserve inline HTML tags and anchors
- do not add notes or explanations
- keep one output line per input line

### 3. Rebuild the EPUB outputs

Run:

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job"
```

This writes:

- `output/*_bilingual.epub`
- `output/*_zh.epub`

### 4. Audit before calling it finished

Run:

```bash
python3 scripts/audit_workspace.py \
  --workspace "/abs/path/book-job"
```

If the audit reports missing ids, incomplete batches, or suspicious English-heavy blocks:

- fix the corresponding `translated/batch_XXX.jsonl`
- compare against `tasks/batch_XXX.jsonl`
- rerun the audit

### 5. Final release rebuild

Run:

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job" \
  --require-complete
```

Use `--require-complete` only for final delivery. It will fail if any task id still lacks a translation.

## Validation

After final rebuild:

1. confirm both EPUB files exist
2. inspect a few translated XHTML files
3. verify images, CSS, and navigation remain present
4. verify bilingual output keeps English first and Chinese second
5. inspect at least one chapter that spans multiple batches
6. inspect acknowledgments, notes, and index

## Working Rules

- Prefer source EPUB over extracted Markdown.
- Preserve structure first, then translate.
- Translate in batches small enough for review and reruns.
- Treat `rebuild_book.py` as an iteration tool, not proof of completeness.
- Treat `audit_workspace.py` as the release gate.
- If translation is incomplete, report exactly which task files are done and which are pending.
