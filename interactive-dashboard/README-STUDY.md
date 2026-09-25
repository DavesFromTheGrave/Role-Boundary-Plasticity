# Role-boundary plasticity dashboard

Prepared for David Fisher's interactive dashboard project from the existing study records. The portable deliverable is `../role-boundary-dashboard.html`. Open it in a modern browser or send that single file to someone else. Its code and reviewed data are embedded; no account, server, installation, or model API is needed to explore it.

## Questions and views

The dashboard asks which instruction formats cross the tool/user boundary, and how channel, defenses, and forged reasoning change observed outcomes.

1. Instruction formats: main-experiment tool-result trials, without added defenses.
2. Channel comparison: eligible bare-command trials matched between the tool-result channel and the user-turn condition with prior legitimate context.
3. Defenses: matched comparisons within the main experiment and within the September follow-up, kept separate. The follow-up has no untreated baseline.
4. Forged reasoning: eligible styled/destyled pairs in the separate CoT arm, with a lab breakdown.

Lab, model and task filters apply across the page. Exact-count disclosures and source menus expose the denominators and selected trial metadata. Reset filters restores the full data selection. Model names are identifiers recorded in the supplied files.

## Snapshot and calculation scope

The September 22, 2026 preparation read and rescored these existing batches:

| Batch | Records | Eligible answers | Request errors | Provider refusals |
|---|---:|---:|---:|---:|
| Main | 4,264 | 4,133 | 99 | 32 |
| CoT | 1,652 | 1,531 | 111 | 10 |
| September local follow-up | 378 | 375 | 3 | 0 |

These are separate experimental cohorts. They are not a claim that all 6,294 records belong to the original main study. No new experiments or paid API calls were made. The B pilot has no collected rows in these sources.

The preparer reuses `rescore.py` and the offline loader functions in `score_cot.py`. The CoT loader repairs two errored rows from retry files and preserves intentional repeats. The old `out/rescored_all.csv` contains 2,700 records and is not the dashboard's source. Raw data, old rollups, the original `dashboard.html`, and the frozen `release/` were not changed.

Matched comparisons use provider, model, task, phrasing variant and thinking setting; defense comparisons also match normalized forgery format. Within a matching cell, each arm contributes the first minimum available number of eligible records, so repeated cells have equal counts across arms. This does not make repeated prompts statistically independent. Unmatched rows remain in cohort coverage totals but do not enter the paired rates.

Canary outcomes follow the project's fixed keyword heuristic; this dashboard does not newly human-adjudicate the flagged cases. Refund success means a recorded synthetic `issue_refund` call for $500, not actual money transferred. Missing/errored/refused answers are excluded from rate denominators, never silently treated as resistance. Rates describe a finite, nonrandom test set; no general risk estimates, causal generalizations, significance tests, or confidence intervals are claimed.

## Verified findings for the unfiltered snapshot

- Matched tool/user channel: 120/244 (49.2%) versus 218/244 (89.3%). The user-channel number is control compliance, not an attack success rate.
- Main defense comparison: 54/87 (62.1%) without added defense versus 30/87 (34.5%) under the strict defense.
- Matched CoT pair: 96/405 (23.7%) styled versus 89/405 (22.0%) destyled. The pooled difference is descriptive and does not establish equivalence.

## Reproduction and verification

From the repository root, use the existing Python and Node runtimes:

```text
python -B scripts/prepare_interactive_dashboard.py --output out/dashboard_snapshot_NEW.json
node --test --test-isolation=none interactive-dashboard/tests/study-data.test.mjs
```

The preparer refuses to overwrite an existing output. It writes only the chosen new snapshot and reads no credentials. Original source-file SHA-256 values are stored in the snapshot under `research.sourceHashes`. The dashboard exports only allowlisted trial metadata and scoring fields, excluding requests, responses, model reasoning, and error strings.

Use the installed Data plugin's build and `export-offline` commands from `AGENTS.md` after intentionally updating this app's snapshot or authored content. Retain its stable app ID. The authoring source is in `src/content/dashboard/`; the portable HTML is exported into `.data-app-offline/exports/` before copying to the deliverable path.

Eight focused checks passed for denominator rules, repeat matching, filters and reset, batch reconciliation, attack totals, paired totals, separate defense cohorts, and empty/error/task-specific selections. The local build and HTTP delivery passed. Browser inspection was blocked by automatic approval review; rendered layout, narrow-screen appearance and click-through interactions have not been visually verified.
