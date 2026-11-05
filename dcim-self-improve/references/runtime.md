# Runtime contract (v2)

Initialize with the repository scripts. Use the initialized run's pinned
`scripts/` thereafter: the run copies programs, geometry helpers and instructions
once. Candidate scripts also retain their actual helper versions. Updating the
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
python3 RUN/scripts/workflow.py --run RUN request
```

Names above are placeholders supplied by the agent, not literal paths. Each
command emits JSON or a nonzero error. Short context reads include only changed
sections when a prior token is supplied. No routine source-code reread is needed.
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
  "nets":[],"wire_weight":1
}
```

Use dimensions actually extracted from the cited reference; each instance is
explicit. Gap, orientation permissions and bounds come from the task/technology,
not historical defaults. Nets are explicit block connectivity for a center-HPWL
proxy; there is no inferred port routing. Budget: evaluations (1..10000), beam
(1..64), seconds (<=60), seed. CPU time and evaluations are bounded, all trials
are retained. The search combines swap, relocate, row split/merge, rotation and
restart, keeping structural diversity. Proposals remain unqualified proxies.

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
reflect_contract=ai-self-proposal-v1 and allowed_sources=[ai, algorithm]. Existing
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
existing search artifact and explicit `order` (block-index permutation), `cuts`
(row boundaries), `rotations` (per block). The same evaluator checks dimensions
and allowed orientation. Algorithm proposals are created only by actual search.
An idea without a supported plan may be retained but cannot be drawn by Builder.

Builder result: round, task_id, outcome (`passed`/`failed`/`incomplete`), summary,
evidence IDs. Analyst review: round, result_id, verdict (same values), scope,
summary, evidence, checks mapping each required check to passed/failed/incomplete/
not_run. Required checks must all pass before a passed verdict.

Memory batch: round, disposition (`new`/`revised`/`no_new`), entries. See
experience-memory.md for the single bounded record format. Request/response and
stage identities are checked; identical resubmission is idempotent, conflicting
resubmission fails. The entire stage transition commits atomically under a run lock.

## Server execution and evidence

Current runner executes fixed generated Python with argv, explicit cwd, separate
stdout/stderr and a 30-second timeout. It does not invoke an EDA binary or scheduler.
Run copies are versioned inputs; each candidate saves draw.py, helper code, source
geometry, execution details, outputs, logs and object IDs. The experiment registry
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
