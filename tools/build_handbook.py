#!/usr/bin/env python3
"""Build a self-contained Russian student handbook from the repository Markdown.

Requires the pandoc command; Python dependencies are standard-library only.
Local Markdown links become anchors. Images and existing linked files are
embedded, so the HTML can be copied out of the repository and opened offline.
"""

import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit


EXPECTED_LESSONS = [
    "01_intro", "02_geometry", "03_drawing", "04_enhancement", "05_applications",
    "06_ar", "07_markers", "08_ros_image", "09_ros_processing", "10_data", "11_mediapipe",
]

CSS = r'''
:root { color-scheme: light; --ink: #172b41; --muted: #526477; --accent: #075985; --line: #d7e2ed; --paper: #fff; --wash: #f3f7fb; }
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 1rem; }
body { margin: 0; background: var(--wash); color: var(--ink); font: 16px/1.7 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
a { color: var(--accent); text-decoration-thickness: .08em; text-underline-offset: .16em; overflow-wrap: anywhere; }
a:focus-visible, summary:focus-visible { outline: 3px solid #e6a020; outline-offset: 4px; }
.cover { max-width: 1450px; margin: 0 auto; padding: 3.5rem 3rem 2rem; }
.eyebrow { margin: 0 0 .6rem; color: var(--accent); font-size: .85rem; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; }
.cover h1 { font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.13; max-width: 1050px; margin: 0 0 1.2rem; letter-spacing: -.025em; }
.cover p { max-width: 920px; }
.facts { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.2rem; }
.facts span { display: inline-block; border: 1px solid #b8d2e5; background: #eaf4fb; padding: .28rem .75rem; border-radius: 999px; font-size: .9rem; }
.layout { display: grid; grid-template-columns: 285px minmax(0, 1fr); gap: 2rem; max-width: 1450px; margin: auto; padding: 0 3rem 4rem; align-items: start; }
.toc { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; padding: 1.2rem 1rem 1.5rem; border: 1px solid var(--line); border-radius: 14px; background: var(--paper); font-size: .9rem; }
.toc h2 { font-size: 1.15rem; margin: 0 0 1rem; }
.toc h3 { font-size: .83rem; text-transform: uppercase; letter-spacing: .04em; margin: 1.2rem 0 .4rem; color: var(--muted); }
.toc ol { margin: 0; padding-left: 1.3rem; }
.toc li { margin: .32rem 0; padding-left: .05rem; }
.toc a { text-decoration: none; }
.toc a:hover { text-decoration: underline; }
main { min-width: 0; }
.course-document, .downloads { margin: 0 0 2rem; padding: 2rem 2.2rem; border: 1px solid var(--line); border-radius: 14px; background: var(--paper); box-shadow: 0 3px 10px #172b4105; }
.source-path { display: flex; flex-wrap: wrap; gap: .4rem 1rem; margin: 0 0 1.2rem; padding-bottom: .8rem; border-bottom: 1px solid var(--line); font-size: .8rem; color: var(--muted); }
h2, h3, h4, h5, h6 { line-height: 1.3; scroll-margin-top: 1rem; }
h2 { margin-top: 0; font-size: 1.8rem; letter-spacing: -.015em; }
h3 { margin-top: 2rem; font-size: 1.38rem; }
h4 { margin-top: 1.7rem; font-size: 1.13rem; }
p { margin: .8rem 0 1rem; }
ul, ol { padding-left: 1.6rem; }
li { margin: .25rem 0; }
pre, code { font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; font-size: .88em; }
code { background: #eef3f8; border-radius: 4px; padding: .1em .28em; overflow-wrap: anywhere; }
pre { background: #f4f7fa; border: 1px solid var(--line); border-left: 3px solid #6b9cba; border-radius: 7px; padding: 1rem; overflow: auto; line-height: 1.55; }
pre code { background: transparent; padding: 0; border-radius: 0; overflow-wrap: normal; }
blockquote { margin: 1.2rem 0; padding: .4rem 1.15rem; border-left: 4px solid #6b9cba; background: #f0f7fc; color: #28445d; }
blockquote p:last-child { margin-bottom: .5rem; }
table { display: block; width: 100%; overflow-x: auto; border-collapse: collapse; margin: 1.2rem 0; font-size: .9rem; }
th, td { border: 1px solid var(--line); padding: .58rem .75rem; vertical-align: top; text-align: left; min-width: 90px; }
th { background: #eaf2f8; font-weight: 700; }
tr:nth-child(even) td { background: #fafcfe; }
img, svg, video { max-width: 100%; height: auto; }
figure { margin: 1.5rem 0; }
figcaption { font-size: .9rem; color: var(--muted); }
hr { border: 0; border-top: 1px solid var(--line); margin: 1.8rem 0; }
.back-to-contents { margin-top: 2rem; padding-top: .8rem; border-top: 1px solid var(--line); font-size: .85rem; }
.missing-resource { color: var(--muted); }
.file-list { columns: 2; column-gap: 2rem; }
.file-list li { break-inside: avoid; }
footer { max-width: 1450px; margin: auto; padding: 0 3rem 2.5rem; color: var(--muted); font-size: .85rem; }
@media (max-width: 1000px) { .layout { grid-template-columns: 235px minmax(0, 1fr); gap: 1rem; padding: 0 1.2rem 2rem; } .cover { padding: 2rem 1.2rem 1rem; } .course-document, .downloads { padding: 1.4rem; } }
@media (max-width: 730px) { .layout { display: block; } .toc { position: static; max-height: none; margin-bottom: 1rem; } .course-document, .downloads { padding: 1.1rem; } .cover h1 { font-size: 2.1rem; } h2 { font-size: 1.55rem; } .file-list { columns: 1; } footer { padding: 0 1.2rem 2rem; } }
@media print {
  @page { size: A4; margin: 17mm 16mm 18mm; }
  html { scroll-behavior: auto; }
  body { color: #111; background: #fff; font-size: 10.5pt; line-height: 1.48; }
  .cover, .layout, footer { display: block; max-width: none; padding: 0; margin: 0; }
  .cover { margin-bottom: 1cm; }
  .cover h1 { font-size: 28pt; }
  .facts span { border-radius: 0; background: #fff; }
  .toc { position: static; max-height: none; overflow: visible; border: 0; border-radius: 0; padding: 0; margin: 0 0 1cm; break-after: page; font-size: 9pt; }
  .toc h3 { margin-top: .6rem; }
  .toc ol { columns: 2; column-gap: 1cm; }
  .toc li { break-inside: avoid; }
  .course-document, .downloads { break-before: page; margin: 0; padding: 0; border: 0; border-radius: 0; box-shadow: none; }
  .source-path { font-size: 8pt; margin-bottom: .5cm; }
  h2, h3, h4 { break-after: avoid; }
  h2 { font-size: 21pt; }
  h3 { font-size: 15pt; }
  h4 { font-size: 12pt; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; overflow: visible; font-size: 8pt; padding: .55rem; }
  pre code { white-space: pre-wrap; overflow-wrap: anywhere; }
  table { display: table; table-layout: auto; overflow: visible; font-size: 8pt; }
  th, td { min-width: 0; padding: .3rem; overflow-wrap: anywhere; }
  tr, img, figure { break-inside: avoid; }
  a { color: #111; }
  .back-to-contents { display: none; }
  .downloads .file-list { columns: 1; }
}
'''


