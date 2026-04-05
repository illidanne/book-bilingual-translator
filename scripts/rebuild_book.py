#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NAMESPACES = {
    "xhtml": XHTML_NS,
    "epub": EPUB_NS,
    "c": CONTAINER_NS,
    "opf": OPF_NS,
    "dc": DC_NS,
}
CSS_BASENAME = "codex_bilingual.css"
CSS_TEXT = """
.codex-translation {
  margin-top: 0.35em;
}

.codex-zh {
  color: #1f2937;
}
""".strip() + "\n"
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
    compact = " ".join(text.split()).strip()
    return len(compact) >= 2 and bool(re.search(r"[A-Za-z]", compact))


def iter_candidates(root: etree._Element) -> list[etree._Element]:
    items: list[etree._Element] = []
    for element in root.iter():
        tag = local_name(element.tag)
        if tag not in TRANSLATABLE_TAGS:
            continue
        if any(local_name(child.tag) in BLOCK_TAGS for child in element.iterdescendants()):
            continue
        text = "".join(element.itertext())
        if not has_meaningful_text(text):
            continue
        items.append(element)
    return items


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def set_inner_xml(element: etree._Element, inner_xml: str) -> None:
    for child in list(element):
        element.remove(child)
    element.text = None
    wrapper = etree.fromstring(
        f'<wrapper xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}">{inner_xml}</wrapper>'.encode("utf-8")
    )
    element.text = wrapper.text
    for child in wrapper:
        element.append(child)


def set_document_lang(tree: etree._ElementTree, lang: str) -> None:
    root = tree.getroot()
    root.set("lang", lang)
    root.set(f"{{{XML_NS}}}lang", lang)
    body = root.find(".//xhtml:body", namespaces=NAMESPACES)
    if body is not None:
        body.set("lang", lang)
        body.set(f"{{{XML_NS}}}lang", lang)


def clone_with_translation(element: etree._Element, translated_html: str) -> etree._Element:
    clone = copy.deepcopy(element)
    classes = [item for item in (clone.get("class") or "").split() if item]
    for extra in ["codex-translation", "codex-zh"]:
        if extra not in classes:
            classes.append(extra)
    if classes:
        clone.set("class", " ".join(classes))
    clone.set("lang", "zh-CN")
    clone.set(f"{{{XML_NS}}}lang", "zh-CN")
    if clone.get("id"):
        clone.attrib.pop("id", None)
    set_inner_xml(clone, translated_html)
    return clone


def add_stylesheet_link(tree: etree._ElementTree, document_path: Path, css_path: Path) -> None:
    root = tree.getroot()
    head = root.find(".//xhtml:head", namespaces=NAMESPACES)
    relative_href = posixpath.relpath(css_path.as_posix(), start=document_path.parent.as_posix())
    for link in head.findall("xhtml:link", namespaces=NAMESPACES):
        if link.get("href") == relative_href:
            return
    link = etree.Element(f"{{{XHTML_NS}}}link")
    link.set("href", relative_href)
    link.set("rel", "stylesheet")
    link.set("type", "text/css")
    head.append(link)


def locate_opf(root_dir: Path) -> Path:
    tree = etree.parse(str(root_dir / "META-INF" / "container.xml"))
    return root_dir / tree.find(".//c:rootfile", namespaces=NAMESPACES).get("full-path")


def ensure_css_manifest(opf_path: Path, css_path: Path) -> None:
    tree = etree.parse(str(opf_path))
    manifest = tree.find(".//opf:manifest", namespaces=NAMESPACES)
    relative_href = posixpath.relpath(css_path.as_posix(), start=opf_path.parent.as_posix())
    for item in manifest.findall("opf:item", namespaces=NAMESPACES):
        if item.get("href") == relative_href:
            break
    else:
        item = etree.Element(f"{{{OPF_NS}}}item")
        item.set("id", "codex-bilingual-css")
        item.set("href", relative_href)
        item.set("media-type", "text/css")
        manifest.append(item)
    tree.write(str(opf_path), encoding="utf-8", xml_declaration=False)


def update_metadata(opf_path: Path, suffix: str, primary_lang: str | None = None) -> None:
    tree = etree.parse(str(opf_path))
    package = tree.getroot()
    if primary_lang:
        package.set(f"{{{XML_NS}}}lang", primary_lang)
    title = tree.find(".//dc:title", namespaces=NAMESPACES)
    if title is not None and title.text and suffix not in title.text:
        title.text = f"{title.text}{suffix}"
    metadata = tree.find(".//opf:metadata", namespaces=NAMESPACES)
    languages = metadata.findall("dc:language", namespaces=NAMESPACES)
    if primary_lang and languages:
        languages[0].text = primary_lang
    if not any((node.text or "").lower().startswith("zh") for node in languages):
        extra = etree.Element(f"{{{DC_NS}}}language")
        extra.text = "zh-CN"
        metadata.append(extra)
    tree.write(str(opf_path), encoding="utf-8", xml_declaration=False)


