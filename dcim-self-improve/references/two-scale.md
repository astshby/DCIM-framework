# Two scales, one reviewed construction loop

Reflect chooses fine, coarse or joint scope from the current bottleneck. Return a
short decision naming the editable region, actions, frozen conditions, algorithm,
budget and decisive check. Fine includes devices, rows, seams, supply/access and
local endpoints. Coarse includes reusable blocks and their connections. These are
relative scopes, not four mandatory stages. Complete the declared SRAM/DCIM module
under its fixed contract first, then optimize. Small tests are Builder diagnostics,
not a substitute for the requested complete-module deliverable. Analyst owns both
independent review and concise experience submission; then Reflect acts, including
failure and closure.

## Enforced placement relations

The block schema rejects unknown fields. width_strict/height_strict reject equality.
An optional block-physical-contract-v1 separates retained full-mask dimensions from
placement boundaries, alignments, track pitch/offset, permitted regions and exact
native repetitions. The full mask envelope always remains in area measurement.
A native repeat cannot be inferred from a bounding box or made legal by zero gap.
A pair spacing exception requires exact source/transform/boundary and immutable
seam report/dependency bindings at search, AI-plan, Builder and recovery boundaries.
The report must state seam geometry, source connectivity and body-supply checks;
the framework verifies its identity, not its scientific truth. Independent Analyst
still checks original reports and actual polygons. An incomplete pair cannot be
passed merely to enable packing. Frozen contracts persist across normal rounds.

## Existing solvers

Read algorithm-portfolio.md for five runnable upstream SciPy methods and optional
EDA implementations with explicit unavailable status. Solver choice is subordinate
to supported actions, decoder and evaluator. Never label a library method as a
reproduction of a paper's complete flow. Mixed or fine/coarse actions may be
combined in one Reflect; there is no mandatory pair of expensive searches.

## Private physical Builder

physical_builder.py binds a task's physical_adapter evidence artifact to a
private-physical-adapter-v1 contract. It freezes code/input dependencies before
prepare, invokes explicit argv actions, journals submit before execution, refuses
duplicate submit, and requires terminal APR/DRC/LVS/function collection before
freezing actual GDS/CDL/DEF and reports. Every task retains complete-module checks.
Node-specific recipes, paths, PDK/IP, source netlists and lessons belong in the
experiment copy only; upstream supplies orchestration, not a fabrication recipe.

A physical adapter task currently binds a captured reference geometry plan. Its
private recipe must state which plan parameters it consumes. A full-module replay
is a construction/evidence test, not an optimization claim. It does not yet support
automatic physical fine/coarse rebuilding and return to the generic search state;
new structure requires explicitly linked construction work. Do not pretend that
a searched rectangle state automatically controlled APR.

## Transferable lessons

- Keep native repetition, all-mask envelope and pin-access extent separate.
- Diagnose a new assembly's actual short/open path; a past failure coordinate is
  not the cause of every later failure. Preserve native body ties unless removal
  is supported by the new connectivity evidence.
- Scope LVS/ERC and function separately; a behavioral test is not analog memory
  margin or genuine-device verification.
- Freeze source intent and all recipe dependencies before execution. Wrapper port
  order matters; changing it creates a new source revision rather than rewriting
  the prior launch record.
- Preserve per-net regressions even when aggregate area/HPWL improves.
- Unsupported checks remain incomplete, and rejected candidates remain available
  for diagnosis. None of these methods transfers process-specific dimensions,
  rule exceptions or qualification passes.

When most sampled coarse states violate constraints, inspect the decoder/action domain before increasing evaluations. A finite local endpoint optimum is not a global or routed optimum. Preserve no-improvement results and separate solver/domain tests from a physical design round.

## Captured construction plans and declared verification stages

A private physical adapter may declare required_stages explicitly instead of the
legacy APR/DRC/LVS/function sequence. The complete task and independently scoped
checks remain mandatory. A local postroute materializer is named honestly; inherited
DEF placement is provenance and is not a fresh APR result. Unknown stages reject.

construction_plan binds the task to an immutable evidence artifact. The Builder
copies it to construction-plan.json and verifies the actual consumed file bytes
before every action, including finalization. {PLAN} passes that copy to the private
generator. Finalization requires a construction_witness whose plan hash matches
the captured artifact and whose output hash matches the generated GDS. This binds
execution identity; the private materializer and independent Analyst must still
check the actual allowed changes, preserved circuit and fresh physical reports.

Private stage launch manifests must bind immutable construction inputs and the current stage's rule/input files. Keep incrementally updated result indexes and prior stages' outputs separate from launch dependencies. Validate the captured input identities immediately before launching the tool, retain job ownership and terminal evidence, and report any historical dependency drift without rewriting old manifests. A software-only repair of this bookkeeping does not retroactively validate a previous run.

## Source-bound physical action admission

