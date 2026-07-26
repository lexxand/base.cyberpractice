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


REGISTRY = Path("scripts/regulation_registry.json")
REPORT = Path("docs/regulation/source-audits/latest.md")
TIMEOUT = 12
IPS_TIMEOUT = 25
IPS_BASE = "http://pravo.gov.ru/proxy/ips/"


def cleanup(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def plain_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return cleanup(value)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def check_url(url: str) -> dict[str, Any]:
    if not urlparse(url).scheme:
        return {
            "url": url,
            "status": "local-link",
            "detail": "Локальная ссылка внутри базы знаний; внешний HTTP-запрос не выполнялся.",
        }
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
            stream=True,
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


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    unresolved = [doc for doc in registry if doc.get("kind") == "external_official"]
    lines = [
        "# Аудит внешних официальных источников",
        "",
        "Этот отчёт показывает документы, которые пока не импортированы как полный",
        "текст или проверяемый официальный HTML/файл. Ошибки сети здесь не являются",
        "доказательством отсутствия документа: они фиксируют, что источник не был",
        "доступен из текущей среды проверки.",
        "",
        f"Осталось external-документов: **{len(unresolved)}**.",
        "",
    ]
    for doc in unresolved:
        lines.extend(
            [
                f"## {doc['title']}",
                "",
                f"- Документ: `{doc['id']}`",
                f"- Орган: {doc.get('authority', '')}",
                f"- Вид: {doc.get('document_kind', '')}",
                f"- Номер: {doc.get('number', '') or 'не указан'}",
                f"- Дата: {doc.get('date', '')}",
                f"- Примечание: {doc.get('note', '')}",
                "",
                "| Ссылка | Результат | Детали |",
                "|---|---|---|",
            ]
        )
        for link in doc.get("official_links", []):
            result = check_url(link["url"])
            details = result.get("detail") or (
                f"HTTP {result.get('status_code')} / {result.get('content_type')} / {result.get('final_url')}"
            )
            lines.append(f"| [{md_escape(link['label'])}]({report_link(doc, link['url'])}) | {result['status']} | {md_escape(details)} |")
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
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