def stable_id(prefix, value):
    readable = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "document"
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return prefix + "-" + readable + "-" + digest


def inline_text(inlines):
    pieces = []
    for inline in inlines:
        kind = inline.get("t")
        content = inline.get("c")
        if kind == "Str":
            pieces.append(content)
        elif kind in ("Space", "SoftBreak", "LineBreak"):
            pieces.append(" ")
        elif kind in ("Code", "Math"):
            pieces.append(content[1])
        elif kind in ("Link", "Image", "Span"):
            pieces.append(inline_text(content[1]))
        elif kind in ("Emph", "Strong", "Strikeout", "Superscript", "Subscript", "SmallCaps"):
            pieces.append(inline_text(content))
        elif kind == "Quoted":
            pieces.append(inline_text(content[1]))
    return "".join(pieces).strip()


def walk(value, visitor):
    if isinstance(value, dict):
        visitor(value)
        for item in value.values():
            walk(item, visitor)
    elif isinstance(value, list):
        for item in value:
            walk(item, visitor)


def is_attribute(value):
    return (isinstance(value, list) and len(value) == 3 and isinstance(value[0], str)
            and isinstance(value[1], list) and all(isinstance(item, str) for item in value[1])
            and isinstance(value[2], list)
            and all(isinstance(item, list) and len(item) == 2
                    and all(isinstance(part, str) for part in item) for item in value[2]))


