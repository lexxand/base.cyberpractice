#!/usr/bin/env python3
"""Audit unresolved regulation official-source links.

This script is intentionally non-failing for network errors: its job is to make
the remaining non-full imports observable and reproducible, not to block the
site build when an official domain is unreachable from the current environment.
"""

from __future__ import annotations

import json
import html
import re
from pathlib import Path
from posixpath import relpath
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
import urllib3


REGISTRY = Path("scripts/regulation_registry.json")
STATE = Path("scripts/regulation_state.json")
REPORT = Path("docs/regulation/source-audits/latest.md")
TIMEOUT = 12
IPS_TIMEOUT = 25
IPS_BASE = "http://pravo.gov.ru/proxy/ips/"
FULL_IMPORT_KINDS = {"ips", "official_html"}
NON_FULL_KINDS = {"official_card", "official_file", "external_official"}


def cleanup(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def plain_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return cleanup(value)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def check_url(url: str, verify: bool = True) -> dict[str, Any]:
    if not urlparse(url).scheme:
        return {
            "url": url,
            "status": "local-link",
            "detail": "Локальная ссылка внутри базы знаний; внешний HTTP-запрос не выполнялся.",
        }
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
            stream=True,
            verify=verify,
        )
        # Do not download large bodies here; connection and headers are enough.
        response.close()
        return {
            "url": url,
            "status": "ok" if response.ok else "http-error",
            "status_code": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("content-type", ""),
        }
    except requests.RequestException as exc:
        detail = re.sub(r" at 0x[0-9a-fA-F]+", " at 0x…", str(exc))
        return {
            "url": url,
            "status": "network-error",
            "detail": f"{exc.__class__.__name__}: {detail}",
        }


