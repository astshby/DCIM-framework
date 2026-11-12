# DCIM framework

## Continuation branch scope, 2026-11-12

This is `coarse_fine`, extending ea525fd's relative fine/coarse/joint hierarchy
and opted-in physical consumer. Preferred new work uses the improve-3-derived
`main`. `coarse` preserves the older coarse runtime and integrated workflow APIs.
`pro` retains its previous checkpoint. Existing runs use their fixed versions.

This branch preserves its original configuration, request/Reflect/Builder/Analyst/
memory transitions and executable hierarchy/physical APIs. It does not provide
main's new initialization schema or coarse's later combined-decision API. The
selected improve-3 lessons guide task granularity, context and evidence reuse
within those contracts. No executable code or test changes are introduced here.

The captured complete8x4 physical coarse round closed with failed physical
qualification due to OD density. Fine and return-coarse physical rounds were
not executed. The physical consumer's identity/pose checks do not establish raw
mask/body/electrical truth or complete fine/coarse qualification. No further
physical run or PPA benefit is claimed by this guidance update.

Read `dcim-self-improve/references/improve3-guidance.md` and `references/two-scale.md`
for applicable lessons, actual consumers and remaining limits. No old pinned
run, experimental state or source evidence is changed by branch continuation.

# DCIM Framework

This repository implements a process-neutral DCIM learning and construction loop.
It combines improve 1's generic configuration/history/geometry with improve 2's
evidence checking and route-memory principles. The old 12FFC seed is retained in
Git history and is absent from the active package.

Read AGENTS.md at entry; HANDOFF.md is the user/developer optimization record,
not a runtime input. The reusable skill is
`dcim-self-improve/SKILL.md`; its `references/runtime.md` describes executable
commands and payloads. No PDK, compiler IP, models or EDA binaries are distributed.

## Initialize

Agents generate private configuration outside this repository. Existing
project/input_files configurations are supported:

```sh
python3 dcim-self-improve/scripts/configure.py --output ../dcim.v2.local.json --from-config ../dcim.local.json --init study01
```

Use the resulting run's copied `scripts/` for subsequent calls. Initialization
pins programs, geometry helpers and instructions, creates a resumable state and
refuses overwriting existing runs. Relative paths resolve against configuration.
Core code runs with Python 3.8+; newer interpreters can be selected explicitly.
Optional GDS import/export requires gdspy; geometry JSON/SVG needs no external
package. The private configuration remains agent-managed.

## Implemented loop

Reflect0 imports compiler and digital-flow layouts with `learn.py`, extracts
geometry/hierarchy observations and specifies the next construction. Inside Reflect,
`planner.py` runs simulated annealing, local improvement, sampled large-neighborhood
rearrangement, coordinate beam search or adaptive destroy/repair search. Every later search starts at actual output
from the immediately preceding reviewed round, preserving its coordinates. All four role guides stay under `dcim-self-improve/references/`: initialize.md,
reflect.md, builder.md and analyst.md. `roles.py` centralizes their loading. AI self-reflection and actual algorithm outputs share route records. Every
Reflect, including closure, must submit one new testable AI proposal with a
difference from existing routes. Human proposals/feedback are not Reflect inputs.

`workflow.py` enforces Reflect -> Builder -> Analyst -> committed short memory ->
Reflect, including failed and final rounds. It persists real AI requests/replies;
it does not supply a canned AI answer. `context --since TOKEN` returns only changed
sections. `memory.py` provides bounded same-format reads/writes and supersession.
`builder.py` creates and executes a new drawing Python script, retaining actual
inputs, helper code, hierarchical geometry JSON, SVG, optional explicit-precision GDS, stdout/stderr and evidence.
It recovers a `placement_state.json` from actual generated instance geometry; the
next search verifies that state against retained layout evidence. Multiple Builder
candidates require an explicit primary baseline; missing output cannot silently
fall back to an older round.
Reflect0 creates bounded learning goals linked to captured references and required
checks. Builder retains exact goals in learning_contract.json; Analyst reports
per-goal conclusions with current evidence. Context keeps active goals and latest
outcomes available beyond recent-memory limits. Corrections supersede old versions;
process-bound conclusions do not automatically apply to another node or run.
experience.py publishes reviewed methods and their evidence as immutable private
bundles; explicitly configured receiving runs pin and retrieve applicable methods
as reference-only hypotheses, preserving source status and revalidation needs.
The original evidence checker and compatible history helper remain available.

New runs can be copied or renamed as complete trees: request recovery uses
hash-verified run-owned objects and experience retrieval uses pinned bundles.
Original paths remain provenance metadata. For standalone evidence trees,
`evidence.py freeze --base-root /absolute/tree --out /absolute/tree/frozen.json FILE...`
writes a portable v2 manifest; omit the flag for legacy v1. See
`references/evidence-tools.md` for dependency and historical-report requirements.
Existing runs keep their pinned versions; this update does not migrate them or
make external EDA paths portable automatically.

