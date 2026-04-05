#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
NAMESPACES = {
    "xhtml": XHTML_NS,
    "epub": EPUB_NS,
    "c": CONTAINER_NS,
    "opf": OPF_NS,
}

TRANSLATABLE_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "figcaption",
    "blockquote",
    "td",
    "th",
}
BLOCK_TAGS = TRANSLATABLE_TAGS | {"div", "ol", "ul", "table", "tr"}


def local_name(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def has_meaningful_text(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    return len(compact) >= 2 and bool(re.search(r"[A-Za-z]", compact))


def serialize_inner_xml(element: etree._Element) -> str:
    pieces: list[str] = []
    if element.text:
        pieces.append(element.text)
    for child in element:
        pieces.append(etree.tostring(child, encoding="unicode"))
    return "".join(pieces).strip()


def locate_opf(root_dir: Path) -> Path:
    container_path = root_dir / "META-INF" / "container.xml"
    tree = etree.parse(str(container_path))
    return root_dir / tree.find(".//c:rootfile", namespaces=NAMESPACES).get("full-path")


def get_spine_documents(opf_path: Path) -> list[Path]:
    tree = etree.parse(str(opf_path))
    base_dir = opf_path.parent
    manifest: dict[str, Path] = {}
    for item in tree.findall(".//opf:manifest/opf:item", namespaces=NAMESPACES):
        item_id = item.get("id")
        href = item.get("href")
        media_type = item.get("media-type", "")
        if item_id and href and media_type in {"application/xhtml+xml", "text/html"}:
            manifest[item_id] = (base_dir / href).resolve()
    docs: list[Path] = []
    for itemref in tree.findall(".//opf:spine/opf:itemref", namespaces=NAMESPACES):
        item_id = itemref.get("idref")
        if item_id in manifest:
            docs.append(manifest[item_id])
    return docs


def extract_tasks(doc_path: Path, root_dir: Path) -> list[dict]:
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(str(doc_path), parser)
    tasks: list[dict] = []
    order = 0
    for element in tree.getroot().iter():
        tag = local_name(element.tag)
        if tag not in TRANSLATABLE_TAGS:
            continue
        if any(local_name(child.tag) in BLOCK_TAGS for child in element.iterdescendants()):
            continue
        text = "".join(element.itertext())
        inner_html = serialize_inner_xml(element)
        if not inner_html or not has_meaningful_text(text):
            continue
        xpath = tree.getpath(element)
        tasks.append(
            {
                "id": f"{doc_path.relative_to(root_dir).as_posix()}::{order}",
                "file": doc_path.relative_to(root_dir).as_posix(),
                "order": order,
                "tag": tag,
                "xpath": xpath,
                "source_html": inner_html,
                "source_text": re.sub(r"\s+", " ", text).strip(),
            }
        )
        order += 1
    return tasks


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_prompt_text(batch_file: Path) -> str:
    return f"""请读取这个 JSONL 任务文件并逐行翻译其中的 `source_html` 为简体中文，保留内联 HTML 标签、链接、脚注锚点和顺序不变。

输入文件：
{batch_file}

输出要求：
1. 逐行输出 JSONL。
2. 每行只包含 `id` 和 `translated_html`。
3. `id` 必须与输入完全一致。
4. `translated_html` 必须保留原有内联 HTML 结构，不要添加解释或备注。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a Codex translation workspace from an EPUB.")
    parser.add_argument("--input", required=True, help="Path to source EPUB")
    parser.add_argument("--workspace", required=True, help="Workspace directory to create")
    parser.add_argument("--batch-size", type=int, default=120, help="Number of records per task file")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    source_dir = workspace / "source"
    tasks_dir = workspace / "tasks"
    translated_dir = workspace / "translated"
    output_dir = workspace / "output"
    prompts_dir = workspace / "prompts"
    translated_dir.mkdir()
    output_dir.mkdir()
    prompts_dir.mkdir()

    with ZipFile(input_path) as archive:
        archive.extractall(source_dir)

    opf_path = locate_opf(source_dir)
    docs = get_spine_documents(opf_path)
    all_tasks: list[dict] = []
    for doc in docs:
        all_tasks.extend(extract_tasks(doc, source_dir))

    batch_count = math.ceil(len(all_tasks) / args.batch_size) if all_tasks else 0
    batch_files: list[str] = []
    for batch_index in range(batch_count):
        start = batch_index * args.batch_size
        end = start + args.batch_size
        batch_rows = all_tasks[start:end]
        batch_name = f"batch_{batch_index + 1:03d}.jsonl"
        batch_path = tasks_dir / batch_name
        write_jsonl(batch_path, batch_rows)
        batch_files.append(str(batch_path.relative_to(workspace)))
        (prompts_dir / f"batch_{batch_index + 1:03d}.txt").write_text(
            build_prompt_text(batch_path),
            encoding="utf-8",
        )

    manifest = {
        "input_epub": str(input_path),
        "workspace": str(workspace),
        "opf_path": str(opf_path.relative_to(source_dir)),
        "task_count": len(all_tasks),
        "batch_size": args.batch_size,
        "batch_files": batch_files,
    }
    (workspace / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared workspace: {workspace}")
    print(f"Tasks: {len(all_tasks)}")
    print(f"Batches: {batch_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
