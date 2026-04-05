# Book Bilingual Translator

把英文 EPUB 图书转换为：

- 中文版 EPUB
- 中英对照版 EPUB

这个项目采用“Codex 负责翻译，Python 脚本负责拆书、审计和重建”的工作方式，不依赖外部翻译 API。

## 适用场景

适合需要把英文电子书批量翻译成：

- 适合阅读的中文单语版本
- 保留英文原文并插入中文译文的双语版本

它优先保留 EPUB 的原始结构，包括：

- 章节顺序
- 图片
- 链接
- 脚注锚点
- 大部分内联格式

## 仓库结构

- `SKILL.md`：Codex skill 入口
- `agents/openai.yaml`：可选的 agent 元数据
- `scripts/prepare_book.py`：拆包 EPUB 并生成翻译任务
- `scripts/rebuild_book.py`：重建双语版和中文版 EPUB
- `scripts/audit_workspace.py`：审计缺失项、重复项和疑似漏译段落
- `references/workflow.md`：Codex 工作流说明
- `references/pipeline.md`：EPUB 保真规则
- `references/release-checklist.md`：最终交付检查表

## 环境要求

- Python 3.10+
- `lxml`

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 安装为 Codex Skill

把这个目录放到 Codex 的 skill 目录下即可：

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R /path/to/book-bilingual-translator "$CODEX_HOME/skills/book-bilingual-translator"
```

如果你的环境使用 `~/.codex/skills`，可以这样：

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/book-bilingual-translator ~/.codex/skills/book-bilingual-translator
```

安装后，可直接在 Codex 里这样调用：

```text
Use $book-bilingual-translator to turn this English EPUB into a Chinese-only edition and a Chinese-English bilingual edition.
```

## 快速开始

### 1. 生成工作区

```bash
python3 scripts/prepare_book.py \
  --input "/绝对路径/book.epub" \
  --workspace "/绝对路径/book-job"
```

这一步会生成：

- `source/`：解包后的 EPUB
- `tasks/`：待翻译的 JSONL 批次
- `prompts/`：给 Codex 用的提示词
- `translated/`：译文 JSONL 输出目录
- `output/`：重建后的 EPUB 输出目录
- `manifest.json`：工作区清单

### 2. 用 Codex 逐批翻译

对每个 `tasks/batch_XXX.jsonl`，在 `translated/` 下写入同名文件。

每行格式必须是：

```json
{"id":"...", "translated_html":"..."}
```

注意：

- 必须保留 `id`
- 必须保留内联 HTML、链接、斜体、脚注锚点
- 一条输入对应一条输出
- 不要加解释、注释或额外说明

### 3. 重建 EPUB

```bash
python3 scripts/rebuild_book.py \
  --workspace "/绝对路径/book-job"
```

会输出：

- `output/*_bilingual.epub`
- `output/*_zh.epub`

### 4. 发布前审计

```bash
python3 scripts/audit_workspace.py \
  --workspace "/绝对路径/book-job"
```

然后执行严格重建：

```bash
python3 scripts/rebuild_book.py \
  --workspace "/绝对路径/book-job" \
  --require-complete
```

## 推荐模型

- 正式翻译：`gpt-5.4`
- 试跑和调提示词：`gpt-5.4-mini`

## 推荐提示词

```text
Use $book-bilingual-translator to turn this English EPUB into a Chinese-only edition and a Chinese-English bilingual edition.
First run prepare_book.py, then translate tasks batch by batch, then audit, then rebuild with --require-complete.
```

## 交付前必须确认

不要把“重建成功”当成“翻译已经完整”。

交付前至少确认这些结果：

- `Missing ids: 0`
- `Extra ids: 0`
- `Duplicate ids: 0`
- `Missing translated batch files: none`
- `Incomplete batches: none`

并建议抽查这些位置：

- 前面章节一处
- 中段章节一处
- 后段章节一处
- 致谢
- 注释
- 索引

## 说明

- 本仓库不调用外部翻译 API
- 翻译由 Codex 完成，脚本只负责结构化处理
- 一本书的一个章节可能跨多个 batch，所以一定要审计整个工作区
