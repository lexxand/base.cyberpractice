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
REGISTRY = Path("scripts/regulation_registry.json")

THEME_RULES = [
    (
        "персональные данные",
        [
            r"персональн\w+\s+данн",
            r"152-фз",
            r"обработк\w+\s+персональн",
        ],
    ),
    ("инциденты ПДн", [r"инцидент\w+.*персональн\w+\s+данн"]),
    ("обезличивание ПДн", [r"обезличив"]),
    ("трансграничная передача ПДн", [r"трансграничн"]),
    (
        "надзор/проверочные листы ПДн",
        [
            r"контрол\w+\s*\(надзор\w*\).*персональн\w+\s+данн",
            r"проверочн\w+\s+лист.*персональн\w+\s+данн",
        ],
    ),
    (
        "149-ФЗ / ограничение доступа",
        [
            r"149-фз",
            r"доступ.*ограничен",
            r"единый реестр.*сайт",
            r"доменных имен",
            r"сетевых адрес",
            r"поисков\w+\s+систем",
        ],
    ),
    (
        "интернет-реклама",
        [
            r"реклам",
            r"оператор\w+\s+рекламн\w+\s+данн",
        ],
    ),
    (
        "связь/лицензирование",
        [
            r"лицензировани\w+.*связ",
            r"услуг\w+\s+связ",
            r"сеть связи",
            r"радиочастот",
        ],
    ),
    (
        "СМИ/вещание",
        [
            r"телерадиовещ",
            r"средств\w+\s+массовой информации",
            r"сми",
        ],
    ),
    (
        "служебное/кадры/закупки",
        [
            r"гражданск\w+\s+служб",
            r"должност",
            r"доходах",
            r"имуществ",
            r"конкурс",
            r"закуп",
            r"финансов",
            r"служебн",
            r"аттестационн",
            r"квалификационн",
            r"денежн\w+\s+содержан",
            r"пожарн\w+\s+безопасност",
            r"гражданск\w+\s+оборон",
        ],
    ),
]

CORE_THEMES = {
    "персональные данные",
    "инциденты ПДн",
    "обезличивание ПДн",
    "трансграничная передача ПДн",
    "надзор/проверочные листы ПДн",
}

WATCH_THEMES = {
    "149-ФЗ / ограничение доступа",
    "интернет-реклама",
}


def cp1251_quote(value: str) -> str:
    return quote_from_bytes(value.encode("cp1251"))


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def registry_by_nd() -> dict[str, dict[str, object]]:
    if not REGISTRY.exists():
        return {}
    documents = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {str(doc["nd"]): doc for doc in documents if doc.get("nd")}


def rkn_registry_documents() -> list[dict[str, object]]:
    if not REGISTRY.exists():
        return []
    documents = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return [
        doc
        for doc in documents
        if doc.get("category") == "roskomnadzor" and doc.get("document_kind") == "Приказ"
    ]


def classify_order(item: dict[str, object], registered: dict[str, dict[str, object]]) -> None:
    text = f"{item['heading']} {item.get('description', '')}".lower().replace("ё", "е")
    themes = []
    for theme, patterns in THEME_RULES:
        if any(re.search(pattern, text) for pattern in patterns):
            themes.append(theme)
    if not themes:
        themes.append("прочее")
    item["themes"] = themes

    nd = str(item["nd"])
    if nd in registered:
        doc = registered[nd]
        item["registry_status"] = "в основном реестре"
        item["registry_id"] = doc.get("id", "")
        item["registry_output"] = doc.get("output", "")
    elif CORE_THEMES.intersection(themes):
        item["registry_status"] = "кандидат для ИБ/ПДн-реестра"
        item["registry_id"] = ""
        item["registry_output"] = ""
    elif WATCH_THEMES.intersection(themes):
        item["registry_status"] = "смежная тема, нужна ручная оценка"
        item["registry_id"] = ""
        item["registry_output"] = ""
    else:
        item["registry_status"] = "вне текущего ИБ/ПДн-ядра"
        item["registry_id"] = ""
        item["registry_output"] = ""


def order_sort_key(item: dict[str, object]) -> tuple[str, str]:
    date_iso = str(item.get("date_iso", ""))
    if not date_iso:
        match = re.search(r"от\s+(\d{2})\.(\d{2})\.(\d{4})", str(item.get("heading", "")))
        if match:
            date_iso = f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return date_iso, str(item.get("nd", ""))


