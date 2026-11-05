# DCIM Framework

This repository implements a process-neutral DCIM learning and construction loop.
It combines improve 1's generic configuration/history/geometry with improve 2's
evidence checking and route-memory principles. The old 12FFC seed is retained in
Git history and is absent from the active package.

Read AGENTS.md and HANDOFF.md once at entry. The reusable skill is
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
geometry/hierarchy observations and specifies the next construction. `planner.py`
performs bounded diverse beam search over measured blocks: order, row splitting,
merging and allowed rotation. Human methods, AI proposals and actual algorithm
outputs share route records. Human feedback is optional.

`workflow.py` enforces Reflect -> Builder -> Analyst -> committed short memory ->
Reflect, including failed and final rounds. It persists real AI requests/replies;
it does not supply a canned AI answer. `context --since TOKEN` returns only changed
sections. `memory.py` provides bounded same-format reads/writes and supersession.
`builder.py` creates and executes a new drawing Python script, retaining actual
inputs, helper code, hierarchical geometry JSON, SVG, stdout/stderr and evidence.
The original evidence checker and compatible history helper remain available.

The research target is eight input/output channels and storage/compute ratio eight.
Its accounting, precision, process and electrical conditions must be explicit.
No fixed SRAM grouping, bitcell, topology, node or decoder proportion is inherited.

## Scope and validation

Current search optimizes geometry and center-HPWL proxies. It does not synthesize
transistor topology, route inter-block nets, establish electrical performance or
submit EDA jobs. Human/AI explicit plans can be evaluated in the same geometry
representation. New operator families require separate validated extensions.
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
