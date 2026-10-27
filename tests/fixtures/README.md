# Public test fixtures

The Facebook Content JSON files are synthetic contract fixtures, not customer
exports or evidence of a real publication. Source/review/approval states simulate
the Admin contract so the renderer can be tested. The release seal is deliberately
invalid. Page/post identifiers (`1234`, `1234_1`, `1234_2`) are placeholders.

Opaque report, dataset, reviewer, asset, run and evidence identifiers in
`facebook_content_vio.json` are deterministic test-only replacements. Their
references remain consistent; numbers, nulls, coverage, timezones and approval
states are unchanged. In particular, a missing period metric remains null and
post lifetime counts are never converted into period engagement.

These fixtures are excluded from the production Docker image. Only the isolated
design-preview container mounts tests read-only. Never place customer exports,
provider tokens, cookies, OAuth secrets or SMTP credentials in this directory.
