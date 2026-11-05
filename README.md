# DCIM framework

This workspace supports module learning followed by whole-DCIM redesign.
Defaults: 8 input channels, 8 output channels, storage/compute ratio 8.
The ratio is not a precision setting; its accounting must be defined before design.

## Start here

Read `dcim-self-improve/AGENTS.md` for the framework's agent workflow, then
`dcim-self-improve/SKILL.md` and the references needed for the requested stage.
The framework supplies helpers, templates and tests for module learning,
staged verification, design history and evidence-driven self-improvement.

An outer workspace `AGENTS.md` is a separate user/agent-owned file for local
goals, permissions and operating constraints. Create it when needed; the release
does not supply it. The inner `dcim-self-improve/AGENTS.md` explains how to use
this framework and does not grant permission to operate external resources.

Local configuration, experiments and environment-specific files are also
created after deployment. A release contains this README and
`dcim-self-improve/`, including its generic `dcim.example.json`.

The distribution includes no PDK, compiler IP, EDA binaries or accepted circuit.

## Configure

Python 3.8+ is sufficient for configuration and initialization. Optional geometry
tools use the dependencies in `dcim-self-improve/requirements.txt`; install those
only when needed, in a user-owned environment.

First inspect the user-authorized environment and identify actual source paths.
Create `dcim.local.json` beside the framework; it is not included in a release.
The name is a convention: helpers also accept another file through `--config`.

| Setting | Meaning |
| --- | --- |
| `work_root` | Writable run directory, resolved relative to this JSON file |
| `pdk_root`, `compiler_ref_root` | Authorized source directories discovered in this environment |
| `digital_flow_root` | Actual flow/reference material, when identified |
| `input_files` | Files required by the selected task, relative to their source roots |
| `project.macro` | Channels, ratio definition, capacity, precision, signedness, cycles, dimensions and electrical targets |
| `project.technology` | Exact process release and metal stack |
| `project.modules` | SRAM, multiplier, adder, selector/control and accumulator contracts |
| `project.verification` | Screening, closure conditions and optional runtime budgets |

Unknown values remain `null`. Select the exact PDK stack/compiler variant, model
coverage, geometry/interface constraints and test scope during contract setup.
JSON paths are relative to their configuration file, not the shell directory.
Use `./runs` to keep outputs in the new workspace.

Replace the two example source paths below with actual authorized directories:

```sh
python3 dcim-self-improve/scripts/configure.py \
  --output dcim.local.json --work-root ./runs \
  --pdk-root /path/to/pdk \
  --compiler-ref-root /path/to/sram-compiler \
  --input-channels 8 --output-channels 8 --storage-compute-ratio 8
```

## Initialize and inspect

Run from the workspace directory:

```sh
python3 dcim-self-improve/scripts/check_inputs.py --config dcim.local.json --scope compiler
python3 dcim-self-improve/scripts/init_run.py --config dcim.local.json --name experiment01
python3 dcim-self-improve/scripts/status.py --run runs/experiment01
```

The last command assumes `work_root` is `./runs`; otherwise use the `run_root`
printed by initialization. Existing run/configuration names are never overwritten.
To configure and initialize in one command, add `--init experiment01` to the
configuration command and use that command's configuration file.

Initialization creates pending contracts and a first task; it submits no EDA jobs.
An initialized run's `config.json` becomes authoritative for that run; changing
the parent `dcim.local.json` only changes the starting profile for future runs.

## Execute and retain results

Give the agent the workspace and a stage request, for example: inspect/configure
the environment, iterate SRAM, run post-layout simulation for a specified
revision, show layout images, or begin whole-DCIM redesign. Follow any user-owned
workspace `AGENTS.md`, then the framework `AGENTS.md`/`SKILL.md` and the run's
handoff/config/plan. If configuration does not exist, start by inspecting and
configuring the environment instead of assuming a previous run.

Establish function and legal dimensions before compaction. Screen routine changes
with geometry, DRC/LVS and necessary short tests. Fully verify the selected
revision at module-round closure and verify the final macro separately.

Keep every design iteration, including rejected circuits and produced layouts.
Preserve exact visible prompts/skills, their changes and parent versions.
Later verification of an unchanged circuit appends evidence to that version.
Use the framework's `references/history.md` and `scripts/history.py` for recording,
integrity checks and descriptive comparisons. Update each run's `handoff.md`
and `plan.json` so another agent can resume without chat history.

For the detailed workflow, read `dcim-self-improve/references/workflow.md`.

## Publish a clean copy

```sh
python3 dcim-self-improve/scripts/package_workspace.py \
  --readme README.md --archive dcim-framework.zip --copy-to /path/to/new-workspace
```

The target must be absent or empty. Use a new archive filename if one exists.
This includes the complete framework and README, excludes local configuration,
outer `AGENTS.md`, runs and caches, and emits no checksum files. Keep `learn/`
and existing experiment/evidence directories in the local workspace.
