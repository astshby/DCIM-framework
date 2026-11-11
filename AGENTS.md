# DCIM framework instructions

## Entry and scope

This directory is the active framework repository. Start with this file; use
`README.md` for setup commands. Framework developers also read `HANDOFF.md` as the
user/developer optimization record; design roles do not load that history. The reusable skill remains in
`dcim-self-improve/`. Read its `SKILL.md` and only the references needed for the
current task. The handoff records accepted changes and their implementation
status; planned features must not be reported as working features.

The repository was imported from the user's `dcim-self-improve-2` reference.
Sibling `dcim-self-improve*` and future `improve-n` directories are references.
Make framework changes here and record their provenance rather than editing or
automatically synchronizing those reference directories.

## Framework development

Upgrade the framework using evidence from both improve 1 and improve 2. Reuse
general helpers; remove process-specific defaults from the active execution path.
Keep accepted runtime contracts in this file and the references, and record
implementation changes/evidence in `HANDOFF.md`. Current runtime contracts override
inherited campaign instructions, including discarding rejected design branches.
Do not silently apply the inherited 12FFC recipes or four-SRAM grouping to a
different process or project.

Reflect0 learns from compiler and digital-flow layouts and assigns specific
learning-backed construction. Reflect has exactly two method sources: AI
self-reflection and actual bounded heuristic search. The required loop is
initialization, initial Reflect, Builder, Analyst,
committed concise action/experience memory, then Reflect and the next Builder.
Reflect and a concise reflection record are required every reviewed round,
including failure, unchanged strategy and final closure. Each Reflect must
originate one concrete AI proposal with a difference from existing routes and a
minimal discriminating test. Selecting an algorithm winner alone is insufficient.
No human feedback or human route enters Reflect. AI selects the method; programs enforce ordering and execute
bounded searches. A fixed next-task response is not an AI Reflect implementation.

Use stage-scoped route memory with structured action, experience and reflection
records. Retain general methods and process-bound fine detail with evidence.
Submit concise records directly; avoid a separate compression pass. Stable
program entry points should assemble context, validate, execute and persist
results. Use initialized runs' pinned scripts and instruction snapshots. Load instructions
once per task/version, use context tokens to read relevant deltas, and
commit at meaningful boundaries instead of repeatedly reading source or editing
documents during ordinary calls.

Retain every design iteration, its actual circuit/layout, executed code,
parameters, verification, visible prompts and changed instructions, including
failed or rejected designs. Automatic observable event recording is distinct
from short reusable memory. Keep independent review and verification scope.
Run cheap applicable screens during development, qualify the selected module
revision with its agreed full batch, and verify the final macro separately.

Preserve original path strings as provenance, not recovery dependencies. Resolve
run evidence through relative object paths and verify hashes. Move complete run
trees without rewriting state, logs or pinned programs. New standalone evidence
manifests may opt into a common base root; older manifests and pinned runtimes
retain their original path contracts. Keep required compatibility links until
their consumers have an explicitly validated migration.

## Guide boundaries and dispatch

`dcim-self-improve/SKILL.md` preserves improve 2's general engineering experience;
change its process-specific assumptions narrowly. Framework rules belong here.
Role responsibilities and reusable experience stay in references/initialize.md,
reflect.md, builder.md and analyst.md; roles.py loads the appropriate entry.
Do not create a parallel role-SKILL hierarchy. Developer history remains only in
HANDOFF.md and is not copied into new runs.
Short stage/route memory is maintained separately through memory.py; do not replace
these three surfaces with one growing runtime guide.

Initialize through the repository scripts, then call the run's pinned scripts.
Use workflow status/context at entry, retain context tokens, and request only
deltas for the same task. Reflect requests/replies and role results are persisted.
See dcim-self-improve/references/runtime.md for actual commands and schemas.

Reflect0 studies compiler and digital-flow layouts. In every round Reflect must
submit self_proposal naming a NEW AI proposal in proposals, with mechanism,
difference, expected effect, evidence, minimal_test and stop. It may select the
algorithm route, its own plan, or close, but must retain its independent idea.
An unselected idea may be deferred; final reflection does not authorize another
experiment. Programs check the contract and reject verbatim mechanism reuse;
semantic novelty and scientific value still require AI judgment and evidence.

Builder owns one bounded block-level task and its ordinary local debugging. Pass
role/packet/output paths and execution bounds instead of a complete conversation.
Analyst independently checks frozen inputs, reviews the result and commits short
memory before Reflect; it no longer owns the mandatory new idea or next-route
selection. Use isolated role contexts when the available agent API supports them;
report any lack of isolation. Current scripts enforce stage transitions but do
not themselves create AI contexts. Match dispatch to actual available APIs.