def merge_registry_backfill(orders: list[dict[str, object]]) -> list[dict[str, object]]:
    by_nd = {str(order["nd"]): order for order in orders}
    for order in by_nd.values():
        order["discovery_source"] = "IPS a1-запрос по наименованию ведомства"
    for doc in rkn_registry_documents():
        nd = str(doc.get("nd", ""))
        if not nd or nd in by_nd:
            continue
        title = str(doc["title"])
        quoted = re.search(r"«([^»]+)»", title)
        description = quoted.group(1) if quoted else title
        heading = (
            f"Приказ Роскомнадзора от {doc.get('date', '')} № {doc.get('number', '')}"
        )
        by_nd[nd] = {
            "nd": nd,
            "status": "см. карточку IPS",
            "heading": heading,
            "description": description,
            "publications": [],
            "ips_card": f"{BASE}?docbody=&link_id=0&nd={nd}&firstDoc=1",
            "date_iso": doc.get("date_iso", ""),
            "discovery_source": "backfill из основного реестра по IPS nd",
        }
    return sorted(by_nd.values(), key=order_sort_key, reverse=True)


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


def write_outputs(total: int, orders: list[dict[str, object]]) -> int:
    today = dt.date.today().isoformat()
    orders = merge_registry_backfill(orders)
    registered = registry_by_nd()
    for item in orders:
        classify_order(item, registered)
    status_counts: dict[str, int] = {}
    theme_counts: dict[str, int] = {}
    for item in orders:
        status = str(item["registry_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        for theme in item["themes"]:
            theme_s = str(theme)
            theme_counts[theme_s] = theme_counts.get(theme_s, 0) + 1
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "retrieved": today,
                "query": QUERY,
                "ips_total_results": total,
                "rkn_orders_found": len(orders),
                "note": "orders includes the main a1-query result plus registry backfill by IPS nd for Roskomnadzor orders that IPS does not return by the agency-name title query",
                "registry_status_counts": status_counts,
                "theme_counts": theme_counts,
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
        f"- Приказов Роскомнадзора/совместных приказов в каталоге после backfill из основного реестра: `{len(orders)}`.",
        "- Ограничение метода: часть РКН-приказов в IPS не возвращается по",
        "  общему a1-запросу ведомства, поэтому уже импортированные РКН-приказы",
        "  с известным `nd` добавляются в каталог отдельным backfill-шагом.",
        "",
        "## Сводка для отбора",
        "",
        "| Группа | Количество |",
        "|---|---:|",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status.replace('|', '\\|')} | {count} |")
    lines.extend(
        [
            "",
            "## Тематические теги",
            "",
            "| Тема | Количество |",
            "|---|---:|",
        ]
    )
    for theme, count in sorted(theme_counts.items()):
        lines.append(f"| {theme.replace('|', '\\|')} | {count} |")
    lines.extend(
        [
            "",
            "## Полный список",
            "",
            "Колонка «Отбор» показывает, входит ли приказ в основной реестр базы",
            "знаний или требует ручной оценки. Автоматические темы используются",
            "только для первичного отбора; источник истины — карточка IPS и полный",
            "текст документа.",
            "",
        "!!! note \"Назначение страницы\"",
        "",
        "    Это discovery-каталог, а не список полностью импортированных НПА ИБ.",
        "    В нём есть кадровые, закупочные, связные, рекламные и иные административные",
        "    акты. В основной раздел импортируются полные тексты тех приказов, которые",
        "    относятся к персональным данным, инцидентам и практической ИБ.",
        "",
            "| Дата и номер | Статус IPS | Отбор | Темы | Способ нахождения | Наименование | `nd` |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in orders:
        heading = str(item["heading"])
        short = heading.replace(
            "Приказ Федеральной службы по надзору в сфере связи, информационных технологий и массовых коммуникаций от ",
            "",
        )
        description = str(item["description"])
        themes = ", ".join(str(theme) for theme in item["themes"]).replace("|", "\\|")
        registry_status = str(item["registry_status"]).replace("|", "\\|")
        discovery_source = str(item.get("discovery_source", "")).replace("|", "\\|")
        if description:
            title = f"{heading}. {description}"
        else:
            title = heading
        title = title.replace("|", "\\|")
        lines.append(
            f"| {short.replace('|', '\\|')} | {str(item['status']).replace('|', '\\|')} | "
            f"{registry_status} | {themes} | {discovery_source} | "
            f"[{title}]({item['ips_card']}) | `{item['nd']}` |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(orders)


def main() -> int:
    total, orders = discover()
    final_count = write_outputs(total, orders)
    print(f"IPS total results: {total}")
    print(f"Roskomnadzor orders cataloged: {final_count}")
    print(OUTPUT_MD)
    print(OUTPUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