def namespace_attributes(value, document):
    if is_attribute(value):
        if value[0]:
            original = value[0]
            renamed = document["id"] + "--" + original
            document["anchors"][original] = renamed
            value[0] = renamed
        return
    if isinstance(value, dict):
        if value.get("t") in ("RawBlock", "RawInline") and value.get("c", [None])[0] == "html":
            def replace_id(match):
                original = html.unescape(match.group(2))
                renamed = document["id"] + "--" + original
                document["anchors"][original] = renamed
                return match.group(1) + html.escape(renamed, quote=True) + match.group(3)
            value["c"][1] = re.sub(r'(\bid\s*=\s*[\"\x27])([^\"\x27]+)([\"\x27])', replace_id, value["c"][1], flags=re.I)
        for item in value.values():
            namespace_attributes(item, document)
    elif isinstance(value, list):
        for item in value:
            namespace_attributes(item, document)


def find_documents(root):
    root_order = ["README.md", "START_HERE.md", "COURSE_MAP.md", "STUDENT_START.md"]
    root_docs = sorted(root.glob("*.md"), key=lambda path: (root_order.index(path.name) if path.name in root_order else len(root_order), path.name))
    groups = [("Начало работы", root_docs)]
    groups.append(("Уроки 01–11", [root / "lessons" / (stem + ".md") for stem in EXPECTED_LESSONS]))
    groups.append(("Справочник и организация курса", sorted((root / "docs").rglob("*.md"))))
    groups.append(("Шаблоны самостоятельной работы", sorted((root / "templates").rglob("*.md"))))
    extra_lessons = [path for path in sorted((root / "lessons").rglob("*.md")) if path not in groups[1][1]]
    if extra_lessons:
        groups.append(("Дополнительные материалы уроков", extra_lessons))
    return groups


