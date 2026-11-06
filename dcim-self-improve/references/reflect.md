# Reflect: responsibility and reusable experience

Reflect0 learns from compiler AND digital-flow layouts. Compare hierarchy, block
sizes, pins, repeated structure and packing; distinguish observed geometry from
hypothesized mechanisms. Derive a bounded next construction with learning IDs,
module/interface, checks and a stop condition.

Every Reflect must originate one concrete, testable AI idea, including Reflect0,
failed rounds, continuing the same route and closure. This responsibility belongs
to Reflect, transferred from Analyst. The idea may change construction, isolate a
cause, improve a measurement or expose an omitted degree of freedom. State its
mechanism, difference from existing routes, expected observation, evidence,
minimal_test and stop. Repeating the algorithm winner is insufficient. This is a
visible scientific proposal, not a request to record hidden reasoning.

Reflect has two method sources: AI self-reflection and actual heuristic search.
There is no human proposal/feedback input. Project goals/permissions are supplied
through the framework contract. Before freezing the decision request, inspect the
context and run planner.py with a bounded problem/budget if useful. Search results
are evidence; do not fabricate missing algorithm runs.

Compare the AI idea against the algorithm proposals on matched conditions. Choose
one method or the smallest discriminating experiment; the self-proposal need not
win. Use route_updates to defer an unselected idea. Final reflection must still
state a useful new hypothesis or follow-up check, without automatically launching
it. A new idea does not require an expensive competitor on each ordinary repair.

Return request_id/digest, author=ai, comparison, evidence, short reflection,
self_proposal (ID of the new AI proposal in proposals), proposals, optional
route_updates, decision build/close and a task if building. workflow.py rejects
missing ideas, whitespace-only fields, wrong sources and verbatim mechanism reuse.
Those checks enforce observable submissions; they do not prove semantic novelty.
Use plan_spec.placements for a new explicit coordinate placement evaluated under
the same objective and frozen-instance constraints. The shelf input adapter
remains available for explicit proposals; it never reconstructs a saved baseline.

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
| Local search stalls; several blocks must move together | `adaptive` | Choose related, boundary or random groups; adapt sampled/greedy repair weights |
| Several competing placement branches merit retention | `beam` | Retain several coordinate states within a common budget |
| Large standard-cell placement | Mature engine adapter | Not implemented in this release; do not label rectangle search as standard-cell placement |
| Fixed placement, routing defect | Routing adapter / reroute | Not implemented in this release; use a Builder task with a supported implementation |

In bounded synthetic checks, adaptive repair helped loose arrangements more than
already compact repeated seams, where annealing could do better. Treat that as a
selection hypothesis, not an across-process ranking; inspect relevant reviewed
experience and run a small matched comparison when evidence is insufficient.

Choose one primary algorithm from evidence and relevant memory. If uncertain,
compare small runs using the same baseline, objective, evaluation limits and
recorded seeds; preserve the total Reflect budget. Do not run every algorithm by
default. Algorithm choice controls exploration; operations define possible moves.
The current registry offers translate, swap, legal rotation, anchor reinsertion
and connected-cluster translation. Plain `lns` retains sampled compound reinsertion as a cheap comparator.
`adaptive` adds learned operator selection and bounded candidate repair, using
the same fixed evaluator. It is an ALNS-inspired local implementation (see
[sources.md](sources.md)), not an imported placement engine. `step_um` is a search step, not an inferred process grid; supply `grid_um`
only from the applicable placement contract.

Call the run's pinned `planner.py`; inspect `--catalog` or context capabilities.
Only Reflect0 needs `--problem`; later searches reuse the previous output's
problem unless bounds, movable scope or objective are explicitly changed.
See [runtime.md](runtime.md) for exact inputs and commands.

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

## Persistent learning targets

Submit `learning_updates` when creating or correcting a learning hypothesis.
Use condition / operation / observation / next_test (each <=240 characters),
module, stage, general/process scope, captured reference evidence and required
check names. General means a transferable method, not a process-independent
signoff result. Process hypotheses bind process/release/stack exactly.

The first Builder task must bind compiler AND digital-flow observations through
its `learning_goals`. Later tasks may reuse active goals or correct them with a
new ID and `supersedes`; retain the original and its checks. Task checks must
include each bound goal's checks. Each candidate saves learning_contract.json.
Analyst returns supported/refuted/inconclusive with current-round evidence for
every bound goal. `learning_focus` keeps active goals and their latest checks
available even after recent short memory ages out; Reflect sees all modules,
while Builder/Analyst see the task module. Check contradictory outcomes before
reusing a goal. Up to six active goals per module and 24 overall bound retrieval.

## General lessons to carry across nodes

- Compiler points reveal dimensions and overhead for their stated interfaces;
  two sizes do not establish a universal area-scaling law. Compare width, height,
  boundary and parent cost as well as area. Test the smallest useful new case.
- A compact leaf can worsen repeated seams, access or shared periphery. Learn
  from the actual repeated slice before scaling to a macro; accept a larger
  module when the complete parent demonstrably improves.
- An inactive output alone does not establish removable circuitry. Trace its
  timing/assist, supply and well dependencies; use a controlled removal test.
- Distinguish physical weight bandwidth from nominal port width or serialized
  software access. Bind a proposed mapping to an independent arithmetic oracle.

These are conditional methods distilled from improve 2 and legacy experiments,
not transferred qualification. Sources and exclusions: [sources.md](sources.md).


Plan a meaningful compact preliminary experiment before deciding repair scope. Treat a high DRC count as diagnostic input, not sufficient evidence to discard a route; preserve the mandatory PP/NP and body-supply constraints in SKILL.md.


The program may add role_experience from explicitly configured, pinned experience
bundles. These are reviewed source methods, always reference-only in this run;
inspect source_status, conditions and evidence before a new test. To maintain
reusable experience after review, publish selected current lessons with
experience.py; see experience-memory.md. Static role text remains versioned policy,
not a per-round journal. No automatic write to the installed guide is performed.
