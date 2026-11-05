# Stage-Scoped Route Memory

Revision: stage-route-memory-20261102. Read when retrieving or updating
experience. This governs future reviews; do not rewrite active packets or
historical evidence merely to adopt the structure.

## Scope before topic

Keep user-approved design principles separate from AI experimental memory.
Read the applicable project principles and [layout-order.md](layout-order.md);
AI may propose a revision with evidence, not silently replace human direction.
Transfer organization intent across nodes, not dimensions or rule exemptions.

Use the five stages in [stage-progress.md](stage-progress.md) as the first
retrieval boundary. Within a stage select by node/rule domain, module/interface
and route. A stage is navigation, not evidence that two implementations share
constraints. Multiple routes may remain active; no forced single winner.

Use a small index and create documents only when needed:

```text
knowledge/index.md                         stage -> summary path
knowledge/stage-2/summary.md                scoped route summaries
knowledge/stage-2/<route>/experience.md     current reusable conclusions
```

The index also points to the existing human-principle documents without
copying them. Stage summaries identify route/scope, lifecycle, supported
result and limitations, replacement if any, and detail/evidence paths.
They are current compact summaries, not a chronological round log.

Inside the selected scope, organize useful content under:

- Route effects, including process/construction mechanisms and sharing details.
  Pin access, well/tap context and folding failures belong to their route first.
- Electrical/sizing conditions and effects.
- Verification/tool methods.

These are optional sections, not required labels on every entry. Do not promote
a construction lesson to node-wide knowledge just because it cites a PDK rule.
Default to route-local scope. Analyst may make a stage-shared entry only with
evidence for its stated applicability; other stages link it rather than copy it.
Tool-wide methods bind tool/version assumptions rather than an invented node.

## Retrieval and route lifecycle

Builder reads human principles, the relevant stage summary and selected active
route details. It does not read inactive-route engineering history by default.
Analyst uses active details for the current task and short route summaries for
alternatives; it may skip irrelevant inactive summaries entirely. Reopen old
detail only for an explicit question that could change the decision.

Distinguish active, deferred, refuted-in-scope and superseded routes. Deferred
does not mean wrong; superseded does not mean functionally invalid.
Mark superseded-by/supersedes links in the current summary and replacement,
without modifying old acceptance evidence. A claim revision can supersede a
claim without retiring the whole route. A stopped trial does not refute its
entire topology family.

For inactive routes retain a short scope/result, why stopped or replaced,
what would warrant reopening, and evidence/replacement pointers. Do not keep
expanding their repair diaries or copy failed construction recipes into active
memory. Raw reports, code and historical decisions remain at their original
paths; this is exclusion from default retrieval, not evidence deletion.
An unvalidated diagnosis must remain uncertain, not become a general prohibition.

## Submission and review every round

A round here is a bounded Builder result followed by Analyst review, not every
internal routing retry. Every such round updates memory:

1. Builder submits proposed conclusions in its result using
   [experience.md](../templates/experience.md), with the relevant stage/route.
   Include failed or inconclusive experiments. If none, explicitly state
   no new reusable conclusion and the observation supporting that assessment.
   Builder does not edit accepted shared memory.
2. Analyst checks evidence and scope, then accepts, narrows, merges, rejects
   or leaves the proposal uncertain. Review this round's observations even if
   Builder omitted or overstated a lesson; missing submission is a handoff gap,
   not permission to fabricate an experiment.
3. Update the stage route summary every round with the review/result binding.
   Update affected conclusions and supersession links when evidence changes.
   With no new conclusion, refresh the compact summary's review binding and
   state no new conclusion/scope unchanged; do not append duplicate lessons.
   A framework-only review can record this outcome against its affected stage.
4. Record changed memory paths/revisions and disposition in the Analyst decision.
   Main chat checks this alongside task admission before dispatch.

The claim template has six fields: stage, applicability, single conclusion,
mechanism, evidence and supersession. Applicability includes the route and
unresolved limits. A mechanism may be unknown; observations stay separate from
causal hypotheses. Counterexamples are optional, never manufactured.
Preserve known contradictory evidence or restrict the claim accordingly;
optional counterexample testing is not permission to hide known failures.

Compare route benefit only at matched function/load/boundary/qualification.
Placement-only gains, MOS counts and simplified graph passes are not qualified
routed savings. Do not infer an alternative is worse because it is deferred.

Keep current dispatch priorities in policy.md, stage advancement in PROGRESS.md,
and historical reasoning in decisions/. None replaces the memory update.
No task queues, job lists or successive "next task" paragraphs in experience.

## Existing flat memories

Do not automatically ingest or rewrite an entire old library. At an authorized
review, index the relevant existing route conclusion, then extract only the
current reusable claim when useful. Keep old files as linked historical inputs.
Explicit packet references to an old file can be read in bounded excerpts;
new packets should point to the stage summary and selected effective route.
This skill revision does not itself migrate a live run or validate its claims.
