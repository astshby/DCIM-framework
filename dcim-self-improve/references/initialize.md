# Initialization and first task

Python 3.8+ and the standard library suffice for initialization, dispatch and
PV/wave readers. GDS measurements additionally need the optional `gdspy` library.
No dependency installation or EDA execution is performed by setup.

## Private configuration

Start from `dcim.example.json`. `schema_version`, `node`, `work_root`, `resources`
and `stages` are explicit. A resource has a private `path`, semantic `role` and
`kind` of `file` or `directory`. A directory requires its exact relative `files`.
Optional `sha256` for a file or `hashes` keyed by relative directory file name
reject stale sources. Stage lists name the required resource IDs. An empty
planning list supports an empty design when source creation is the first task.
Later stages declare their actual requirements. There are no implicit filename
searches or technology defaults.

`check_inputs.py --config PATH --stage STAGE` returns availability, byte identities
and targeted missing/stale rows. It establishes availability for the declared
scope. The AI still checks circuit authority, rule/model applicability and
functional/physical legality. Configured addresses remain private.

An optional `initial_recipe` object declares `root`, `entrypoint` and `files`.
All dependency paths must stay within that root. Initialization copies only those
files to `initial_design/` and editable `design/`. It never executes them or
infers undeclared imports. Declare the complete local closure and external
resources, then inspect/test the copied recipe for the target task. No recipe
is required for initial source creation by Builder.

## Atomic publication and pinning

`init_run.py --config PATH --name NAME --stage STAGE` uses an exclusive per-name
lock, a private staging directory and a same-filesystem rename. Existing runs
are preserved. Missing inputs or copy/validation/publication failure clean only
that invocation's staging and lock so the name can be retried. Process death can
leave a named lock/staging directory. Inspect actual process/output ownership
before explicitly recovering that interrupted initialization. Never erase runs
on a blind retry.

A run contains `framework/`, `config.json`, `original-config.json`,
`input-check.json`, `initial_design/`, editable `design/`, and task/knowledge/
evidence/decision directories. `initial-manifest.json` records relative pinned
files plus exact external reference identities. Pin the manifest digest in the
first task or an external trusted record. The self-consistency checker does not
authenticate a deliberately rewritten manifest.

`python3 RUN/framework/scripts/check_inputs.py --run RUN` checks the pinned bytes
and original external input identities. Editable design/results are deliberately
outside that initial snapshot. Preserve each later candidate with `evidence.py
freeze` and its actual execution/semantic checks.

Moving the whole run preserves its initial-manifest verification when external
inputs remain at their declared addresses. `config.json` external paths remain
absolute. Dispatch/evidence schema-v1 packages bind absolute paths and stay tied
to their original roots. After relocation prepare a new task/context package
from the moved pinned scripts and explicitly rebound addresses. Old package
bindings and historical evidence stay intact. Moving a run does not relocate
PDK installations, private recipes or already prepared context packages.

## Actual AI handoff

Main performs initial reflection/planning from user intent and available sources,
then writes an actual bounded task. Use `templates/task_packet.md` for content.
For executable dispatch, write three JSON files using `templates/dispatch.schema.md`.
No fixed AI plan is emitted by initialization. A first selection is authored by
Main during initial planning. Subsequent selections come from Analyst decisions.

```sh
python3 RUN/framework/scripts/context_dispatch.py overview --catalog CATALOG --stage 1
python3 RUN/framework/scripts/context_dispatch.py prepare --task TASK --selection SELECTION --catalog CATALOG --out NEW_PACKAGE
python3 RUN/framework/scripts/context_dispatch.py open --package NEW_PACKAGE --expected-sha256 DIGEST
```

`prepare` returns a compact card for Main. Builder executes the `open` command on
the declared host, reads its context, then implements within the task scope.
Use the native agent API's actual fresh-context mechanism and record its returned
ID with `record`. Main can execute a bounded task directly when authorized.
Normal initialization requires no comparison experiment or proprietary seed.
