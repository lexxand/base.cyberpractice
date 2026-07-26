#!/usr/bin/env python3
"""Import and check regulation documents from official sources.

The primary source for Russian legal texts is pravo.gov.ru/proxy/ips. The
script intentionally preserves the official Word-generated HTML fragment instead
of flattening it to plain Markdown: IPS uses CSS classes for footnotes,
subscripts, alignment and table structure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


BASE = "http://pravo.gov.ru/proxy/ips/"
REGISTRY = Path("scripts/regulation_registry.json")
STATE = Path("scripts/regulation_state.json")


@dataclass(frozen=True)
class Edition:
    rdk: str
    label: str
    pending: list[str]


def get(url: str, timeout: int = 40) -> bytes:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.content


def decode_cp1251(content: bytes) -> str:
    return content.decode("windows-1251", errors="replace")


def cleanup(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def plain_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return cleanup(value)


def yaml(value: Any) -> str:
    if value is None:
        return '""'
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def search_nd(date: str, number: str) -> tuple[str, str, str, str]:
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
    text = decode_cp1251(get(BASE + "?" + urlencode(params), timeout=20))
    nds = sorted(set(re.findall(r"nd=(\d+)", text)))
    if not nds:
        raise RuntimeError(f"Cannot find nd for {date} No. {number}")
    plain = plain_text(text)
    title_match = re.search(
        r"1\s+(?:Действует|Не действует).*?((?:Федеральный закон|Указ Президента|Постановление Правительства|Приказ|Доктрина).+?)(?:Официальный интернет-портал|Собрание законодательства|\"Российская газета\"|$)",
        plain,
    )
    status_match = re.search(r"\b(Действует[^ФУПДО]+|Не действует[^ФУПДО]+)", plain)
    publication_match = re.search(
        r"Официальный интернет-портал правовой информации .*? от\s*([^,]+?)\s*,\s*ст\.\s*([0-9]+)",
        plain,
    )
    return (
        nds[0],
        cleanup(title_match.group(1)) if title_match else "",
        cleanup(status_match.group(1)) if status_match else "",
        publication_match.group(2) if publication_match else "",
    )


def resolve_edition(nd: str) -> tuple[Edition, str, str]:
    card_url = f"{BASE}?docbody=&link_id=0&nd={nd}&firstDoc=1"
    text = decode_cp1251(get(card_url, timeout=40))
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
    title_match = re.search(r"<title>(.*?)</title>", text, flags=re.I | re.S)
    title = cleanup(title_match.group(1)) if title_match else ""
    status = "Не определен"
    plain = plain_text(text)
    status_match = re.search(r"\b(Действует[^<]+?|Не действует[^<]+?)\s+(?:Федеральный закон|Указ|Постановление|Приказ|Доктрина|Об )", plain)
    if status_match:
        status = cleanup(status_match.group(1))
    if selected:
        value, label = selected.groups()
        return Edition(value.split(",", 1)[0], cleanup(label), pending), title, status
    iframe = re.search(r"<iframe[^>]+src=['\"]([^'\"]*doc_itself[^'\"]+)['\"]", text, re.I)
    if not iframe:
        raise RuntimeError(f"Cannot find doc_itself iframe for nd={nd}")
    rdk_match = re.search(r"rdk=(\d+)", html.unescape(iframe.group(1)))
    rdk = rdk_match.group(1) if rdk_match else "0"
    return Edition(rdk, "Исходная редакция" if rdk == "0" else f"rdk={rdk}", pending), title, status


def list_editions(nd: str) -> list[Edition]:
    card_url = f"{BASE}?docbody=&link_id=0&nd={nd}&firstDoc=1"
    text = decode_cp1251(get(card_url, timeout=40))
    options = re.findall(
        r"<option[^>]+value=['\"]([^'\"]+)['\"][^>]*>(.*?)</option>",
        text,
        flags=re.I | re.S,
    )
    editions: list[Edition] = []
    pending: list[str] = []
    for value, option_text in options:
        label = cleanup(option_text)
        if value == "n" or "не готов" in label.lower():
            pending.append(label)
            continue
        rdk = value.split(",", 1)[0]
        editions.append(Edition(rdk=rdk, label=label, pending=[]))
    for edition in editions:
        edition.pending.extend(pending)
    return editions


def fetch_document(nd: str, rdk: str) -> tuple[str, bytes, str]:
    url = f"{BASE}?doc_itself=&nd={nd}&page=1&rdk={rdk}&link_id=0"
    raw = get(url, timeout=60)
    return decode_cp1251(raw), raw, url


def extract_document_html(page: str) -> str:
    marker = 'id="text_content"'
    start = page.find(marker)
    if start == -1:
        raise RuntimeError("Cannot find text_content")
    fragment = page[start:]
    body_start = re.search(r"<body\b[^>]*>", fragment, re.I)
    if body_start:
        fragment = fragment[body_start.end() :]
    body_end = re.search(r"</body>", fragment, re.I)
    if body_end:
        fragment = fragment[: body_end.start()]
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    fragment = re.sub(r"\s+", " ", fragment).strip()
    fragment = re.sub(r"</(p|table|div)>\s*<", r"</\1>\n<", fragment, flags=re.I)
    fragment = re.sub(r">\s*<(p|table|div)\b", r">\n<\1", fragment, flags=re.I)
    return fragment


def publication_url(publication_number: str) -> str:
    return f"http://publication.pravo.gov.ru/document/{publication_number}"


def import_ips(doc: dict[str, Any]) -> dict[str, Any]:
    nd = doc.get("nd")
    searched_title = ""
    searched_status = ""
    searched_publication = ""
    if not nd:
        nd, searched_title, searched_status, searched_publication = search_nd(
            doc["date"], doc["number"]
        )
    edition, card_title, card_status = resolve_edition(nd)
    page, raw, source_url = fetch_document(nd, edition.rdk)
    doc_html = extract_document_html(page)
    sha256 = hashlib.sha256(raw).hexdigest()
    today = dt.date.today().isoformat()
    title = doc.get("title") or card_title or searched_title
    status = card_status if card_status != "Не определен" else searched_status
    publication_number = doc.get("publication_number") or searched_publication
    output = Path(doc["output"])
    output.parent.mkdir(parents=True, exist_ok=True)

    pending_block = ""
    if edition.pending:
        pending_block = (
            "\n!!! warning \"Неподготовленные редакции в официальной базе\"\n\n"
            + "\n".join(f"    - {item}" for item in edition.pending)
            + "\n"
        )
    links = [
        f"- [Консолидированный текст в pravo.gov.ru/proxy/ips]({source_url})",
        f"- [Карточка документа в pravo.gov.ru/proxy/ips]({BASE}?docbody=&link_id=0&nd={nd}&firstDoc=1)",
    ]
    if publication_number:
        links.append(f"- [Официальное опубликование]({publication_url(publication_number)})")
    body = f"""---
