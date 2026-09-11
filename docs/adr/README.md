# rcms/docs/adr/ — implementation-level decisions

**Scope:** decisions made *at the code level* for this specific repo —
folder structure, dependency management, code-level conventions. Not
domain/business rules.

**Domain-level ADRs (identifiers, Job types, the n8n contract, DMP
vendoring, etc. — ADR-01 through ADR-12, and Architecture v3.1's
ADR-13/14/15) stay canonical in `Octava_RCMS_Technical_Spec.md` and
`Octava_Architecture_Framework_Scaffolding.md` on Drive.** They are not
duplicated here. This split follows the same reasoning as this repo's
own `README.md`/`DESIGN.md`/`DATA-MODEL.md` versus the Drive spec: Drive
holds decisions that change rarely and need a durable audit trail; a
git repo's own docs, versioned by normal commits, are the better tool
for anything that evolves at code-review cadence.

## Registry name

`rcms` — used as the `registry:` field in each ADR's frontmatter, per
the ADR rollup tool's convention (`adr-rollup/example-adr/`). Numbered
independently from any other registry (the Drive-hosted ones, or
`RCMS-Research`'s own log) — by design, not an oversight. If this
repo's numbers happen to collide with another registry's, that's fine;
the registry name is what disambiguates, and the rollup tool checks for
content overlap regardless of number.

## Current log

| ID | Title | Status |
|---|---|---|
| ADR-001 | domain/adapters/api restructure | accepted |
| ADR-002 | pip, not uv, for dependency management | accepted (open question flagged) |
| ADR-003 | Authority vs. cache field Kind classification | accepted (verified against source) |
| ADR-004 | Job state-transition validation | accepted |
| ADR-005 | WorkCase cache-flag cascade on Job PATCH | accepted |
| ADR-006 | Single shared Postgres instance for the lab (DMP + RCMS) | accepted (amended 2026-09-11) |

**Note on ADR-006's number:** originally drafted and delivered as
"ADR-005" in a separate session that didn't have this log's actual
contents in view — a real collision with the ADR-005 already recorded
here (WorkCase cache-flag cascade). Caught and renumbered when this
log was reconstructed. Exactly the class of mistake the `adr-rollup`
tool exists to catch automatically; worth an actual run against this
repo once it's back in place, rather than relying on manual review
catching the next one.

## Adding a new one

Copy the frontmatter shape from any file here, or from
`adr-rollup/example-adr/ADR-001-example-template.md`. Required fields:
`id`, `registry: rcms`. Write the `## Summary` section densely — that's
what the rollup tool actually compares across registries when checking
for collisions or convergent decisions elsewhere. **Check this table
for the next free number before assigning one** — the ADR-005/006 mix-up
above is exactly what skipping that check produces.