A new private adapter may opt into action_guard (physical-action-guard-v1). The
captured adapter fixes the exact parent GDS/CDL/DEF artifact hashes, each action's
operation/object/parameters, affected condition names, and explicitly frozen
unaffected condition names. A proposal cannot remove a required condition, change
the target, or demote an affected condition to frozen. The construction plan must
carry exactly those actions and checks. An affected unknown or failed check blocks
execution before prepare; an unaffected frozen unknown stays visible.

Each check binds the same action and baseline to an immutable check record, plus a
separately captured raw JSON observation selected by a JSON pointer. A bare pass
boolean or free-form report sentence is not a structured observation. Hash and
reference validation establishes identity, not the physical truth of that record.
The private checker and independent Analyst must examine source endpoints, actual
conductors, rule applicability and the completeness of the declared affected set.
The adapter declares that set; this capability does not infer it from masks.

The physical Builder revalidates original artifacts at every prepare, submit,
collect and finalize entry. It copies the admitted parent GDS/CDL/DEF and admission
record into the candidate, checks their bytes along with the plan/adapter/dependency
copies on later entries, and passes standalone {PLAN}, {ADMISSION}, {PARENT_GDS},
{PARENT_CDL}, {PARENT_DEF} argv tokens to prepare. Finalization requires a witness
covering the plan/admission and all three actual output hashes. The recipe's code
and its claimed consumption still require independent review.

This opt-in preserves legacy adapters and pinned runs. It does not supply a mask
materializer, source synthesis, an APR action decoder, scheduler permission,
routing or qualification. Selecting an existing pin point is a read-only geometry
choice until the parent routing contract is checked. New mask edits require the
implemented reconstruction and the complete module's required physical checks.

## Executable hierarchy v1 (software geometry backend)

hierarchy.py separates a complete goal (sram/dcim) from a scope (fine/coarse/joint).
Nodes retain stable IDs. Leaf source/cell/dimensions and explicit net/pin anchors
are fixed. Group ports map to immediate child ports; local translations flatten
recursively into the existing block placement state. The frontier partitions all
leaves. refine/compose change this view only; translate moves a leaf or every leaf
of a group. Ancestor/descendant overlapping moves in one decision reject; refine
then move then compose is an explicit ordered action list. Rotation, topology
change, device mask synthesis and physical_adapter dispatch are unsupported.

Every tree contains must obligations and claims with owners, dependencies, checks,
status and evidence. Scope changes preserve their immutable definitions. Actual
movement stales dependent evidence and ancestor interfaces, conservatively including
routing/physical checks when their influence is unknown. Pure view changes preserve
evidence. These are revalidation requirements, not automatic proof of compliance.
All inherited MUST checks enter the Builder task and independent review.

planner.bind_initial captures a round0 reference search once. Capture the initial
hierarchical-placement-v1 JSON as ordinary evidence, then call planner.plan with
scope_decision and hierarchy_artifact (or CLI options). Later decisions must bind
the immediately preceding reviewed candidate's hierarchy_state.json, reconstructed
against layout.json by the baseline reader. The existing identity/physical guards
remain. Scope planning creates a measured AI route; Reflect still originates its
own new proposal and commits the task in the ordinary role sequence.

New campaigns default to dcim-campaign-v2: SRAM goal -> integrated DCIM goal.
Compute role descriptions do not become mandatory standalone macro prerequisites.
Each goal keeps stage=module; relative scope changes do not alter memory retrieval.
Version1 plans remain readable and can be explicitly created with --schema-version 1.
The campaign is an acceptance ledger; physical capability remains unavailable
until a supported physical hierarchy decoder is implemented and tested.

Software geometry roundtrips test execution/identity/invalidation only.
Physical roundtrips require a supported physical decoder and separately scoped
independent validation.


Analyst may submit hierarchy_checks keyed by retained obligation/claim ID, each
with status passed/failed/incomplete and current-round evidence IDs also reviewed.
Passed records require every corresponding task check to pass. The immutable
candidate remains unchanged; next scope planning applies the immediately previous
review as an explicit evidence overlay. Stale records without reviewed replacement
stay stale. No old pass is silently revived. Scope algorithm must be
explicit_actions; other names reject instead of claiming an unexecuted optimizer.


The hierarchy geometry backend may pass only geometry, hierarchy_identity,
interface (declared endpoint mapping), pin_anchor_mapping, leaf_identity,
constraint_inheritance, scope_consumption, evidence_invalidation and
relative_transforms. It rejects passed status for DRC/source LVS/ERC, body/TAP,
physical pin access, real implant seams, routed dimensions or electrical/function
verification. Such checks remain incomplete/not_run/failed as evidence warrants.
This restriction covers the whole hierarchy review and its record overlays;
legacy execution modes retain their existing review contracts.


Changed leaf net incidence expands invalidation to remote endpoints and their
ancestors. Custom/unknown check semantics conservatively stale on any pose change;
only geometry, leaf_identity, relative_transforms and pin_anchor_mapping use
bounded declared local dependencies. Group-port aliases to an identical immediate
child terminal reject; distinct terminal names on the same net remain distinct.
