# DCIM Framework

An AI-assisted framework for constructing and improving digital compute-in-memory
circuits and layouts. Tasks bind circuit intent, applicable references, physical
constraints and checks to a specific candidate. Reviewed experience informs later
construction and repair.

The `main` branch provides the improve-3-derived workflow. Technology-specific
resources and construction recipes are supplied through private configuration.

## Branches

| Branch | Purpose | Workflow |
| --- | --- | --- |
| [main](https://github.com/astshby/DCIM-framework/tree/main) | Process-neutral improve-3-derived workflow, with configuration, initialization, context and evidence helpers | Main plans, Builder implements, Analyst reviews and reflects |
| [coarse](https://github.com/astshby/DCIM-framework/tree/coarse) | Earlier coarse-placement workflow, executable search and action guards | Integrated `initial-plan` / `reviewed-decision`, with legacy role APIs |
| [coarse_fine](https://github.com/astshby/DCIM-framework/tree/coarse_fine) | Experimental relative fine/coarse hierarchy, joint actions and physical-consumer interfaces | Earlier explicit role loop with granularity selection |

Each branch documents its own commands and validation scope. Existing runs retain
their pinned programs, instructions and configuration contracts.

## Workflow

```text
Main initial planning -> Builder -> Analyst -> Main admission -> next task or closure
```

- Main selects references and experience, extracts construction constraints and
  defines a bounded first task. This includes the initial reference-learning work
  previously assigned to Reflect0.
- Builder constructs a connected block or runs a decisive experiment, including
  ordinary diagnosed repairs within the task's bounds.
- Analyst independently reviews the evidence, updates scoped experience, writes
  a concise reflection and proposes the next executable task or closure.
- Main checks architecture, MUST constraints and authorized resources before
  admitting the proposed task.

Reference selection depends on the task. Sources can include independent circuit
intent, applicable compiler output, native cells, standard-cell layouts, process
documentation and reviewed experience. Initialization records declared sources.
The initial planner explicitly selects any compiler references.

## Getting started

Python 3.8+ supports the core helpers through the standard library. GDS evidence
readers additionally use `gdspy` and `shapely`. Physical execution uses configured
EDA tools and verified private recipes.

1. Read [AGENTS.md](AGENTS.md), the [skill](dcim-self-improve/SKILL.md) and the
   [initialization guide](dcim-self-improve/references/initialize.md).
2. Create a private configuration using
   [dcim.example.json](dcim-self-improve/dcim.example.json). Declare the target
   profile, writable run root, reference roles and stage-required files.
   An initial design may be empty.
3. Check inputs and initialize a new run from the repository root.

```sh
python3 dcim-self-improve/scripts/check_inputs.py --config ../dcim.private.json --stage planning
python3 dcim-self-improve/scripts/init_run.py --config ../dcim.private.json --name trial01
```

Initialization returns `run_root`. Replace `RUN_DIR` below with that path.

```sh
python3 RUN_DIR/framework/scripts/check_inputs.py --run RUN_DIR
```

Main writes the initial task and selects Builder's resources and experience. The
[dispatch schema](dcim-self-improve/templates/dispatch.schema.md) describes JSON
inputs and `context_dispatch.py prepare`, `open` and `record` handoffs. The
available native agent API performs actual dispatch. Use the run's pinned scripts
for subsequent work.

## Physical construction

Tasks declare parent dimensions, functional rows, device phases, metal/track
alignment, intended continuous PP/NP interfaces, TAP/body ownership and signal/
power access. Intended PP/NP interfaces abut directly. TAP removal requires real
powered body access and applicable checks on the final candidate.

Structural choices normally use two mechanism-distinct cheap screens, with
recorded evidence supporting single-route or serial execution where appropriate.
Routine repair proceeds within its bounded Builder task. See the
[task-admission guide](dcim-self-improve/references/task-admission.md) and
[layout-order guide](dcim-self-improve/references/layout-order.md).

## Repository guide

| Location | Contents |
| --- | --- |
| `dcim-self-improve/SKILL.md` | Construction principles and MUST constraints |
| `dcim-self-improve/references/` | Roles, physical interfaces and experience handling |
| `dcim-self-improve/templates/` | Task, result, review, experience and dispatch formats |
| `dcim-self-improve/scripts/` | Input checks, atomic initialization, configuration, context and evidence helpers |
| `dcim-self-improve/tests/` | Synthetic software regression |
| `HANDOFF.md` | Developer history, migration details and verification records |

## Evidence and portability

Runs pin initial code, instructions, configuration and declared reference
identities. Task checkpoints retain candidates, executed code, parameters,
checks, failed trials, experience and reflection. Experience retains its source
and technology scope.

Geometry, DRC, independent source LVS, function, ERC, electrical/PVT and complete
parent acceptance each require applicable evidence. Software regressions establish
tested software behavior. Physical qualification is evaluated on the actual
candidate and process resources.

Whole-run relocation supports the initial manifest when external input addresses
remain valid. Prepared dispatch/evidence schema-v1 packages bind absolute source
paths and require newly prepared packages after relocation. Preserve prior
bindings as provenance.

## Development checks

```sh
python3 -m unittest discover -s dcim-self-improve/tests -v
python3 -m unittest discover -s tests -v
git diff --check
```

The core framework is process-neutral. PDK/compiler IP, models, private recipes,
configuration and experiment data belong in the user's private workspace. Source
licensing is described in [LICENSE](LICENSE).
