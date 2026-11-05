---
name: dcim-self-improve
description: Prepare, execute or resume reference-assisted DCIM self-improvement with bounded Builder and Analyst subagents, bundled initial Python generators and shared experimental experience. Use for DCIM design campaigns, not unrelated layout tasks or frozen-method baseline trials.
---

# DCIM self-improvement

The user controls planning and execution through the main conversation.
No external agent service or model weight update is required.
The package has no dependency on the author's home directory or experiment
tree. In the shell examples, set `SKILL_ROOT` to this installed directory;
scripts resolve their bundled resources from their own location.

## Portable setup and external inputs

Read [sources.md](references/sources.md) for external input contracts and seed
provenance. Start from [dcim.example.json](dcim.example.json); keep a private
`dcim.local.json` outside the published package. All configured relative paths
resolve against the configuration file, not the process working directory.
`--config` takes precedence over the `DCIM_CONFIG` environment variable.

Supply the addresses needed by the selected stage in the private configuration:

| Key | Address / required input |
| --- | --- |
| `work_root` | Writable new-run directory; never a historical experiment root |
| `pdk_root` | Licensed target-node PDK installation; the initial recipes target TSMC 12FFC, not an arbitrary PDK |
| `native_ref_root` | Private target-native PCell GDS/placement metadata and independent SRAM/LRCC/FA CDL; exact filenames in `sources.md` |
| `compiler_ref_root` | Target-node SRAM compiler reference with GDSII and SPICE; check electrical-model availability separately |
| `reference_22nm_root` | Authorized 22nm REF package containing `01_schematic` through `05_restricted_resize_script` |
| `hierarchy_22nm` | Optional full-reference `hierarchy.json` including local decode and parent placements |
| `experience_root` | Optional read-only condensed prior experience and its cited evidence |
| `warm_start_root` | Optional newer Python/evidence tree; not needed for the bundled initial scripts |

PDK, compiler IP, REF layouts/netlists, simulator models, credentials and EDA
binaries are **not distributed** here. Obtain them through the user's authorized
foundry/IP/project channels. No public download address is assumed. Record the
actual user-provided addresses in the private config and task packet; never
hardcode them in reusable source. See `sources.md` for PDK-relative layer-map,
DRC/LVS and model locations. Inspect redistribution rights for technology-specific
recipes before publishing; no project license is selected by this change.

The bundled [initial Python](assets/seed/) contains editable SRAM, LRCC, 22T FA,
geometry/router and independent arithmetic/topology code. It is a starting
implementation, not the latest qualified candidate or a complete macro flow.
Initialize a new run without launching EDA:

```bash
python3 "$SKILL_ROOT/scripts/init_run.py" --config dcim.local.json --name trial01
python3 "$SKILL_ROOT/scripts/check_inputs.py" --config dcim.local.json --scope seed
python3 "$SKILL_ROOT/assets/seed/arithmetic_contract.py"
```

Use Python 3.10+ and the dependencies in [requirements.txt](requirements.txt)
for physical generation. The arithmetic check and run initialization use only
the standard library. Read [seed.md](references/seed.md) before generation.
Use a supplied project constraints document when available; otherwise Planning
must establish the target and acceptance scope. The original campaign used
12nm, eight input/output channels and storage/compute ratio eight (not weight
bitwidth); do not silently impose its area numbers on another project.

Read only the role needed now: [builder.md](references/builder.md) or
[analyst.md](references/analyst.md). Do not load both roles' full evidence.

## Authorization and planning

- Framework setup/review requests do not authorize EDA jobs. Prepare instructions,
  packets and local checks only. An execution/resume request authorizes the
  bounded workflow within the user's stated resource limits.
- Main chat handles Planning: objective, stage, electrical/area comparison scope,
  time budget if supplied, and task assignment. Ordinary failures do not require
  renewed approval. Ask the user only for a genuine unresolved blocker.
