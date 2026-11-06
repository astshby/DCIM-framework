---
name: dcim-reflect
description: Plan a DCIM rapid iteration inside Reflect using the immediately previous layout, reviewed experience, an original AI idea and bounded placement heuristics. Use for Reflect0 and subsequent route selection, including failed rounds and closure.
---

# Reflect rapid iteration

Reflect combines AI planning, actual heuristic searches and selection of the next
Builder task. Search calls are tools within Reflect, not another role or stage.
The loop and authority remain in [AGENTS.md](../../../AGENTS.md). The general
engineering experience remains in the [main guide](../../SKILL.md); learned
route-specific conclusions remain in short memory, not in this file.

## Begin from the actual previous round

Read the Reflect context delta after Analyst commits memory. The default baseline
is the candidate selected in the immediately preceding Builder result and reviewed
by Analyst. Even a failed candidate can be the next repair baseline when it has
usable geometry. Never silently substitute an older accepted version. If output
is absent, report the missing baseline and repair/recover that round's output.
Multiple candidates need an explicit primary baseline in the Builder result;
`--baseline` can select another candidate only if that same round's result and
review both cite it. Reflect0 alone starts from learned compiler/digital-flow
references; supply explicit initial placements when a reference arrangement exists.

Search imports coordinates, orientations and instance identities from retained
actual geometry plus its placement state. No automatic row repacking or snapping
of the baseline. A fresh objective re-evaluates both baseline and candidates under
the same conditions. Frozen instances stay exactly fixed. A new module population,
netlist or topology needs an explicit construction capability; the placement
search cannot pretend to implement it.

## Choose an algorithm and operations

| Evidence / task | First choice | Search scope |
| --- | --- | --- |
| Small/medium block arrangement, orientation or spacing | `anneal` | Legal instance moves; retain the best candidate separately from the current state |
| Mostly satisfactory placement, small local defect | `local` | Set `movable_ids` to the affected instances; freeze the remainder |
| Local search stalls; several blocks must move together | `lns` | Sample destroy/reinsert moves over a bounded subset |
| Several competing placement branches merit retention | `beam` | Retain several coordinate states within a common budget |
| Large standard-cell placement | Mature engine adapter | Not implemented in this release; do not label rectangle search as standard-cell placement |
| Fixed placement, routing defect | Routing adapter / reroute | Not implemented in this release; use a Builder task with a supported implementation |

Choose one primary algorithm from evidence and relevant memory. If uncertain,
compare small runs using the same baseline, objective, evaluation limits and
recorded seeds; preserve the total Reflect budget. Do not run every algorithm by
default. Algorithm choice controls exploration; operations define possible moves.
The current registry offers translate, swap, legal rotation, anchor reinsertion
and connected-cluster translation. LNS composes reinsertion across a sampled
subset. `step_um` is a search step, not an inferred process grid; supply `grid_um`
only from the applicable placement contract.

Call the run's pinned `planner.py`; inspect `--catalog` or context capabilities.
Only Reflect0 needs `--problem`; later searches reuse the previous output's
problem unless bounds, movable scope or objective are explicitly changed.
See [runtime.md](../../references/runtime.md) for exact inputs and commands.

## Interpret results and select

The fixed evaluator measures origin-anchored envelope area and center-HPWL.
It screens pairwise rectangle spacing, outline and an explicitly supplied grid.
It does not measure pin access, real routing, DRC/LVS, timing or power. Keep the
proxy status visible. Low proxy cost is a reason to build, not a qualified win.
AI does not invent numeric measurements. Record objective changes before search,
and don't adjust weights afterwards to make a chosen candidate appear better.

Each Reflect originates one new AI idea with mechanism, difference, expected
observation, minimal test and stop. It may target construction or a weakness in
measurement. Compare it with actual algorithm outputs; the AI idea need not win.
A coordinate plan can enter the same evaluator through `plan_spec.placements`.
Selecting a deliberately worse proxy for an informative experiment requires a
clear experiment rationale; do not call it a measured improvement.

Compose supported operations immediately through the existing search interface.
For an unsupported operation, assign its implementation and minimal verification
to Builder within the ordinary loop; register/version it after actual checks.
No extra operator-development stage, human input, or claim of autonomous arbitrary
code generation is introduced. Every new operator retains the common state and
independent evaluator contracts.

Return one concrete execution plan (or close): source baseline, chosen route,
learning references, expected effect, checks and stop. Freeze the final request
after search; its evidence remains immutable. Preserve trace, rejected candidates
and all generated layouts. Analyst checks Builder's actual output and commits
short condition / operation / observation / next_test records. Retrieve those
records next round; never replace reviewed experience with the search score.

## Bounded execution

Use CPU-only proxy evaluation in this release, with evaluation, proposal-step and
wall-time limits. Cached states avoid repeated objective work. Read summaries and
context deltas; inspect full traces only to diagnose a specific result. Record
algorithm/version, parameters, operations, baseline and objective identities.
No EDA or scheduler calls occur in these searches. Expensive verification belongs
to the authorized Builder/Analyst task and its selected revisions.
