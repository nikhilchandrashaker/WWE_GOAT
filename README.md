# The Ledger — Pro Wrestling Analytics

A GOAT-scoring, rivalry-mapping, title-history, and win-prediction project built from a raw wrestling results database (88,243 matches, 1963–2026).

## Files

| File | What it is |
|---|---|
| `wwe_analytics_dashboard.html` | The interactive dashboard. Open it in any browser — all data is embedded, no server needed. |
| `wwe_clean.sqlite` | The cleaned database behind the dashboard. Query it directly with any SQLite tool if you want something the dashboard doesn't show. |
| `wwe_db_2026-01-18.sqlite` | The original raw source file (untouched), for reference. |

## Why the data needed cleaning first

The raw `Wrestlers` table wasn't one row per person — 76% of its rows were tag-team or multi-person combos stored as a single name (e.g. `"Christian York & Joey Matthews"` as one entity). Left as-is, every tag match a wrestler competed in would be invisible to their individual record. Phase 0 of this project split those combo rows into individuals and reclassified every match into one of three shapes:

| Shape | Definition | Count | Used for |
|---|---|---|---|
| Singles | 1 vs 1 | 61,149 | Individual GOAT score, singles record |
| Tag | 2+ vs 2+ | 23,483 | Team record only, kept separate |
| Multi-man | 1 vs many (battle royals, handicaps) | 3,597 | Its own bucket, not counted as singles or tag |

## `wwe_clean.sqlite` schema

- `wrestlers_individual` — 5,991 canonical individuals (`id`, `name`, `possible_collision`)
- `wrestlers_teams` — the original 14,679 combo entities, kept for reference
- `matches_singles`, `matches_tag`, `matches_multiman` — matches split by shape
- `participation` — flat (match, wrestler, side, context) table everything downstream aggregates from
- `wrestler_stats` — one row per individual: singles/tag/multi-man records, longevity, title reigns, strength of schedule, GOAT score
- `rivalries` — head-to-head pairs with 3+ meetings
- `title_reigns` — chronological reign history per belt (singles and tag)
- `belts_clean`, `match_types_clean` — junk blank-name rows removed

## GOAT score (draft weights — tell me how to retune)

For wrestlers with 10+ singles matches, each component is normalized 0–1 across the qualified pool, then combined:

- **30%** singles win rate
- **25%** total days held as singles champion
- **15%** years active
- **15%** singles match volume
- **15%** strength of schedule (average opponent win rate)

This is a first pass. Swap weights, add/remove components, or change the 10-match qualifying threshold and I'll rebuild the leaderboard.

## Win-prediction model

Logistic regression trained on 61,149 singles matches, using only information available **before** the match (no lookahead): career win rate entering, opponent's win rate entering, head-to-head win rate entering, experience gap, and title-match flag.

- **Test accuracy:** 72.6%
- **Test AUC:** 0.800
- **Naive baseline** (just pick whoever has the better career win rate): 70.0%

The model beats the baseline, but only modestly — wrestling outcomes follow narrative/booking logic that raw stats can't fully capture. Treat the predictor tab as illustrative, not a forecasting tool.

## Known limitations (also flagged live in the dashboard)

1. **109 wrestlers flagged `possible_collision`** — a career with a 15+ year span and an 8+ year gap in it. Could be a legend who appears sporadically (Pat Patterson, Gerald Brisco), or two unrelated people who used the same generic ring name (e.g. "Jason," "Angel," "The Shadow"). Not auto-resolved — flagged instead, since a wrong automatic split would be worse than an honest caveat.
2. **Same person, different names** (e.g. ring-name changes, nicknames) are still tracked as separate individuals. The Phase 0 split fixed the tag-combo problem, not name-continuity across a rebrand.
3. **Title reign lengths can be inflated** when a belt was retired, unified, or the dataset simply stops recording defenses for it — the reign's "end" becomes the dataset's end date (2026-01-16) instead of the belt's actual retirement. These are flagged with a ⚠ in the Title History tab wherever a reign has no recorded end and runs past ~5 years.
4. **`duration` is missing for 63% of matches** — excluded from the prediction model and from any average-match-length stats to avoid noise from heavy imputation.
5. **14 matches dropped** during Phase 0 due to broken winner/loser references in the source data — negligible, but not zero.

## Rebuilding from scratch

The pipeline is three scripts, run in order against the raw `.sqlite`:

1. `phase0_clean.py` — splits combos, classifies match shape, builds the core clean tables
2. `phase1_stats.py` — computes `wrestler_stats` and the GOAT score
3. `phase3_4.py` — computes `rivalries` and `title_reigns`
4. `phase5_model.py` — trains the win-prediction model, exports `model_export.json`
5. `build_dashboard.py` — assembles the final HTML dashboard with all data embedded
