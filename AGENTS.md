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
