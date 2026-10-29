# Customer Channels and Reports

## Implemented scaffold

The authenticated `/workspace/channels` and `/workspace/reports` pages share the
existing Workspace shell, customer selection, typography, Ctrl+K search and
period preferences. They use only the existing session, workspace detail and
integration catalogue BFF reads. Customer/workspace selection and logout retain
the existing cookie, Origin and CSRF checks. No new public Customer API or Admin
endpoint has been introduced.

Channels has nine analysis areas with search, categories, status filters and
deep links such as `?channel=facebook_content`. SEO is an analysis composite
covering GA4, Search Console and future keyword datasets; it is not a connector
or an alias for Search Console. Instagram remains available in the integration
source catalogue. The analysis inventory follows the nine areas in the supplied
design rather than the connector inventory.

Reports has ten layout previews: one cross-channel layout plus the nine analysis
areas. It includes a scoped saved-report list, status tabs, search, pagination,
export history and an in-memory layout designer. The designer can preview a
name, period, layout and source selection. It does **not** save a report, schedule
a delivery, export a PDF or create a sharing grant. This is explicit in the UI.
All three publication capabilities remain false. No DB migration is required.

Saved-report/history totals remain `—` until a corresponding collection has
actually loaded. Channel status counts describe the nine rendered cards, not
business KPIs. Null metrics remain `—`; only a supplied numeric zero is zero.
The page makes no automatic sync frequency or certification claims.

## Future data binding

`app/mappers/customer_library.py` defines presentation metadata and empty values.
It rejects a mismatched workspace or selected client between the two Admin reads.
Connection status is taken only from same-workspace, same-client catalogue rows.
It never queries legacy reports, adapters, credentials or arbitrary tenant data.

The browser exposes two presentation bridges:

- `VioChannels.getContext()` / `VioChannels.render(snapshot)`
- `VioReports.getContext()` / `VioReports.render(snapshot)`

These are local rendering hooks, **not** authenticated data sources. A future
tenant-scoped BFF loader must read normalized data from Admin and call the bridge.
Each snapshot must echo every field of the current context: `schema_version: 1`,
`request_id`, `scope.workspace_id`, `scope.client_id`, `period.start`, `period.end`,
`currency` and `timezone`. Mismatched or stale envelopes are rejected. Context
changes clear the old snapshot and close previews; consumers can subscribe to
`customer:library-context` and abort obsolete requests.

Channel rows use `channels: [{workspace_id, client_id, id, state, metrics}]`.
`id` must match an analysis area. `metrics` is a map of known metric keys to
numbers or null. Only `state: ready` can display numeric values. Field labels and
units remain defined by trusted presentation metadata, not response HTML.
Percent values use fractions in `[0,1]`, currency uses the workspace currency,
and ROAS is a ratio. Invalid numbers are missing, not zero. Do not calculate
unique Facebook reach by adding post reach, infer organic spend, substitute
impressions for views, or manufacture conversion/revenue metrics. Preserve the
existing Facebook Content definitions when implementing the Admin normalizer.

Saved report rows use `reports_loaded: true` and
`reports: [{workspace_id, client_id, id, name, status, period, source_ids, updated_at}]`.
Supported statuses are `draft`, `scheduled`, `published`. IDs use letters,
numbers, underscores and hyphens (up to 128 characters). Titles are at most 160
characters. An empty loaded array is distinct from an unavailable collection.
The scaffold renders up to 1,000 rows, ten per page; a production loader should
provide server pagination for larger libraries.

Export metadata uses `exports_loaded` and
`exports: [{workspace_id, client_id, name, created_at}]`. Neither records nor
layout previews accept arbitrary file, viewer or export URLs. All response text
is inserted with `textContent`; no report HTML is executed.

Before enabling real report actions, add explicit Admin-backed capabilities,
customer/client ACL checks, immutable Dataset/Bundle revision binding, authorized
Viewer grants, and tested BFF routes. Do not expose legacy demo URLs, reuse a
tenant's old bundle by name, or treat this scaffold as a publication grant.

## Verification

- `python -m pytest -q`
- `node --check static/js/customer/library.js` (also channels/reports/shell)
- `npm run build:css`
- `python scripts/check_customer_library_ui.py`
- `python scripts/check_customer_tour_ui.py`
- `git diff --check`

Browser QA uses isolated `@example.invalid` accounts and synthetic future payloads
in browser memory only. It does not send verification/reset emails, contact
providers, or persist report fixture records. Screenshots/logs are ignored under
`.work/customer-library-qa/`.
