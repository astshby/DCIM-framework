# SRAM-anchored layout order

This is the initial physical-planning policy for the current reference-assisted
DCIM project, not a universal rule for all circuits or technology nodes.
Use it when selecting the next layout task. It does not change the Builder /
Analyst role interfaces or authorize EDA by itself.

## Physical dependencies, not independent leaf minimization

1. Establish independent circuit/netlist intent, function and intended
   composition first; detailed OA schematic work is optional. Inspect the
   supplied DCIM reference GDS hierarchy, array transforms and functional
   placement, not only old bbox summaries or a single primitive. Bind the
   source/top and selected observations to the task. Inspect the
   target-node SRAM compiler reference if available, its model/device options,
   rule domain, taps, boundaries, legal mirror phases and interfaces. Use the
   existing 12nm Python and scoped experience. Do not assume compiler SRAM rules
   apply to arithmetic logic, or that physical reference availability implies
   usable electrical models.
2. Build the reference-consistent four-SRAM grouping with its required physical
   context. Identify exactly which hierarchy objects "four SRAMs" names in this
   task; do not silently reinterpret this as four bits, four macros, or a new
   storage/compute ratio. Validate enough physical and electrical behavior to
   justify its use as a geometry anchor.
3. Measure the grouping's repeat height, placement envelope, actual routed
   envelope, legal overlap, termination/tap ownership and accessible pin bands.
   Emit these measured dimensions and qualification gaps in Builder's result.
   A standalone full-mask bbox is not automatically the tiling pitch.
4. Organize the **whole associated LRCC/multiplication plus complete multibit
   adder** alongside the corresponding four-SRAM group, within its common
   height band. Use available functional height to pack/fold devices vertically
   and reduce actual routed width, accounting for carry, bitline, supply and
   input access. The target is the combined organization, not equal height for
   one FA, one LRCC or an isolated adder, and not separate full-height budgets
   stacked for LRCC and addition. Do not require primitive bboxes to be equal.
   Derive the needed adder hierarchy and widths from the target channel
   configuration and verified circuit specification, not example bit counts.
   Preserve independent operands: an adder requiring two SRAM/LRCC sources may
   serve two groups placed horizontally in the same height band; do not use
   one group twice or multiply height by source count or bit count.
   Report functional row/column placements separately from OD/PO spans,
   terminations/dummy, access, routing and PG envelopes. A low single row plus
   tall metal escape is not proof of height matching or compactness.
   Follow [compactness.md](compactness.md) for the rule-compact first candidate
   and final measured/tighter-trial review.
5. Compose a small SRAM + multiplication + addition tile. Check actual routes,
   shared boundaries, height and width. Use this measured tile width, not the
   sum of independent bboxes, as the next physical constraint.
6. Design the local decoder/row-control layout beneath it. For the current
   two-local-decoder arrangement, start from half the corresponding tile width
   per decoder, with explicit seam/edge allowances. Derive output placement,
   driver/load needs and repeat pitch from the tile and electrical conditions.
   This rule is for the matching local decoder, not a global decoder/controller.
   Logical decode requirements and load estimates may be planned earlier; its
   final physical organization follows the measured tile.
7. Validate a small connected tile plus decoder before expensive macro work.
   Align repeated tiles and peripheral blocks at parent level. Reopen the
   relevant SRAM or compute/decoder geometry when evidence shows the initial
   height, width, access or electrical assumptions were wrong.

Analyst may improve this ordering and advancement/return criteria when actual
evidence justifies it. The agreed four-SRAM group is the current target;
if its organization or height is unsuitable, propose a measured alternative
and its functional/area/timing consequences to the user before changing the
grouping or budget. Do not repeatedly force a bad
height by shrinking rule margins, under-sizing drivers or hiding external
routes. Parent area and function remain the objectives; the anchor is not an
immutable acceptance criterion. Leaves need not reach their absolute minima
before a bounded composition probe.

## Reference support and limits

The supplied 22nm K16/C16/S16 GDS preserves selected cells from its upstream
full reference. Recheck the actual supplied GDS and identify which variant/top
was inspected. The optional `hierarchy_22nm` in [sources.md](sources.md) is a
placement aid, not a substitute for that inspection. Selected common cells
show the following organization:

- `sram_subarray_16x4` has four functional `sram_subcol_16` placements
  (each stores 16 addresses along X), four `lrcc`/`lrcc_0` placements along Y,
  plus separately owned edge/dummy context. This is the four-SRAM group, not
  four bits or four complete macros.
- The four functional row positions use a 1.08 um phase/pitch and a 4.32 um
  four-row repeat. LRCC origins along Y are -.24, .84, 1.92 and 3.00 um.
  Mirrored SRAM reference origins must be transformed before interpreting
  row locations; the reference-origin list alone is not four row centers.
- `adder_5b_stage0` has its LSB at Y=0, three ordinary `fa22t` array elements
  at Y=1.08/2.16/3.24 um and folded MSB circuitry alongside. `adder_6b_stage1`
  uses four ordinary FA rows at Y=0/1.08/2.16/3.24 um; wider reference
  adders fold extra circuitry into columns rather than increasing row count.
  These bit counts describe that reference, not the new target's specification.
- `cim_16x4sub_add_stage0` places two mirrored SRAM/LRCC groups on opposite
  sides of the complete adder, in a common functional height organization.
  This does not mean all standalone full-mask bboxes are equal: the reference
  SRAM/LRCC group's full-mask height is 9.26 um, including protruding
  edge/dummy context, versus the standalone adder's 5.65 um.
- `dec_local` full-mask width 7.28 um versus
  `cim_16x4sub_add_stage0` width 14.48 um, a ratio about 0.50276.
- `row_control_stage0` contains two mirrored local decoders; width 14.56 um,
  not exactly the compute block's 14.48 um.
- Both `row_control_stage1` and `cim_16x4sub_add_stage1` place their two stage0
  children at x = 0 and 18.46 um. Matching hierarchical repeat placement is
  stronger evidence than equality of isolated full-mask bboxes.

These are source geometry/placement observations, not new DRC/LVS, extracted
connectivity or electrical qualification. A repeat is not automatically a
legal new-node envelope. Transfer the whole-group packing intent, not the
22nm dimensions, bit widths, rule exemptions or transistor scaling.
