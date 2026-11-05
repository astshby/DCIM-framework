# DCIM framework instructions

## Entry and scope

This directory is the active framework repository. Start with this file and
`HANDOFF.md`; use `README.md` for setup commands. The reusable skill remains in
`dcim-self-improve/`. Read its `SKILL.md` and only the references needed for the
current task. The handoff records accepted changes and their implementation
status; planned features must not be reported as working features.

The repository was imported from the user's `dcim-self-improve-2` reference.
Sibling `dcim-self-improve*` and future `improve-n` directories are references.
Make framework changes here and record their provenance rather than editing or
automatically synchronizing those reference directories.

## Framework development

Preserve the existing structure and reuse its helpers. Implement the accepted
Reflect, initialization and memory changes against the contracts in `HANDOFF.md`.
Its current decisions supersede conflicting inherited campaign instructions,
including fixed role interfaces and discarding rejected design branches.
Do not silently apply the inherited 12FFC recipes or four-SRAM grouping to a
different process or project.

The required loop is initialization, initial Reflect, Builder, Analyst,
committed concise action/experience memory, then Reflect and the next Builder.
Reflect and a concise reflection record are required every reviewed round,
including failure, unchanged strategy and final closure. Human feedback is an
optional input. AI selects the method; programs enforce ordering and execute
bounded searches. A fixed next-task response is not an AI Reflect implementation.

Use stage-scoped route memory with structured action, experience and reflection
records. Retain general methods and process-bound fine detail with evidence.
Submit concise records directly; avoid a separate compression pass. Stable
program entry points should assemble context, validate, execute and persist
results. Load instructions once per task/version, read relevant deltas, and
commit at meaningful boundaries instead of repeatedly reading source or editing
documents during ordinary calls.

Retain every design iteration, its actual circuit/layout, executed code,
parameters, verification, visible prompts and changed instructions, including
failed or rejected designs. Automatic observable event recording is distinct
from short reusable memory. Keep independent review and verification scope.
Run cheap applicable screens during development, qualify the selected module
revision with its agreed full batch, and verify the final macro separately.

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
