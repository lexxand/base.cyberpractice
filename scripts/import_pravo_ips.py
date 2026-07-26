#!/usr/bin/env python3
"""Import current consolidated text from pravo.gov.ru/proxy/ips."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

import requests


BASE = "http://pravo.gov.ru/proxy/ips/"


@dataclass(frozen=True)
class Target:
    authority: str
    date: str
    number: str
    output: Path


@dataclass(frozen=True)
class SearchResult:
    nd: str
    title: str
    status: str
    publication: str
    publication_number: str


@dataclass(frozen=True)
class Edition:
    rdk: str
    label: str
    pending: list[str]


class MarkdownExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
        self.in_table = 0
        self.table_html: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_s = "".join(
            f' {name}="{html.escape(value or "", quote=True)}"' for name, value in attrs
        )
        if tag in {"script", "style", "head", "xml"}:
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "table":
            self._blank()
            self.in_table += 1
        if self.in_table:
            self.table_html.append(f"<{tag}{attrs_s}>")
            return
        if tag in {"p", "div", "section"}:
            self._blank()
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"li"}:
            self._blank()
            self.parts.append("- ")
        elif tag in {"b", "strong"}:
            self.parts.append("**")
        elif tag in {"i", "em"}:
            self.parts.append("*")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip:
            if tag in {"script", "style", "head", "xml"}:
                self.skip -= 1
            return
        if self.in_table:
            self.table_html.append(f"</{tag}>")
            if tag == "table":
                self.in_table -= 1
                if self.in_table == 0:
                    self.parts.append(clean_raw_html("".join(self.table_html)))
                    self.table_html.clear()
                    self._blank()
            return
        if tag in {"p", "div", "section", "li"}:
            self._blank()
        elif tag in {"b", "strong"}:
            self.parts.append("**")
        elif tag in {"i", "em"}:
            self.parts.append("*")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.in_table:
            self.table_html.append(html.escape(data))
            return
        self.parts.append(data.replace("\xa0", " "))

    def get_markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip() + "\n"

    def _blank(self) -> None:
        if not self.parts:
            return
        current = "".join(self.parts[-3:])
        if not current.endswith("\n\n"):
            if current.endswith("\n"):
                self.parts.append("\n")
            else:
                self.parts.append("\n\n")


def clean_raw_html(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*(</(?:tr|td|th|table)>)\s*", r"\1", value)
    value = re.sub(r"\s*(<(?:tr|td|th|table)\b[^>]*>)\s*", r"\1", value)
    return value.strip()


def get(url: str) -> bytes:
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    return response.content


def decode_cp1251(content: bytes) -> str:
    return content.decode("windows-1251", errors="replace")


def search(date: str, number: str) -> SearchResult:
    params = {
        "list_itself": "",
        "x": "0",
        "y": "0",
        "bpas": "cd00000",
        "a7type": "1",
        "a7date": date,
        "a8": number,
        "a8type": "2",
        "sort": "7",
        "page": "firstlast",
    }
    text = decode_cp1251(get(BASE + "?" + urlencode(params)))
    nds = sorted(set(re.findall(r"nd=(\d+)", text)))
    if not nds:
        raise RuntimeError(f"Cannot find nd for {date} No. {number}")
    plain = plain_text(text)
    status_match = re.search(r"\b(Действует[^П]+?)\s+Приказ", plain)
    title_match = re.search(r"(Приказ .+?)(?: Официальный интернет-портал|$)", plain)
    publication_match = re.search(
        r"Официальный интернет-портал правовой информации .*? от\s*([^,]+?)\s*,\s*ст\.\s*([0-9]+)",
        plain,
    )
    return SearchResult(
        nd=nds[0],
        title=title_match.group(1).strip() if title_match else f"Приказ от {date} № {number}",
        status=status_match.group(1).strip() if status_match else "Не определен",
        publication=publication_match.group(1).strip() if publication_match else "",
        publication_number=publication_match.group(2).strip() if publication_match else "",
    )


def resolve_edition(nd: str) -> Edition:
    url = f"{BASE}?docbody=&link_id=0&nd={nd}&firstDoc=1"
    text = decode_cp1251(get(url))
    options = re.findall(
        r"<option[^>]+value=['\"]([^'\"]+)['\"][^>]*>(.*?)</option>",
        text,
        flags=re.I | re.S,
    )
    selected = re.search(
        r"<option[^>]+value=['\"]([^'\"]+)['\"][^>]*selected[^>]*>(.*?)</option>",
        text,
        flags=re.I | re.S,
    )
    pending = [
        cleanup(option_text)
        for _, option_text in options
        if "не готов" in cleanup(option_text).lower()
    ]
    if selected:
        value, label = selected.groups()
        return Edition(rdk=value.split(",", 1)[0], label=cleanup(label), pending=pending)
    iframe = re.search(r"<iframe[^>]+src=['\"]([^'\"]*doc_itself[^'\"]+)['\"]", text, re.I)
    if not iframe:
        raise RuntimeError(f"Cannot find doc_itself iframe for nd={nd}")
    rdk_match = re.search(r"rdk=(\d+)", html.unescape(iframe.group(1)))
    rdk = rdk_match.group(1) if rdk_match else "0"
    return Edition(rdk=rdk, label="Исходная редакция" if rdk == "0" else f"rdk={rdk}", pending=pending)


def fetch_document(nd: str, rdk: str) -> tuple[str, bytes, str]:
    url = f"{BASE}?doc_itself=&nd={nd}&page=1&rdk={rdk}&link_id=0"
    content = get(url)
    return decode_cp1251(content), content, url


def extract_document_html(page: str) -> str:
    marker = 'id="text_content"'
    start = page.find(marker)
    if start == -1:
        raise RuntimeError("Cannot find text_content")
    fragment = page[start:]
    body_start = re.search(r"<body\b[^>]*>", fragment, re.I)
    if body_start:
        fragment = fragment[body_start.end() :]
    body_end_match = re.search(r"</body>", fragment, re.I)
    body_end = body_end_match.start() if body_end_match else -1
    if body_end != -1:
        fragment = fragment[:body_end]
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    fragment = re.sub(r"\s+", " ", fragment).strip()
    fragment = re.sub(r"</(p|table|div)>\s*<", r"</\1>\n<", fragment, flags=re.I)
    fragment = re.sub(r">\s*<(p|table|div)\b", r">\n<\1", fragment, flags=re.I)
    return fragment


def to_markdown(document_html: str) -> str:
    parser = MarkdownExtractor()
    parser.feed(document_html)
    return parser.get_markdown()


def plain_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return cleanup(value)


def cleanup(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def slug_id(authority: str, number: str, date: str) -> str:
    prefix = "fstec" if "ФСТЭК" in authority else "fsb" if "ФСБ" in authority else "reg"
    year = date.rsplit(".", 1)[-1]
    return f"{prefix}-order-{number}-{year}"


def yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_page(target: Target) -> tuple[str, SearchResult, Edition, str]:
    found = search(target.date, target.number)
    edition = resolve_edition(found.nd)
    page, raw, doc_url = fetch_document(found.nd, edition.rdk)
    doc_html = extract_document_html(page)
    today = dt.date.today().isoformat()
    sha256 = hashlib.sha256(raw).hexdigest()
    publication_url = (
        f"http://publication.pravo.gov.ru/document/{found.publication_number}"
        if found.publication_number
        else ""
    )
    pending_note = "\n".join(f"- {item}" for item in edition.pending)
    pending_block = (
        "\n!!! warning \"Неподготовленные редакции в официальной базе\"\n\n"
        + "\n".join(f"    - {item}" for item in edition.pending)
        + "\n"
        if edition.pending
        else ""
    )
    links = [
        f"- [Консолидированный текст в pravo.gov.ru/proxy/ips]({doc_url})",
        f"- [Карточка документа в pravo.gov.ru/proxy/ips]({BASE}?docbody=&link_id=0&nd={found.nd}&firstDoc=1)",
    ]
    if publication_url:
        links.append(f"- [Официальное опубликование]({publication_url})")
    header = f"""---
