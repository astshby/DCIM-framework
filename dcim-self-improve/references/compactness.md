# Rule-Compact Construction and Stage Acceptance

## Start with constraints

Before a physical stage, review the relevant target-node reference and actual
applicable DRC rules. For this run that includes the 12nm SRAM compiler as
SRAM/reference evidence, not permission to transfer its device-domain rules
or marker exemptions to custom arithmetic. Review every reused result.
Create/update the independent circuit/netlist and functional baseline before
layout. Detailed OA schematics are optional in this area-first DCIM campaign;
do not delay physical exploration for drawing/native-export polish. Record
a small geometry contract in the task/result:

- Corresponding parent/group, measured height/width band and alignment origin.
- Independent function/topology, fixed versus adjustable W/L/fin counts,
  legal device options/grid/orientation, required pin access and loads.
- Hard height and width bounds, alignment and interfaces, distinguished from
  the dimension being minimized. For example minimize routed width within
  the SRAM-height band, or fit decoder width while minimizing height.
  Name a genuinely unknown bound and how it will be established; never
  invent it or silently trade excess height/width for a lower area.
- Timing feasibility: applicable parent/path budget, input slew/source,
  output fanout/load and corner. Use existing target evidence; do not invent
  leaf budgets or equate late functional sample success with timing closure.
- Referenced rule IDs/deck locations and measured limiting shapes/pitches.
  Distinguish exact rule bounds from engineering allowance or unproved gaps.

Use Python to construct a rule-compact first candidate using these constraints:
pack on legal device/routing grids, account for enclosure/spacing, carry and
pin escape, required taps, termination and supplies. Do not start with arbitrary
large gaps and call a passing DRC compact. Do not uniformly scale geometry,
change transistor sizing silently, hide routes outside the measured boundary,
or replace original foundry checks with Python's simplified rule model.
Do not carry conservative schematic W/L or fin counts forward as an implicit
physical constraint. Review legal compact device choices against model and
reference evidence; use only the drive required by the specified function,
load and timing. Sizing changes are permitted within the task's declared
degrees of freedom, with independent source parameters and layout kept in
sync and affected electrical checks rerun. An unchanged truth table alone
does not establish electrical equivalence after resizing. Original standard
cell GDS is not resized by geometric scaling.
Use reviewed standard-cell topology/density/timing as a reference or candidate
where useful. Original SPICE, GDS, LEF and timing views support different
claims; no library marker exemptions may migrate to custom geometry. Actual
parent routes, taps, supply/context and access determine the area objective.

## Parent-constrained arithmetic

Derive the required adder hierarchy and operand/result widths from the target
channel configuration, actual connectivity, operand representation and
independent circuit/function specification. Record that derivation before
choosing an implementation. Bit counts mentioned as alignment examples are
not fixed topology, operand-width or output-width requirements.
Map the complete required multibit adder and its associated LRCC/multiply set
to the corresponding four-SRAM group(s). Their **combined physical
organization** shares one measured group-height/alignment band while width is
minimized. Use its available device region for vertical packing and folding;
bind the group's vertical origin and corresponding lower/upper functional
row bands so "aligned" is not reduced to merely staying below an H ceiling.
Do not optimize one isolated FA/adder against the ceiling and append LRCC
later with its own height allowance. Multiple independent source groups may
be side by side, not silently collapsed to one operand or stacked to gain H.
Wider arithmetic does not automatically receive extra height.

Record functional devices/bit-slice row and column placements, their upstream
SRAM/LRCC access correspondence, and actual carry/sign/tap/body/PG/escape
geometry. Distinguish functional placement height, OD/PO spans (which can
include taps/dummy), route/PG envelope and all-mask bbox. No invented density
percentage follows from a bbox span. Show actual device masks at a common
scale with the SRAM group when diagnosing height use.
For an unchanged functional topology and comparison boundary, functional
MOS count divided by actual routed area may supplement width as a density
diagnostic; count dummy/tap separately. Do not reward added transistors or
substitute this metric for correctness, timing or minimum width.

Merely keeping a one-row device strip below the ceiling while routing/PG
occupies the rest does not demonstrate matching or density improvement.
Do not manufacture apparent alignment with padding, dummy fill or tall
access routes. Primitive bboxes need not be equal, nor must every FA or LRCC
individually fill the group height. Judge a legal vertical/folded organization
by the whole connected block's measured routed width/area and electrical
behavior; report any untested packing freedom explicitly.

Bind the numerical band and origin to the accepted geometry evidence in the
current task, not a dimension embedded in this reusable skill. A conservative
group-repeat witness is not extra usable arithmetic height.
Later stages must recheck their corresponding hierarchy and actual interfaces;
do not silently multiply the height by bitwidth or reuse a different group's
envelope. If evidence shows the four-SRAM grouping or band is unsuitable,
Analyst reports limiting rules/shapes and measured alternatives to the user
before changing this agreed target, rather than silently relaxing it.

## Validate compactness, not just legality

Keep a working qualified candidate. Reject violations of hard H/W/interface
constraints before area ranking; a smaller area with the wrong shape is not
an improvement. Measure actual all-mask/routed W/H/area
and legal repeat pitch separately, including owned context and external escape.
Run original DRC and independent LVS; add the required electrical/PEX/post
checks to the selected candidate, not to obviously invalid shrink probes.

Try a meaningful tighter placement/routing variant where a plausible degree
of freedom remains. These local parameter probes stay within one bounded
Builder action; they are not new structural routes or new agents per step.
Use measured rule/geometry evidence to choose the probe, not blind uniform
shrink or an assumed monotonic binary search. A failed probe may motivate
another legal ordering/router, not a proof that all layouts are impossible.
If no tighter probe is meaningful, give the explicit rule/grid lower-bound
argument or diagnostic limitation, rather than inventing a trial.

At each physical stage's final review, Builder supplies and Analyst summarizes:

| Candidate / changed parameter | Actual W/H/area; repeat pitch if relevant | DRC / LVS | Required electrical scope | Limiter / evidence |
| --- | --- | --- | --- | --- |

Include the current smallest verified dimensions, comparison boundary and
qualification scope; the tighter candidates actually tried and their outcomes;
remaining untested space; and why to stop, change structure or compose.
For group-height arithmetic, explicitly review the combined LRCC/complete
adder functional placement, not just its maximum Y; a gap-only neighbor shrink
does not test internal packing. An isolated passing adder is a reusable
subresult, not acceptance of the whole height-matched compute organization.
Separate smallest physically verified from smallest fully qualified when they
differ. Do not rank different boundary/load/sizing scopes as like-for-like.
If none passed, say no verified minimum exists and report the measured failure.
If no tighter trial occurred, say so and leave compactness unqualified; other
accepted scopes may advance provisionally with that gap explicit.

Do not require a global optimum before useful parent composition. Claim a
local parameter limit only with supporting bounds/probes, never a global
optimum from DRC zero. Preserve existing evidence; do not retroactively claim
that older accepted stages satisfied this newly requested compactness review.