class HandbookBuilder:
    def __init__(self, root, output, pandoc, max_embed_bytes):
        self.root = root
        self.output = output
        self.pandoc = pandoc
        self.max_embed_bytes = max_embed_bytes
        self.documents = []
        self.by_path = {}
        self.groups = []
        self.resources = {}
        self.directories = {}
        self.warnings = set()
        self.api_version = None

    def run_pandoc(self, arguments, input_text=None):
        result = subprocess.run([self.pandoc] + arguments, input=input_text,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, encoding="utf-8", check=True,
                                cwd=str(self.root))
        if result.stderr.strip():
            self.warnings.add(result.stderr.strip())
        return result.stdout

    def read_sources(self):
        groups = find_documents(self.root)
        missing = [str(path.relative_to(self.root)) for _, paths in groups for path in paths if not path.is_file()]
        if not (self.root / "README.md").is_file():
            missing.append("README.md")
        if missing:
            raise ValueError("Не найдены обязательные исходники: " + ", ".join(missing))
        for group_name, paths in groups:
            current_group = []
            for path in paths:
                path = path.resolve()
                if path in self.by_path:
                    continue
                relative = path.relative_to(self.root).as_posix()
                ast = json.loads(self.run_pandoc(["--from=gfm+tex_math_dollars+raw_html", "--to=json", str(path)]))
                if not ast.get("blocks"):
                    raise ValueError("Пустая глава: " + relative)
                self.api_version = ast["pandoc-api-version"]
                first_header = next((block for block in ast["blocks"] if block.get("t") == "Header"), None)
                title = inline_text(first_header["c"][2]) if first_header else path.stem.replace("_", " ")
                document = {"path": path, "relative": relative, "id": stable_id("doc", relative),
                            "title": title, "ast": ast, "anchors": {}}
                namespace_attributes(ast["blocks"], document)
                self.documents.append(document)
                self.by_path[path] = document
                current_group.append(document)
            if current_group:
                self.groups.append((group_name, current_group))

    def embed_file(self, path, image=False):
        if path not in self.resources:
            size = path.stat().st_size
            if size > self.max_embed_bytes:
                raise ValueError("Файл слишком велик для автономного HTML: %s (%d байт). Укажите --max-embed-mb при необходимости." % (path.relative_to(self.root), size))
            data = path.read_bytes()
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            self.resources[path] = "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")
        return self.resources[path]

    def resolve_target(self, target, document, image=False):
        parts = urlsplit(target)
        if parts.scheme or parts.netloc:
            return target, None
        # This check must happen before reading any local file: never embed the
        # handbook in itself, even if a previous build is already present.
        if Path(unquote(parts.path)).name.upper() == "STUDENT_GUIDE.HTML":
            return "#contents", None
        if not parts.path:
            fragment = unquote(parts.fragment)
            if not fragment or fragment == "contents":
                return "#contents", None
            anchor = document["anchors"].get(fragment)
            if anchor:
                return "#" + anchor, None
            self.warnings.add("Не найден якорь #%s в %s; ссылка ведёт к началу главы." % (fragment, document["relative"]))
            return "#" + document["id"], None
        path = (document["path"].parent / unquote(parts.path)).resolve()
        if path == self.output:
            return "#contents", None
        if path in self.by_path:
            destination = self.by_path[path]
            fragment = unquote(parts.fragment)
            if fragment and fragment in destination["anchors"]:
                return "#" + destination["anchors"][fragment], None
            if fragment:
                self.warnings.add("Не найден якорь %s в %s; ссылка ведёт к началу главы." % (fragment, destination["relative"]))
            return "#" + destination["id"], None
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            self.warnings.add("Внешний локальный путь не встраивается: " + target)
            return None, None
        if path.is_dir():
            if relative.as_posix() in (".", ""):
                return "#contents", None
            self.directories[path] = stable_id("files", relative.as_posix())
            return "#" + self.directories[path], None
        if path.is_file():
            return self.embed_file(path, image=image), path.name
        self.warnings.add("Файл пока отсутствует в репозитории: %s (ссылка из %s)." % (relative.as_posix(), document["relative"]))
        return None, None

    def transform_document(self, document):
        def visitor(node):
            kind = node.get("t")
            if kind == "Header":
                node["c"][0] = min(6, node["c"][0] + 1)
            elif kind in ("Link", "Image"):
                attributes, label, destination = node["c"]
                original = destination[0]
                target, filename = self.resolve_target(original, document, image=(kind == "Image"))
                remote_image = kind == "Image" and urlsplit(original).scheme not in ("", "data")
                if remote_image:
                    self.warnings.add("Удалённое изображение оставлено ссылкой для автономного чтения: " + original)
                    node["t"] = "Link"
                    node["c"] = [attributes, label or [{"t": "Str", "c": "Изображение"}], [original, destination[1]]]
                elif target is None:
                    node["t"] = "Span"
                    node["c"] = [["", ["missing-resource"], []], label + [{"t": "Space"}, {"t": "Str", "c": "(файл рабочей копии: " + original + ")"}]]
                else:
                    destination[0] = target
                    if filename and kind == "Link":
                        attributes[2].append(["download", filename])
            elif kind in ("RawBlock", "RawInline") and node.get("c", [None])[0] == "html":
                def replace_resource(match):
                    attribute = match.group(1)
                    original = html.unescape(match.group(3))
                    target, _ = self.resolve_target(original, document, image=(attribute.lower() == "src"))
                    if target is None:
                        raise ValueError("Не удалось встроить HTML-ресурс %s в %s" % (original, document["relative"]))
                    if attribute.lower() == "src" and not target.startswith("data:"):
                        raise ValueError("Для автономного HTML нужен локальный ресурс: " + original)
                    return attribute + match.group(2) + html.escape(target, quote=True) + match.group(4)
                node["c"][1] = re.sub(r'(\b(?:href|src))(\s*=\s*[\"\x27])([^\"\x27]*)([\"\x27])', replace_resource, node["c"][1], flags=re.I)
        walk(document["ast"]["blocks"], visitor)

    def downloads_html(self):
        sections = []
        for directory, identifier in sorted(self.directories.items(), key=lambda item: str(item[0])):
            relative = directory.relative_to(self.root).as_posix()
            items = []
            for path in sorted(directory.rglob("*")):
                if not path.is_file() or any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(directory).parts):
                    continue
                if path.resolve() == self.output or path.name.upper() == "STUDENT_GUIDE.HTML":
                    continue
                label = html.escape(path.relative_to(directory).as_posix())
                if path.resolve() in self.by_path:
                    link = "#" + self.by_path[path.resolve()]["id"]
                    items.append('<li><a href="%s">%s</a></li>' % (link, label))
                else:
                    data_uri = self.embed_file(path.resolve())
                    items.append('<li><a download="%s" href="%s">%s</a></li>' % (html.escape(path.name, quote=True), data_uri, label))
            sections.append('<section class="downloads" id="%s"><h2>Файлы: %s</h2><p>Ссылки на существующие файлы встроены в этот HTML. Сохраните их в соответствующую папку рабочей копии.</p><ul class="file-list">%s</ul><p class="back-to-contents"><a href="#contents">К оглавлению</a></p></section>' % (identifier, html.escape(relative), "".join(items) or "<li>Файлы будут созданы при выполнении упражнений.</li>"))
        return "\n".join(sections)

    def build(self):
        self.read_sources()
        blocks = []
        for document in self.documents:
            self.transform_document(document)
            source_link = self.embed_file(document["path"])
            badge = '<div class="source-path"><span>Исходник: <code>%s</code></span><a download="%s" href="%s">Скачать Markdown</a></div>' % (html.escape(document["relative"]), html.escape(document["path"].name, quote=True), source_link)
            back = '<p class="back-to-contents"><a href="#contents">К оглавлению</a></p>'
            content = [{"t": "RawBlock", "c": ["html", badge]}] + document["ast"]["blocks"] + [{"t": "RawBlock", "c": ["html", back]}]
            blocks.append({"t": "Div", "c": [[document["id"], ["course-document"], [["data-source", document["relative"]]]], content]})
        ast = {"pandoc-api-version": self.api_version, "meta": {}, "blocks": blocks}
        body = self.run_pandoc(["--from=json", "--to=html5", "--mathml", "--no-highlight", "--wrap=none"], json.dumps(ast, ensure_ascii=False))
        toc = []
        for name, documents in self.groups:
            toc.append("<h3>" + html.escape(name) + "</h3><ol>")
            for document in documents:
                toc.append('<li><a href="#%s">%s</a></li>' % (document["id"], html.escape(document["title"])))
            toc.append("</ol>")
        downloads = self.downloads_html()
        if self.directories:
            toc.append("<h3>Встроенные файлы</h3><ol>")
            for directory, identifier in sorted(self.directories.items(), key=lambda item: str(item[0])):
                toc.append('<li><a href="#%s">%s</a></li>' % (identifier, html.escape(directory.relative_to(self.root).as_posix())))
            toc.append("</ol>")
        return '''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Самостоятельный курс компьютерного зрения на ROSMASTER X3 PLUS: 11 глав, практические задания, инструкции и шаблоны отчётов.">
<title>Компьютерное зрение на ROSMASTER — учебник студента</title>
<style>''' + CSS + '''</style></head><body>
<header class="cover"><p class="eyebrow">ROSMASTER X3 PLUS · самостоятельная практика</p>
<h1>Компьютерное зрение: от первого изображения до ROS</h1>
<p>Полный учебник курса: стартовые инструкции, одиннадцать глав, справочные материалы и шаблоны самостоятельной работы. Читайте по порядку и выполняйте практику в репозитории или ноутбуках.</p>
<p>Этот файл открывается без интернета: текст, оформление и локальные иллюстрации встроены. Ссылки на официальные источники ведут в интернет. Скачивание встроенного файла не заменяет установку окружения по стартовой инструкции.</p>
<div class="facts"><span>11 учебных глав</span><span>Python · OpenCV · ROS</span><span>Светлая тема и печать</span></div></header>
<div class="layout"><nav class="toc" id="contents" aria-label="Оглавление"><h2>Оглавление</h2>''' + "".join(toc) + '''</nav>
<main id="main-content">''' + body + downloads + '''</main></div>
<footer>Для печати используйте команду браузера «Печать» или «Сохранить как PDF». Версия исходников определяется рабочей копией репозитория, из которой собран этот файл.</footer>
</body></html>
'''


