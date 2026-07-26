#!/usr/bin/env python3
"""Discover Roskomnadzor orders in the official pravo.gov.ru/proxy/ips index.

The old IPS search endpoint expects Windows-1251 percent-encoded query values.
This script intentionally uses the IPS `list_itself` result page because it
contains official `nd` identifiers and publication metadata.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.parse import quote_from_bytes

import requests


BASE = "http://pravo.gov.ru/proxy/ips/"
QUERY = "Федеральная служба по надзору в сфере связи"
OUTPUT_MD = Path("docs/regulation/russia/roskomnadzor/ips-order-discovery.md")
OUTPUT_JSON = Path("scripts/rkn_order_discovery.json")


def cp1251_quote(value: str) -> str:
    return quote_from_bytes(value.encode("cp1251"))


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def list_url(start: int, size: int) -> str:
    query = cp1251_quote(QUERY)
    return (
        f"{BASE}?list_itself=&x=0&y=0&bpas=cd00000"
        "&a3=&a3type=&a3value="
        "&a6=&a6type=&a6value="
        "&a15=&a15type=&a15value="
        "&a7type=1&a7from=&a7to=&a7date="
        "&a8=&a8type=2"
        f"&a1={query}"
        "&a0="
        "&a16=&a16type=&a16value="
        "&a17=&a17type=&a17value="
        "&a4=&a4type=&a4value="
        "&a23=&a23type=&a23value="
        "&textpres=&sort=7"
        f"&start={start}&lstsize={size}"
    )


def fetch(url: str) -> str:
    response = requests.get(url, timeout=80, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.content.decode("windows-1251", errors="replace")


def parse_list_page(page: str) -> tuple[int | None, list[dict[str, object]]]:
    list_size_match = re.search(r"top\.listSize\s*=\s*(\d+)", page)
    list_size = int(list_size_match.group(1)) if list_size_match else None
    items: list[dict[str, object]] = []
    for chunk in re.split(r"<!-- BEGIN элемент списка -->", page)[1:]:
        chunk = chunk.split("<!-- END элемент списка -->", 1)[0]
        nd_match = re.search(r'name="check_(\d+)"', chunk) or re.search(r"nd=(\d+)", chunk)
        heading_match = re.search(
            r'<a id="link_\d+"[^>]*>(.*?)</a>', chunk, flags=re.I | re.S
        )
        if not nd_match or not heading_match:
            continue
        status_match = re.search(
            r'<span class="tiny_italic_bold">(.*?)</span>', chunk, flags=re.I | re.S
        )
        description_matches = re.findall(
            r'<span class="bold">(.*?)</span>', chunk, flags=re.I | re.S
        )
        publications = re.findall(r"<li class='tiny'>(.*?)</li>", chunk, flags=re.I | re.S)
        heading = clean(heading_match.group(1))
        description = " ".join(clean(value) for value in description_matches)
        if not heading.startswith(
            "Приказ Федеральной службы по надзору в сфере связи, "
            "информационных технологий и массовых коммуникаций от"
        ):
            continue
        items.append(
            {
                "nd": nd_match.group(1),
                "status": clean(status_match.group(1)) if status_match else "",
                "heading": heading,
                "description": description,
                "publications": [clean(value) for value in publications],
                "ips_card": f"{BASE}?docbody=&link_id=0&nd={nd_match.group(1)}&firstDoc=1",
            }
        )
    return list_size, items


def discover() -> tuple[int, list[dict[str, object]]]:
    page_size = 100
    first_page = fetch(list_url(0, page_size))
    total, first_items = parse_list_page(first_page)
    if total is None:
        raise RuntimeError("Cannot determine IPS list size")
    by_nd = {str(item["nd"]): item for item in first_items}
    for start in range(page_size, total, page_size):
        _, page_items = parse_list_page(fetch(list_url(start, page_size)))
        for item in page_items:
            by_nd.setdefault(str(item["nd"]), item)
    return total, list(by_nd.values())


def write_outputs(total: int, orders: list[dict[str, object]]) -> None:
    today = dt.date.today().isoformat()
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "retrieved": today,
                "query": QUERY,
                "ips_total_results": total,
                "rkn_orders_found": len(orders),
                "orders": orders,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "---",
        "id: rkn-ips-order-discovery",
        'title: "Каталог приказов Роскомнадзора, найденных в IPS"',
        "type: discovery-report",
        "category: roskomnadzor",
        f"updated: {today}",
        "review_status: official-ips-discovery",
        "---",
        "",
        "# Каталог приказов Роскомнадзора, найденных в IPS",
        "",
        f"Дата проверки: `{today}`.",
        "",
        "Источник: официальный поиск `pravo.gov.ru/proxy/ips` по полю",
        f"`Наименование` со строкой `{QUERY}`.",
        "",
        f"- Всего результатов IPS по запросу: `{total}`.",
        f"- Приказов Роскомнадзора/совместных приказов, начинающихся с наименования ведомства: `{len(orders)}`.",
        "",
        "!!! note \"Назначение страницы\"",
        "",
        "    Это discovery-каталог, а не список полностью импортированных НПА ИБ.",
        "    В нём есть кадровые, закупочные, связные, рекламные и иные административные",
        "    акты. В основной раздел импортируются полные тексты тех приказов, которые",
        "    относятся к персональным данным, инцидентам и практической ИБ.",
        "",
        "| Дата и номер | Статус IPS | Наименование | `nd` |",
        "|---|---|---|---|",
    ]
    for item in orders:
        heading = str(item["heading"])
        short = heading.replace(
            "Приказ Федеральной службы по надзору в сфере связи, информационных технологий и массовых коммуникаций от ",
            "",
        )
        description = str(item["description"])
        if description:
            title = f"{heading}. {description}"
        else:
            title = heading
        title = title.replace("|", "\\|")
        lines.append(
            f"| {short.replace('|', '\\|')} | {str(item['status']).replace('|', '\\|')} | "
            f"[{title}]({item['ips_card']}) | `{item['nd']}` |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    total, orders = discover()
    write_outputs(total, orders)
    print(f"IPS total results: {total}")
    print(f"Roskomnadzor orders found: {len(orders)}")
    print(OUTPUT_MD)
    print(OUTPUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