id: {doc["id"]}
title: {yaml(title)}
type: normative-document
category: {yaml(doc.get("category", ""))}
authority: {yaml(doc.get("authority", ""))}
document_kind: {yaml(doc.get("document_kind", ""))}
document_number: {yaml(doc.get("number", ""))}
document_date: {doc.get("date_iso", "")}
legal_status: {yaml(status)}
source: "pravo.gov.ru/proxy/ips"
source_nd: {yaml(nd)}
source_rdk: {yaml(edition.rdk)}
source_edition: {yaml(edition.label)}
source_retrieved: {today}
source_sha256: {yaml(sha256)}
updated: {today}
review_status: imported
---

# {title}

!!! info "Источник и редакция"

    Текст импортирован {today} из официальной базы `pravo.gov.ru/proxy/ips`.
    Использована редакция: `{edition.label}` (`nd={nd}`, `rdk={edition.rdk}`).
    Статус по официальной базе: `{status}`.
{pending_block}
## Карточка документа

| Поле | Значение |
|---|---|
| Орган | {doc.get("authority", "")} |
| Вид документа | {doc.get("document_kind", "")} |
| Номер | {doc.get("number", "")} |
| Дата принятия | {doc.get("date", "")} |
| Статус в официальной базе | {status} |
| Редакция | {edition.label} |
| `nd` | `{nd}` |
| `rdk` | `{edition.rdk}` |
| Номер опубликования | `{publication_number or "не определен"}` |
| SHA-256 HTML-источника | `{sha256}` |

## Официальные ссылки

{chr(10).join(links)}

## Полный текст документа

<div class="pravo-doc" markdown="0">

{doc_html}

