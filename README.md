# Age of Enteland — engine + solver (Python)

A rules-accurate simulation engine for Entelect's "Age of Enteland" University
Cup challenge, plus a heuristic solver that plans and writes submission
files, and a CLI to drive both.

```
enteland/
  data.py         global constant tables (resources, recipes, components,
                   upgrades, tools) loaded from data/resources.json
  state.py        level data model (Level, Town, Node, Route) — loads a
                   level JSON file
  simulator.py     the engine: executes an actions list tick-by-tick-exact
                   against a level, action by action, per the spec's rules
  scoring.py       PROXY scoring only — see "About scoring" below
  solver.py        GreedySolver: a heuristic baseline planner
data/resources.json  global constants (digitised from the spec + the
                      supporting-resources.zip you were given)
examples/            two level files used for validation (see Tests)
tests/                pytest-free tests (plain asserts) validating the
                      engine against the spec's own Worked Example
cli.py                `plan` (run the solver, write a submission .txt) and
                      `run` (replay/verify an actions file)
```

## Quick start

```bash
# sanity-check the engine against the spec's own worked example
python3 tests/test_worked_example.py

# plan a level with the heuristic solver (once you have the real level file
# from the challenge site's "Download Supporting Resources"/level pack)
python3 cli.py plan --level 2 --level-file path/to/level2.json \
    --out level2_actions.txt --verbose

# re-verify a submission (yours or the solver's) exactly like the judge will
python3 cli.py run --level 2 --level-file path/to/level2.json \
    --actions level2_actions.txt
```

`level2_actions.txt` is exactly the `{"actions": [...]}` JSON the Submissions
section describes — zip up this source tree as the "source code" part of a
submission, alongside that `.txt`.

## What's implemented (engine)

Every mechanic in the spec: travel (standard + fast routes, tolls, boots),
buy, sell (raw resources at the global price; crafted goods at the current
town's item-rate), craft (recipes, construction components with their
dependency chains, tools), build (production + civic upgrades, per-town
uniqueness, prerequisites), gather (all node types, pickaxe), upkeep
(doubling + refresh-not-stack + fire-station's +50% duration), the
tick-limit cutoff rule, and the "invalid action = 1 tick, log, continue"
rule for malformed or prerequisite-failing actions. Level gating (which
mechanics are legal) is driven by `data/resources.json`'s `level_unlocks`.

**Validated against the spec's own Worked Example** (`tests/test_worked_example.py`):
replaying the same 7 actions the spec walks through reproduces its exact
numbers — tick 16, Enteloot 200 → 360 — action for action.

### Interpretation notes (things the spec leaves slightly open)

1. **Passive trickle formula.** The spec gives `accumulated = floor(tick /
   rate) × amount` and says amount/rate can change mid-run (production
   upgrades, civic % bonuses, upkeep's temporary doubling, police-station's
   rate cut). The engine flushes each town's trickle into the player's
   balance immediately before any such change (and additionally splits a
   flush at an upkeep-expiry boundary), so the formula is exact for the
   normal case. The one approximation: if a rate change (police-station)
   and something else land inside the same unflushed window, the very last
   partial cycle at that boundary is attributed with the newer rate. This
   only matters for a same-tick coincidence involving the police-station,
   which is late-game and rare.
2. **Trickle is auto-credited to the player's global balance** (Assumption
   6), not to a town-local pool — consistent with Unlimited Inventory and
   selling from anywhere.
3. **Tick-limit cutoff vs. generic invalid-action handling** are treated as
   two different rules per Assumption 1 vs. Assumption 4: if an action's
   *real* cost (or 1 tick, for something malformed/prerequisite-failing)
   would push the clock past `total_ticks`, it's skipped and the clock
   jumps straight to `total_ticks` (once) — it does *not* also pay the
   generic 1-tick invalid-action penalty.
4. **Upkeep's boost window** is modelled as starting the moment the 5-tick
   upkeep action *completes* (not when it's triggered), lasting 50 ticks
   (75 with fire-station at that town).

None of this affects the well-specified core (ticks, Enteloot, inventory,
upgrade/tool effects) — those are implemented literally off the spec's
tables and formulas.

## About scoring (important)

The spec describes scoring only qualitatively for Level 1 ("generation of
Enteloot, value of held items, a multiplier from items sold") and Level 2-4
("infrastructure is the primary driver, spread across towns earns a
multiplier"). It gives exact `score_value` points per upgrade, but the
precise combining formula isn't published — the one concrete formula in the
document (`distribution_multiplier = built / total_possible`) is explicitly
listed under "Ideas" as a proposal, not a confirmed rule.

`scoring.py` therefore implements a clearly-labelled **estimate**, good
enough for the solver to rank candidate strategies against each other, but
it will not match the official judge's number. If Entelect publishes/
clarifies the real formula, that's the one file to change — nothing else in
the engine depends on it.

## About the solver (`solver.py`)

`GreedySolver` is a **heuristic baseline**, not a true optimiser — the real
planning problem (routing + gather/buy/craft/sell/build scheduling under one
shared tick budget) is a large combinatorial search. What it does: at each
step it prices a handful of candidate "programs" — gather-and-sell a
resource, craft-and-sell a good, craft a tool, or build an upgrade
(recursively expanding the construction-component dependency chain and
choosing gather-vs-buy per ingredient) — by value gained per tick spent, and
greedily runs the best one, repeating until the tick budget runs out.

It's deliberately built to run directly against the live `Simulator`
(rather than plan on paper and hope), so **everything it writes out is
already verified valid and deterministic** — see the `plan`/`run` round-trip
in the CLI section above.

Known simplifications worth improving if you want a stronger score:
- Route planning ignores fast routes (always takes the standard route) —
  there's a real opportunity in evaluating toll-vs-ticks-saved.
- Programs are evaluated and picked one at a time (greedy), with no
  look-ahead or backtracking.
- Tool value is a flat heuristic constant (their real value — ticks saved
  on every future travel/gather — depends on how much run remains).
- Ingredient sourcing (`_source_leaf_plan`) doesn't yet apply an
  already-owned pickaxe's gather-time discount to its own cost estimate
  (the engine still executes and charges the *correct* discounted cost —
  this only makes the solver's own ranking slightly conservative).

## Tests

```bash
python3 tests/test_worked_example.py
```
Covers: the spec's Worked Example reproduced exactly, invalid-action
handling (unknown destination, insufficient resources, unknown type,
missing field — each 1 tick, logged, run continues), and the tick-limit
cutoff (action skipped, clock jumps to `total_ticks`, remaining actions all
skipped too).

`examples/level_example.json` is the full 3-town map from the spec's
Appendix (JSON level file example) — useful for exercising fast
routes/tolls end-to-end; the solver currently doesn't route over fast edges
(see above) so it'll only ever take the standard Demacia↔Piltover edge there.
`examples/worked_example_level.json` is a minimal 2-town/1-node map built to
match the Worked Example's own numbers (its passive trickle rates are set
very high specifically so trickle contributes nothing inside the 16-tick
window being checked, isolating the travel/gather/craft/sell arithmetic the
example is illustrating).

## What you still need to do

1. Get the actual `level1.json`..`level4.json` files from the challenge
   site (they weren't in `supporting-resources.zip` — that only contained
   the global constants table) and drop them wherever you like.
2. Run `plan` for each level, eyeball/tune the solver if you want a better
   score than the greedy baseline, then `run` to double-check validity
   before uploading both the source zip and the `.txt` per level.
