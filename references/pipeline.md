# Pipeline

## Preferred input

Use the original `.epub` whenever possible. It preserves:

- manifest and spine order
- chapter XHTML
- CSS and fonts
- images and title pages
- navigation and notes

## Translation unit

Translate block-level XHTML fragments instead of flattening text. Preferred targets:

- `p`
- `h1` to `h6`
- `li`
- `blockquote`
- `figcaption`
- `td`
- `th`

This keeps inline tags such as emphasis, links, spans, and footnote anchors intact.

## Task record shape

Each task record should contain:

- `id`
- `file`
- `order`
- `tag`
- `source_html`
- `source_text`

Codex should return:

- `id`
- `translated_html`

## Bilingual output

For each translated block:

- keep the original English block
- insert a sibling block after it
- reuse the same tag name and most attributes
- append translation classes like `codex-translation` and `codex-zh`

## Chinese-only output

For each translated block:

- keep the surrounding XHTML structure
- replace the block inner HTML with the Chinese translation

## Formatting preservation rules

- preserve existing classes and ids when practical
- do not remove images, SVG, or pagebreak spans
- keep relative asset paths unchanged
- inject one extra CSS file and link it from processed XHTML files
- update the OPF manifest when adding the CSS asset

## Practical notes

- batches should stay modest so Codex can translate reliably
- notes and indexes may need a separate pass
- use iterative rebuilds during work, but use strict rebuild for release
- chapters often cross batch boundaries, so chapter-level QA must check all related batches
