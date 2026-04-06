---
description: 自动拆解、翻译并重建双语与单语版 EPUB 书籍 (纯内置管线模式)
---

# EPUB 纯内置模型端到端协同工作流

此工作流用于指挥代理串联书籍拆包、任务读取、增量翻译排期、审计缺漏及重建的端到端执行流程。

本工作流的设计目标是：

- 翻译阶段优先使用环境内置模型能力
- 不使用任何外部翻译 API、Key 或 endpoint 配置
- 继续复用本仓库现有的本地脚本完成 prepare、audit 与 rebuild

注意：本工作流只适用于真正支持工作流发现、文件读写和命令执行的 Antigravity 类环境。如果当前运行环境不支持这些能力，应回退到仓库文档中的手动 batch 流程。

## 核心机制：增量批处理与断点续投

为解决整本书由于内容过大导致的上下文超载问题，翻译采用断点续传机制：
1. **分批读取**：每次模型仅处理 `tasks/` 下尚未翻译的 1~2 个 `.jsonl` 文件。
2. **渐进提交**：将新生成的批次写入 `translated/` 目录。
3. **审计对齐**：使用 `scripts/audit_workspace.py` 判断还有多少批次待翻译，如果尚有空缺或 Missing ids，循环继续执行下一个批次的翻译。

## 步骤流程

1. 环境准备与项目切分
使用以下命令解析源书，要求用户输入源 `epub` 的完整路径（`<input_epub>`）及其预备存放的翻译工作区路径（`<workspace_dir>`）：
```bash
python3 scripts/prepare_book.py --input "<input_epub>" --workspace "<workspace_dir>"
```

2. 逐批内置模型翻译执行 (断点续跑)
指示 Antigravity：
- 对比 `<workspace_dir>/tasks/` 和 `<workspace_dir>/translated/` 的文件差异。
- 提取其中未翻译的一批文件任务。
- 由模型自身对 `source_html` 内容进行准确翻译，强制保留全部带有 `id` 追踪及 HTML 标签的包裹，并且每一行均严丝合缝地只输出 `{"id":"...", "translated_html":"..."}`。
- 将翻译完的结果写入 `<workspace_dir>/translated/` 并落盘。

请注意：

- 不要尝试一轮生成整本书
- 应以 batch 为单位增量推进
- 审计失败时，应按缺失批次或缺失 ids 继续补跑
- 本工作流不假设一次运行就能完整完成整本长书

3. 工作区合规审计与打补丁
当前轮次的批处理结束后，立即检查并验证覆盖率：
```bash
python3 scripts/audit_workspace.py --workspace "<workspace_dir>"
```
如果输出依然包含 “Missing ids” 或批次未翻译完：根据提醒报告缺失的 IDs 或任务批次，系统要求代理接续返回 **步骤2** 专门定位处理遗漏的部分并予以追加重写。

4. 书籍最终重建与打包
当所有的 Audit 工作均顺利清零通过验收后，执行：
```bash
python3 scripts/rebuild_book.py --workspace "<workspace_dir>" --require-complete
```
即可将译文打包装订为最终的双语版与中文版 EPUB 产物。
