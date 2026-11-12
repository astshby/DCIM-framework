# DCIM framework

Main provides a process-neutral reference-assisted DCIM workflow based directly
on improve-3. Main handles initial planning and admission, Builder implements one
bounded task, and Analyst reviews the evidence, maintains experience, writes an
actual concise reflection and proposes a next task or closure.

## Branches

| Branch | Scope |
| --- | --- |
| `main` | Preferred new workflow with small configuration/init/check/context/evidence helpers and task-scoped AI handoffs |
| `coarse` | Continuation of the older coarse executable loop, action guards and physical/evidence APIs, with scoped generic improve-3 guidance |
| `coarse_fine` | Continuation of the older fine/coarse hierarchy/action/physical consumer work, with scoped generic improve-3 guidance and its incomplete physical qualification explicitly retained |

Existing runs use their fixed scripts and instructions. Branch checkout does not
upgrade them. `pro` preserves its previous development checkpoint. Source/Git
history retains earlier engines and technology-specific implementations.

## Start

Read `AGENTS.md`, then `dcim-self-improve/SKILL.md` and the assigned role reference.
Use `dcim-self-improve/dcim.example.json` as a schema example for a private config.
Declare node/profile, writable output root, actual reference roles and the exact
stage-required input files. Initial circuit authoring can start with no seed.

```sh
python3 dcim-self-improve/scripts/check_inputs.py --config PRIVATE --stage planning
python3 dcim-self-improve/scripts/init_run.py --config PRIVATE --name trial01
python3 RUN/framework/scripts/check_inputs.py --run RUN
```

Main then writes the actual initial task and resource/experience selection.
`templates/dispatch.schema.md` documents the executable JSON inputs to
`context_dispatch.py prepare`. Builder opens the returned package with its
expected digest before editing. Native agent dispatch uses the actual available
API. Initialization does not produce a canned AI plan or launch EDA.

Python 3.8+ and the standard library support initialization, dispatch and PV/wave
readers. GDS evidence additionally uses optional `gdspy`. Tested interpreter and
optional dependency gaps are recorded in `HANDOFF.md`.

## Main and improve-3

Main directly imports improve-3's role/context/evidence/memory approach. It
retains bounded Builder ownership, explicit AI-selected materials, route-local
experience, functional-row/straight PP/NP/TAP/body/interface intent, compactness
and parent-area admission. Analyst explicitly includes actual reflection.

Main replaces improve-3's seed-dependent init/check helpers with explicit
stage-resource configuration, exclusive atomic initialization, pinned code/
instructions/initial design and declared external reference identities. Empty
starts and declared private recipe dependencies are supported. Technology-specific
generator/router/arithmetic/macro topology, fixed grouping, model/host choices,
node dimensions and compiler filenames are outside the active package. Private
recipes keep those details. Main removes mandatory paired structural screens
and hard model preferences from ordinary tasks. Controlled comparison requirements
apply only when requested by the task.

Earlier generic evidence practices informed init pinning, exact input identity,
atomic publication and recovery. Their large orchestrator/search/action/hierarchy
engines remain on continuation branches. Main does not integrate those engines.
See `HANDOFF.md` for source identities, adoption and verification scope.

## Evidence and portability

A run pins initial programs/instructions, config and declared inputs. Editable
candidate code/results are preserved at task checkpoints with evidence manifests.
Hashes prove byte identity. File availability does not prove functional legality.
Geometry, DRC, independent source LVS, function, ERC, electrical/PVT and complete
parent acceptance retain their separate scopes. No physical experiment or PPA
benefit follows from software regression.

Whole-run relocation supports the initial pinned manifest when external addresses
remain valid. Prepared dispatch/evidence schema-v1 packages use absolute source
paths. Rebind into a new package after relocation and preserve old bindings.
No automatic EDA runner, physical decoder, PDK installation or foundry checker is
included. User authorization and private verified runners govern execution.

## Software checks and packaging

```sh
python3 -m unittest discover -s dcim-self-improve/tests -v
python3 -m unittest discover -s tests -v
git diff --check
python3 scripts/package_workspace.py
```

The packaging runner verifies selected bytes and atomically replaces the single
sibling `dcim-framework.zip`. Private config, runs, inputs and Git metadata stay
outside the release. Preserve the repository LICENSE and verify source/recipe
rights when importing additional material. Server commits remain local. The user
handles GitHub publication.
