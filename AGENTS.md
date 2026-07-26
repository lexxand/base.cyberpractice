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

The importer supports three source classes:

- `ips`: full official text imported from `pravo.gov.ru/proxy/ips` with `nd`,
  `rdk`, edition label, retrieval date and SHA-256.
- `official_html`: full official text imported from a regulator's official
  HTML page with source URL, retrieval date and SHA-256 of the extracted HTML
  fragment. Preserve the official HTML structure and do not flatten it to plain
  Markdown.
- `external_official`: official-source card only. Do not present these pages as
  full current text until an official full-text source has been resolved.

Current registry coverage:

- total documents: 60;
- full IPS imports: 37;
- full official HTML imports: 1;
- official external cards requiring a dedicated source parser or manual source
  resolution: 22.

Current category coverage:

- federal laws: 7;
- presidential decrees: 3;
- government resolutions: 9;
- FSTEC documents: 10;
- FSB documents: 6;
- Roskomnadzor documents: 10;
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

`scripts/import_regulations.py check` uses explicit exit codes:

- `0`: checked successfully, no document changes detected;
- `1`: checked successfully, document changes detected and the report was
  written;
- `2`: technical failure while checking official sources. Treat this as a
  failed workflow, not as a regulatory update.

Before publishing regulation changes, run the coverage audit:

```text
python scripts/audit_regulation_coverage.py
```

The audit verifies that every document in `scripts/regulation_registry.json`
exists, has a direct link from `docs/regulation/index.md`, and is present in
`mkdocs.yml` navigation. Grouped rows on the landing page must link to every
concrete document, not to a category index page.

## Roskomnadzor Order Discovery

Use the reproducible IPS discovery script when refreshing the catalog of
Roskomnadzor orders:

```text
python scripts/discover_rkn_orders.py
```

The old IPS search requires Windows-1251 percent-encoding for Cyrillic query
values. The working official query is `list_itself` by field `Наименование`
(`a1`) with the value `Федеральная служба по надзору в сфере связи`; use
`start` and `lstsize` for pagination.

Current discovery output:

- official IPS query results: 360;
- Roskomnadzor orders / joint orders starting with the agency name: 195;
- generated human page:
  `docs/regulation/russia/roskomnadzor/ips-order-discovery.md`;
- generated machine-readable state: `scripts/rkn_order_discovery.json`.

Do not automatically import all discovered Roskomnadzor orders into the main
regulation registry. The discovered set includes кадровые, закупочные, связные,
рекламные and other administrative acts that are outside the practical
cybersecurity / personal-data scope. Import full IPS text into the registry only
for documents relevant to the regulation knowledge base, while keeping the full
official discovery catalog available for review.

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
- Additional Roskomnadzor personal-data orders resolved through IPS and added
  after the coverage audit:
  - Order No. 253 of 24.12.2021, `nd=602911772`, control checklist for federal
    state supervision over personal data processing;
  - Order No. 128 of 05.08.2022, `nd=603389824`, list of foreign states
    providing adequate protection of personal data subjects' rights.
  - Order No. 201 of 15.12.2022, `nd=605539645`, personal data processing in
    Roskomnadzor itself;
  - Order No. 1 of 10.01.2023, `nd=605502743`, amendments to the personal-data
    supervision checklist from Order No. 253.
  The main imported Roskomnadzor scope is the personal-data/incident subset
  relevant to the regulation page. The separate IPS discovery catalog tracks the
  broader official order set.
- GOST texts, Bank of Russia acts, BDU/FSTEC methodical documents and some
  regulator documents are not IPS legal texts in this workflow. They require
  dedicated official-source importers and must remain cards until those importers
  preserve the official text and licensing constraints correctly.
- The BDU FSTEC vulnerability-regulation page (`https://bdu.fstec.ru/regulations`)
  contains the full official HTML text and is imported as `official_html`.
  In the local environment the certificate chain for `bdu.fstec.ru` is not
  trusted by the system CA bundle, so the importer uses `tls_verify=false` for
  this source and records that fact in the generated Markdown metadata.
- BDU FSTEC document pages such as `https://bdu.fstec.ru/documents/20`,
  `/documents/25` and `/documents/18` are official metadata cards, not full
  document texts. Import them as `official_card`, preserve the card HTML, hash
  the extracted card fragment, and explicitly warn that the page is not a full
  current text. Do not relabel these cards as imported full documents unless the
  actual official FSTEC text page or file has been retrieved and preserved.
- From the current environment `fstec.ru` and `fsb.ru` time out at TCP/HTTPS
  connection time for the checked pages. Record the exact official URL when a
  trusted official card exposes it, but do not synthesize document text from
  secondary databases.
- Bank of Russia search currently resolves several relevant acts to official
  `cbr.ru` PDF file endpoints. Keep those pages as official-source cards unless
  there is explicit permission and a repeatable extractor for official CBR
  files; do not silently convert PDFs into Markdown during the regulation import
  workflow.
- The regulation landing page previously had grouped rows that linked
  `Постановления № 79, № 313, № 608` and `ГОСТ Р 59710, 59711, 59712` to
  category index pages instead of direct document pages. This is not acceptable
  for coverage accounting; each document row/group must expose direct links to
  all concrete imported documents.
- The daily update workflow must not use generic GitHub Actions failure as a
  signal for document changes. A network/source failure and a detected legal
  text change are different states; only exit code `1` from the importer means
  "changed".
- The old analytical bibliography in `docs/regulation/index.md` is hidden from
  the rendered page and must not be used as a source for imported document
  texts. Authoritative source metadata belongs in each generated document card.
