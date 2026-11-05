# Stage progress and expectations

Use these stable milestones for the current DCIM flow. Independent circuit/
netlist intent and function precede the respective layout work; detailed OA
schematic drawing is optional. Meet parent H/W/alignment/interface constraints
before minimizing actual area subject to timing/correctness. W/L/fin counts
are not automatically frozen by historical schematics.

| Stage | Visible milestone and dependency |
| --- | --- |
| 1. SRAM | Review reference/reuse, qualify the scoped four-subcolumn grouping, and measure actual height, repeat/context ownership and pin access. |
| 2. Multiplication and multibit addition | Align the whole associated LRCC/multiply plus complete adder organization to one four-SRAM group-height band; use functional height to compress width, then measure a connected SRAM-compute tile. |
| 3. Local decode | Fit the matching decoder organization beneath the measured tile width, with real outputs, loads and parent routing. Half-width applies only to the matching two-decoder organization. |
| 4. Read/write drivers | Complete the required read/write drivers and peripheral interfaces against actual loading, access and control timing; include their area and supply routing. |
| 5. Whole macro | Integrate K/C/S hierarchy and required periphery; separately qualify function, DRC, independent LVS, full routed/PG envelope and required electrical/PVT scope. |

Stages are an overview, not a ban on early load planning or later feedback.
Arithmetic can have several bounded substeps without pretending each is a
new overall phase. Single-primitive height or an isolated adder's tall
route/PG bbox does not qualify combined group-height utilization.
A single connected adder does not complete stage 2;
an ideal product source does not establish SRAM-to-LRCC functionality.
Real boundary/access/electrical evidence can reopen an accepted earlier stage.

## Snapshot

After each Analyst review, refresh `<run>/PROGRESS.md` using
[the template](../templates/progress.md). Keep one current Markdown snapshot,
not a new status database, log archive, dashboard service or extra agent.
Include all five stages, the current action, the review/task identifiers and
short evidence references. Preserve detailed evidence at its original path.
Use the user's language in the snapshot and returned summary.
Keep table cells to short phrases; link to detailed conditions and verification
reports instead of repeating them. The snapshot is a scan-friendly overview.

Use clear stage states such as `not_started`, `in_progress`, `awaiting_review`,
`accepted_for_scope` and `reopened`; translate them for the user when useful.
An accepted stage names its scope and open parent/PVT conditions. A pending
task is not running. Preserve the separate check states (`not_run`,
`incomplete`, `failed`, `passed`, `not_applicable`) from the underlying evidence.
Never average these states into a completion percentage.

For each stage say what is already established, what is missing and the next
observable milestone. For the active stage state:

- Change since the last review, or explicitly no stage advancement.
- Next bounded action and the expected artifact/measurement if it works.
- State the assigned block/hierarchy and local implementation freedom, so the
  user can distinguish a block delivery from a narrow diagnostic. Identify
  which result was independently reviewed by Analyst.
- Decisive check and the main uncertainty or failure-triggered return path.
- Cost expectation only when supported by relevant measurements; otherwise
  unknown. A local simulation time is not a whole-stage delivery estimate.

At final physical-stage review, include the smallest verified W/H/area with
scope, actual tighter-trial outcomes and the stop/compose rationale from
[compactness.md](compactness.md). Keep detailed candidate rows in the decision
or evidence and only the concise measured conclusion in the progress snapshot.

Lead the Analyst decision and returned summary with current stage, accepted
scope and next expectation. Main chat presents the compact table or equivalent
stage summary at meaningful review boundaries. During Builder execution it
can report the active action while preserving the last accepted evidence.
Do not rewrite historical decisions, re-execute EDA just to refresh progress,
or turn a reporting-only task into design advancement.