</div>
"""
    output.write_text(body, encoding="utf-8")
    return {
        "id": doc["id"],
        "kind": "ips",
        "output": str(output),
        "title": title,
        "nd": nd,
        "rdk": edition.rdk,
        "edition": edition.label,
        "status": status,
        "sha256": sha256,
        "source_url": source_url,
        "pending": edition.pending,
        "checked_at": today,
    }


def import_external(doc: dict[str, Any]) -> dict[str, Any]:
    today = dt.date.today().isoformat()
    output = Path(doc["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    links = "\n".join(f"- [{item['label']}]({item['url']})" for item in doc.get("official_links", []))
    body = f"""---
id: {doc["id"]}
title: {yaml(doc["title"])}
type: normative-document
category: {yaml(doc.get("category", ""))}
authority: {yaml(doc.get("authority", ""))}
document_kind: {yaml(doc.get("document_kind", ""))}
document_number: {yaml(doc.get("number", ""))}
document_date: {doc.get("date_iso", "")}
legal_status: {yaml(doc.get("legal_status", "Требует проверки"))}
source: {yaml(doc.get("source", "external_official"))}
source_retrieved: {today}
updated: {today}
review_status: external-official-card
---

# {doc["title"]}

!!! warning "Полный текст не импортирован"

    Для этого документа пока не найден подтвержденный `nd` в `pravo.gov.ru/proxy/ips`.
    Страница является карточкой официального источника и не помечается как полный
    актуальный текст.

## Карточка документа

| Поле | Значение |
|---|---|
| Орган | {doc.get("authority", "")} |
| Вид документа | {doc.get("document_kind", "")} |
| Номер | {doc.get("number", "")} |
| Дата | {doc.get("date", "")} |
| Статус | {doc.get("legal_status", "Требует проверки")} |

## Официальные ссылки

{links or "- Официальная ссылка требует уточнения."}

## Примечание

