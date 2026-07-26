#!/usr/bin/env python3
"""Audit unresolved regulation official-source links.

This script is intentionally non-failing for network errors: its job is to make
the remaining non-full imports observable and reproducible, not to block the
site build when an official domain is unreachable from the current environment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from posixpath import relpath
from typing import Any
from urllib.parse import urlparse

import requests


REGISTRY = Path("scripts/regulation_registry.json")
REPORT = Path("docs/regulation/source-audits/latest.md")
TIMEOUT = 12


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
            lines.append(f"| [{link['label']}]({report_link(doc, link['url'])}) | {result['status']} | {details} |")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