def write_tree(tree: etree._ElementTree, path: Path) -> None:
    tree.write(str(path), encoding="utf-8", xml_declaration=False, pretty_print=False)


def zip_epub(source_dir: Path, output_path: Path) -> None:
    with ZipFile(output_path, "w") as archive:
        mimetype_path = source_dir / "mimetype"
        archive.write(mimetype_path, "mimetype", compress_type=ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir() or path == mimetype_path:
                continue
            archive.write(path, path.relative_to(source_dir).as_posix(), compress_type=ZIP_DEFLATED)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild bilingual and Chinese EPUB files from translated JSONL.")
    parser.add_argument("--workspace", required=True, help="Workspace created by prepare_book.py")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail if any task id from manifest batches is missing in translated/",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    source_dir = workspace / "source"
    translated_dir = workspace / "translated"
    output_dir = workspace / "output"
    bilingual_dir = workspace / "_build_bilingual"
    zh_dir = workspace / "_build_zh"
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))

    all_task_ids: set[str] = set()
    for task_file in manifest["batch_files"]:
        for row in load_jsonl(workspace / task_file):
            all_task_ids.add(row["id"])

    translations: dict[str, str] = {}
    for path in sorted(translated_dir.glob("*.jsonl")):
        for row in load_jsonl(path):
            translations[row["id"]] = row["translated_html"]

    if args.require_complete:
        missing_ids = sorted(all_task_ids - set(translations))
        if missing_ids:
            preview = "\n".join(missing_ids[:20])
            raise SystemExit(
                f"Missing translations for {len(missing_ids)} task ids.\n"
                f"First missing ids:\n{preview}"
            )

    shutil.rmtree(bilingual_dir, ignore_errors=True)
    shutil.rmtree(zh_dir, ignore_errors=True)
    shutil.copytree(source_dir, bilingual_dir)
    shutil.copytree(source_dir, zh_dir)

    source_opf = locate_opf(source_dir)
    bilingual_opf = locate_opf(bilingual_dir)
    zh_opf = locate_opf(zh_dir)
    bilingual_css = bilingual_opf.parent / "css" / CSS_BASENAME
    zh_css = zh_opf.parent / "css" / CSS_BASENAME
    bilingual_css.parent.mkdir(parents=True, exist_ok=True)
    zh_css.parent.mkdir(parents=True, exist_ok=True)
    bilingual_css.write_text(CSS_TEXT, encoding="utf-8")
    zh_css.write_text(CSS_TEXT, encoding="utf-8")
    ensure_css_manifest(bilingual_opf, bilingual_css)
    ensure_css_manifest(zh_opf, zh_css)
    update_metadata(bilingual_opf, "（中英对照）")
    update_metadata(zh_opf, "（中文版）", primary_lang="zh-CN")

    file_to_rows: dict[str, list[tuple[int, str]]] = {}
    for task_file in manifest["batch_files"]:
        for row in load_jsonl(workspace / task_file):
            translated_html = translations.get(row["id"])
            if translated_html is None:
                continue
            file_to_rows.setdefault(row["file"], []).append((row["order"], translated_html))

    for relative_file, rows in file_to_rows.items():
        rows.sort(key=lambda item: item[0])
        parser_xml = etree.XMLParser(recover=True, remove_blank_text=False)
        bilingual_path = bilingual_dir / relative_file
        zh_path = zh_dir / relative_file
        bilingual_tree = etree.parse(str(bilingual_path), parser_xml)
        zh_tree = etree.parse(str(zh_path), parser_xml)
        bilingual_lookup = {index: element for index, element in enumerate(iter_candidates(bilingual_tree.getroot()))}
        zh_lookup = {index: element for index, element in enumerate(iter_candidates(zh_tree.getroot()))}

        for order, translated_html in rows:
            bilingual_element = bilingual_lookup.get(order)
            zh_element = zh_lookup.get(order)
            if bilingual_element is None or zh_element is None:
                continue
            parent = bilingual_element.getparent()
            parent.insert(parent.index(bilingual_element) + 1, clone_with_translation(bilingual_element, translated_html))
            zh_element.set("lang", "zh-CN")
            zh_element.set(f"{{{XML_NS}}}lang", "zh-CN")
            set_inner_xml(zh_element, translated_html)

        add_stylesheet_link(bilingual_tree, bilingual_path, bilingual_css)
        add_stylesheet_link(zh_tree, zh_path, zh_css)
        set_document_lang(zh_tree, "zh-CN")
        write_tree(bilingual_tree, bilingual_path)
        write_tree(zh_tree, zh_path)

    input_name = Path(manifest["input_epub"]).stem
    bilingual_epub = output_dir / f"{input_name}_bilingual.epub"
    zh_epub = output_dir / f"{input_name}_zh.epub"
    zip_epub(bilingual_dir, bilingual_epub)
    zip_epub(zh_dir, zh_epub)
    print(f"Bilingual EPUB: {bilingual_epub}")
    print(f"Chinese EPUB: {zh_epub}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
