# Transistor search and full-flow planning

Read this for a `transistor_proxy` task or a staged campaign. The existing role
order is unchanged: initialize -> Reflect0 -> Builder -> independent Analyst ->
committed short memory -> Reflect. Failure, no improvement and closure still
require Reflect. Search steps are not role rounds.

## Representations and implemented scope

`planner.py` dispatches `transistor-placement-v1` problems to the bounded device
engine. Legacy rectangle problems remain supported. Device state is the order
of named transistors in declared P/N rows plus explicitly allowed S/D flips.
Neither source/drain net names nor device identity may change. Row polarity,
model, body net, height and a declared sharing group govern whether adjacent
facing nets can omit an abstract diffusion-break gap. This does not certify a
shared diffusion polygon, implant seam, well or real body contact.

The built-in `anneal` and `local` methods use adjacent swaps, reinsertion, legal
S/D flips and paired swaps in two rows. Preserve evaluation, proposal-step and
wall-clock budgets, seed, baseline and all evaluated states. The objective is
origin-anchored row/resource envelope area normalized by device area, nominal
terminal-anchor HPWL and diffusion-break count. Weights are frozen for each
search; compare the actual baseline under the same evaluator. All feasible
candidates must satisfy declared bounds and reserved-region screens.

The implementation does not synthesize a transistor topology, choose electrical
W/L, fold fingers, delete TAPs, generate foundry mask geometry or route a net.
Terminal coordinates are nominal anchors, not extracted pin polygons. Body
checks preserve declared nets only. Do not label `transistor_proxy` evidence as
DRC, source LVS, ERC, timing, functionality or complete DCIM qualification.

## Explicit input contract

Use `assets/transistor-example/` only as a SYNTHETIC numerical example, never as
a PDK or circuit recipe. Its units are micrometers but its numbers are arbitrary.
The example circuit is for permutation checks, not a qualified SRAM/logic cell.

Every key in the device problem is required and unknown fields are rejected:

- `schema`, exact `technology` (process/release/stack), and `sources` artifact IDs
  for a captured JSON netlist and declared rule contract.
- `rows`: id, pmos/nmos kind, y/height and body_net. All coordinates and sizes use
  the supplied grid. The whole row envelope remains in the area account.
- `devices`: id, row, kind, model, abstract width/height, named g/s/d/b terminals,
  explicit sd_swap permission and share_group (or null). Width is placement
  extent, not electrical transistor channel width; it never authorizes resizing.
- `rules`: diffusion_gap_um, allow_diffusion_sharing, grid_um. No inferred node
  default, PP/NP exception or generated tap coverage.
- `ports`: named nets at declared coordinates; `obstacles` and `reserved_access`
  rectangles (the latter name their intended net). Empty lists are explicit.
- `constraints`: max_width_um/max_height_um and width_strict/height_strict.
  Strict bounds reject equality; the search cannot exceed configured macro bounds.
- `objective`: wire_weight and break_weight. Missing physical metrics stay absent.

`source_payloads` defines canonical captured JSON: netlist-v1 contains technology,
devices and ports; rules-v1 contains technology, rows, rules, obstacles and reserved
access. Capture original inputs with `workflow evidence`; search compares content,
not just labels/paths. These snapshots preserve provenance but are not independent
proof that extracted inputs match silicon. Keep source extraction and checking
as separately evidenced work.

After Reflect0 the next search reloads the actual previous Builder output,
including a failed reviewed candidate with recoverable output. Only objective
and bounds may change within this representation. Changed circuit, device set,
rule contract or representation requires an explicitly linked new construction
run; it must retain parent artifacts and cannot silently reset the old run.

## Module learning

Project planning inventories compiler and digital-flow references. A module task
binds its configured reference_scope: SRAM/compiler, logic/digital_flow. A dcim
integration task binds both. Bind source observations through learning_goals;
Analyst reviews each bound goal using current output evidence. A new phase does
not reset the role-round number or drop prior baseline provenance.

## Commands and role boundary

Use the run's pinned scripts after initialization. Capture netlist and rule files:

```sh
python3 RUN/scripts/workflow.py --run RUN evidence --id synthetic-circuit --path NETLIST_JSON
python3 RUN/scripts/workflow.py --run RUN evidence --id synthetic-rules --path RULES_JSON
python3 RUN/scripts/planner.py --run RUN --problem PROBLEM_JSON --budget BUDGET_JSON
```

Capture the applicable reference layout with learn.py before Reflect0. Search
writes algorithm routes. Request an AI Reflect packet and return an actual AI
response; a deterministic demo response is a protocol fixture, not AI reasoning.
A device task uses execution=transistor_proxy and checks device_identity,
terminal_mapping and abstract_geometry. AI can submit a competing device state
as plan_spec={search: SEARCH_ID, device_state: STATE} under the same evaluator.

Builder preserves input.json, source netlist/rules, a standalone engine, build.py,
execution/outcome/logs, transistor-layout.json, placement_state.json and manifest.
It does not export a GDS for an abstract plan. Analyst reads frozen originals and
runs the independent checker (which does not import the placement evaluator):

```sh
python3 RUN/scripts/device_audit.py --input CANDIDATE/input.json --layout CANDIDATE/transistor-layout.json --netlist CANDIDATE/source-netlist.json --rules CANDIDATE/source-rules.json
```

Save the Analyst's output as evidence. Submit result, review with exact
scope=transistor_proxy, commit concise memory, then Reflect. Successful proxy
review can pass only the three implemented abstract checks. Final Reflect can
close while proposing a deferred test; it does not authorize another experiment.

## Campaign planning and gates

`campaign.py` plans enabled modules (SRAM before compute), tile, repeated tile,
and macro. It does not replace Reflect or dispatch jobs. Create a new immutable
campaign outside source using a normalized project JSON:

```sh
python3 scripts/campaign.py --root CAMPAIGN create --project PROJECT_JSON --profile abstract
python3 scripts/campaign.py --root CAMPAIGN status
python3 scripts/campaign.py --root CAMPAIGN binding --stage sram
python3 scripts/campaign.py --root CAMPAIGN accept --stage sram --run RUN --candidate CANDIDATE_ID
```

Freeze the returned campaign_binding into the Reflect task before construction.
Accepted output must come from the last reviewed round of a closed run, after
Builder, Analyst, memory and final Reflect. Required files/checks, source evidence,
project identity and parent versions are verified and copied into campaign-owned
objects. Records append; parent reselection makes dependent selections stale.
Old accepted evidence is retained. No existing run is upgraded or resumed.

`abstract` permits the implemented device module stage; connected tile/repeat/macro
remain awaiting_capability. `physical` also requires an implemented physical
construction adapter. Missing task inputs appear as awaiting_inputs, and missing
parents as awaiting_parents. Neither profile can complete a physical macro using
abstract passes. Physical gates name routed dimensions, DRC, source LVS, function
and ERC; their actual adapters/decks are future work. PEX/post-layout simulation
is not silently added. Interface identities currently hash declared contract text
and macro parameters, not external contract-file bytes or semantic equivalence.

## Evidence-driven next capabilities

First add target-native device extraction/generation and measured terminal
shapes. Validate legal diffusion/implant seams, row height, taps, boundary cells
and real body supply against the target rules. Next connect a minimal SRAM/compute
tile with pin-access and routing feedback. Add explicit topology/folding variants
only with source-netlist and functional equivalence checks. Use repeated seams
and complete parent-routed dimensions before scaling to whole-macro exploration.
Each new capability enters the same reviewed loop with versioned inputs and
negative tests; bounded search outcomes never establish global optimality.
