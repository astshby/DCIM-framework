---
name: dcim-self-improve
description: Learn DCIM structure from compiler and digital-flow layouts, generate geometry candidates through bounded heuristic planning, and run reviewed Builder/Analyst/Reflect iterations with concise versioned memory.
---

# DCIM learning and construction

Use the repository AGENTS/HANDOFF at entry. Load this skill once per version.
Run `scripts/workflow.py --run RUN status`, then `context --role ROLE`.
Retain the returned token; subsequent `context --since TOKEN` returns changed
sections only. Use the packet and fixed scripts without repeatedly reading their
source. A source change is a separate versioned framework revision.

Reflect0 studies actual compiler and digital-flow layouts through `learn.py`.
It extracts geometry and hierarchy observations, interprets mechanisms, then
chooses the specific next construction using cited learning IDs. A picture or
bounding box does not establish electrical correctness. Missing references keep
planning open; they do not authorize fabricated learning.

Reflect compares optional human methods, AI hypotheses and actual algorithm
outputs. `planner.py` generates new placement routes with bounded diverse beam
search; every trial and stop reason is retained. Human involvement is optional.
The current implemented objective is geometry plus center-based HPWL, a proxy.
Use explicit process conditions, allowable transformations and independent checks.

The program enforces learning -> Reflect0 -> Builder -> Analyst -> short memory
commit -> Reflect -> next Builder. Every reviewed round, including failures,
no-new-memory and closure, requires a short reflection. Reflect replies come from
an actual AI context via the saved request/reply interface, never a fixed answer.

Read [runtime.md](references/runtime.md) once for command/payload contracts.
Role packets include [reflect.md](references/reflect.md), [builder.md](references/builder.md)
or [analyst.md](references/analyst.md), not the whole historical campaign.
Read [experience-memory.md](references/experience-memory.md) when correcting memory.
Use [evidence-tools.md](references/evidence-tools.md) for independent report checks.

Keep external DCIM/PDK/compiler sources read-only. Configuration and runs live
outside this repository. Framework setup does not authorize EDA. This release's
Builder executes generated geometry Python only; live EDA scheduling is not
implemented. Preserve actual programs, dependencies, layouts, failed candidates,
visible requests/replies and instruction versions. Independent acceptance and
foundry rules cannot be relaxed. Program gates cover its entry points; they are
not an operating-system sandbox or proof of AI reasoning quality.
