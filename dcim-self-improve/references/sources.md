# External inputs and seed provenance

Addresses belong in the user's private JSON configuration, never in this
package. Relative addresses resolve against that file. The example uses
`external/` as a mount convention, not as a bundled data directory. There are
no implicit searches of a home directory, sibling experiments or old skills.
Use `scripts/check_inputs.py` for the required inputs of the selected scope.

## Target PDK (`pdk_root`)

The original seed targets the licensed TSMC 12FFC core-device stack
`1P11M_2Xa1Xd_h_3Xe_vhv_2Y2R`,
`iPDK_CLN12FFCLL_v1.0_2p4a_20190306`. Supply the installation root with:

| Path relative to `pdk_root` | Purpose |
| --- | --- |
| `tsmcN12/` | Virtuoso technology library |
| `tsmcN12/tsmcN12.layermap` | GDS to layer/purpose map |
| `Calibre/drc/calibre_block.drc.15a` | Original block DRC deck |
| `Calibre/lvs/calibre.lvs` | Independent-source LVS deck |
| `models/toplevel.scs` | Spectre model entry; verify sections and device coverage |

The paths identify the original integration, not portable foundry guarantees.
For a different release/stack, adapt and verify the adapter before use. Numeric
layers, mask dimensions and fin/gate phases in the seed are technology-specific.
Changing `pdk_root` does not port those recipes to another technology.
Do not distribute decks/models or weaken rule switches. The package stages no
EDA jobs and does not provide scheduler/host/tool-installation defaults.

## Native device reference (`native_ref_root`)

This private, read-only reference is distinct from the SRAM compiler REF and
the 22nm circuit/layout REF. It provides permitted target-native core PCell
shapes and independently sourced transistor circuits. Required filenames:

```text
native12/
  sram6t12_v1_layout_v2.gds
  sram6t12_v1_layout_v2.json
  sram6t12_v1_layout_v2_lvs/source.cdl
  lrcc12_v1_layout_v2.gds
  lrcc12_v1_layout_v2.json
  lrcc12_v1_layout_v2_lvs/source.cdl
  fa22t12_v1_layout_v2_lvs/source.cdl
```

SRAM metadata contains `cell` and `placements` entries `NQ`, `AXQ`, `PQ`;
the referenced GDS also has `M1_SUB_...` and `M1_NW_...` tap masters.
LRCC metadata has `cell` and placement values `[x_um, y_um, kind, fins]`,
where `kind` is `n`/`p`. FA CDL uses `M_M0` through `M_M21` and the
independent 22T topology checked by `fa_recipe.py`.

These contracts preserve the existing seed format. Another authorized reference
requires an explicit importer/adapter; do not silently substitute arbitrary
geometry or layout-extracted connectivity. Native model coverage, DRC, LVS
and electrical qualification remain separate obligations.

## Compiler SRAM (`compiler_ref_root`)

Supply the authorized `sram12_ref16x8m2` reference root with:

```text
GDSII/sram12_ref16x8m2_m4xdh.gds
SPICE/sram12_ref16x8m2.spi
```

These files support reference inspection, not a blanket simulation claim.
The historical HCSR SRAM branch had physical/LVS evidence but lacked usable
HCSR simulation models. Verify device models and rule-domain applicability
before treating compiler evidence as an electrically qualified anchor.
The seed `seam` generator is a core-6T diagnostic, not the reference-consistent
four-subcolumn grouping required by the physical-planning policy.

## 22nm REF (`reference_22nm_root`, optional `hierarchy_22nm`)

Supply the authorized `packages_22nm` root containing:

- `01_schematic`: circuit reference.
- `02_basic_leaves`: device/leaf reference.
- `03_composition_rules`: composition evidence.
- `04_source_gds`: source layout.
- `05_restricted_resize_script`: construction/reference scripts.

Keep access restrictions attached to these inputs. The historical storage/
compute ratio 16 does not determine the target ratio or freeze topology.
The optional full-reference `hierarchy.json` is separate from this package.
Its `cells` records include bboxes, widths/heights and instance references
for the cells named in `layout-order.md`, including decode. That file supports
placement observations, not target-node signoff.

For group-height planning, the task must identify the actual supplied DCIM
GDS path and top (including whether it is a resized K16/C16/S16 variant or its
upstream macro). Inspect selected hierarchy/masks and transformed array
placements directly; do not substitute a cached bbox summary for GDS review.
Preserve the reference read-only and record provenance in the run, not private
paths or licensed geometry in this package. Transfer the combined
SRAM-group/LRCC/complete-adder organization described in `layout-order.md`,
not source-node dimensions, rule domains or example adder bit widths.

## Optional warm start and shared experience

`warm_start_root` may point to a newer, read-only experiment. First inspect its
short current-state summary and selected generator's actual dependency closure.
Do not import an entire history, fixed area budgets or old orchestration rules.
`experience_root` holds a condensed cause-based ledger plus its cited evidence;
missing historical evidence limits the claim, not the acceptance standard.
New conclusions belong in `<run>/knowledge/`, shared by Builder and Analyst.

## Bundled initial source

`assets/seed/` is adapted from the user-owned
`coremos12_k8_c8_s8_20261027/design` source inspected on 2026-10-31.
It retains the original geometry representation, native-core SRAM construction,
LRCC/FA topology and Python router. Portable configuration replaces the old
sibling-directory dependency. The large experimental flag tree, accepted
candidate snapshots, compiled search binaries, private masks/CDL, decks,
model files and host-specific Makefile are intentionally excluded.

The integer reduction contract and macro connectivity sketch are included;
the latter's historical placement coordinates are not a new floorplan.
No full-macro physical/electrical runner or OA schematic is claimed.
Seed generation does not inherit prior DRC/LVS acceptance.

Use the installed Virtuoso, EDA-host and Spectre skills if available and
applicable, locating them through normal skill discovery rather than an author's
installation path. Otherwise inspect the user's actual tool documentation and
runner APIs. No dependency on a frozen-method skill is required.
