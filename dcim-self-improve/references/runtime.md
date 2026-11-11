# Runtime contract (v5 / reflect-multiscale-v5)

Initialize with the repository scripts. Use the initialized run's pinned
`scripts/` thereafter: the run copies programs, geometry helpers and instructions
once, including scripts/search and references/{initialize,reflect,builder,analyst}.md
(flat names under run/instructions). HANDOFF.md is developer history and is not copied. Candidate
scripts also retain their actual helper versions. No redundant design/ copy is made. Updating the
framework does not silently alter a running experiment. Start a new run when
changing config/program contracts, linking the previous evidence deliberately.
The protocol is tested on Python 3.8; a newer configurable Python can be adopted
without changing these contracts. Optional GDS libraries are separate.

## Agent entry points

Commands below use absolute RUN/INPUT paths. `--run` precedes the subcommand.

```sh
python3 SKILL/scripts/configure.py --output PRIVATE_CONFIG --from-config OLD_CONFIG --init NAME
python3 SKILL/scripts/roles.py --config PRIVATE_CONFIG
python3 RUN/scripts/workflow.py --run RUN status
python3 RUN/scripts/workflow.py --run RUN context --role initialize
python3 RUN/scripts/workflow.py --run RUN context --role reflect
python3 RUN/scripts/learn.py --run RUN --kind compiler --layout GDS_OR_JSON --top CELL --context SOURCE_JSON
python3 RUN/scripts/learn.py --run RUN --kind digital_flow --layout GDS_OR_JSON --top CELL --context SOURCE_JSON
python3 RUN/scripts/planner.py --run RUN --catalog
python3 RUN/scripts/planner.py --run RUN --problem PROBLEM_JSON --budget BUDGET_JSON
python3 RUN/scripts/workflow.py --run RUN request
python3 RUN/scripts/workflow.py --run RUN reflect --input AI_REPLY
python3 RUN/scripts/workflow.py --run RUN context --role builder --since PRIOR_TOKEN
python3 RUN/scripts/builder.py --run RUN --candidate NAME
python3 RUN/scripts/workflow.py --run RUN result --input BUILDER_RESULT
python3 RUN/scripts/workflow.py --run RUN context --role analyst
python3 RUN/scripts/workflow.py --run RUN evidence --id REPORT_ID --path REPORT
python3 RUN/scripts/workflow.py --run RUN review --input ANALYST_REVIEW
python3 RUN/scripts/memory.py --run RUN commit --input MEMORY_BATCH
python3 RUN/scripts/workflow.py --run RUN context --role reflect --since PRIOR_TOKEN
python3 RUN/scripts/planner.py --run RUN --budget BUDGET_JSON
python3 RUN/scripts/workflow.py --run RUN request
```

Names above are placeholders supplied by the agent, not literal paths. Each
command emits JSON or a nonzero error. Short context reads include only changed
sections when a prior token is supplied. Instruction deltas are per file, so
changing roles does not resend unchanged AGENTS.md or the general SKILL.md;
instruction_scope names the currently applicable files. Prior routes are bounded
to eight concise summaries for Reflect, with full history retained on disk. No routine source-code reread is needed.
Reference import/search precede a Reflect request; a saved request is immutable.
Actual AI replies must be supplied; the runner has no model API dependency.

## Reference and search inputs

Source context: `module`, `process`, `release`, `stack`, `source_run` strings.
Captured JSON uses `cells` mapping cell names to polygons, labels and references;
see the public `geometry.py` representation. GDS extraction is read-only.
Learning records include hierarchy, dimensions, pin labels, placements and layer
counts. They do not infer transistor topology or timing from physical shapes.

Search problem:

```json
{
  "blocks": [{"id":"a0","source":"learn-ID","cell":"ADD","width_um":2,
              "height_um":3,"orientations":[0]}],
  "gap_um":0.2,"max_width_um":20,"max_height_um":20,
  "nets":[],"wire_weight":1,"step_um":0.1
}
```

Use dimensions actually extracted from the cited reference; each instance is
explicit. Gap, orientation permissions and bounds come from the task/technology,
not historical defaults. Nets are explicit block connectivity for a center-HPWL
proxy; there is no inferred port routing. Optional `grid_um` declares a real
placement grid; `step_um` only sets the translation step (default one micrometer),
not a process rule. `movable_ids` optionally restricts which instances can change.
Reflect0 can supply `initial_placements` with exact id/source/cell/x_um/y_um/
width_um/height_um/rotation_deg fields. Without it, only Reflect0 uses a single-row
reference initialization. Subsequent searches never use that fallback.

