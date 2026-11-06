# Reflect

Use the [Reflect experience guide](../roles/reflect/SKILL.md) for algorithm and
operation selection. It is pinned as instructions/reflect-SKILL.md in new runs.
Search is an internal Reflect tool call, with no added workflow stage. After
Reflect0, use the immediately preceding reviewed candidate as the baseline.

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
