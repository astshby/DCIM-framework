# Stage-Scoped Route Memory

Revision: stage-route-memory-20261109-context-dispatch. Read when retrieving or updating
experience. This governs future reviews; do not rewrite active packets or
historical evidence merely to adopt the structure.

## Scope before topic

Keep user-approved design principles separate from AI experimental memory.
Read the applicable project principles and [layout-order.md](layout-order.md);
AI may propose a revision with evidence, not silently replace human direction.
Transfer organization intent across nodes, not dimensions or rule exemptions.

Use the task-declared stages described in [stage-progress.md](stage-progress.md) as the first
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

Analyst starts from the stage overview and explicitly selects relevant human
principles, stage summaries, route mechanisms and task/rule/tool resources.
Builder reads that selected material in its own context; Main need not read
the full body. Neither script keywords nor tag/layer ranking selects a
structure. Analyst uses active details and short alternative-route summaries,
reopening old detail only for an explicit decision-relevant question. Builder
does not read inactive-route engineering history by default.

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

## Builder context contract

A fresh structural Builder receives a small task packet, not the parent chat
or every previous log. Use `scripts/context_dispatch.py` for the following
selection-to-delivery contract:

1. `overview --catalog CATALOG --stage STAGE` returns all catalog entries for
   that stage. It is an index view, not a source validation or route decision.
2. Analyst writes an explicit selection: task/host/profile/stage,
   `catalog_revision`, `decision`, `route_id`, `entry_ids`, and resources with
   `id`, `path`, `purpose`, optional `sha256`, and `inline`/`reference` mode.
3. `prepare --task TASK --selection SELECTION --catalog CATALOG --out DIR`
   resolves selected `requires` dependencies and assembles a new exclusive
   package. It returns a small dispatch card, not the bundle body. Entry
   metadata and paths are included; summary/evidence text needs an explicitly
   selected inline resource to appear in the body.
4. Main checks admission/card and makes one native dispatch with its bootstrap.
   The first dispatch of a new task uses `the native fresh-context setting`; ordinary work
   within the same active route AND explicit task reuses its Builder.
   Main does not open/paste the experience body, but must check the mandatory
   inline architecture contract against the proposed placement.
5. Builder itself runs `open --package DIR --expected-sha256 HASH` on the
   declared host, reads the emitted context and applies the task.
6. `record --package DIR --agent-id ID` records the actual native tool-returned
   ID. It is caller-reported bookkeeping, not proof of dispatch, reading or
   understanding. Ordinary Python does not invoke the native API. Reconcile
   an uncertain native submission before retry; the script is not an
   exactly-once dispatcher.

There is no `expand` command. Missing context or a changed selection requires
Analyst's explicit new selection and a new package, leaving old bindings
unchanged. Main can deliver its bootstrap to the existing Builder while the
same task remains active; a later task uses a fresh instance and file handoff.
A context supplement alone does not authorize rerunning completed verification.

### Binding And Budget Checks

`prepare` checks the execution hostname allowlist, matching host identities,
task/profile/stage identities, catalog revision, explicit decision/route,
unique IDs, required resources and missing/cyclic experience dependencies.
It resolves existing source files within declared `allowed_roots`, including
task/selection/catalog and the dispatcher/evidence/config scripts; the catalog root
must itself be declared. Optional resource hashes are checked when supplied.
All bound source bytes/hashes are recorded, and the package uses evidence.py's
schema-version-1 manifest. Entry revisions are metadata, not an independently
checked per-entry version registry or a semantic applicability check.

`max_bundle_bytes` bounds the assembled UTF-8 bytes and each inline file;
it is not a character count or exact token measurement. Overflow is incomplete:
Analyst must split/reselect, never silently truncate or auto-drop material.
`open` checks the expected manifest digest, frozen package files, current
source fingerprints and execution hostname before emitting the bundle.
These checks do not prove authority, comprehension, or physical correctness.
Source-root guards do not sandbox Builder writes or validate the output
directory against the task's write scope; Main/Builder retain that obligation.

### Selected Content

Organize Builder's selected working context in these layers:

1. Current user constraints, admitted task, immutable baseline, allowed edits,
   required checks, output ownership and installed skill revision.
   For physical tasks this includes a mandatory inline architecture contract:
   approved hierarchy/adjacency/mirroring, common functional rows, continuous
   straight PP/NP bands and shared TAP/body ownership. Bind its authoritative
   sources as required resources, not optional experience. See
   [architecture admission](layout-order.md#mandatory-architecture-admission).
2. Resolved experience index, relevant stage summary and selected route entries.
   Analyst identifies decision-relevant earlier mechanisms as well as the newest
   result. A chronological latest report alone is not a history search.
3. Actual generator/contact/interface code and applicable rule excerpts needed
   to apply or challenge those mechanisms. Open raw evidence only for a concrete
   missing detail or contradiction; do not replay already completed verification.

Before committing to a structural placement, Builder checks the relevant
summaries and records a short experience-use section in the working result:
source and scope -> adopted/adapted/not applicable -> concrete construction,
route, check or experiment affected. Do not create one document per lesson,
copy whole histories, or treat a read receipt as evidence of correct use.
No fixed number of retrieved entries is required.

For compaction, include earlier contact/routing/context-sharing mechanisms,
not only the latest DRC repair. Old dimensions, device domains, metal allowances
and failed fixed-template bounds do not automatically transfer to a new parent.
Inactive routes are summary-only by default; reopen detail for a named useful
mechanism rather than discarding it solely because the route was superseded.

If the index is missing or older than relevant accepted results, name that gap,
ask Analyst to select bounded result/experience fallback sources and refresh
the index. Missing or changed frozen sources require a new valid package;
unrelated library housekeeping does not block already valid admitted work.
Do not silently assume no experience exists or scan all logs.

The Builder role is reusable; an instance is not a permanent route memory.
Reuse it only for ordinary repairs within the same active route and task.
After delivery, a structural decision, a stage change or a new substantive
task, close that instance and start fresh with `the native fresh-context setting`, even on
the same route. Carry the current result, source/layout/code bindings,
terminal or explicitly handed-over active job identity/collection instructions,
tried mechanisms and unresolved issues, plus scoped memory paths; do not
copy full transcripts or repeat completed experiments to restore context.
Small bundle bytes do not establish a short total session: subsequent messages
and tool outputs also accumulate. File handoffs bound the task lifecycle;
do not create a new agent for every routine fix or merely to read a supplement.
Reading and writing memory are explicit actions, not automatic model training.

## Submission and review every round

A round here is a bounded implementation result followed by an Analyst decision, not every
internal routing retry. Every such round updates memory:

1. Builder submits proposed conclusions in its result using
   [experience.md](../templates/experience.md), with the relevant stage/route.
   Include failed or inconclusive experiments. If none, explicitly state
   no new reusable conclusion and the observation supporting that assessment.
   Builder does not edit accepted shared memory.
2. Analyst assesses the supplied evidence and scope, then accepts, narrows, merges, rejects
   or leaves the proposal uncertain. Review this round's observations even if
   Builder omitted or overstated a lesson; missing submission is a handoff gap,
   not permission to fabricate an experiment.
3. Update the stage route summary every round with the review/result binding.
   Update affected conclusions and supersession links when evidence changes.
   With no new conclusion, refresh the compact summary's review binding and
   state no new conclusion/scope unchanged; do not append duplicate lessons.
   A framework-only review can record this outcome against its affected stage.
4. Record changed memory paths/revisions and disposition in the Analyst decision.
   No mandatory independent replay is required. Main chat checks the decision
   and task admission before dispatch.

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