After round zero, omit `--problem` to reuse the previous candidate's saved problem.
The program loads the immediately preceding result's baseline_candidate, verifies
its retained placement_state.json against actual layout.json transforms and starts
at those exact coordinates. An optional `--baseline CANDIDATE` must be cited in
both that round's result and review. Missing output stops search; an older accepted
candidate is never substituted. An explicit problem may change bounds, gap, grid,
move scope or objective; instance definitions and nets must remain identical.

Budget example:

```json
{"algorithm":"anneal","evaluations":256,"steps":2048,"seconds":5,"seed":4,
 "operators":["translate","swap","rotate","reinsert","cluster_shift"],
 "temperature":1,"cooling":0.99}
```

Algorithms: `anneal` (default), `local`, `lns`, `beam`, `adaptive`. Common limits: evaluations
1..10000, steps 1..100000, seconds (0,60], integer seed. `beam` controls retained
parent-pool width (1..64). `patience` bounds sampled non-improving local/LNS steps;
`neighborhood` bounds LNS subset size (1..64, clamped to movable count). LNS requires
`reinsert` in its allowed operations and samples a compound destroy/reinsert move;
it does not claim exhaustive or optimal repair. All options are recorded.

`adaptive` is a local ALNS-inspired strategy. It selects one of six pairs:
random/related/edge subset selection times sampled/greedy repair. Related favors
connected nearby instances; edge favors the right/top envelope. Sampled repair
repositions the subset jointly. Greedy repair explores a bounded beam of complete
coordinate states, one selected instance at a time; unprocessed members retain
their old coordinates. This is not an exact solver for a removed partial layout.
Each scored repair candidate consumes the SAME evaluation budget; duplicates use
the cache. Best-so-far includes intermediate repair states even at budget stop.

Additional options: repair_candidates 1..32 (default 8), repair_beam 1..4 (2),
adaptation_decay [0,1] (0.8). Candidate anchors mix low-envelope positions and
random positions; their preordering is an unqualified geometric heuristic, not
an extra objective evaluation. SA acceptance uses temperature/cooling. Outcome
rewards are 5=new best, 2=improved current, 1=accepted changed state, 0=otherwise.
Pair weight becomes max(0.1, decay*weight+(1-decay)*reward); positive floor preserves
exploration. Weights, uses, rewards and actual evaluations remain in the trace.
Incomplete repairs get no outcome reward. Weights reset each search call; Reflect
uses recorded summaries/experience for cross-round selection. No cross-run trained
policy is implied. A repair-heavy call makes fewer macro proposals under the same
evaluation cap. Do not compare algorithms only by proposal count.

```json
{"algorithm":"adaptive","evaluations":256,"steps":512,"seconds":5,"seed":4,
 "neighborhood":3,"repair_candidates":8,"repair_beam":2,"adaptation_decay":0.8}
```

Each Reflect also has aggregate caps of eight search calls, 10000 evaluations,
100000 proposal steps and 60 seconds of measured search wall time. Calls are
serialized by the run lock; effective budgets are capped by the remainder.
Identical requests return retained results without consuming another search call.
These are cheap CPU searches, not EDA job budgets. Wall-time stopping can change
results even with a fixed seed; deterministic regression uses evaluation/step caps.

All algorithms share coordinate state, operation implementations and evaluator.
Pairwise rectangle gap, outline and declared grid are cheap constraints. The
objective remains area/sum(block areas) + wire_weight*center_HPWL/sqrt(sum areas),
using an origin-anchored envelope. Baseline and candidates are evaluated with the
same objective. Trial identities/cache, parents, applied operations/parameters,
acceptance decisions, baseline evaluation, best candidate and stop reason are
retained. SA can accept worse feasible proxy costs, while best-so-far is retained;
no algorithm promotes a proxy to DRC/LVS/electrical qualification. If nothing
improves, the feasible baseline remains a possible unchanged result.

## Reflect and stage submissions

Reflect reply fields: request_id, request_digest, author=`ai`, comparison (<=1200
characters), evidence IDs, reflection (the short memory schema), self_proposal,
decision (`build`/`close`), proposals (1..6), route_updates and learning_updates
(optional), task.
self_proposal names a NEW AI route in proposals. Its difference from existing
routes and minimal distinguishing experiment are mandatory, even at closure.
Each proposal needs source=ai, mechanism, expected, minimal_test, stop and evidence;
the self-proposal additionally needs difference. Exact normalized mechanism reuse
is rejected; semantic novelty remains an AI/evidence responsibility. The reply
cannot supply human feedback or human-source proposals. Requests carry
reflect_contract=reflect-multiscale-v5 and allowed_sources=[ai, algorithm]. Existing
requests from an older contract must not be silently reinterpreted.
A close reply still requires reflection and a new idea. Task fields:

