---
name: dcim-self-improve
description: Plan, initialize and execute reference-assisted DCIM improvement with bounded Builder tasks, scoped experience and integrated Analyst review and reflection.
---

# DCIM self-improvement

Main owns initial planning and architectural admission. Builder implements one
bounded connected block or decisive experiment. Analyst reviews the actual
result, updates scoped experience, records an actual concise reflection and
proposes the next executable task or closure. Main checks that decision against
the authorized architecture, MUST constraints and execution scope.

## Initial planning and executable setup

Use [sources.md](references/sources.md) and [initialize.md](references/initialize.md).
The private configuration declares the target node/profile, work root, reference
roles and stage-required file sets. Relative addresses resolve against that
configuration. `--config` overrides `DCIM_CONFIG`. There is no default PDK,
compiler, layer map, generator, model, device grouping or execution host.

Main performs one initial-planning step. Establish objective, stage, electrical
conditions, independent circuit intent, parent H/W/function/interface constraints,
reference applicability, permissions and first bounded task. Select experience
and resources using the actual supplied material. Missing optional references
remain explicit gaps. A fresh design can start with an empty `design/` directory.
A declared private recipe may supply editable initial Python and its dependencies.

```sh
python3 "$SKILL_ROOT/scripts/check_inputs.py" --config private.json --stage planning
python3 "$SKILL_ROOT/scripts/init_run.py" --config private.json --name trial01 --stage planning
python3 "$RUN/framework/scripts/check_inputs.py" --run "$RUN"
```

Initialization pins scripts, SKILL, references, templates, initial configuration,
initial design code and hashes of the stage's declared reference files. It
executes no generator or EDA. File availability and identity establish setup
readiness. Functional, electrical and physical legality require their own checks.
Comparison baselines and controlled campaign protocols belong to tasks that
request them. They are unnecessary for ordinary fresh initialization.

Main writes an actual task, selection and catalog using the documented dispatch
schema. An empty catalog is valid when there is no applicable experience.
`context_dispatch.py prepare` materializes that AI selection. Builder runs `open`
and reads the emitted task/context before editing. See [experience-memory.md](references/experience-memory.md).

## Bounded roles

Read the assigned [Builder](references/builder.md) or [Analyst](references/analyst.md)
reference. Main chooses an available model according to task uncertainty and the
user's preference and records its actual ID and reason. A new substantive task
uses a fresh context where the agent API supports it. Within the same active
task, ordinary device, contact, pin, routing and rule repairs stay with Builder.
Record the actual native API's isolation setting and returned agent ID.
Scripts assemble context and record identity. They do not invoke native agents.

Builder returns the actual candidate, code/dependency versions, scoped checks,
failed trials, terminal or explicitly transferred jobs and experience proposal.
A structural/interface/constraint change returns to Analyst and Main. Analyst
uses completed artifact-bound results for decisions and requests a targeted
check when missing or contradictory evidence can alter the decision. Full
independent replay is available when the user requests an audit.

Every reviewed result, including failure, strategy reuse and closure, includes
experience disposition and an actual concise reflection. The Analyst output
states what changed in the diagnosis, what mechanism is retained or revised,
why the next bounded action follows and what observation will settle it.
A diagnosed ordinary repair can reuse its mechanism. A separate Reflect agent
or a newly invented route on every repair is unnecessary.

## Physical intent and admission

Read [layout-order.md](references/layout-order.md), [compactness.md](references/compactness.md)
and [task-admission.md](references/task-admission.md) for applicable physical work.
Bind actual source/top/circuit roles and reference observations. Group counts,
channel/operand widths, decoder organization and numeric dimensions come from
the task and private configuration/recipes. Cross-node evidence can inform
organization hypotheses. Target-node rules and device models must be established.

Physical tasks carry an inline architecture contract with parent dimensions,
functional row origins/heights/phases, actual hierarchy/order/transforms,
straight continuous intended PP/NP bands, TAP/body/termination ownership and
signal/PG access. Bind authoritative sources as required resources. Main resolves
conflicting proposed coordinates before construction. Report unknown diagnostic
conditions explicitly. Qualification requires their applicable checks.

At intended PP/NP interfaces require direct abutment without artificial gaps or
overlap. Remove redundant standalone TAP/context only when actual legal powered
same-body access survives. Recheck the final joined artifact, including rule
domain, repeats, boundaries, functional row alignment and parent-routed access.
DRC zero, equal all-mask height and one shared boundary each establish a limited
observation. Preserve independent source LVS, function, ERC and electrical gates
where the task requires them. Never scale masks, borrow marker exemptions or
weaken a foundry deck to produce a pass.

Measure the complete connected routed/PG/context envelope against hard W/H
and interface constraints before claiming area improvement. Retain meaningful
compact trials and failures, with their verification scope. A macro-area account
separates measured implementation, projections, sharing hypotheses and unknowns.
Use bounded parent observations when full expansion is unsupported. Structural
alternatives are AI-selected when they can resolve a real uncertainty. Ordinary
repair has no mandatory paired-candidate or parallel-agent gate.

## Evidence, memory and recovery

Use [evidence-tools.md](references/evidence-tools.md) for existing `pv`, `wave`,
`gds`, `freeze` and `check` readers. Freeze original artifacts, declared executed
inputs, specs, independent source and relevant dependencies. Reuse unchanged,
fully bound conclusions within their original scope. Tool/reader changes receive
focused positive/negative regression. Changed circuit or sizing receives its
affected functional/electrical checks.

Keep experience under stage, node/rule domain, module and route. Analyst selects
relevant entries, marks applicability and maintains active/deferred/superseded
summaries with source evidence. Preserve failed observations and uncertain causes.
Bytes/hashes establish identity. They cannot establish execution, comprehension,
raw observation truth, functional legality or foundry qualification.

Use a run's pinned programs/instructions. Before recovery inspect current state,
concise handoff and owned jobs. Reconcile uncertain submissions before retry.
Preserve prior evidence and append decisions, experiences, actual reflection,
parameter/code versions, prompts and timing at meaningful task boundaries.
The small main package has no scheduler, physical-action engine or automatic
acceptance state machine. EDA execution uses the authorized private runner.
Developer HANDOFF is outside normal design-role context.

## Scope and authorization

Framework setup and software checks authorize no EDA. Execution follows the
user's selected tasks/resources. Keep private PDK/compiler, models, recipes,
credentials and experimental data outside public Git and ZIP. Write new results
inside the private run. Preserve historical runs and immutable releases.
No task should auto-upgrade an old run or inherit its node-specific pass.