id: {slug_id(target.authority, target.number, target.date)}
title: {yaml(target.authority + " № " + target.number + " от " + target.date)}
type: normative-document
authority: {yaml(target.authority)}
document_number: {yaml(target.number)}
document_date: {dt.datetime.strptime(target.date, "%d.%m.%Y").date().isoformat()}
legal_status: {yaml(found.status)}
source: {yaml("pravo.gov.ru/proxy/ips")}
source_nd: {yaml(found.nd)}
source_rdk: {yaml(edition.rdk)}
source_edition: {yaml(edition.label)}
source_retrieved: {today}
source_sha256: {yaml(sha256)}
updated: {today}
review_status: imported
---

# {target.authority} № {target.number} от {target.date}

!!! info "Источник и редакция"

    Текст импортирован {today} из официальной базы `pravo.gov.ru/proxy/ips`.
    Использована редакция: `{edition.label}` (`nd={found.nd}`, `rdk={edition.rdk}`).
    Статус по официальному поиску: `{found.status}`.
{pending_block}
## Карточка документа

| Поле | Значение |
|---|---|
| Орган | {target.authority} |
| Номер | {target.number} |
| Дата принятия | {target.date} |
| Статус в официальной базе | {found.status} |
| Редакция | {edition.label} |
| `nd` | `{found.nd}` |
| `rdk` | `{edition.rdk}` |
| Официальное опубликование | {found.publication or "Не определено"} |
| Номер опубликования | `{found.publication_number or "не определен"}` |
| SHA-256 HTML-источника | `{sha256}` |

## Официальные ссылки

{chr(10).join(links)}

## Полный текст документа

<div class="pravo-doc" markdown="0">

"""
    if pending_note:
        header += "<!-- pending editions:\n" + pending_note + "\n-->\n\n"
    return header + doc_html.strip() + "\n\n</div>\n", found, edition, doc_url


def parse_target(raw: str) -> Target:
    authority, date, number, output = raw.split("|", 3)
    return Target(authority=authority, date=date, number=number, output=Path(output))


def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        nargs="+",
        help="AUTHORITY|DD.MM.YYYY|NUMBER|OUTPUT.md",
    )
    args = parser.parse_args(list(argv))
    for raw_target in args.target:
        target = parse_target(raw_target)
        content, found, edition, doc_url = build_page(target)
        target.output.parent.mkdir(parents=True, exist_ok=True)
        target.output.write_text(content, encoding="utf-8")
        print(
            f"{target.output}: nd={found.nd} rdk={edition.rdk} status={found.status} url={doc_url}"
        )
        if edition.pending:
            print("  pending: " + "; ".join(edition.pending))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
