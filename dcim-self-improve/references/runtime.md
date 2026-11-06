# Runtime contract (v3 / reflect-search-v2)

Initialize with the repository scripts. Use the initialized run's pinned
`scripts/` thereafter: the run copies programs, geometry helpers and instructions
once, including scripts/search and the role-specific reflect-SKILL.md. Candidate
scripts also retain their actual helper versions. No redundant design/ copy is made. Updating the
framework does not silently alter a running experiment. Start a new run when
changing config/program contracts, linking the previous evidence deliberately.
The protocol is tested on Python 3.8; a newer configurable Python can be adopted
without changing these contracts. Optional GDS libraries are separate.

## Agent entry points

Commands below use absolute RUN/INPUT paths. `--run` precedes the subcommand.

```sh
python3 SKILL/scripts/configure.py --output PRIVATE_CONFIG --from-config OLD_CONFIG --init NAME
python3 RUN/scripts/workflow.py --run RUN status
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

Algorithms: `anneal` (default), `local`, `lns`, `beam`. Common limits: evaluations
1..10000, steps 1..100000, seconds (0,60], integer seed. `beam` controls retained
parent-pool width (1..64). `patience` bounds sampled non-improving local/LNS steps;
`neighborhood` bounds LNS subset size (1..64, clamped to movable count). LNS requires
`reinsert` in its allowed operations and samples a compound destroy/reinsert move;
it does not claim exhaustive or optimal repair. All options are recorded.

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
decision (`build`/`close`), proposals (1..6), route_updates (optional), task.
self_proposal names a NEW AI route in proposals. Its difference from existing
routes and minimal distinguishing experiment are mandatory, even at closure.
Each proposal needs source=ai, mechanism, expected, minimal_test, stop and evidence;
the self-proposal additionally needs difference. Exact normalized mechanism reuse
is rejected; semantic novelty remains an AI/evidence responsibility. The reply
cannot supply human feedback or human-source proposals. Requests carry
reflect_contract=reflect-search-v2 and allowed_sources=[ai, algorithm]. Existing
requests from an older contract must not be silently reinterpreted.
A close reply still requires reflection and a new idea. Task fields:

```json
{
  "route":"ROUTE_ID","module":"adder","stage":"module",
  "goal":"Test the learned grouping","stop":"One screened candidate",
  "checks":["geometry"],"execution":"geometry_only",
  "max_candidates":2,"learning_ids":["learn-ID"]
}
```

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
can seed repair, retaining its failed qualification status.

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
