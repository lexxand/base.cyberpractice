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

For `ips` entries that already have `nd` in `scripts/regulation_registry.json`,
the importer still performs the exact `list_itself` lookup by date and number
to retrieve official search-result metadata: legal status and publication
number. The lookup result must be selected by the registry `nd` when the result
page contains several acts with the same date and number. Do not take the first
`list_itself` result blindly: for example, `10.01.2023 № 1` returns both a
Government Resolution and a Roskomnadzor Order. If the expected `nd` is absent,
keep using the registry `nd` for the text import and do not attach metadata
from a different document.

The importer supports five source classes:

- `ips`: full official text imported from `pravo.gov.ru/proxy/ips` with `nd`,
  `rdk`, edition label, retrieval date and SHA-256.
- `official_html`: full official text imported from a regulator's official
  HTML page with source URL, retrieval date and SHA-256 of the extracted HTML
  fragment. Preserve the official HTML structure and do not flatten it to plain
  Markdown.
- `official_card`: official metadata/card HTML imported from an official source
  when the page does not contain the full document text. Hash and monitor the
  extracted official card fragment, but warn that the page is not a full current
  text.
- `official_file`: official file endpoint imported without extracting text.
  Hash and monitor the exact downloaded file bytes, record content type, final
  URL, file size and content disposition, but warn that the page is not a full
  Markdown text.
- `external_official`: official-source card only. Do not present these pages as
  full current text until an official full-text source has been resolved.

Current registry coverage:

- total documents: 66;
- full IPS imports: 43;
- full official HTML imports: 1;
- official metadata-card imports: 14;
- official file imports without text extraction: 5;
- official external cards requiring a dedicated source parser or manual source
  resolution: 3.

Current category coverage:

- federal laws: 7;
- presidential decrees: 3;
- government resolutions: 9;
- FSTEC documents: 10;
- FSB documents: 6;
- Roskomnadzor documents: 16;
- Bank of Russia documents: 5;
- national standards: 10.

## Daily Change Checking

Use the stored state in `scripts/regulation_state.json` to detect changes in
published official sources:

```text
python scripts/import_regulations.py check --report docs/regulation/change-reports/latest.md
```

The check compares current official `rdk` and source SHA-256 against the last
imported state. For `ips` and `official_html` it can produce text-line
examples. For `official_card` it reports official card changes. For
`official_file` it reports byte-level file changes and requires manual review
unless a text extractor for that file type has been explicitly added. If the
official source changed, it writes a short Markdown report with:

- document id and title;
- old and new `rdk`;
- source URL;
- short human-readable summary;
- examples of added and removed text fragments.

The summary generator must prefer meaningful legal/document changes over raw
HTML noise. It filters service lines such as document headers, search controls,
signature checks and trivial layout fragments, then classifies changed text by
visible content signals:

- edition/status note changed;
- points, subpoints or paragraphs changed;
- appendices, forms, lists or tables changed;
- security measures, requirements or procedures changed;
- references to laws/orders/resolutions changed;
- dates or deadlines changed.

Keep the generated examples in real diff order so paired "removed/added"
changes are readable. The historical sample
`docs/regulation/change-reports/sample-fstec-239-history.md` is the regression
fixture for this behavior.

If the added and removed meaningful lines are the same multiset, report it as
an ordering/HTML-layout change, not as a substantive legal text change. This
happens on some official cards, for example when `protect.gost.ru` reorders
rows in the "changes" tab without changing the visible set of entries.

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


## External Official Source Audit

For documents that remain `external_official`, generate a reproducible audit
report of their official links:

```text
python scripts/audit_regulation_external_sources.py
```

The report is written to `docs/regulation/source-audits/latest.md`. Network
errors in this report mean that the official domain was unreachable from the
current environment; they are not evidence that the document does not exist.
Do not replace unreachable official sources with Consultant Plus, Garant or
other secondary databases.

The scheduled workflow `.github/workflows/check-regulation-updates.yml` runs
this audit after the imported-source check. The audit report is intentionally
deterministic: it does not include the current date and normalizes transient
Python object addresses in network exceptions. This prevents daily noise commits
when the same official domains remain unreachable.

The external-source audit also records reproducible `pravo.gov.ru/proxy/ips`
search evidence for unresolved documents. Keep the exact IPS query links in
`docs/regulation/source-audits/latest.md`:

- for numbered acts, check `list_itself` by exact date and number;
- for all unresolved acts, check `list_itself` by name, using Windows-1251
  percent-encoding;
- for historical acts, include a name search without the original date when
  that is needed to show replacement acts.

For Roskomnadzor Order No. 996, the exact IPS date/number search still returns
no document. The name search without date returns replacement/current 2025 acts
(`nd=607604898`, Government Resolution No. 1154, and `nd=607599406`,
Roskomnadzor Order No. 140), not the original 2013 order.

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
- Roskomnadzor orders / joint orders cataloged after registry backfill: 200;
- generated human page:
  `docs/regulation/russia/roskomnadzor/ips-order-discovery.md`;
- generated machine-readable state: `scripts/rkn_order_discovery.json`.