```json
{
  "route":"ROUTE_ID","module":"adder","stage":"module",
  "goal":"Test the learned grouping","stop":"One screened candidate",
  "checks":["geometry"],"execution":"geometry_only",
  "max_candidates":2,"learning_ids":["learn-compiler","learn-flow"],
  "learning_goals":["goal-parent-boundary"]
}
```

`learning_updates` creates or supersedes bounded persistent hypotheses. Example:

```json
[{"id":"goal-parent-boundary","module":"adder","stage":"module","scope":"general",
  "condition":"Compiler and flow references have explicit retained boundaries",
  "operation":"Test the complete parent at a shared interface",
  "observation":"Reference envelopes motivate a grouping hypothesis, not qualification",
  "next_test":"Independently check actual parent geometry and separation",
  "evidence":["learn-compiler","learn-flow"],"checks":["geometry"]}]
```

Each text field is <=240 characters, updates <=6, evidence <=8, active goals <=6
per module and <=24 overall. Stage/module and process scope must match the task;
process scope requires exact technology. General methods carry no technology
claim. Evidence must include captured learning observations; Analyst review IDs
may additionally justify a correction. A correction supplies supersedes and a
new ID, retaining the old goal and all outcomes. Task learning_ids must carry its
goals' reference sources and task checks must include their checks. Every task binds its module-specific reference kinds; dcim integration binds
both compiler and digital-flow. Later tasks reuse or revise applicable goals. Closing without a construction needs no new goal.

Context learning_focus returns active goals plus latest learning_checks regardless
of recent-memory age. Reflect sees all modules; Builder/Analyst see their task
module. Full old outcomes stay in state and immutable reviews. Goals persist within the run. Cross-run methods use explicitly selected reviewed
experience bundles (described below); receiving tasks must validate them anew.

AI proposals contain the fields above. They may supply a `plan_spec` referencing an
search artifact from this Reflect and explicit `placements` (the coordinate
fields listed above). Legacy `order` (block-index permutation), `cuts` (row
boundaries) and `rotations` remain an explicit input adapter. The same evaluator
checks dimensions, orientation, gap, outline, grid and frozen-instance positions.
Only a measured current-Reflect plan can be selected for Builder; stale routes
remain archived and cannot become a new build without current evaluation. Algorithm proposals are created only by actual search.
An idea without a supported plan may be retained but cannot be drawn by Builder.

Builder result: round, task_id, outcome (`passed`/`failed`/`incomplete`), summary,
evidence IDs, and `baseline_candidate` when multiple candidates are retained.
A single candidate is inferred automatically. The chosen candidate must be in
this round result evidence; a passed result needs an actual placement snapshot.
Analyst review: round, result_id, verdict (same values), scope,
summary, evidence, checks mapping each required check to passed/failed/incomplete/
not_run. Required checks must all pass before a passed verdict. Review evidence
must include the chosen baseline candidate. A failed review with usable geometry
can seed repair, retaining its failed qualification status. Each candidate stores
learning_contract.json containing the exact bound goal versions. Analyst must
add learning_checks with exactly the task goal IDs:

```json
{"goal-parent-boundary":{"conclusion":"supported",
 "observation":"Independent checks passed within the synthetic geometry scope",
 "evidence":["CANDIDATE_ID","INDEPENDENT_REPORT_ID"]}}
```

Evidence must be included in the review and include current-round candidate/file
or evidence artifacts. Supported requires every goal check passed; refuted requires
checks completed (passed or failed); missing work is inconclusive. An inconclusive
result may cite the current Builder result when construction produced no output.
No check status alone proves scientific validity: Analyst must inspect evidence.
Learning outcomes are retained separately from the original goal and are available
to subsequent Reflect. Ordinary short memory still follows the review.

Memory batch: round, disposition (`new`/`revised`/`no_new`), entries. See
experience-memory.md for the single bounded record format.
Program-derived search_context metadata links each applicable record to its
search and baseline, without adding AI-authored text. Request/response and stage
identities are checked; identical resubmission is idempotent, conflicting
resubmission fails. The entire stage transition commits atomically under a run lock.

## Server execution and evidence

Current runner executes fixed generated Python with argv, explicit cwd, separate
stdout/stderr and a 30-second timeout. It does not invoke an EDA binary or scheduler.
Run copies are versioned inputs; each candidate saves draw.py, helper code, source
geometry, execution details, outputs, logs and object IDs. Placement state is
measured from actual generated references, not copied blindly from a proposal.
Default context reports the previous baseline, capability catalog and current
search summaries; full trial traces are read only for a specific investigation. The experiment registry
retains accepted and failed trials. Original input changes do not change snapshots.
An interrupted candidate directory is retained and never automatically rerun.
Inspect its execution/outcome files before collecting or creating a new candidate.