- Establish independent circuit/netlist intent and a functional baseline before
  layout. In this DCIM campaign, satisfy the applicable parent height, width,
  alignment and interface constraints first, then minimize actual implemented
  area subject to timing and correctness. Area alone cannot qualify an
  out-of-band shape. W/L and fin counts are implementation variables unless
  explicitly fixed for a scoped experiment; do not freeze conservative
  schematic sizing and make the layout accommodate it. Use legal, model-valid
  compact sizing with sufficient verified drive, not unnecessary margin.
  Detailed OA schematics/native export are optional, not a mandatory gate on
  every iteration. Create them when useful or requested.
  Never report a netlist as an existing schematic view without checking.
- Standard cells may inform topology, density and timing or be reviewed for
  scoped implementation reuse. Compare real parent-routed area and timing,
  not just cell sums/LEF size; do not assume custom logic is always preferred.
  Do not replace the entire DCIM with a different APR macro without checking
  the target interfaces, storage organization and comparison scope.
- At first execution, inspect current source summaries, generator dependencies,
  actual runner commands and live jobs. Do not start by rerunning a macro.
  Area units and comparison boundary must be established before claiming success.

## Initial physical-planning order

Read [layout-order.md](references/layout-order.md) before selecting layout tasks.
Inspect the supplied reference GDS's actual hierarchy and functional placement,
then establish a target-node reference-consistent four-SRAM grouping and measure
its height/pitch and interfaces. The alignment object is the **whole associated
LRCC/multiplication and complete multibit-adder organization against one SRAM
group**, not one FA, one LRCC or an isolated adder. Use that group's available
device height for vertical packing/folding to reduce actual routed width;
a single low device row with high escape/PG wiring does not establish matching.
Do not pad individual primitive bboxes to equal height or stack LRCC and adder
as separately height-budgeted blocks. Measure a connected compute tile, then
shape the decoder beneath its width (half-width only for the matching two-decoder
organization). Retain the agreed four-SRAM grouping; if it is inappropriate,
present measured alternatives to the user before changing that target.

Read [compactness.md](references/compactness.md) at each physical stage's start
and final review. Start from reviewed references and applicable DRC rules with
a rule-compact Python-generated candidate, not an arbitrary loose baseline.
Declare upstream height/width constraints and the dimension being minimized.
Final stage acceptance reports the smallest verified dimensions and actual
tighter trials, with independent physical/electrical status and remaining
search scope. Separate functional device/row distribution from routing/PG and
dummy/termination envelopes; matching the all-mask height alone does not show
useful height utilization. DRC zero or one failed shrink does not prove optimality.

## Visible progress

Use the fixed reporting stages in [stage-progress.md](references/stage-progress.md):
SRAM -> height-constrained multiplication/multibit addition and connected tile
-> local decode -> read/write drivers -> whole-macro integration/qualification.
They are progress landmarks, not fixed iteration counts or a ban on feedback.
Each Analyst decision summarizes the current stage, accepted scope, remaining
gap and next expected observable result, and refreshes the run's `PROGRESS.md`.
Main chat shows that concise stage summary to the user at review boundaries,
not just agent IDs, task numbers or a file link. Keep test status and stage
progress separate; do not invent completion percentages or delivery dates.

## Context lifecycle and dispatch

Use native subagents for bounded implementation and independent analysis.
Discover the tools and fields actually available in the session and explicitly
disable inherited parent history using that API. Do not assume a historical
spawn/wait/close interface exists.

1. Planning writes one task packet using
   [templates/task_packet.md](templates/task_packet.md), or one per independent
   candidate for the parallel low-cost screen described below.
2. Start a fresh Builder for one bounded block-level milestone or decisive
   experiment, not one coordinate edit or individual tool command.
   Pass only: role-reference path, packet path, output path, and critical execution
   restrictions. Use `fork_context=false`; do not paste this conversation.
3. Keep the original Builder active for ordinary debugging within the same
   route and explicit task; tool failures, pin fixes and local regressions do
   not start another agent/Analyst cycle. Builder writes a result packet with proposed experience (or explicit no-new
   assessment), returns a short summary and evidence paths, then finishes.
   Collect its result and close the agent before the next stage.
