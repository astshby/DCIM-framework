# Reference intake

learn.py accepts compiler, digital_flow, circuit, native_device, composition
and standard_cell. Use the actual role. Circuit intent need not masquerade as
compiler/digital flow. --sources binds an optional JSON map of circuit, metadata
and rules files. circuit/native_device require independent circuit sources.
Circuit-only intake omits --layout and retains --top and declared observation.
It captures source text and never claims circuit parsing or connectivity checks.

Context binds module, process, release, stack, source_run, purpose and observation.
New source roles require explicit purpose and observation. purpose is
implementation, circuit_intent or organization_only. Layout observations bind the
exact bytes and top, hierarchy, placements, pin labels and envelope. Every source
dependency has a retained artifact and SHA-256. Changed bytes create a new entry.
Cross-node organization_only sources may inform general organization hypotheses.
They cannot supply implementation geometry or process-specific learning goals.

Private inputs resolve through configuration and task evidence. No private node
recipes or author paths are distributed. Independent circuit intent, native device
geometry and full parent composition play distinct roles. Their availability does
not establish electrical models, physical qualification or accepted reuse rights.

# Inputs and provenance

The generic configuration, module contract, history and geometry helpers derive
from improve 1. Evidence parsing and stage/route retrieval principles derive from
improve 2. The fixed 12FFC seed was removed from the active tree; its prior version
remains in repository Git. Neither reference directory is modified or synchronized.

Agents create private configuration with `configure.py`, optionally --from-config.
Paths resolve against the configuration file. Project precision, ratio accounting,
process/release/stack and electrical conditions remain explicit. Existing configs
using project/input_files are supported; old native12/warm-start keys need deliberate
migration, not silent reuse. No node-specific compiler filenames are prescribed.

`learn.py` accepts captured geometry JSON or GDS (optional gdspy). Context identifies
module/process/release/stack/source_run. Keep reference-only observations distinct
from qualified implementation. Proprietary inputs stay outside the package.


## Method references used in this framework

| Source | Reusable content | Boundary |
| --- | --- | --- |
| improve 1 | Config, history, geometry helpers | No inherited process defaults |
| improve 2, experience-memory/compactness/analyst references | Scoped retrieval; concise conditional claims; supersession; complete-parent and independent checks | No new per-round diary or Analyst-owned mandatory idea |
| Legacy tsmc22nm-dcim_start knowledge/general and decisions | Repeated-seam tests; parent connectivity; local neighbor context; capacity/bandwidth accounting; raw-output retention | No fixed capacity, dimensions, rule decks, topology, PEX waiver or job permissions |

Legacy source topics include precompaction-lessons, local-route-repair-neighbor-context,
output-inactivity-and-removal, source-interface-and-integrated-routing037,
primitive-screen-does-not-compose039, raw-prefix-retention-guard033,
storage-bandwidth-and-locality035 and decisions 025/031. These are historical
observations, not present framework instructions. Extracted methods live in the
role references. Source snapshots/hashes and developer rationale stay in the
private workspace audit referenced by HANDOFF.md; proprietary material is not
copied into this package. General methods must be revalidated for new conditions.

## Open-source algorithm research

- [N-Wouda/ALNS](https://github.com/N-Wouda/ALNS), MIT license;
  [operator selection, documentation 7.0.0](https://alns.readthedocs.io/en/latest/api/select.html)
  and [acceptance criteria](https://alns.readthedocs.io/en/latest/api/accept.html).
  The adaptive strategy borrows the destroy/repair, outcome reward and decayed
  selection ideas. This repository contains its OWN standard-library placement
  implementation; no ALNS code is copied, vendored, imported or installed. Local
  choices differ: six pair weights with a positive floor, complete-state bounded
  repair, framework evaluation accounting and frozen-instance enforcement.
- [SciPy differential evolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html)
  and [dual annealing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html)
  were compared as generic numerical search options. They are not integrated.
  The current discrete coordinate and repair contract motivated choosing ALNS-style
  neighborhoods first; this is a task-fit decision, not a performance ranking.
- [Google OR-Tools](https://github.com/google/or-tools) was examined as a future
  constraint-solver option, not a heuristic library installed by this release.
  No CP-SAT adapter or certified optimal placement is implemented.

Search remains cheap module geometry/center-wire estimation. External standard-cell
placement/routing engines require explicit adapters and authorized validation.

## Device-granularity planning sources (2026-11-09)

- *BonnCell: Automatic Cell Layout in the 7-nm Era* (author-hosted report accompanying the TCAD 2020 paper): https://www.or.uni-bonn.de/~hougardy/paper/7nmBonnCell_OR_Report.pdf . Detailed transistor placement and cell routing motivate separating legal construction from route quality. No BonnCell source/PDK or claimed reproduction is included.
- Haoxing Ren, Matthew Fojtik, Brucek Khailany. *NVCell: Standard Cell Layout in Advanced Technology Nodes with Reinforcement Learning* (2021): https://arxiv.org/abs/2107.07044 ; author preprint https://d1qx31qr3h6wln.cloudfront.net/publications/NVCell_preprint.pdf . SA placement and routing feedback motivate the device neighborhood; its RL/router and performance claims are not reproduced.
- D. Lee, D. Park, C.-T. Ho, I. Kang, H. Kim, S. Gao, B. Lin, C.-K. Cheng. *SP&R: SMT-based Simultaneous Place-and-Route for Standard Cell Synthesis of Advanced Nodes*, ICCAD 2020, DOI 10.1145/3400302.3415692. Author project https://github.com/ckchengucsd/SMTCell . Constraint-centric joint placement/routing is a future comparator; no SMT/Z3 solver is integrated.
- OpenROAD detailed placement and global routing documentation: https://openroad.readthedocs.io/en/latest/main/src/dpl/README.html and https://openroad.readthedocs.io/en/latest/main/src/grt/README.html . Placement padding and routing-resource derating show why required access/resource regions must survive compaction. No OpenROAD adapter is installed by this change.

The new transistor_search.py is an original standard-library implementation of bounded simulated annealing and local search with declared-net diffusion-break predicates. It implements neither a published complete tool nor a process-qualified layout algorithm. Results from synthetic fixtures cannot be compared with paper PPA numbers.

For the runnable upstream optimizer portfolio, exact software versions and explicitly unavailable EDA engines, see [algorithm-portfolio.md](algorithm-portfolio.md). The general transferable experience from the private22nm experiments is in [two-scale.md](two-scale.md); no node recipe or inherited qualification is included here.