The research target is eight input/output channels and storage/compute ratio eight.
Its accounting, precision, process and electrical conditions must be explicit.
No fixed SRAM grouping, bitcell, topology, node or decoder proportion is inherited.

## Repository and execution structure

- `scripts/planner.py`: stable Reflect entry, baseline provenance, budgets and persistence.
- `scripts/search/model.py`: coordinate state, constraints and common proxy objective.
- `scripts/search/operators.py`: reusable placement modifications.
- `scripts/search/algorithms.py`: strategy registry and bounded exploration.
- `scripts/search/baseline.py`: recover and verify actual previous-round placements.
- `scripts/search/adaptive.py`: ALNS-inspired operator selection and bounded repair.
- `scripts/roles.py`: one registry for existing role references and initialization context.
- `scripts/learning_contract.py`: persistent goals, task/check binding and outcome retrieval.
- `references/{initialize,reflect,builder,analyst}.md`: role functions and reusable experience.
- `references/sources.md`: method provenance and external-library research status.

These paths are relative to `dcim-self-improve/`. Programs and guidance are pinned
at initialization; ordinary calls use those copies and context deltas. Search caches
identical states, and identical calls return retained results. Per-call limits and
aggregate Reflect limits bound CPU exploration. Raw traces stay in immutable
artifacts; default context contains summaries. The unused duplicate `run/design`
helper tree has been removed. No EDA is launched by these entry points.

## Scope and validation

Current search optimizes geometry and center-HPWL proxies. It does not synthesize
transistor topology, route inter-block nets, establish electrical performance or
submit EDA jobs. AI explicit plans can be evaluated in the same geometry
representation. New operations use the shared state/evaluator interface and are
implemented and checked within the existing role loop. No new planning stage is
introduced. External standard-cell engines and routing adapters remain unsupported.
The adaptive search references [N-Wouda/ALNS](https://github.com/N-Wouda/ALNS)
concepts through a local standard-library implementation. No external algorithm
library is installed or vendored. It records six destroy/repair pair weights and
charges all evaluated repair states to the common budget; it is not guaranteed
to beat other strategies. See references/sources.md for comparisons and provenance.
Protocol gates cover the fixed entry points, not arbitrary shell actions.

```sh
python3 -B -m unittest discover -s dcim-self-improve/tests -v
python3 -B -m unittest discover -s tests -v
```

Tests use synthetic geometry/evidence. Optional GDS/PSF cases report skips when
inputs or dependencies are unavailable. They do not qualify a physical design.

## Delivery

At each completed framework iteration, update HANDOFF.md, run relevant checks,
commit locally and run `python3 scripts/package_workspace.py`. This atomically
replaces the sibling `dcim-framework.zip`. Git retains revisions; one ZIP holds
the current framework. Private configuration, experiments, caches and proprietary
inputs remain outside Git/package. Preserve existing reference directories and
experimental history in the enclosing workspace.

## License

Framework code and documentation are [MIT licensed](LICENSE). External PDK, compiler,
standard-cell IP, EDA tools and private experiment artifacts are not covered or distributed.

## Device-granularity search and campaign planning

New runs use schema 5 and the reflect-multiscale-v5 contract. `planner.py` also accepts
`transistor-placement-v1`: named-device row permutations, explicitly allowed
source/drain flips, declared sharing predicates and nominal terminal HPWL.
Builder produces a replayable abstract device layout; `device_audit.py` provides
an independent checker. This is not foundry mask generation or physical signoff.

`campaign.py` records the full module/tile/repeat/macro plan, fixed parent versions
and stage acceptance. It admits only reviewed, memory-committed, Reflect-closed
runs; unavailable physical/routing stages remain explicitly blocked. Existing
pinned runs remain unchanged. See `dcim-self-improve/references/transistor-planning.md`
for schemas, commands, qualification boundaries and the implementation roadmap.

## Two-scale constraints and upstream solver portfolio

See dcim-self-improve/references/two-scale.md. Five SciPy implementations can
operate through shared fine/coarse decoders and hard checks; optional EDA engines
are catalogued separately with their actual unavailable state. Native repeat
relations are evidence-bound and distinct from retained full-mask dimensions.
Private physical Builder recipes are captured at runtime, never distributed with
PDK/IP or node-specific assumptions. New requests use reflect-multiscale-v5.

## Source-bound physical actions

Private adapters can opt into physical-action-guard-v1 to bind parent GDS/CDL/DEF,
exact actions, fixed affected/frozen conditions, raw observations, consumed copies
and final output witnesses. Unknown affected conditions block prepare; unrelated
frozen unknowns remain explicit. See references/two-scale.md and runtime.md under
dcim-self-improve/. This validates declared execution identity and coverage. It
does not infer impact domains, prove physical rules, provide mask reconstruction
or grant EDA permission. Existing pinned runs and legacy adapters are unchanged.
