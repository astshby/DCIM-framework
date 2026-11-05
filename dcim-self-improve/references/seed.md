# Initial Python scripts

## Scope and dependencies

The initial code is a portable subset of the existing native-core generator,
not an archive of all repair branches. `init_run.py` copies it into the run's
`design/` directory; edit that copy, not the installed seed.

| File | Initial capability |
| --- | --- |
| `seed_config.py` | Explicit JSON path resolution and external-input checks |
| `prepare_seed.py` | One isolated pair, SRAM, seam, LRCC or FA candidate |
| `geometry.py` | Read-only GDS import, hierarchy, bboxes and Virtuoso SKILL emission |
| `core_geometry.py` | Native shared pair, 6T SRAM and diagnostic SRAM seam |
| `logic_geometry.py`, `fa_geometry.py`, `fa_recipe.py` | LRCC and independent 22T FA construction |
| `route12.py`, `repair_logic_routes.py`, `fracture_mask_holes.py` | Python routing and geometry utilities; no compiled binary dependency |
| `arithmetic_contract.py` | Signed/unsigned eight-term reduction contract |
| `macro_topology.py` | Independent macro connectivity sketch and integer evaluator |

Physical recipes require `numpy`, `shapely` and `gdspy`. SKILL emission additionally
requires the verified `virtuoso-bridge` Python builders used by `geometry.py`.
Use a virtual environment; the package does not install tools or connect to a
Virtuoso session. Resolve bridge installation through the user's EDA setup.

## Initialization

Pass a private config with a writable `work_root`:

```bash
python3 "$SKILL_ROOT/scripts/init_run.py" --config dcim.local.json --name trial01
```

This creates `<work_root>/trial01/design`, local task templates and a
`config.json` whose external addresses are rebased relative to the run.
It refuses an existing run and overlapping read-only input/output roots.
Initialization does not require the PDK or REF to be mounted and does not
establish input qualification.

The generated run's config sets `work_root` to `.`. In the following examples,
`RUN_ROOT` is the resolved run directory printed by initialization:

```bash
python3 "$SKILL_ROOT/scripts/check_inputs.py" --config "$RUN_ROOT/config.json" --scope seed
python3 "$RUN_ROOT/design/arithmetic_contract.py"
python3 "$RUN_ROOT/design/prepare_seed.py" --config "$RUN_ROOT/config.json" --id sram01 --kind sram --geometry-only
```

`--geometry-only` emits geometry, independent CDL and measured full-mask bbox
without importing the bridge or reading the PDK layer map. It still needs the
authorized native REF. To additionally emit `layout.il`, omit that flag and
provide an explicit, already-existing scratch library:

```bash
python3 "$RUN_ROOT/design/prepare_seed.py" --config "$RUN_ROOT/config.json" --id sram02 --kind sram --library scratch_dcim
```

The script only writes files. It never creates an OA library, loads SKILL,
exports GDS, submits jobs or launches simulation. Inspect and execute generated
SKILL through the user's verified Virtuoso workflow only after authorization.
Existing destination cells are guarded by the emitter; use a new candidate
ID/library instead of overwriting earlier results.

Each candidate includes `source.cdl`, `geometry.json.gz` and `candidate.json`.
`layout.il` and `cell_names.json` appear only with emission enabled.
All DRC/LVS/electrical states start as `not_run`, `accepted` is false, and
measured bbox area is not a placement pitch or a qualified macro area.
The SRAM `seam` kind is a diagnostic; it is not the policy's four-SRAM
reference-consistent grouping. A callable historical recipe can still fail
routing or require repair; do not turn that into a pass.

## Local checks

```bash
python3 -B -m unittest discover -s "$SKILL_ROOT/tests" -v
```

Tests use synthetic configuration/geometry in temporary directories and do
not require proprietary inputs, the bridge, EDA licenses or job submission.
Real DRC, independent LVS, pre-layout and post-layout checks must be supplied
and reported separately for the user's environment.
