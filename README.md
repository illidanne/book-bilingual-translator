# Book Bilingual Translator

Translate an English EPUB into:

- a Simplified Chinese edition
- a Chinese-English bilingual edition

This project uses Codex for translation and local Python scripts for deterministic EPUB extraction, auditing, and rebuild.

## Install As A Codex Skill

Clone or copy this repository, then place the skill directory under your Codex skills folder:

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R /path/to/book-bilingual-translator "$CODEX_HOME/skills/book-bilingual-translator"
```

If your Codex environment uses `~/.codex/skills`, the equivalent is:

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/book-bilingual-translator ~/.codex/skills/book-bilingual-translator
```

After that, you can invoke it in Codex with a prompt like:

```text
Use $book-bilingual-translator to turn this English EPUB into a Chinese-only edition and a Chinese-English bilingual edition.
```

## 中文简介

这个仓库提供一套面向 Codex 的 EPUB 翻译工作流，目标是把英文电子书转换成：

- 中文版 EPUB
- 中英对照版 EPUB

它不调用外部翻译 API。脚本负责拆书、审计和重建，真正的翻译由 Codex 分批完成。

## Features

- EPUB-first workflow, preserving chapter order, images, links, and most formatting
- resumable batch translation with JSONL task files
- bilingual and Chinese-only rebuild targets
- release audit for missing ids, duplicate ids, incomplete batches, and English-heavy leftovers
- strict final rebuild mode with `--require-complete`

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

### 1. Prepare a workspace

```bash
python3 scripts/prepare_book.py \
  --input "/abs/path/book.epub" \
  --workspace "/abs/path/book-job"
```

This creates:

- `source/`: unpacked EPUB contents
- `tasks/`: JSONL task batches for translation
- `prompts/`: ready-to-use Codex prompts
- `translated/`: where translated JSONL files should be written
- `output/`: rebuilt EPUB outputs
- `manifest.json`: workspace manifest

### 2. Translate each batch with Codex

For every `tasks/batch_XXX.jsonl`, write a matching file to `translated/`:

```json
{"id":"...", "translated_html":"..."}
```

Rules:

- preserve `id`
- keep inline HTML, links, italics, and note anchors
- output one JSON object per input record
- do not add explanations or notes

### 3. Rebuild EPUB outputs

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job"
```

This writes:

- `output/*_bilingual.epub`
- `output/*_zh.epub`

### 4. Audit before release

```bash
python3 scripts/audit_workspace.py \
  --workspace "/abs/path/book-job"
```

Then run the strict final rebuild:

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job" \
  --require-complete
```

## Recommended Codex Usage

- Use `gpt-5.4` for final translation quality.
- Use `gpt-5.4-mini` for smoke tests, prompt tuning, and small trials.

Suggested prompt:

```text
Use $book-bilingual-translator to turn this English EPUB into a Chinese-only edition and a Chinese-English bilingual edition.
First run prepare_book.py, then translate tasks batch by batch, then audit, then rebuild with --require-complete.
```

## Install Notes

- Keep the directory name as `book-bilingual-translator` so the skill name matches `SKILL.md`.
- If you update the repository later, replace the installed folder or pull the new commits into your local clone.
- The scripts do not require network access, but Codex itself is responsible for the translation pass.

## Release Rules

Do not treat a successful rebuild as proof of completeness.

Before calling a book finished, confirm all of these:

- `Missing ids: 0`
- `Extra ids: 0`
- `Duplicate ids: 0`
- `Missing translated batch files: none`
- `Incomplete batches: none`

Also spot-check:

- one early chapter
- one middle chapter
- one late chapter
- acknowledgments
- notes
- index

## Notes

- This repository does not call an external translation API.
- The local scripts preserve EPUB structure; Codex performs the translation.
- EPUB chapters often span multiple batch files, so always audit the whole workspace.