4. Start a fresh Analyst after an interpretable result, competing measurements,
   or a diagnostic gap. Supply the relevant task/result paths and analyst role
   reference, not the Builder transcript. Analyst independently runs the
   applicable evidence tools against frozen original inputs.
5. Analyst writes its decision, next task(s), the reviewed memory update for
   this round and the stage-progress snapshot, then finishes. Before dispatch, main chat
   checks the admission record in
   [task-admission.md](references/task-admission.md): macro-area account,
   candidate screens, permitted execution tier and unresolved high-value freedoms.
   Also check the memory-update paths/disposition required by
   [experience-memory.md](references/experience-memory.md).
   Missing justification returns to Analyst; a local pass is not dispatch approval.
   Use the installed templates for new packets; old run-local copies do not
   supersede these requirements. Main chat presents the
   concise progress/expectation summary and dispatches the chosen next action.
6. Repeat with fresh agents. Do not resume an old agent to carry an entire
   optimization campaign. During a still-active bounded action, focused
   clarification is allowed; it is not permission to add unrelated actions.

The main chat may directly repair a small, already diagnosed local adapter
defect and execute its focused regression without creating another Analyst
and Builder pair. This does not replace independent review of a new design
strategy, change acceptance criteria, or constitute an isolated reference
trial. Use a fresh role at a meaningful design/evidence boundary; do not
create a new agent and packet for each ordinary script or coordinate error.
When asked to finalize a bounded task, return the current exact result and
owned-job state promptly instead of extending the investigation.

For design work, prefer a deliverable such as one connected, geometry-constrained
arithmetic block with applicable qualification, or one actual parent connection.
The packet states the block boundary, hard H/W constraints versus dimensions
being minimized, allowed sizing/placement/access/routing changes and stop
conditions. Builder owns local engineering iterations inside that contract;
an ordinary access or routing failure need not create another Analyst cycle.
Analyst reviews a meaningful result, exhausted supported route, required
contract change or genuine blocker, then chooses the next block/route. Main
chat assigns and communicates; it does not replace that independent review.

Spawn message pattern (substitute actual paths; this is not an external CLI):

```text
Act as Builder. Read <resolved-skill-root>/references/builder.md.
Read task packet <absolute-task-path>. Write result to <absolute-result-path>.
Follow the packet's write scope and execution permissions. Do not read parent
conversation history or launch additional subagents. Return a short outcome
and artifact paths, not raw tool output.
```

Use the same pattern for Analyst with `analyst.md`. At structural choices,
dispatch the two mechanism-distinct low-cost initial screens concurrently to
two fresh Builders. Give both the same frozen baseline and comparison boundary,
but disjoint candidate, evidence, result and job/OA namespaces. Neither Builder
reads, edits or waits for the other one's outputs; each completes independently.
Collect both results (or an explicit terminal failed/unavailable result), then
give them to Analyst for comparison and continue/switch/both/stop judgment.
Do not leave a finished Builder waiting for its peer. This parallelism is for
bounded cheap screens, not two full macro implementations or blanket parallel
PEX/post. Stay within aggregate resource authorization; record an explicit
serial/single-route exception if resources, tools or genuine input dependencies
prevent independent execution. Do not introduce a barrier between Builders.
There is no separate Planner, Curator, Distiller or reviewer agent.
If fresh-context subagents are unavailable, report the limitation. Offer a new
App conversation with the same explicit packet; do not silently substitute
same-chat role switching and claim context isolation.

For framework setup validation, use a read-only fresh-context Builder followed
by Analyst with fixture packets and separate outputs. This smoke test must not
launch EDA, modify source designs, or claim optimization success.

## Bounded reads

Packets include intent, parent constraints, relevant code/evidence paths,
hypothesis, action and decisive checks. Builder searches the shared experience
itself; there is no retrieval agent or special retrieval engine.
Follow [experience-memory.md](references/experience-memory.md): retrieve by
stage, then node/module/route before topic. Inactive routes are summary-only
for Analyst when relevant and excluded from Builder's default detail reads.

