# DCIM Framework

This repository is the active workspace for DCIM framework development. It was
imported from the newer `dcim-self-improve-2` reference while preserving the
`dcim-self-improve/` skill layout. Sibling improve-n directories are reference
snapshots; develop and commit framework changes here.

## Start here

Read `AGENTS.md` for framework instructions and `HANDOFF.md` for accepted design
decisions, implementation status, mathematical action/memory definitions and the
next task. Then load `dcim-self-improve/SKILL.md` and the references needed now.
The enclosing workspace's AGENTS and handoff describe local ownership and goals.

The package includes instructions, templates, evidence helpers and inherited
12FFC construction recipes. It includes no PDK, compiler IP, models or EDA
binaries. Those recipes and their four-SRAM grouping are scoped historical
starting points, not a qualified implementation for another process.

## Configure a private run

Keep configuration and run outputs outside this repository. Copy
`dcim-self-improve/dcim.example.json` to a new private `dcim.local.json`, then edit
the addresses for the intended stage. Relative JSON paths resolve against the
configuration file. The existing local profile must be checked before reuse.

The current configuration keys include `work_root`, `pdk_root`,
`native_ref_root`, `compiler_ref_root`, `reference_22nm_root`, `hierarchy_22nm`,
`experience_root` and `warm_start_root`. See
`dcim-self-improve/references/sources.md` for required source files and scope.
Define channel counts, storage/compute accounting, precision, process, geometry
interfaces, electrical conditions and acceptance in the task before design.
The current research target is eight input channels, eight output channels and
a storage/compute ratio of eight; the ratio is not a weight bitwidth.

From this repository, using an appropriate Python interpreter:

```sh
python3 dcim-self-improve/scripts/check_inputs.py --config ../dcim.local.json --scope seed
python3 dcim-self-improve/scripts/init_run.py --config ../dcim.local.json --name trial01
```

Input checks inspect configured files; initialization copies the seed and
configuration into a new run and refuses an existing name. Neither launches
EDA or establishes circuit qualification. Physical generation and inherited
evidence-tool documentation require Python 3.10+ and applicable dependencies in
`dcim-self-improve/requirements.txt`. Check the actual interpreter and tool
interfaces before execution. Packaging uses only the Python 3.8+ standard library.

## Current workflow and pending changes

The inherited framework supplies bounded Builder/Analyst tasks, stage-scoped
route memory, cheap candidate screens and reusable evidence tools. Learn modules
before whole-DCIM redesign; establish correctness and geometry interfaces before
compaction, screen routine changes, and fully verify selected module and macro
revisions within their declared scope. Preserve failed designs and exact methods.

The accepted target loop is initial Reflect, Builder, Analyst, committed concise
action/experience memory, then Reflect for the next round. Every reviewed round
requires reflection. Program-enforced initialization, actual AI Reflect dispatch,
structured memory writes and complete execution entry points remain pending;
`HANDOFF.md` defines their implementation and acceptance. Do not report these
planned features as implemented.

## Iterate, commit and package

Update `AGENTS.md` when framework rules change and `HANDOFF.md` at handoff and
iteration boundaries. Run checks appropriate to the change, review and commit:

```sh
git diff
git add .
git commit -m "Describe the completed framework change"
python3 scripts/package_workspace.py
```

The packaging command validates a temporary ZIP and atomically replaces the
sibling `dcim-framework.zip`. Reuse the same command after each completed
framework iteration. Git retains previous revisions; the ZIP contains the
current framework with one `dcim-framework/` top-level folder and can be extracted
without Git. No remote repository is configured by setup.

The archive includes this README, framework AGENTS/handoff, skill, packaging
helper and tests. It excludes `.git`, caches, private local configuration,
credentials, runs, experiment evidence and checksum sidecars. The enclosing
workspace's local AGENTS/handoff are outside the archive. Existing `learn/`,
viewing links and experimental records stay in their local workspace.

Packaging checks can be run without PDK or EDA:

```sh
python3 -B -m unittest discover -s tests -p 'test_package_workspace.py' -v
```