`history.py` additionally retains full iteration/prompt bundles and appended
verification, adapted from improve 1. `evidence.py` from improve 2 checks immutable
report dependencies; its freeze alone remains a fingerprint operation. SHA values
inside run metadata identify evidence, not release checksum sidecars.

Program enforcement applies to these entry points. Direct shell execution and
manual state edits are not sandboxed. Independent AI context isolation, live EDA
submission/recovery, actual routed objectives and broader circuit/topology search
are not implemented by this geometry protocol.


A continuing AI context may use `request --since TOKEN` after consuming that context
packet. The immutable request retains instruction identities and only changed
instruction text. Its returned context_token can be used for later deltas. Omit
--since for a fresh AI context; never reuse another agent's receipt. Missing or
unknown tokens fall back to full instructions. An already frozen request remains
immutable on retry. This optimizes delivery, not evidence retention.

Run relocation preserves the whole run directory, including pinned programs,
instructions, objects and experience bundles. New request indexes store relative
paths; request/reply recovery reads the hash-verified request object. The returned
`path` is a usable absolute object path in the current location. It is a read-only
input, not a place to write an AI reply. Save the reply as a new file.
Artifact `origin_path` and experience origin metadata describe where capture
occurred; runtime lookup uses relative objects/manifests. Artifact `suffix` retains
the input format; legacy `source` fields supply only that format and are never
opened. Old request path fields are also ignored by this version's reader.

Use the moved run's `scripts/workflow.py --run /new/run status` at entry, then its
normal request/context commands. Migration does not update already pinned code:
existing runs retain their original behavior and may still need compatibility
links. Do not replace their scripts, config, state or immutable evidence in place.
External EDA dependencies and older history bundles have their own path contracts;
portable evidence manifests are described in evidence-tools.md. A moved run is
not permission to rerun an interrupted candidate or resubmit a job.


Tasks may request optional `export_gds_precision_m` (positive and <1e-6 meters)
from an explicitly checked source/technology resolution. Builder then retains
layout.gds and gds-map.json as candidate evidence. This requires gdspy. Missing
export dependencies fail the candidate; export never implies DRC/LVS acceptance.
Labels retain origin, orientation, reflection, anchor and magnification. Check
mask and label preservation independently before trusting real-layout roundtrips.


External role experience is opt-in through experience_root and explicit
input_files.experience_root bundle manifests. experience.py publishes selected
reviewed lessons and evidence into a NEW run-owned directory. Initialization
pins verified bundles; role_experience returns scoped reference-only methods.
See experience-memory.md for promotion, version selection and trust boundaries.

## Device mode and campaign coordination

For transistor-placement-v1, execution=transistor_proxy, independent device audit,
and closed-run campaign acceptance, read [transistor-planning.md](transistor-planning.md).
The coordinate examples above retain their legacy rectangle representation; device
plans cannot be reinterpreted as routed or foundry-qualified layouts.

Existing solver and private physical Builder contracts: [two-scale.md](two-scale.md).

## Optional physical action guard

The existing private-physical-adapter-v1 contract accepts action_guard. Its shape
is {schema: physical-action-guard-v1, baseline: BASELINE, required: REQUIRED}.
BASELINE maps exactly layout.gds, source.cdl and routed.def to {artifact, sha256}.
REQUIRED maps action IDs to operation, object, parameters, conditions (nonempty
affected names) and optional frozen_conditions (unaffected names). Each condition
is unique; affected/frozen sets must be disjoint. The captured adapter fixes these
values before a plan is accepted.

A guarded construction_plan is physical-action-plan-v1 with baseline, actions and
checks. Every action has exactly id, operation, object and parameters and equals
the adapter's action. Every check has exactly action_id, condition, artifact,
sha256 and record. Its artifact is a physical-action-checks-v1 object containing
records. Each selected record has action, condition, baseline, scope (affected or
frozen_unaffected), status (passed or unknown), and observation. observation has
artifact, sha256 and pointer; it must resolve into nonempty structured data in a
separate captured raw JSON artifact. Unknown affected checks reject.

Guarded prepare argv must include the standalone PLAN, ADMISSION, PARENT_GDS,
PARENT_CDL and PARENT_DEF placeholders with braces, so the consumed copies are
reviewable. The Builder writes action-admission.json and baseline/ copies; these
are rechecked on subsequent actions. A physical-action-witness-v1 consumption
record has exactly schema, plan_sha256, admission_sha256 and outputs. outputs maps
the three baseline labels to the actual deliverable hashes. All stage receipts
and complete-module checks still apply; witness validity does not qualify design.

See two-scale.md for limits: fixed declared action scope, no automatic discovery
of impacted conditions, no physical solver or topology reconstruction, and no
inherited validation from an identity match.