def ips_get(params: dict[str, str]) -> dict[str, Any]:
    url = IPS_BASE + "?" + urlencode(params, encoding="windows-1251")
    try:
        response = requests.get(
            url,
            timeout=IPS_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        text = response.content.decode("windows-1251", errors="replace")
        return {
            "url": url,
            "status": "ok" if response.status_code < 400 else "http-error",
            "status_code": response.status_code,
            "content_length": len(response.content),
            "results": parse_ips_results(text),
            "plain": plain_text(text),
        }
    except requests.RequestException as exc:
        detail = re.sub(r" at 0x[0-9a-fA-F]+", " at 0x…", str(exc))
        return {
            "url": url,
            "status": "network-error",
            "detail": f"{exc.__class__.__name__}: {detail}",
            "results": [],
        }


def parse_ips_results(text: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    chunks = re.split(r"<!--\s*BEGIN элемент списка\s*-->", text, flags=re.I)
    for chunk in chunks[1:]:
        nd_match = re.search(r'name=["\']check_(\d+)["\']', chunk, flags=re.I)
        status_match = re.search(
            r'<span\b[^>]*class=["\']tiny_italic_bold["\'][^>]*>(.*?)</span>',
            chunk,
            flags=re.I | re.S,
        )
        title_match = re.search(
            r'<a\b[^>]*class=["\']bold["\'][^>]*>(.*?)</a>',
            chunk,
            flags=re.I | re.S,
        )
        name_match = re.search(
            r'<span\b[^>]*class=["\']bold["\'][^>]*>(.*?)</span>',
            chunk,
            flags=re.I | re.S,
        )
        if not nd_match:
            continue
        nd = nd_match.group(1)
        name_clean = cleanup(name_match.group(1)) if name_match else ""
        title_clean = cleanup(title_match.group(1)) if title_match else ""
        results.append(
            {
                "nd": nd,
                "status": cleanup(status_match.group(1)) if status_match else "не определён",
                "title": f"{title_clean}. {name_clean}" if name_clean else title_clean,
            }
        )
    if results:
        return results

    blocks = re.findall(
        r"<table\b[^>]*class=[\"'][^\"']*list_elem[^\"']*[\"'][^>]*>(.*?)</table>\s*</td></tr>\s*</table>",
        text,
        flags=re.I | re.S,
    )
    for block in blocks:
        nd_match = re.search(r"nd=(\d+)", block)
        title_match = re.search(
            r"<a\b[^>]*class=[\"']bold[\"'][^>]*>(.*?)</a>",
            block,
            flags=re.I | re.S,
        )
        name_match = re.search(
            r"<span\b[^>]*class=[\"']bold[\"'][^>]*>(.*?)</span>",
            block,
            flags=re.I | re.S,
        )
        status_match = re.search(
            r"<span\b[^>]*class=[\"']tiny_italic_bold[\"'][^>]*>(.*?)</span>",
            block,
            flags=re.I | re.S,
        )
        if not nd_match:
            continue
        title = cleanup(title_match.group(1)) if title_match else ""
        name = cleanup(name_match.group(1)) if name_match else ""
        if name:
            title = f"{title}. {name}" if title else name
        result = {
            "nd": nd_match.group(1),
            "status": cleanup(status_match.group(1)) if status_match else "не определён",
            "title": title or f"nd={nd_match.group(1)}",
        }
        if result not in results:
            results.append(result)
    if results:
        return results

    nds = re.findall(r'name=["\']check_(\d+)["\']', text, flags=re.I)
    doc_type = (
        r"Федеральный закон|Указ Президента|Постановление Правительства|"
        r"Приказ|Доктрина|Методический документ"
    )
    for idx, match in enumerate(
        re.finditer(
            rf"(?:^|\s)(\d+)\s+((?:Действует|Не действует)(?:(?!{doc_type}).)*?)\s+"
            rf"((?:{doc_type}).*?)(?=\s+Официальный интернет-портал|\s+Собрание законодательства|\s+\d+\s+(?:Действует|Не действует)|$)",
            plain_text(text),
            flags=re.I | re.S,
        )
    ):
        nd = nds[idx] if idx < len(nds) else ""
        if not nd:
            continue
        results.append(
            {
                "nd": nd,
                "status": cleanup(match.group(2)) or "не определён",
                "title": cleanup(match.group(3)),
            }
        )
    return results


def title_query(doc: dict[str, Any]) -> str:
    title = doc["title"]
    quoted = re.search(r"«([^»]+)»", title)
    if quoted:
        return quoted.group(1)
    return title


def ips_checks(doc: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    checks: list[tuple[str, dict[str, Any]]] = []
    if doc.get("date") and doc.get("number"):
        checks.append(
            (
                "Точный поиск по дате и номеру",
                ips_get(
                    {
                        "list_itself": "",
                        "x": "0",
                        "y": "0",
                        "bpas": "cd00000",
                        "a7type": "1",
                        "a7date": doc["date"],
                        "a8": doc["number"],
                        "a8type": "2",
                        "sort": "7",
                        "page": "firstlast",
                    }
                ),
            )
        )
    if doc.get("title"):
        params = {
            "list_itself": "",
            "x": "0",
            "y": "0",
            "bpas": "cd00000",
            "a1": title_query(doc),
            "a1type": "1",
            "sort": "7",
            "page": "firstlast",
        }
        if doc.get("date"):
            params["a7type"] = "1"
            params["a7date"] = doc["date"]
        checks.append(("Поиск по наименованию в IPS", ips_get(params)))
        if doc.get("number"):
            broad_params = dict(params)
            broad_params.pop("a7type", None)
            broad_params.pop("a7date", None)
            checks.append(("Поиск по наименованию в IPS без ограничения даты", ips_get(broad_params)))
    return checks


def ips_result_summary(result: dict[str, Any]) -> str:
    if result["status"] == "network-error":
        return result["detail"]
    if result.get("status_code") == 204 or not result.get("results"):
        return f"документы не найдены; HTTP {result.get('status_code')}, bytes={result.get('content_length')}"
    values = []
    for item in result["results"][:5]:
        values.append(f"nd={item['nd']} — {item['status']} — {item['title']}")
    if len(result["results"]) > 5:
        values.append(f"ещё {len(result['results']) - 5}")
    return "<br>".join(md_escape(value) for value in values)


def report_link(doc: dict[str, Any], url: str) -> str:
    if urlparse(url).scheme:
        return url
    source = Path(doc["output"]).parent / url
    return relpath(source.as_posix(), REPORT.parent.as_posix())


def load_state() -> dict[str, Any]:
    if not STATE.exists():
        return {"documents": {}}
    return json.loads(STATE.read_text(encoding="utf-8"))


def non_full_reason(doc: dict[str, Any]) -> str:
    kind = doc.get("kind", "")
    if kind == "official_card":
        return (
            "импортирована официальная карточка/страница метаданных; полный "
            "текст документа в этом источнике не опубликован или требует "
            "отдельного официального источника"
        )
    if kind == "official_file":
        return (
            "зафиксирован официальный файл и его SHA-256; полный текст файла "
            "не извлекается в Markdown до добавления отдельного repeatable "
            "extractor"
        )
    if kind == "external_official":
        return (
            "есть официальные ссылки-кандидаты, но полный официальный источник "
            "пока не получен и не захэширован"
        )
    return "тип источника требует ручной проверки"


def source_links(doc: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    source_url = doc.get("source_url")
    if source_url:
        links.append({"label": "Основной источник записи", "url": source_url})
    seen = {item["url"] for item in links}
    for link in doc.get("official_links", []):
        if link["url"] in seen:
            continue
        links.append({"label": link["label"], "url": link["url"]})
        seen.add(link["url"])
    return links


def should_run_ips_checks(doc: dict[str, Any]) -> bool:
    if doc.get("kind") == "external_official":
        return True
    authority = str(doc.get("authority", "")).lower()
    category = str(doc.get("category", "")).lower()
    if category in {"fstec", "fsb", "roskomnadzor"}:
        return True
    return any(value in authority for value in ["фстэк", "фсб", "роскомнадзор"])


def state_summary(doc: dict[str, Any], state: dict[str, Any]) -> list[str]:
    item = state.get("documents", {}).get(doc["id"], {})
    if not item:
        return ["- Состояние: нет записи в `scripts/regulation_state.json`"]
    lines = [f"- Последняя проверка state: {item.get('checked_at', 'не указана')}"]
    if item.get("sha256"):
        lines.append(f"- SHA-256 источника в state: `{item['sha256']}`")
    if item.get("source_url"):
        lines.append(f"- Source URL в state: {item['source_url']}")
    if item.get("content_type"):
        lines.append(f"- Content-Type файла в state: `{item.get('content_type', '')}`")
    if item.get("size_bytes") is not None:
        lines.append(f"- Размер файла в state: `{item.get('size_bytes')}` байт")
    if item.get("status"):
        lines.append(f"- Статус в state: {item['status']}")
    return lines


def state_item(doc: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return state.get("documents", {}).get(doc["id"], {})


def kind_label(kind: str) -> str:
    return {
        "official_card": "official_card — официальная карточка без полного текста",
        "official_file": "official_file — официальный файл без извлечения текста",
        "external_official": "external_official — внешний официальный источник требует разрешения",
    }.get(kind, kind)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    state = load_state()
    unresolved = [doc for doc in registry if doc.get("kind") in NON_FULL_KINDS]
    kind_counts: dict[str, int] = {}
    for doc in unresolved:
        kind = doc.get("kind", "")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    lines = [
        "# Аудит неполных официальных источников",
        "",
        "Этот отчёт показывает документы, которые пока не импортированы как",
        "полный текущий HTML-текст. Сюда входят официальные карточки,",
        "официальные файлы без извлечения текста и внешние официальные ссылки,",
        "для которых полный источник ещё не получен. Ошибки сети здесь не",
        "являются доказательством отсутствия документа: они фиксируют, что",
        "источник не был доступен из текущей среды проверки.",
        "",
        f"Осталось non-full документов: **{len(unresolved)}**.",
        "",
        "| Класс источника | Количество |",
        "|---|---:|",
    ]
    for kind in sorted(kind_counts):
        lines.append(f"| {kind_label(kind)} | {kind_counts[kind]} |")
    lines.append("")
    for doc in unresolved:
        lines.extend(
            [
                f"## {doc['title']}",
                "",
                f"- Документ: `{doc['id']}`",
                f"- Класс источника: `{doc.get('kind', '')}`",
                f"- Орган: {doc.get('authority', '')}",
                f"- Вид: {doc.get('document_kind', '')}",
                f"- Номер: {doc.get('number', '') or 'не указан'}",
                f"- Дата: {doc.get('date', '')}",
                f"- Почему не full-text: {non_full_reason(doc)}",
                f"- Примечание: {doc.get('note', '')}",
                *state_summary(doc, state),
                "",
                "| Ссылка | Результат | Детали |",
                "|---|---|---|",
            ]
        )
        if doc.get("kind") == "external_official":
            verify = bool(doc.get("tls_verify", True))
            for link in source_links(doc):
                result = check_url(link["url"], verify=verify)
                details = result.get("detail") or (
                    f"HTTP {result.get('status_code')} / {result.get('content_type')} / {result.get('final_url')}"
                )
                lines.append(f"| [{md_escape(link['label'])}]({report_link(doc, link['url'])}) | {result['status']} | {md_escape(details)} |")
        else:
            current_state = state_item(doc, state)
            for link in source_links(doc):
                if link["url"] == current_state.get("source_url"):
                    result = "tracked-by-importer"
                    detail = (
                        "Источник уже проверяется ежедневным "
                        "`scripts/import_regulations.py check` по сохранённому "
                        "SHA-256/метаданным state; live HTTP-проверка здесь "
                        "не выполняется, чтобы не создавать шумные daily-коммиты."
                    )
                else:
                    result = "reference-link"
                    detail = (
                        "Справочная официальная ссылка из реестра; основной "
                        "контроль ведётся по source/state записи выше."
                    )
                lines.append(
                    f"| [{md_escape(link['label'])}]({report_link(doc, link['url'])}) | {result} | {md_escape(detail)} |"
                )
        if should_run_ips_checks(doc):
            lines.extend(
                [
                    "",
                    "### IPS-проверка",
                    "",
                    "| Проверка | IPS-запрос | Результат |",
                    "|---|---|---|",
                ]
            )
            for label, result in ips_checks(doc):
                lines.append(
                    f"| {md_escape(label)} | [запрос]({result['url']}) | {ips_result_summary(result)} |"
                )
        else:
            lines.extend(
                [
                    "",
                    "### IPS-проверка",
                    "",
                    "Не выполнялась: для этого класса источника основной официальный",
                    "контроль ведётся по карточке/файлу профильного регулятора, а не",
                    "по `pravo.gov.ru/proxy/ips`.",
                    "",
                ]
            )
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    while lines and not lines[-1]:
        lines.pop()
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
