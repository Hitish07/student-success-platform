# Data integration and cleaning

Phase 4 brings independent academic, attendance, LMS, engagement, placement,
skills, and feedback feeds into one normalized student view. The feeds remain
separate in PostgreSQL so that source-specific quality problems are visible and
can be corrected without changing the student, authentication, or course tables.

## Source data

The seven `source_*_records` tables contain raw external student identifiers
and nullable source metrics. Attendance has one `OVERALL` row and zero or more
subject-code rows per student. Engagement records are keyed by one of `events`,
`clubs`, `hackathons`, or `certifications`. Source tables intentionally do not
constrain metric ranges or record uniqueness: integration must be able to ingest
and report messy feeds rather than reject them on arrival.

For the fictional seed data, identifiers in the forms `STU-000123`,
`student-123`, and `123` (also case/whitespace/punctuation variants) resolve to
the internal student ID `123`. Resolution removes whitespace and punctuation
and compares the result against aliases derived from existing student IDs.
Unmatched IDs are excluded from unified rows and counted as unresolved when the
report covers the whole institution. The pipeline does not guess identity from
names or email prefixes.

## Cleaning and merge behavior

- Logical duplicate keys are student + source record type; academic records
  further use term, attendance uses subject code, engagement uses activity
  type, and feedback uses category. The earliest inserted row wins and later
  matching rows are removed.
- CGPA must be in `[0, 10]`; percentage and placement/skill metrics in
  `[0, 100]`; feedback ratings in `[1, 5]`; count values must be whole,
  nonnegative numbers (backlogs at most 50).
- Invalid individual values are treated as missing and counted in
  `out_of_range_values`. Unknown engagement categories are excluded and counted
  in `invalid_rows`.
- Multiple valid values for the same student/metric are combined by median.
  Overall attendance uses the source's explicit overall value when present;
  otherwise it is the mean of that student's valid subject attendance.
- `rows_cleaned` counts resolved, unique source records retained in the merge;
  a record can remain after one or more invalid metric cells are nulled.
- Missing unified values are imputed with the institution- or department-scope
  median for that metric. If a metric has no valid value anywhere in scope,
  count values default to `0`, score values default to `0`, and feedback rating
  defaults to neutral `3`. `nulls_imputed` counts output cells imputed by this
  rule; it is not the count of null cells in the raw feeds.

## Run and inspect

For a fresh database, apply migrations and seed all fictional demo data:

```powershell
Set-Location .\backend
python -m alembic upgrade head
python -m app.seed
```

If the institution and student accounts already exist from an earlier seed,
apply the migration and add only the integration feeds:

```powershell
Set-Location .\backend
python -m alembic upgrade head
python -m app.seed_integration
```

The integration seed refuses to run if any source table already contains rows.
All generated source data is fictional and includes missing values, repeated
records, inconsistent identifier formats, unmatched identifiers, and
out-of-range metrics.

`GET /analytics/data-integration` returns `{ students, quality_report }`.
It requires a dean or principal access token. Deans receive only students and
quality counts associated with their department; principals receive the
institution-wide result. Students and faculty cannot call this endpoint. The
report includes ingested and cleaned rows per source, imputation/duplicate/
validation counts, and unmatched rows where the requested scope permits
counting them. The returned student view includes source coverage, cohort,
department, and cleaned metrics for the later scoring and dashboard phases.

Example (using the principal demo login):

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"principal@demo.invalid","password":"DemoPass123!"}'
Invoke-RestMethod `
  -Uri http://localhost:8000/analytics/data-integration `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```
