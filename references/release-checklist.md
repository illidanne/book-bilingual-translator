# Release Checklist

Use this checklist before treating a translated book as final.

## 1. Coverage audit

Run:

```bash
python3 scripts/audit_workspace.py \
  --workspace "/abs/path/book-job"
```

Do not ship the book until all of these are true:

- `Missing ids: 0`
- `Extra ids: 0`
- `Duplicate ids: 0`
- `Missing translated batch files: none`
- `Incomplete batches: none`

## 2. Suspect-English audit

The audit script also flags blocks that still look too English-heavy.

Typical reasons:

- the `translated/` file is missing records
- `translated_html` is still the original English
- the translation is half Chinese and half English

When suspects appear:

1. open the reported `translated/batch_XXX.jsonl`
2. compare the record to the matching `tasks/batch_XXX.jsonl`
3. rewrite the affected `translated_html`
4. rerun `audit_workspace.py`

## 3. Final rebuild

Once coverage is complete, run:

```bash
python3 scripts/rebuild_book.py \
  --workspace "/abs/path/book-job" \
  --require-complete
```

`--require-complete` makes rebuild fail if any task id still lacks a translation.

## 4. Spot-check the EPUB

Open the rebuilt `_zh.epub` and `_bilingual.epub` and inspect:

- front matter
- one early chapter
- one middle chapter
- one late chapter
- acknowledgments
- notes
- index

Prefer checking the places most likely to fail:

- chapters that span multiple batch files
- notes and index sections
- pages with quotations, italics, links, or footnote anchors

## 5. Root-cause guide for common failures

### Symptom: some paragraphs are still English in the final EPUB

Most likely cause:

- the corresponding `translated/batch_XXX.jsonl` is missing ids
- or the file exists but some `translated_html` values are still English

Less likely cause:

- rebuild did not run after edits

### Symptom: a whole chapter looks partly translated and partly untranslated

Most likely cause:

- the chapter crosses batch boundaries and only one batch was corrected

Check all batch files that cover that chapter before rebuilding again.