Use scoped `rg -n` and bounded excerpts. Exclude candidate snapshots, dependency
trees and backups from broad searches unless investigating one explicit item.
Keep returned summaries within the packet's text limit. Put full logs on disk.
If necessary evidence becomes too large, write a focused finding and issue a
new packet at the action boundary; do not repeatedly append whole histories.
These are instruction-level context controls, not a sandbox or exact token cap.

## Evidence tool reuse

Before evidence work read the inventory and applicable command contract in
[evidence-tools.md](references/evidence-tools.md). The bundled
`scripts/evidence.py` provides `pv`, `wave`, `gds`, `freeze` and `check`:
DRC/LVS evidence checks, waveform reading, geometry comparison and input
dependency checks. Reuse these tools instead of rewriting mechanical checkers.
Builder freezes the original evidence and relevant dependencies; Analyst runs
the tools itself against that snapshot and records its own outputs. Only
unchanged, fully bound dependencies support inheriting an accepted conclusion.
Tool-change positive/negative regressions run when the tool/readers change,
not as newly authored fixtures every round. New artifacts and changed circuit
semantics still require their affected checks and independent oracles.

## Search and self-improvement

- At structural decisions, default to two mechanism-distinct candidates and
  actual low-cost initial screens before selecting costly implementation.
  A single-route exception needs an evidence-based reason; ordinary diagnosed
  repairs do not require a fabricated competitor. Follow
  [task-admission.md](references/task-admission.md), also for hierarchy advancement.
  Predictions are hypotheses; untested candidates are not ranked. This is
  GEPA-inspired, not a reproduction of GEPA.
- Use cheap discriminating checks before costly simulation. Do not replace
  mandatory final electrical verification with screening results.
- No fixed iteration count. Each route states an expectation and what evidence
  would settle it. Analyst decides continue/switch/stop from the evidence and
  expected value of another test, including elapsed/estimated simulation time.
- Do not require global leaf optimality or invent hard leaf budgets. This does
  not authorize expanding a design with unresolved macro-area risk: distinguish
  a bounded parent observation from full higher-level implementation, and admit
  only the tier justified by the area account and decisive evidence.
- Preserve acceptance criteria. DRC, LVS, area and electrical qualification are
  independent states; DRC zero does not prove compactness or functionality.
- Analyst proposes improvements with evidence, mechanism and a validation plan;
  Builder implements and validates. Design Python, reusable construction code,
  diagnostic tools and optimization policy may improve. No need to label all
  changes "harness". Agent role instructions and interfaces remain fixed;
  they are not an autonomous modification target.
- Validate narrowly first, then use a related case when feasible. Unsuccessful
  changes are discarded; continue with the working version. Never delete
  pre-existing evidence. Keep only a useful failure lesson, not a branch archive.
- Every bounded Builder/Analyst round updates stage-scoped route memory:
  Builder proposes, Analyst reviews and updates, including an explicit no-new
  outcome when appropriate. Follow [experience-memory.md](references/experience-memory.md).
  Construction mechanisms stay under their route; inactive-route repair detail
  is not default context. Human principles, experience, policy and progress stay
  separate. Counterexamples are optional; known contradictions cannot be hidden.

## Workspace ownership

Use the user's selected output root, or `<work_root>/<run>/` from the private
configuration, for new work; see [templates/](templates/) for contracts.
Do not default to writing into the installed skill. Treat source experiments and
recorded method releases as read-only inputs. The installed layout skill may
evolve at an explicit stage checkpoint when authorized by the user: back up
its prior release, record the evidence and scope, and bind later candidates
to the new version. Preserve fixed versions within controlled comparison
groups. Old no-subagent/frozen-method/fixed-leaf-budget rules describe those
old trials, not this new workflow. Do not edit or relabel baseline trials.
Inspect imported paths before copying a generator: `ROOT` relocation alone
does not fix sibling references, generated shared libraries or PDK dependencies.
Read actual EDA skills and runner APIs before operations. Never weaken decks,
independent LVS references, electrical tests or success criteria to pass a run.