At structural decisions compare mechanism-distinct cheap screens when useful,
with common frozen inputs and disjoint candidate/evidence/job namespaces. No peer
output inspection or waiting inside an independent screen. Keep aggregate resource
bounds; document serial or single-route reasons. This is not blanket permission
for parallel macro implementation or PEX. Ordinary fixes do not require artificial
competitors. No separate planner, curator, compression or retrieval AI role is needed.

Search is part of Reflect, not an additional phase. Reflect reads reviewed memory,
originates an AI idea, selects an algorithm/operations and budget, executes proxy
searches, then chooses the next Builder plan. Read the role-specific
`dcim-self-improve/references/reflect.md` once per version. Preserve the main
SKILL.md as the general experience guide.

After Reflect0, every search baseline must be actual geometry from the immediately
preceding Builder round, cited by its result and Analyst review. The default is
that result's selected baseline candidate; another candidate requires the same
round's evidence. Never reset to a shelf arrangement or silently use an older
accepted design. Missing output is an explicit recovery requirement. Failed
reviews remain visible when their geometry is used for repair. Compare baseline
and candidates with the same fixed evaluator; proxy gains are not qualification.
Builder retains measured placement state, and Analyst records applicable results
in the existing bounded memory format. New operations are implemented and checked
within the ordinary loop; no operator-development stage is added.

Reflect0 learning hypotheses use the same four short text fields as memory, plus
scope, source evidence and required checks. Each Builder task binds active goals;
each task binds its module-specific reference sources; dcim integration binds both. Candidate output
retains exact goal versions. Analyst reports every bound goal with current evidence
and explicit supported/refuted/inconclusive status before committing short memory.
Active goals remain retrievable independently of recent-memory limits; corrections
supersede and retain the original. General method hypotheses are not cross-node
signoff; process details require exact technology and affected conclusions must be
revalidated. Reviewed experience may be published with experience.py into immutable
private bundles. Receiving runs pin explicitly selected bundles and retrieve them
as reference-only hypotheses, never inherited passes. Read roles and recent applicable experience newest first without
changing the existing stage sequence.

Routine framework regression uses synthetic inputs without launching EDA.
Explicitly requested real-design trials use independent copies and retain actual
qualification limits; framework setup alone still does not authorize EDA. Preserve
role isolation limitations and actual execution provenance in the validation record.

## Ownership and delivery

Keep private configuration, PDK/compiler inputs, runs and experiment evidence
outside this repository. Resolve configured relative paths against their JSON
file. Framework setup, tests and packaging do not authorize EDA jobs. Respect
the enclosing workspace's ownership rules and identify jobs before stopping them.

At each completed framework iteration, update this file if policy changed and
update `HANDOFF.md` with completed work, evidence, limitations and the next task.
Run checks appropriate to the change, commit locally, then run:

```sh
python3 scripts/package_workspace.py
```

This atomically replaces the sibling `dcim-framework.zip`. Git retains framework
revisions; there is one current ZIP. Check Git status and the package result
before reporting completion. Keep the enclosing workspace's `AGENTS.md` and
`HANDOFF.md` current at requested handoff boundaries, including this closeout.

## Two-scale and physical-adapter contracts

Analyst owns both independent review and concise experience submission; there is
no extra memory role. Reflect may jointly choose fine/coarse actions in one bounded
task, using implemented operations and fixed MUST constraints. Complete module
requirements cannot be replaced by a smaller diagnostic deliverable. Read
references/two-scale.md and algorithm-portfolio.md for current interfaces.

Unknown geometry contract fields are rejected. Full masks, placement boundaries
and native repeat transforms are distinct. Exact seam exceptions require immutable
source/report bindings at all runtime entries; those bindings do not certify raw
foundry reports. Existing upstream solver calls are explicit; unavailable EDA
adapters cannot silently fall back to a different algorithm. Private physical
recipes and node experience remain outside this reusable repository.


## Optional physical action admission

New adapters may bind physical-action-guard-v1: exact parent GDS/CDL/DEF, actions,
affected/frozen conditions, raw observations and final consumption witnesses.
The captured adapter fixes the condition set; plans cannot silently weaken it.
Unknown affected conditions block execution. Every action entry revalidates
original evidence and consumed copies. This validates identity and declared scope,
not automatic impact discovery, scientific truth or EDA permission. Independent
Analyst review of the complete module and private recipe remains mandatory.