{doc.get("note", "Документ требует ручного уточнения официального источника.")}
"""
    output.write_text(body, encoding="utf-8")
    return {
        "id": doc["id"],
        "kind": "external_official",
        "output": str(output),
        "title": doc["title"],
        "checked_at": today,
        "status": doc.get("legal_status", "Требует проверки"),
    }


def load_registry(path: Path = REGISTRY) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state() -> dict[str, Any]:
    if not STATE.exists():
        return {"documents": {}}
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(results: list[dict[str, Any]]) -> None:
    state = load_state()
    documents = state.setdefault("documents", {})
    for result in results:
        documents[result["id"]] = result
    state["updated"] = dt.date.today().isoformat()
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def import_all(ids: set[str] | None = None) -> list[dict[str, Any]]:
    results = []
    for doc in load_registry():
        if ids and doc["id"] not in ids:
            continue
        if doc.get("kind") == "ips":
            results.append(import_ips(doc))
        else:
            results.append(import_external(doc))
        print(f"{results[-1]['id']}: {results[-1]['kind']} -> {results[-1]['output']}")
    save_state(results)
    return results


def text_digest_from_html(doc_html: str) -> str:
    text = plain_text(doc_html)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def document_lines(document_html: str) -> list[str]:
    value = re.sub(r"</(p|tr|table|div)>\s*", "\n", document_html, flags=re.I)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    lines = [cleanup(line) for line in value.splitlines()]
    return [line for line in lines if line]


def check_updates(ids: set[str] | None = None) -> list[dict[str, Any]]:
    state = load_state().get("documents", {})
    changes = []
    for doc in load_registry():
        if doc.get("kind") != "ips":
            continue
        if ids and doc["id"] not in ids:
            continue
        old = state.get(doc["id"], {})
        nd = doc.get("nd") or old.get("nd")
        if not nd:
            nd, _, _, _ = search_nd(doc["date"], doc["number"])
        edition, title, status = resolve_edition(nd)
        page, raw, source_url = fetch_document(nd, edition.rdk)
        sha256 = hashlib.sha256(raw).hexdigest()
        if old.get("sha256") and old.get("sha256") != sha256:
            old_lines: list[str] = []
            try:
                old_lines = document_lines(Path(doc["output"]).read_text(encoding="utf-8"))
            except FileNotFoundError:
                pass
            new_lines = document_lines(extract_document_html(page))
            diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
            added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
            removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
            examples = []
            for line in diff:
                if line.startswith("+") and not line.startswith("+++"):
                    examples.append("добавлено: " + line[1:220])
                if line.startswith("-") and not line.startswith("---"):
                    examples.append("удалено: " + line[1:220])
                if len(examples) >= 4:
                    break
            changes.append(
                {
                    "id": doc["id"],
                    "title": doc.get("title") or title,
                    "old_rdk": old.get("rdk"),
                    "new_rdk": edition.rdk,
                    "old_sha256": old.get("sha256"),
                    "new_sha256": sha256,
                    "summary": f"Изменилась официальная HTML-редакция: добавлено абзацев/строк: {added}, удалено: {removed}.",
                    "examples": examples,
                    "source_url": source_url,
                    "status": status,
                }
            )
    return changes


def summarize_diff(old_html: str, new_html: str) -> tuple[str, list[str]]:
    diff = list(difflib.unified_diff(document_lines(old_html), document_lines(new_html), n=0))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    examples = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            examples.append("Добавлено: " + line[1:220])
        if line.startswith("-") and not line.startswith("---"):
            examples.append("Удалено: " + line[1:220])
        if len(examples) >= 4:
            break
    if added == 0 and removed == 0:
        return "Текстовая часть без изменений; вероятно изменилось служебное HTML-оформление.", []
    parts = []
    if added:
        parts.append(f"добавлено строк: {added}")
    if removed:
        parts.append(f"удалено строк: {removed}")
    return "Изменился текст документа: " + ", ".join(parts) + ".", examples


def history_report(doc_id: str, limit: int, output: Path) -> None:
    docs = {doc["id"]: doc for doc in load_registry()}
    doc = docs[doc_id]
    if doc.get("kind") != "ips":
        raise RuntimeError(f"{doc_id} is not an IPS document")
    nd = doc.get("nd")
    if not nd:
        nd, _, _, _ = search_nd(doc["date"], doc["number"])
    editions = list_editions(nd)
    if len(editions) < 2:
        body = f"# История редакций: {doc['title']}\n\nВ IPS найдена только одна подготовленная редакция.\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
        print(output)
        return
    pairs = list(zip(editions, editions[1:]))[-limit:]
    lines = [f"# История редакций: {doc['title']}", "", f"`nd={nd}`", ""]
    for old, new in pairs:
        old_page, _, old_url = fetch_document(nd, old.rdk)
        new_page, _, new_url = fetch_document(nd, new.rdk)
        summary, examples = summarize_diff(extract_document_html(old_page), extract_document_html(new_page))
        lines.extend(
            [
                f"## {old.label} → {new.label}",
                "",
                f"- Старый текст: {old_url}",
                f"- Новый текст: {new_url}",
                f"- Короткая сводка: {summary}",
                "",
            ]
        )
        if examples:
            lines.extend(["Примеры изменений:", ""])
            lines.extend(f"- {example}" for example in examples)
            lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output)


def write_report(changes: list[dict[str, Any]], output: Path) -> None:
    today = dt.date.today().isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not changes:
        body = f"# Проверка изменений НПА за {today}\n\nИзменений в импортированных IPS-документах не обнаружено.\n"
    else:
        lines = [f"# Проверка изменений НПА за {today}", ""]
        for item in changes:
            lines.extend(
                [
                    f"## {item['title']}",
                    "",
                    f"- Документ: `{item['id']}`",
                    f"- Редакция: `{item['old_rdk']}` -> `{item['new_rdk']}`",
                    f"- Источник: {item['source_url']}",
                    f"- Сводка: {item['summary']}",
                    "",
                ]
            )
            if item.get("examples"):
                lines.extend(["Примеры изменений:", ""])
                lines.extend(f"- {example}" for example in item["examples"])
                lines.append("")
        body = "\n".join(lines)
    output.write_text(body, encoding="utf-8")
    print(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    import_parser = sub.add_parser("import")
    import_parser.add_argument("--id", action="append", dest="ids")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--id", action="append", dest="ids")
    check_parser.add_argument("--report", default="")
    history_parser = sub.add_parser("history")
    history_parser.add_argument("--id", required=True)
    history_parser.add_argument("--limit", type=int, default=3)
    history_parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.command == "import":
        ids = set(args.ids or []) or None
        import_all(ids)
        return 0
    if args.command == "history":
        history_report(args.id, args.limit, Path(args.report))
        return 0
    ids = set(args.ids or []) or None
    try:
        changes = check_updates(ids)
    except Exception as exc:
        print(f"Regulation update check failed: {exc}", file=sys.stderr)
        return 2
    if args.report:
        write_report(changes, Path(args.report))
    else:
        print(json.dumps(changes, ensure_ascii=False, indent=2))
    return 1 if changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
