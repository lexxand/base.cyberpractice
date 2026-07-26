#!/usr/bin/env python3
"""Audit regulation registry coverage in Markdown pages and MkDocs nav.

The regulation landing page is treated as the human-facing list of imported
documents. Every registry item must have a direct link from that page and must
be present in the MkDocs navigation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath


REGISTRY = Path("scripts/regulation_registry.json")
INDEX = Path("docs/regulation/index.md")
MKDOCS = Path("mkdocs.yml")


def local_md_links(markdown: str) -> set[str]:
    links: set[str] = set()
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+\.md)(?:#[^)]+)?\)", markdown):
        href = match.group(1)
        if href.startswith("russia/"):
            links.add(str(PurePosixPath("docs/regulation") / href))
        elif href.startswith("regulation/russia/"):
            links.add(str(PurePosixPath("docs") / href))
    return links


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    outputs = {str(Path(item["output"]).as_posix()) for item in registry}
    errors: list[str] = []

    for output in sorted(outputs):
        if not Path(output).exists():
            errors.append(f"registry output is missing: {output}")

    index_links = local_md_links(INDEX.read_text(encoding="utf-8"))
    for output in sorted(outputs - index_links):
        errors.append(f"registry document is not linked from docs/regulation/index.md: {output}")

    for link in sorted(index_links - outputs):
        if link != "docs/regulation/russia/index.md":
            errors.append(f"index links to a non-registry regulation page: {link}")

    mkdocs = MKDOCS.read_text(encoding="utf-8")
    for output in sorted(outputs):
        nav_path = output.removeprefix("docs/")
        if nav_path not in mkdocs:
            errors.append(f"registry document is missing from mkdocs.yml nav: {nav_path}")

    if errors:
        print("Regulation coverage audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Regulation coverage audit passed: {len(outputs)} registry documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
