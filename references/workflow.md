# Codex Workflow

This skill is for a Codex-driven workflow, not an external translation API workflow.

## Recommended model

- Use `gpt-5.4` for the final translation pass.
- Use `gpt-5.4-mini` for smoke tests, prompt tuning, and small chapter batches.

## Roles

- Local scripts do the deterministic work:
  - unpack EPUB
  - extract XHTML blocks
  - write translation task files
  - rebuild bilingual and Chinese-only EPUB files
- Codex does the translation work:
  - translate the extracted block HTML into Simplified Chinese
  - preserve inline HTML
  - keep fragment order unchanged

## Practical loop

1. Run `prepare_book.py` on the EPUB.
2. Translate one task file at a time with Codex.
3. Save the translated JSONL into `translated/`.
4. For iterative progress, run `rebuild_book.py`.
5. Before final delivery, run `audit_workspace.py`.
6. Run `rebuild_book.py --require-complete`.
7. Inspect the output EPUB files.

## Finalization rule

Do not assume a chapter is complete just because one batch is fixed.

Books often span multiple batch files per chapter. Before calling the book finished:

- audit the whole workspace
- check for missing ids
- check for missing translated batch files
- check suspicious English-heavy blocks
- then do the final rebuild with `--require-complete`

## Why this design

- no external API requirement
- resumable by batch
- easier to review before rebuilding
- preserves EPUB structure better than raw Markdown translation
