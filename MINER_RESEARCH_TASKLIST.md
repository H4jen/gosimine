# Miner Research Tasklist

> Obsolete intake format: `seed/miner_intake.csv` is retained only as historical reference. New
> research must prepare a reviewed canonical dossier in `seed/miners/<TICKER>.json`, including
> project-model components where applicable. A future exporter may create a human-readable review
> artifact from that JSON.

Use this tasklist to research one new mining-stock listing and prepare a verified JSON dossier.
It is designed to be given to an AI researcher, but a human must review the final dossier before
it enters the catalog.

## Operating Rules

1. Research one tradeable listing, not a general company. Preserve the Yahoo Finance ticker,
   including its exchange suffix, such as `TSK.TO`.
2. Do not invent, calculate, convert, or interpolate a company fact. When a primary source does
  not disclose a useful input, continue through the blank-resolution loop before deciding whether
  to leave it blank or include an explicitly marked temporary estimate.
3. Keep reported financial facts in their source currency. Do not convert CAD to USD during
   intake.
4. Use company filings, NI 43-101/JORC technical reports, feasibility studies, earnings
   releases, and official investor materials as evidence. Use a reputable market-data source only
   for share count or financial data when an issuer source is unavailable, and name that source.
5. Mark every non-company estimate exactly as `Temporary estimate - verification pending:` and
   list every affected parameter and assumption in its source field.
6. Do not label warrants, options, or RSUs as `potential_conversion_shares`. Put them in
   `potential_dilution_shares`. Use conversion shares only for a convertible instrument with a
   disclosed share count.
7. Do not fill a resource field with reserves, a production target with a resource estimate, or
   financing proceeds with debt.
8. Return URLs and quoted evidence for every populated field. A URL alone is not sufficient.
9. Pull Yahoo Finance data for the exact listing during every miner-research pass, before the
  draft dossier is submitted. Record the ticker queried, retrieval date/time, latest close and
  quote currency, market timestamp, and Yahoo share-count result in the evidence register.
  Yahoo data is secondary market evidence: use issuer disclosures first for company facts, and
  do not substitute Yahoo values for sourced study, resource, debt, or dilution data.
10. If Yahoo returns a 404, an empty quote, a quote-currency mismatch, or no positive share
  count, stop before seed creation. Resolve the exact Yahoo ticker with the issuer's listing
  disclosure, then rerun the Yahoo check; do not retain an unrefreshable ticker.
11. Use Google AI Mode as a secondary source after primary issuer research: first cross-check
  reported facts and locate supporting documents, then use it to identify gaps and leads. Treat
  a Google-only answer as unverified; verify its cited issuer or technical-report source before
  recording it as a reported fact. When it cannot be verified but is useful, include it only as
  an explicitly approved `Temporary estimate - verification pending`.

## Required Deliverable

Return these sections in this order:

1. Listing identity
2. Evidence register
3. Field-by-field decisions
4. Draft JSON dossier
5. Review flags

Return a JSON-ready dossier structure. The filename is the Yahoo ticker with periods replaced by
underscores, such as `TSK_V.json` for `TSK.V`.

## Step 1: Establish Listing Identity

Find and report:

- Company name
- Yahoo Finance ticker and exchange suffix
- Trading currency
- Primary commodity
- Stage and lifecycle status, using the project's controlled values where possible

Evidence must identify the exact listing. Flag an ambiguity if the company has multiple listings
or if the Yahoo ticker cannot be confirmed.

### 1.1 Validate Yahoo Finance Market Data

Before researching model inputs, query Yahoo Finance for the exact ticker. Record the following
in the evidence register:

- Ticker submitted to Yahoo Finance
- Retrieval timestamp
- Latest close, quote currency, and market timestamp
- Yahoo Finance shares-outstanding value, if returned

Checks:

- The Yahoo quote currency must match the listing trading currency. Investigate any mismatch
  before proceeding.
- A valid ticker must return a non-empty quote and a positive close. A stale, delisted, renamed,
  or unsupported ticker is a blocking listing-identity failure, not an unavailable market field.
- Compare the Yahoo share count to the latest issuer figure. Prefer the issuer value when it is
  current and supported; document a material difference as a review flag.
- Do not write market prices or Yahoo retrieval timestamps into `seed/miner_intake.csv`.

## Step 2: Create an Evidence Register

Before extracting numbers, collect the best available primary source for each group. Then use
Google AI Mode to cross-check those findings and identify gaps. For every source, record title,
publisher, publication/effective date, URL, and the relevant page/table/section.

### 2.1 Use Google AI Mode to Find Missing Evidence

After completing the initial issuer-site search, use Google AI Mode to cross-check the extracted
facts and investigate each remaining field, for example: `Avino ASM latest basic shares
outstanding source` or `Avino latest technical report resource effective date`. Capture its
suggested documents, search terms, and any conflicting values in a lead list. Follow each lead to
the original document, then extract the value, date, and quotation from that original source. If
the original cannot be reached or does not support the claimed value, include the Google result
only as an explicitly approved temporary estimate; otherwise leave the field unavailable.