The discovery page adds automatic thematic tags and a registry-selection
status for each row. The tags are only a first-pass triage aid; do not treat
them as legal classification. Current generated groups:

- 15 orders are already in the main regulation registry by IPS `nd`;
- 0 orders remain candidates for manual ИБ/ПДн review;
- 24 orders are adjacent 149-ФЗ / internet-advertising topics requiring manual
  review before import;
- 161 orders are outside the current ИБ/ПДн core.

Important IPS limitation: the broad `a1` agency-name query does not return
several Roskomnadzor personal-data orders that are already in the main
registry, including orders No. 128, 178, 179, 180 and 140. Keep the discovery
script's registry backfill by known IPS `nd`; otherwise the catalog falsely
looks less complete than the imported regulation set.

The previous six "manual ИБ/ПДн review" candidates from discovery were imported
as full IPS texts on 2026-07-27:

- Roskomnadzor Order No. 105 of 15.06.2017, `nd=102442788`, amendments to the
  old adequate-protection countries list;
- Roskomnadzor Order No. 1 of 14.01.2019, `nd=102543425`, amendments to the old
  adequate-protection countries list;
- Roskomnadzor Order No. 109 of 28.08.2020, `nd=102865732`, historical
  amendments to Roskomnadzor internal personal-data processing rules;
- Roskomnadzor Order No. 137 of 22.10.2020, `nd=102921342`, historical
  amendment to Roskomnadzor internal personal-data processing rules;
- Roskomnadzor Order No. 106 of 21.06.2021, `nd=602367821`, rules for using
  Roskomnadzor's information system and interaction between data subjects and
  operators;
- Roskomnadzor Order No. 183 of 14.09.2021, `nd=602494309`, amendments to the
  old adequate-protection countries list.

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
- GOST cards are imported from exact `protect.gost.ru/gost/details/...`
  official pages as `official_card`. The imported card preserves official
  metadata such as designation, title, status, registration data, keywords and
  scope. Full GOST text is not imported into Markdown until there is a separate
  explicit decision on official-file extraction and licensing constraints.
- Some BDU/FSTEC methodical documents and some regulator documents are not IPS
  legal texts in this workflow. They require dedicated official-source
  importers and must remain cards until those importers preserve the official
  text and licensing constraints correctly.
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
- From the current environment `fstec.ru` times out at TCP connection time for
  the checked pages. `fsb.ru` times out over HTTPS but is reachable over HTTP;
  use the HTTP official page when importing FSB official cards. Record the exact
  official URL when a trusted official card exposes it, but do not synthesize
  document text from secondary databases.
- Additional network check on 2026-07-27 resolved `fstec.ru` to
  `95.173.157.32`; both HTTPS and HTTP connections to the official document
  pages and tested `/files/...pdf` paths timed out before TLS/HTTP response.
  Do not promote search-index hints for FSTEC PDF paths into imported source
  metadata until the official file is actually fetched and its SHA-256 is
  recorded.
- FSB Order No. 378 is imported as `official_card` from the HTTP official FSB
  article dated 21.06.2016. The article lists the order among the currently
  active personal-data security normative-methodical documents, but does not
  publish the full order text.
- For `http://` official sources, record `source_tls_verify:
  "not_applicable_http"` instead of `true`; TLS verification is not meaningful
  on plain HTTP.
- The remaining `external_official` documents after the CBR/GOST/FSB pass are:
  FSTEC methodical documents dated 25.11.2025 and 12.05.2026, and historical
  Roskomnadzor Order No. 996. Exact official URLs are recorded in their
  generated cards where available, but the current environment times out against
  the relevant official domains (`fstec.ru`, `rkn.gov.ru`, `digital.gov.ru`).
  Keep them as non-full cards until an official source can be fetched
  repeatably.
- BDU FSTEC open document catalog was checked for the FSTEC methodical
  documents dated 25.11.2025 and 12.05.2026. The accessible BDU catalog pages
  and sections currently expose documents such as `/documents/18` and
  `/documents/29`-`/documents/32`, but not these two methodical documents. Do
  not invent BDU cards for them unless they appear in the official BDU catalog.
- Repeated IPS searches for historical Roskomnadzor Order No. 996 by exact
  date/number, title, 2013 date range, and registration number did not resolve
  the original order. The IPS title search resolves the replacement 2025
  Roskomnadzor Order No. 140 and Government Resolution No. 1154 instead.
- A search-index check found an additional official regional Roskomnadzor URL
  for Order No. 996 at `https://24.rkn.gov.ru/docs/24/sm38732/Fajl_1.htm`.
  The snippet identifies the order dated 05.09.2013, registration No. 29935 and
  applicability of points 1-15, but the official page itself times out from the
  current environment. Keep it as an official link candidate only; do not treat
  it as imported text until the page is actually fetched and hashed.
- Bank of Russia search currently resolves the tracked relevant acts to official
  `cbr.ru` PDF file endpoints. Import those endpoints as `official_file` so the
  exact official file is hashed and monitored daily. Do not silently convert
  these PDFs into Markdown during the regulation import workflow; add a
  repeatable official-file extractor first if full text import is required.
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
