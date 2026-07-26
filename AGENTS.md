# Project Instructions

## Official Russian Regulation Texts

When importing Russian legal or regulatory documents, use the official
`pravo.gov.ru/proxy/ips` database as the primary source for the current
consolidated text.

Do not use PDFs, Consultant Plus, Garant, or other secondary legal databases as
the source of the document text when the document is available through
`pravo.gov.ru/proxy/ips`.

### Import Flow

1. Find the document in the old IPS database by date and number:

   ```text
   http://pravo.gov.ru/proxy/ips/?searchres=&...
   http://pravo.gov.ru/proxy/ips/?searchlist=&...
   http://pravo.gov.ru/proxy/ips/?list_itself=&...
   ```

2. Extract the document `nd` from the `list_itself` result.

3. Open the IPS document card:

   ```text
   http://pravo.gov.ru/proxy/ips/?docbody=&link_id=0&nd=<ND>&firstDoc=1
   ```

4. Determine the selected current `rdk` from the document card or from the
   `doc_itself` iframe.

5. Download the full text:

   ```text
   http://pravo.gov.ru/proxy/ips/?doc_itself=&nd=<ND>&page=1&rdk=<RDK>&link_id=0
   ```

6. Decode the response as `windows-1251` and extract `#text_content`.

7. Preserve the official document body as inline HTML inside the Markdown page.
   Do not flatten Word-generated markup into plain text: classes such as `W9`
   are used for superscript footnote marks, and flattening them turns references
   like `8¹` into incorrect text such as `81`.

8. Preserve complex tables as inline HTML when Markdown tables would lose
   `rowspan`, `colspan`, or other structure.

9. Add metadata to each generated Markdown file:

   - official source;
   - `nd`;
   - `rdk`;
   - edition label;
   - official status from search results;
   - retrieval date;
   - SHA-256 of the downloaded HTML source;
   - official IPS and publication links.

### Currency Rules

- If the IPS card has a selected prepared edition, use that edition.
- If the IPS card shows a newer edition marked `не готова`, do not claim that
  the imported text is the fully current prepared text. Add a warning and handle
  the document manually.
- `publication.pravo.gov.ru` pages are official publication cards, but they
  usually do not provide consolidated current HTML text. Use them as publication
  links, not as the main source for current text.
- Never label a document as "full current text" unless the current `nd` and
  `rdk` were resolved from the official IPS card.

### Existing Helper

Use `scripts/import_pravo_ips.py` for repeatable imports from
`pravo.gov.ru/proxy/ips`.

## Current Regulation Import Process

The authoritative registry for the regulation section is
`scripts/regulation_registry.json`.

Use the registry-driven importer for ongoing work:

```text
python scripts/import_regulations.py import
```

The importer supports two source classes:

- `ips`: full official text imported from `pravo.gov.ru/proxy/ips` with `nd`,
  `rdk`, edition label, retrieval date and SHA-256.
- `external_official`: official-source card only. Do not present these pages as
  full current text until an official full-text source has been resolved.

Current registry coverage:

- total documents: 56;
- full IPS imports: 33;
- official external cards requiring a dedicated source parser or manual source
  resolution: 23.

Current category coverage:

- federal laws: 7;
- presidential decrees: 3;
- government resolutions: 9;
- FSTEC documents: 10;
- FSB documents: 6;
- Roskomnadzor documents: 6;
- Bank of Russia documents: 5;
- national standards: 10.

## Daily Change Checking

Use the stored state in `scripts/regulation_state.json` to detect changes in
published IPS documents:

```text
python scripts/import_regulations.py check --report docs/regulation/change-reports/latest.md
```

The check compares current official `rdk` and source HTML SHA-256 against the
last imported state. If the official HTML changed, it writes a short Markdown
report with:

- document id and title;
- old and new `rdk`;
- source URL;
- short human-readable summary;
- examples of added and removed text fragments.

The scheduled workflow is `.github/workflows/check-regulation-updates.yml`. It
runs daily and, when a change is detected, re-imports the registry and commits
the changed documents, updated state and report.

For testing historical change handling on a document with multiple prepared
editions:

```text
python scripts/import_regulations.py history --id fstec-order-239-2017 --limit 3 --report docs/regulation/change-reports/sample-fstec-239-history.md
```

## Findings From Import

- The original regulation overview linked Government Resolution No. 1119 to
  `nd=102160655`, which is a different document. The correct IPS document found
  by official search is `nd=102160483`.
- FSTEC Order No. 239 has a prepared current edition `rdk=4`, but the IPS card
  also lists a newer unprepared edition: `5 - от 28.08.2024 № 159 (изм.)(не
  готова)`. Do not describe the imported text as fully current without this
  warning.
- Several IPS cards for federal laws also contain unprepared newer editions.
  Import the selected prepared edition and preserve the warning.
- FSTEC Orders No. 21 and No. 31, FSB Order No. 378 and Roskomnadzor Order No.
  996 were not resolved by simple IPS date/number search during this pass. They
  are represented as official-source cards until a verified official full-text
  source is found.
- GOST texts, Bank of Russia acts, BDU/FSTEC methodical documents and some
  regulator documents are not IPS legal texts in this workflow. They require
  dedicated official-source importers and must remain cards until those importers
  preserve the official text and licensing constraints correctly.
