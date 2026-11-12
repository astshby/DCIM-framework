# Stage progress

Main declares stages for the actual task. A DCIM campaign may use storage,
connected multiplication/arithmetic, control/decode, peripheral completion and
whole-macro qualification as landmarks. Smaller initial circuit tasks can use
fewer milestones. These are planning landmarks and permit feedback.

After meaningful decisions Analyst refreshes `PROGRESS.md` from the template.
State the current task, accepted scope, actual change or unchanged progress,
remaining gap and next observable result. Keep evidence at its original path.
A prepared task is pending until actually dispatched. Geometric, DRC, source
LVS, ERC, functional, electrical and parent-integration checks have separate
states. Accepted stages retain their scope and open conditions.

Use states such as `not_started`, `in_progress`, `awaiting_review`,
`accepted_for_scope` and `reopened`. Include bounded expected action, decisive
check, return condition and supported cost estimate or unknown. Do not infer
completion percentages or whole-stage timing from a local test.
