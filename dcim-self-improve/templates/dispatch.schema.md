# Executable dispatch inputs

Main authors the initial task and selection after actual initial planning.
Analyst authors later selections. Prepare accepts three JSON objects.
All file paths must be absolute and within declared allowed roots. Use actual
hostname allowlists, an available interpreter/model and task-owned new outputs.

The task requires `task_id`, integer `stage`, `profile`, `host`,
`execution_hostnames`, `allowed_roots`, `required_resource_ids`,
`max_bundle_bytes`, `python` and `model`. Additional fields carry the actual
objective, inline architecture, permissions, checks, outputs and stopping boundary.

```json
{
  "task_id": "first-block", "stage": 1, "profile": "private-target-profile",
  "host": "private-runner-label", "execution_hostnames": ["actual-hostname"],
  "allowed_roots": ["/absolute/run", "/absolute/run/knowledge"],
  "required_resource_ids": ["intent"], "max_bundle_bytes": 24000,
  "python": "/absolute/available-python", "model": "actual-supported-model",
  "objective": "Actual bounded deliverable from Main planning",
  "execution": "Authorized operations and resource scope",
  "checks": "Actual decisive checks and required evidence",
  "outputs": "Task-owned absolute paths and stop condition"
}
```

An allowed root must contain the pinned dispatcher, evidence and configuration
helper scripts. The catalog root itself must appear in `allowed_roots`.

```json
{
  "host": "private-runner-label", "root": "/absolute/run/knowledge",
  "revision": "initial", "entries": []
}
```

An empty experience catalog is valid. Entries, when available, have `id`, `stage`,
`revision`, `summary_path`, `evidence_paths`, `conclusion` and optional `requires`
entry IDs. Their summary/evidence files are bound references. Explicitly select
an inline resource when its actual text must appear in the context bundle.

```json
{
  "task_id": "first-block", "stage": 1, "profile": "private-target-profile",
  "host": "private-runner-label", "catalog_revision": "initial",
  "decision": "Actual Main initial decision and rationale", "route_id": "initial-source",
  "entry_ids": [],
  "resources": [
    {"id": "intent", "path": "/absolute/run/tasks/first-task.md", "mode": "inline", "purpose": "Actual bounded task, roles, sources and constraints"}
  ]
}
```

Resources may provide expected `sha256`. Selection may provide
`catalog_sha256`. Prepare checks them, assembles selected context and returns a
compact dispatch card. Main invokes the actual native agent API. Builder runs
`open --package DIR --expected-sha256 DIGEST` with the returned card identity.
Record the actual returned agent ID with `record`. Python performs bookkeeping.