| Group | Preferred evidence | Fields supported |
| --- | --- | --- |
| Project study | Feasibility study, PEA/PFS, technical report, or formal guidance | production, AISC, mine life, NPV, study metal prices, discount rate |
| Resource | Current NI 43-101/JORC resource technical report or company release | measured and indicated resources, inferred resources, total resources |
| Financial | Latest financial statements or MD&A | cash, debt, financial date |
| Dilution | Financing release, share-structure report, notes to financial statements | convertible shares, warrants, options, RSUs |
| Shares | Latest share-structure report, financial statement, or issuer presentation | basic shares outstanding |

Use the most recent applicable source. A study can be older than a financial statement; retain
each source's own as-of date instead of forcing all values to one date.

## Step 3: Extract Facts by Evidence Group

For each prospective field, capture the exact disclosed value, unit, currency, date, source URL,
and supporting quotation. Then classify it as `reported`, `temporary estimate`, or `unavailable`.

### 3.1 Project Study or Operating Inputs

Collect when disclosed:

- `annual_production_ounces`
- `annual_payable_gold_ounces` and/or `annual_payable_silver_ounces`
- `annual_payable_copper_pounds`, when payable copper is disclosed
- `aisc_per_ounce`
- `mine_life_years`
- `after_tax_npv` and `after_tax_npv_currency`
- `study_discount_rate_percent`
- `study_metal_price_gold_usd_per_ounce`
- `study_metal_price_silver_usd_per_ounce`
- `study_metal_price_copper_usd_per_pound`
- `project_study_as_of_date`

Checks:

- Use each payable metal's disclosed volume unit. Gold and silver use ounces; copper uses pounds.
  For a gold-only miner, use gold ounces; the builder emits `AuEq` units. For silver-equivalent
  studies, only use the issuer's stated equivalent basis.
- Reported production, AISC, mine life, NPV, discount rate, and study metal prices should come
  from the same study where possible.
- Do not call an estimate company-reported. If a temporary estimate is approved, group the
  affected items under one explicit temporary source sentence.

### 3.2 Resources

Collect the current measured-and-indicated total, inferred total, and combined total in the
issuer's reported metal-ounce basis:

- `measured_indicated_resource_equivalent_ounces`
- `inferred_resource_equivalent_ounces`
- `total_resource_equivalent_ounces`
- `resource_as_of_date`

Checks:

- Verify that total equals measured-and-indicated plus inferred, subject to disclosed rounding.
- Record the technical report's effective date, not merely the publication date.
- State the metal basis in the evidence quotation, especially for gold-only miners.

### 3.3 Financial Position

Collect:

- `cash` and `cash_currency`
- `total_debt` and `total_debt_currency`
- `financial_as_of_date`

Checks:

- Use cash and debt exactly as reported. Do not net debt against cash.
- Start with the latest financial statements' balance sheet and debt/borrowings note; use the MD&A
  only to locate or explain the underlying statement evidence.
- Reconcile `total_debt` to current debt plus long-term debt. A statement that one named loan or
  facility was repaid does not establish that company-wide debt is zero; check every remaining
  borrowing facility and the debt note.
- Record the debt-note total when it includes accrued interest or commitment charges. State the
  components in the financial-source text so the all-in amount is auditable. Do not substitute
  total liabilities, lease liabilities, restricted cash, or financing proceeds for total debt.
- Record `0` only when the issuer explicitly reports no debt or the reconciled current and
  long-term debt balances are both zero. Leave debt blank only when it remains unavailable after
  the required search.
- Keep the currency code as reported, such as `CAD` or `USD`.

### 3.4 Capital Structure and Dilution

Collect:

- `basic_shares_outstanding`
- `potential_conversion_shares`
- `potential_dilution_shares`
- `shares_as_of_date`
- `dilution_as_of_date`

Checks:

- Confirm whether basic shares are period-end or a later current number.
- Add warrants, options, and RSUs to `potential_dilution_shares` only when their counts are
  explicitly disclosed.
- Add disclosed convertible-note shares to `potential_conversion_shares`; do not use the note's
  principal amount as a share count.

## Step 4: Resolve Missing or Preliminary Inputs

For every field that is blank after the initial extraction, run a targeted primary-source search
and then a Google AI Mode secondary search. Search the exact field name, listing ticker, project
name, and relevant document type; for example, `ASM mine life NI 43-101`, `Avino after-tax NPV
PFS`, or `Avino warrants options RSUs June 2026`. Record the search terms, sources reviewed, and
outcome in the review flags. A blank is permitted only after this search has found no defensible
value.

### 4.1 Mandatory Blank-Resolution Loop

Complete this loop separately for every blank field. Do not stop after the first relevant document
or the first search-result page.

