# Changelog

All notable changes to this project will be documented in this file.

## 2026-04-06

### Added

- public repository structure with `README.md`, `README.zh-CN.md`, `.gitignore`, and `requirements.txt`
- MIT `LICENSE`
- explicit Codex skill installation instructions
- release-oriented `CHANGELOG.md`
- workspace audit script `scripts/audit_workspace.py`
- strict rebuild gate via `scripts/rebuild_book.py --require-complete`

### Improved

- skill documentation in `SKILL.md`
- reusable workflow guidance in `references/workflow.md`
- release checks in `references/release-checklist.md`
- pipeline guidance in `references/pipeline.md`
- script portability by switching shebangs to `#!/usr/bin/env python3`

### Validated

- full-coverage audit on the example translation workspace
- strict bilingual and Chinese-only EPUB rebuild workflow
