# Reusable evidence tools

Read this inventory before evidence work; use `scripts/evidence.py --help` and
the relevant subcommand's `--help`, not the whole implementation on each task.
Run with Python 3.10+. All commands emit JSON to stdout; store it in the
role's own output directory. No command launches EDA or imports a generator.

| Command | Purpose | Limits |
| --- | --- | --- |
| `freeze --out MANIFEST FILE...` | Fingerprint an explicit dependency list; refuses overwrite | Snapshot, not proof of correctness or execution provenance |
| `check MANIFEST` | Verify every recorded file is unchanged | Dependency identity only; omitted dependencies are not covered |
| `pv SPEC --manifest MANIFEST` | Calibre DRC/LVS report, exact deck edits and execution-input hash checks | Supported report formats only; warnings and job provenance need review |
| `gds SPEC --manifest MANIFEST` | Hierarchical bbox, direct reference count, selected-layer union areas, optional mask XOR and height-band check | Geometry, not connectivity or DRC |
| `wave SPEC --manifest MANIFEST` | Read PSF ASCII, validate time/signals and sample explicit times | No arithmetic, timing or electrical acceptance oracle |

Exit codes: `0 passed`, `1 failed`, `2 incomplete`, `3 unsupported`. A measurement
`passed` means its declared scope only. Missing/truncated evidence, unsupported
formats and stale bindings must never be converted to a pass. JSON identifies
tool version/hash and manifest hash. Do not rank circuits from process exit
codes, bbox sums or successful waveform parsing.

## Freeze and focused checks

Builder records launch-time hashes in an `inputs.json` alongside each PV job:
`gds_sha256`, `source_sha256`, `original_deck_sha256`, `run_deck_sha256`.
Preserve the terminal job record, command, logs and original report. Do not
retroactively invent a launch-time record for legacy evidence.

At the bounded result boundary, finish or explicitly hand over owned jobs.
Freeze explicit spec files and their inputs: relevant design source/GDS,
original/run decks, execution records, reports, models/includes/corner/load,
testbench, raw waveforms, independent oracle and reference/constraint files as
applicable. Include the actual dependency closure for any conclusion proposed
for inheritance, not the entire run tree. Use `context.py`'s existing
`schema_version: 1` / `files` manifest if already available; the same resolved
path/sha256/bytes format is supported. Do not create a competing manifest.

```bash
python3 "$SKILL_ROOT/scripts/evidence.py" freeze --out /run/Bx/frozen.json /run/Bx/pv.json /run/Bx/DRC.rep /run/Bx/inputs.json /run/Bx/rules.drc /pdk/original.drc /run/Bx/layout.gds /run/Bx/source.cdl
python3 "$SKILL_ROOT/scripts/evidence.py" pv /run/Bx/pv.json --manifest /run/Bx/frozen.json
```

Paths in manifests/specs must be explicit absolute paths, not `latest` or globs.
Tool output goes outside frozen inputs. Builder runs `check` and applicable
commands against the frozen inputs. Analyst reuses bound outputs for decisions.
For a decision-changing gap, request a focused Builder check according to
review.md; no second full replay is required. Commands recheck the manifest after reading.
Do not edit a published snapshot while it is assessed;
an intentional update gets a new revision and manifest. Hash checks detect
changes but are not a filesystem lock or a provenance guarantee.

## PV spec

Supply JSON with the following fields (paths are illustrative):

```json
{
  "kind": "drc",
  "report": "/run/Bx/DRC.rep",
  "execution_inputs": "/run/Bx/inputs.json",
  "gds": "/run/Bx/layout.gds",
  "source": "/run/Bx/source.cdl",
  "top": "compute_top",
  "original_deck": "/pdk/original.drc",
  "run_deck": "/run/Bx/rules.drc",
  "replacements": [
    ["\"GDSFILENAME\"", "\"/run/Bx/layout.gds\""],
    ["\"TOPCELLNAME\"", "\"compute_top\""]
  ]
}
```

For LVS use `"kind": "lvs"` and add `"source_top": "independent_source"`;
declare exact source-path/top replacements and any explicitly approved setup
change. Check that replacement pairs are authorized bindings/settings,
not rule weakening. The tool compares the entire resulting deck byte-for-byte
as text, rather than broadly stripping setup lines. Included deck files are
additional manifest dependencies. Optional DRC `expected_rules` is the
deck/version-specific rule count, not a universal constant. Parsed rule counts
must match the executed-rule footer and actual/expanded totals.

Legacy reports without execution bindings remain incomplete under this command;
Main chat may inspect them explicitly as limited historical evidence, not silently
create fresh qualification. A valid frozen manifest alone cannot establish that
the current files produced an old report. Inspect terminal job records and raw
warnings; supported zero-count reports do not resolve deck applicability,
black boxes, waived checks or unmeasured scope.

## GDS spec

```json
{
  "gds": "/run/Bx/layout.gds",
  "top": "compute_top",
  "layers": [[6, 0], [17, 0]],
  "band_y_um": [-0.259, 3.005],
  "compare_gds": "/run/baseline/layout.gds",
  "compare_top": "compute_top"
}
```

Only `gds` and `top` are required. Optional layer list controls union/XOR
measurements; comparison requires explicit layers. Units are converted from the
GDS library unit to micrometers. Hierarchical transformations are applied.
XOR compares common coordinates without implicit registration; differing origin,
rotation or context can be meaningful, so declare the comparison frame.
Selected layers are the task's responsibility; all-mask bbox is not functional
device height. Missing layer geometry has zero area, not proof of a valid design.

## Waveform spec

```json
{
  "format": "psf_ascii",
  "psf": "/run/Bx/raw/tran.tran.tran",
  "signals": ["G0", "G1"],
  "time_signal": "time",
  "sample_times_s": [9e-10, 1.9e-9]
}
```

Uses the user's verified `virtuoso_bridge.spectre.psf` reader; do not install an
unverified substitute or rewrite PSF parsing. Binary/other formats return
unsupported. All requested real vectors must be finite and match a strictly
increasing time vector. Sampling uses linear interpolation without extrapolation;
the independent oracle must choose valid settled samples away from transitions.
Use the same reader API directly in a thin oracle when full arrays are needed.
Missing signals or incomplete coverage are incomplete, not a circuit pass.
The oracle still independently verifies stimulus, arithmetic/topology, load,
corner, thresholds and timing as appropriate.

## Testing and change ownership

Run the shared positive/negative suite when these tools or their reader
dependencies change:

```bash
python3 -B -m unittest discover -s "$SKILL_ROOT/tests" -p 'test_evidence.py' -v
```

Do not rewrite these parser/hash/geometry fixtures every round. Each new result
still gets artifact checks; changed circuits/oracles get affected semantic
regressions and relevant negative controls. Shared parsing is not two independent
implementations: retain targeted raw-report checks when needed and independent
circuit intent/oracles. A tool change must pass known-good, known-bad,
truncation/missing-input and stale/wrong-binding cases, plus a relevant real
historical case when available. Record tested tool/reader version and outcomes.

Installed tools are read-only during autonomous runs. If unsupported behavior
requires an adapter, propose a bounded run-local tool change with validation;
do not silently write another parser in every review or modify the skill.
