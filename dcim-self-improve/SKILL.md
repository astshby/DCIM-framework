---
name: dcim-self-improve
description: Prepare, execute or resume reference-assisted DCIM self-improvement with bounded Reflect, Builder and Analyst roles, reusable Python tools and shared experimental experience. Use for DCIM design campaigns, not unrelated layout tasks or frozen-method baseline trials.
---

# DCIM self-improvement

This is the general experience guide maintained from improve 2. Framework order,
role dispatch and program entry points belong to [AGENTS.md](../AGENTS.md).
Stage/route knowledge remains separately maintained in the memory records.

The user controls planning and execution through the main conversation.
No external agent service or model weight update is required.
The package has no dependency on the author's home directory or experiment
tree. In the shell examples, set `SKILL_ROOT` to this installed directory;
scripts resolve their bundled resources from their own location.

## Portable setup and external inputs

Read [sources.md](references/sources.md) for external input contracts and tool
provenance. Start from [dcim.example.json](dcim.example.json); keep a private
`dcim.local.json` outside the published package. All configured relative paths
resolve against the configuration file, not the process working directory.
`--config` takes precedence over the `DCIM_CONFIG` environment variable.

Supply the addresses needed by the selected stage in the private configuration:

| Key | Address / required input |
| --- | --- |
| `work_root` | Writable new-run directory; never a historical experiment root |
| `pdk_root` | Licensed target-node PDK installation with declared release, stack and models |
| `circuit_ref_root` | Independent circuit/netlist and target-native layout references |
| `compiler_ref_root` | Target-node SRAM compiler reference with GDSII and SPICE; check electrical-model availability separately |
| `digital_flow_root` | Target-process digital-flow layouts and their circuit/constraint evidence |
| `experience_root` | Optional read-only condensed prior experience and its cited evidence |

PDK, compiler IP, REF layouts/netlists, simulator models, credentials and EDA
binaries are **not distributed** here. Obtain them through the user's authorized
foundry/IP/project channels. No public download address is assumed. Record the
actual user-provided addresses in the private config and task packet; never
hardcode them in reusable source. See `sources.md` for PDK-relative layer-map,
DRC/LVS and model locations. Inspect redistribution rights for technology-specific
recipes before publishing; no project license is selected by this change.

The bundled [Python tools](assets/tools/) support geometry inspection, drawing
and explicit construction inputs. They are not a qualified circuit or macro flow.
Initialize through the framework's stable entry points; see
[runtime.md](references/runtime.md) for commands and dependency requirements.
Use a supplied project constraints document when available; otherwise Planning
must establish the target and acceptance scope. This project's eight input/output
channels and storage/compute ratio eight are explicit requirements, not weight
bitwidth or a universal reference design. Do not transfer historical area numbers.

Read only the role needed now: [reflect.md](references/reflect.md), [builder.md](references/builder.md) or
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
then establish a target-node reference-consistent SRAM grouping and measure
its height/pitch and interfaces. The alignment object is the **whole associated
multiplication and complete multibit-adder organization against one SRAM
group**, not one FA, one multiplier or an isolated adder. Use that group's available
device height for vertical packing/folding to reduce actual routed width;
a single low device row with high escape/PG wiring does not establish matching.
Do not pad individual primitive bboxes to equal height or stack multiplication and adder
as separately height-budgeted blocks. Measure a connected compute tile, then
shape the decoder beneath its width (half-width only for the matching two-decoder
organization). Derive the grouping from the declared task and actual reference;
Reflect compares measured alternatives if that grouping is inappropriate.

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

Use the reporting stages in [stage-progress.md](references/stage-progress.md):
SRAM -> height-constrained multiplication/multibit addition and connected tile
-> local decode -> read/write drivers -> whole-macro integration/qualification.
They are progress landmarks, not fixed iteration counts or a ban on feedback.
Each Analyst decision summarizes the current stage, accepted scope, remaining
gap and next expected observable result, and updates the program's stage record.
Main chat shows that concise stage summary to the user at review boundaries,
not just agent IDs, task numbers or a file link. Keep test status and stage
progress separate; do not invent completion percentages or delivery dates.

## Task granularity and independent work

Framework dispatch follows [AGENTS.md](../AGENTS.md). Keep these engineering
practices when deciding the scope of work and interpreting results.

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
contract change or genuine blocker. Reflect then chooses the next block/route.
Main chat communicates; it does not replace independent evidence review.

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
  would settle it. Reflect decides continue/switch/stop from the reviewed evidence and
  expected value of another test, including elapsed/estimated simulation time.
- Do not require global leaf optimality or invent hard leaf budgets. This does
  not authorize expanding a design with unresolved macro-area risk: distinguish
  a bounded parent observation from full higher-level implementation, and admit
  only the tier justified by the area account and decisive evidence.
- Preserve acceptance criteria. DRC, LVS, area and electrical qualification are
  independent states; DRC zero does not prove compactness or functionality.
- Reflect must originate one testable AI idea every round, including Reflect0,
  unchanged strategy and final closure. Explain its difference from existing
  routes and give a minimal discriminating test. A new diagnosis, measurement or
  controlled experiment can qualify; merely repeating the algorithm winner cannot.
  Compare it with actual heuristic proposals; no human proposal/feedback channel
  enters Reflect. Analyst supplies independent evidence, and Builder implements
  the selected task. Design Python, reusable construction code,
  diagnostic tools and optimization policy may improve. No need to label all
  changes "harness". Version instruction/interface improvements with evidence,
  preserve their previous text and validate before use.
- Validate narrowly first, then use a related case when feasible. Unsuccessful
  changes are not promoted; continue with the working version. Preserve failed
  circuits, generated layouts, executed code and evidence. Keep the default
  retrieved lesson short while retaining the complete branch archive.
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
