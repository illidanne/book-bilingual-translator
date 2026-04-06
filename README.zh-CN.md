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

- `.agents/workflows/translate-epub.md`：面向 Antigravity 的工作流定义
- `SKILL.md`：Codex skill 入口
- `agents/openai.yaml`：可选的 agent 元数据
- `CHANGELOG.md`：项目变更记录
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

### 2. 通过基座内置模型增量逐批翻译

为了减少依赖并避免管理 API key，翻译阶段可以完全借助内置基座大模型（如 Antigravity 或 Codex）执行，不依赖外部翻译 API。

对每个 `tasks/batch_XXX.jsonl`，在 `translated/` 下写入同名文件。考虑到厚书的上下文负担，建议在对话指令中依靠断点续传：
1. 告诉代理自行读取 `tasks/` 目录下欠缺的批次文件；
2. 逐批输出成译文内容，每次对话完成几个批次的落盘写回。

要求落盘每行格式必须是：

```json
{"id":"...", "translated_html":"..."}
```

注意：

- 本流程可以依靠代理自带的工作流增量读写完成，发现断点只需让它重拾遗漏的批次继续跑。
- 不需要外部翻译 API，但本地 `prepare/audit/rebuild` 脚本仍然是正式流程的一部分。
- 必须严格保留 `id`
- 必须保留内联 HTML、链接、斜体、脚注锚点
- 结构化逐条对应：一条输入必定对应一条输出
- 绝对不要加额外的 markdown block 或者文本解释、预设说明

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

## Antigravity 工作流支持

仓库中还包含一个面向 Antigravity 的工作流文件：`.agents/workflows/translate-epub.md`。

这个工作流只适用于真正支持以下能力的环境：

- 自动识别 `.agents/workflows/`
- 代理原生读写文件
- 通过工作流步骤执行命令

它的作用是帮助编排流程，不是替代本地脚本。下面这些脚本仍然是正式流程的基础：

- `prepare_book.py`
- `audit_workspace.py`
- `rebuild_book.py`

如果你的环境并不识别 `.agents/workflows/`，那就回退到上面那套标准的手动 batch 流程。

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

## 常见问题

### 为什么审计通过后，仍然会看到一些 `Suspicious translated blocks`？

因为审计分成两层：

- 硬性结构检查：缺失 `id`、重复 `id`、缺失批次、不完整批次
- 启发式检查：看某些段落是否仍然“英文味太重”

如果硬性结构项都已经清零，那么工作区在结构上就是完整的。剩下的可疑项，很多其实只是网址、专有名词、目录标题、技术术语，或者保留英文更合适的内容。

### 为什么不能只跑 `rebuild_book.py`？

因为 `rebuild` 只能证明 EPUB 成功生成，不能证明每一条任务都真的被翻译了。正式交付前一定要跑 `audit_workspace.py`，最后再用 `rebuild_book.py --require-complete` 收口。

### 为什么一个章节会落在多个 batch 里？

因为这里的分批是按大小切的，不是按章节切的。长章节经常会跨多个 `batch_XXX.jsonl`。所以某章如果还有漏译，不能只看一个 batch，要把覆盖那一章的所有 batch 一起检查。

### 为什么不建议直接从 Markdown 翻？

通常不建议。这个流程是围绕 EPUB 原始 XHTML 设计的，更容易保留目录、链接、脚注锚点和格式结构。

### 能不能改成别的语言对？

可以，但当前的提示词、说明和审计习惯都是围绕“英文 -> 简体中文”调过的。如果改成别的语言对，最好同步改提示词和人工复核规则。

### Antigravity 工作流是否保证一次就跑完整本书？

不能这样假设。对长书来说，推荐方式仍然是按 batch 增量执行，并在中间穿插审计和断点续跑。工作流能帮助编排步骤，但不应被当成“单次运行必然完整完成整本书”的保证。

## 说明

- 本仓库不调用外部翻译 API
- 翻译由 Codex 完成，脚本只负责结构化处理
- 一本书的一个章节可能跨多个 batch，所以一定要审计整个工作区