1. Search the issuer site and filings for the exact field plus the applicable document type.
  Search both the current listing and the relevant project name.
2. Search the latest financial statements or MD&A for balance-sheet and capital-structure fields;
  search the latest guidance, technical report, PEA, PFS, or feasibility study for operating and
  study fields.
3. Ask Google AI Mode for the field, required scope, and primary-source URL. Ask it to identify
  whether the value is company-wide, project-specific, current guidance, historical actual, or
  an analyst/third-party estimate.
4. Open the issuer or technical-report document suggested by the search. Record its exact value,
  date, currency/unit, page or section, and scope.
5. If the only usable result is project-specific, decide explicitly whether it is a valid direct
  input or a temporary proxy. Never present a project PFS as a company-wide NPV or mine life.
6. If a range is disclosed but the CSV needs one value, use a documented midpoint only as a
  `Temporary estimate - verification pending`, naming the original range and calculation.
7. If an issuer explicitly reports zero debt, record `0` with its currency and source. For fields
  without an applicable instrument, such as conversion shares when no convertible exists, retain
  a blank and explain the absence. Distinguish this `not applicable` blank from an `unavailable`
  blank, where the instrument may exist but its amount could not be supported.
8. Leave the value blank only when this loop finds neither a supported fact nor a useful,
  maintainer-approved temporary estimate.

For every blank or estimated field, add a review flag explaining why.

- `unavailable`: leave the CSV value and associated currency blank. Use `Source missing` only
  when a value is retained but its provenance is absent. State which primary sources and Google
  AI Mode leads were checked before marking it unavailable.
- `temporary estimate`: use only after explicit maintainer approval. Set its applicable date to
  the approval date and put all assumptions in the relevant source field, beginning with
  `Temporary estimate - verification pending:`.
- optional project-study and dilution dates may be blank. The builder records them as
  `1900-01-01` for database compatibility.

When a searched field has a useful but unverified Google result, include it as an explicitly
approved temporary estimate instead of excluding it. Do not add a temporary value merely to make
an analysis available when no useful result exists. The application is allowed to show unavailable
outputs.

## Step 5: Prepare the Draft CSV Row

Use the exact header and column order already in `seed/miner_intake.csv`. Follow these rules:

- Every populated numeric value must be positive, except an explicitly reported `total_debt` of
  `0`.
- Use ISO dates: `YYYY-MM-DD`.
- Use three-letter ISO currency codes.
- Put the five grouped sources at the end: `project_study_source`, `resource_source`,
  `financial_source`, `dilution_source`, and `shares_source`.
- Quote any CSV field containing a comma.
- Keep fields unavailable from disclosure blank rather than using zero, `N/A`, or a guessed value.

## Step 6: Quality Gates

The researcher must verify all of the following before submitting the row:

1. Ticker is valid and corresponds to the requested listing.
2. Every populated field has a source group, date, URL, and supporting quotation in the evidence
   register.
3. Currency is retained exactly as disclosed for NPV, cash, and debt.
4. Resource totals reconcile, allowing stated rounding.
5. Dilution types are correctly separated.
6. Temporary estimates are explicit, dated, and never presented as issuer facts.
7. Every blank field has a documented primary-source search, Google AI Mode secondary search, and
  reason it remains unavailable.
8. CSV field count matches the current header and comma-containing values are quoted.
9. Run `python scripts/build_seed.py --verify-yahoo` and inspect the new JSON before catalog import. Confirm each
   populated CSV value appears under the intended parameter name, with the intended value, unit,
   date, and source.
10. Parse the draft CSV with the project's CSV reader and verify its field count matches the header.
  In particular, check runs of empty columns around conversion shares, dilution shares, and study
  metal prices; a valid field count alone does not prove values did not shift columns.

## Reference Patterns

### VZLA: Fully Sourced Study Dossier

Use VZLA as the model for a developer with disclosed feasibility-study production, AISC, mine
life, NPV, discount rate, metal prices, resources, financials, and dilution. Its intake row shows
how each evidence group feeds many fields without repeating the same URL.

### TSK.V: Partial Dossier with Explicit Assumptions

Use TSK.V as the model when disclosure is incomplete. Its resources, cash, share count, and
dilution are sourced separately. The production, AISC, mine life, NPV, discount rate, and gold
price are deliberately grouped under a temporary-estimate source. This preserves the distinction
between verified company data and provisional model inputs.

## Prompt Template

```text
Research the listing [TICKER] for Gosimine using MINER_RESEARCH_TASKLIST.md.

Produce the five required deliverable sections in the specified order. Use only verifiable
primary issuer sources where possible. For every populated field, give the exact value, unit,
currency, as-of date, direct URL, and quotation with page/table/section reference.

Do not invent, calculate, convert currencies, or substitute estimates for unavailable data. Leave
unavailable CSV cells blank and flag them. Do not create temporary estimates unless explicitly
provided below and label them exactly as required.

Requested temporary estimates, if approved: [NONE OR LIST]
```