class LinkAudit(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.identifiers = set()
        self.duplicates = set()
        self.anchors = set()
        self.invalid_resources = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.identifiers:
                self.duplicates.add(identifier)
            self.identifiers.add(identifier)
        href = attributes.get("href")
        if href:
            if href.startswith("#"):
                self.anchors.add(unquote(href[1:]))
            elif not urlsplit(href).scheme and not href.startswith("//"):
                self.invalid_resources.append(href)
        src = attributes.get("src")
        if src and not src.startswith("data:"):
            self.invalid_resources.append(src)
        if tag in ("script", "iframe", "object", "embed"):
            self.invalid_resources.append("Unexpected active or external element: " + tag)


def audit_html(text):
    audit = LinkAudit()
    audit.feed(text)
    missing = audit.anchors - audit.identifiers
    if missing or audit.duplicates or audit.invalid_resources:
        raise ValueError("Ошибка автономного HTML: отсутствующие якоря=%s; повторные id=%s; внешние/относительные ресурсы=%s" % (sorted(missing), sorted(audit.duplicates), audit.invalid_resources))
    return len(audit.identifiers), len(audit.anchors)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--pandoc", default="pandoc")
    parser.add_argument("--max-embed-mb", type=float, default=16.0)
    parser.add_argument("--strict", action="store_true", help="Fail if a local resource or Markdown anchor is missing, or pandoc reports a warning.")
    parser.add_argument("--check", action="store_true", help="Check the existing handbook against current sources; do not write.")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    output = args.output or root / "STUDENT_GUIDE.html"
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    pandoc = shutil.which(args.pandoc)
    if not pandoc:
        parser.error("Для сборки нужен pandoc. Готовый STUDENT_GUIDE.html можно читать без него.")
    if args.max_embed_mb <= 0:
        parser.error("--max-embed-mb должен быть положительным.")
    builder = HandbookBuilder(root, output, pandoc, int(args.max_embed_mb * 1024 * 1024))
    try:
        result = builder.build()
        identifiers, anchors = audit_html(result)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Не удалось собрать учебник: " + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        return 1
    for warning in sorted(builder.warnings):
        print("Примечание: " + warning, file=sys.stderr)
    if args.strict and builder.warnings:
        print("Строгая проверка не пройдена: исправьте перечисленные ссылки и ресурсы.", file=sys.stderr)
        return 1
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != result:
            print("Учебник требует пересборки: " + str(output), file=sys.stderr)
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result, encoding="utf-8")
    print(("Проверен" if args.check else "Создан") + " учебник: %s; документов: %d; встроенных файлов: %d; якорей: %d/%d." % (output.name, len(builder.documents), len(builder.resources), anchors, identifiers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
