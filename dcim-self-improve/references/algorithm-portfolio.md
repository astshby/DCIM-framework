# Execution and search boundaries

Five existing SciPy solver adapters are executable when SciPy is present.
CP-SAT, SMTCell/Z3 and OpenROAD entries are research references with unimplemented
encoders/evaluators/backend consumers. Installing a dependency cannot create those
interfaces. No algorithms were added by the integrated-workflow refactor.

Select operations and decoder before algorithm. Coarse reference transforms and
measured composition, pro abstract device rows, hierarchy action plans and private
physical consumers have distinct scopes. Inspect actual plan consumption and
routed outputs before attributing physical improvements. Run --catalog for the
pinned profile and executable boundary fields.

For a tiny finite decoded domain, count distinct legal states, compare a finite
enumeration oracle or bounded local choice and inspect cache/duplicate rates.
Several stochastic solver evaluations may decode to the same permutation. Fixed
outer dimensions cannot yield an area gain from internal permutation alone.
Search scores and proxy convergence do not imply qualification or global optimality.

# Source-backed algorithm portfolio

Read this when Reflect chooses a search method across fine and coarse scopes.
The existing role order remains Builder -> Analyst (review plus short memory)
-> Reflect. One Reflect may combine scopes; no mandatory dual-search stage is
introduced. Keep the complete module contract while choosing local actions.

## Actual implementation choices

`algorithm_portfolio.catalog()` reports ten options. Five have executable
adapters to existing SciPy implementations; five are research/adapter work and
cannot execute. Missing adapters raise an error, never fall back to a different
algorithm. The older in-package search methods remain available for backward
compatibility and matched comparisons, separately from this upstream portfolio.
No package was installed into the EDA Python distribution by this change.

| ID | Called upstream function | Useful scope and limitation |
| --- | --- | --- |
| scipy_de | scipy.optimize.differential_evolution | Bounded broad exploration of decoded coordinates, local parameter choices or row orders; population cost must fit the evaluation budget |
| scipy_dual_annealing | scipy.optimize.dual_annealing | Bounded global parameter exploration; all decoded candidates still use the common hard evaluator |
| scipy_basinhopping | scipy.optimize.basinhopping | Repeated local exploration of a small parameter window; this adapter uses the upstream Powell local method and shared state decoder |
| scipy_shgo | scipy.optimize.shgo | Low-dimensional comparator, restricted to at most ten variables; discrete/rank decoding voids a general global-optimum claim |
| scipy_powell | scipy.optimize.minimize(method=Powell) | Small continuous geometric parameter windows; weak choice for permutation-only plateaus |
| ortools_cp_sat | No adapter implemented | Constraint programming for a bounded, explicitly encoded geometry/routing window; not a heuristic fallback |
| smtcell_z3 | No adapter implemented | Published SMTCell/Z3 flow requires its actual input and technology model |
| openroad_hier_rtlmp | No adapter implemented | Published hierarchical macro placement requires a tool and matching design database |
| openroad_global | No adapter implemented | Large-scale global placement; its soft costs cannot replace custom hard rules |
| openroad_detailed | No adapter implemented | Row/site placement and legalization; does not establish arbitrary custom SRAM seam legality |

These are conditional choices, not a ranking. The five executable methods are
existing general optimizer implementations applied to EDA states. Calling them
is not a reproduction of ISEDA 2025, B*-tree, SMTCell or OpenROAD, nor evidence
that one algorithm is universally best. Use actual matched baseline results,
current bottleneck, representation, legal actions and evaluation expense to
choose. CPU optimization here does not launch EDA.

## Shared state codecs and hard evaluation

`solver_adapter.search(problem, budget, initial=None)` returns the existing
baseline/trials/selected/trace protocol. Its block codec varies only movable
coordinates and declared orientations; frozen instances remain exact. A supplied
grid is applied before evaluation. Its device codec uses random keys for row
permutations and explicit flip variables only where S/D swapping is authorized.
It preserves device row membership and terminal-net names. Row dimensions,
physical rules and topology are not variables in this codec.

The actual reviewed baseline is evaluated first, before any upstream solver
proposal, and is never decoded/repacked for that first measurement. Bounds can
retain an infeasible actual baseline for a repair task; only feasible evaluated
candidates are selected. Every decoded state is checked by the same coarse or
device evaluator, including the declared physical contract where supported.
The numeric solver objective orders all feasible candidates ahead of infeasible
ones; the saved score, violations and geometry remain the raw evaluator values.

Powell and local basin steps may numerically leave their variable box. The
adapter clamps variable values to the declared domain before decoding; this is
not permission to move fixed objects, clip masks or waive physical constraints.
Actual construction and independent acceptance still require their own evidence.

`solver_adapter.optimize(bounds, baseline, decoder, evaluator, budget,
initial_vector=None)` also supports a private construction adapter's explicit
parameter domain. This does not synthesize the decoder: it must be implemented,
versioned and checked. It can represent local metal endpoints, bounded block
moves or joint scope parameters while retaining the same complete-module goal.

## Budgets and provenance

Budget fields: algorithm, evaluations (1..10000), steps (1..100000), seconds
(positive and <=60), seed (integer), population (5..64), temperature, stepsize,
and local_iterations (1..1000). Unknown fields are rejected. Each objective
invocation counts as a proposal step, including cache hits. Each new decoded
state consumes one evaluation. The baseline consumes one evaluation. Repeated
states use a cache, and all measured states and proposal traces are retained.
Budget termination preserves the best measured state and an explicit reason.

Time limits are cooperatively checked at evaluation boundaries; they are not an
OS sandbox or a timeout for arbitrary EDA work. The run planner additionally
enforces its aggregate Reflect budget. SciPy package/version and adapter/codec
identities are retained; deterministic seeds do not promise identical results
across different package/platform versions.

## Primary sources and implementation provenance

- SciPy v1.4.1 optimization reference: https://docs.scipy.org/doc/scipy-1.4.1/reference/optimize.html . Existing SciPy implementation, BSD-3-Clause; no source algorithm copied into this package.
- Storn and Price (1997), differential evolution: https://docs.scipy.org/doc/scipy-1.4.1/reference/generated/scipy.optimize.differential_evolution.html . The function documentation links the published method and its implementation.
- Xiang et al. (1997) and Xiang and Gong (2000), generalized/dual annealing: https://docs.scipy.org/doc/scipy-1.4.1/reference/generated/scipy.optimize.dual_annealing.html .
- Wales and Doye (1997), basin hopping: https://docs.scipy.org/doc/scipy-1.4.1/reference/generated/scipy.optimize.basinhopping.html .
- Endres, Sandrock and Focke (2018), SHGO: https://docs.scipy.org/doc/scipy-1.4.1/reference/generated/scipy.optimize.shgo.html .
- Powell (1964), direction-set local minimization: https://docs.scipy.org/doc/scipy-1.4.1/reference/optimize.minimize-powell.html .
- Guo and Lin, Multi-Row Standard Cell Layout Synthesis with Enhanced Scalability, ISEDA 2025: https://zhywhite.github.io/paper/CELL_ISEDA2025_Guo.pdf . Connectivity clustering plus local transistor and cluster-level search motivates joint scopes; this adapter does not reproduce that flow. Its soft IO preferences must not replace required pin/track contracts.
- Wu and Chang, Placement with Alignment and Performance Constraints Using the B*-tree Representation, ICCD 2004, DOI 10.1109/ICCD.2004.1347979: https://iccd.et.tudelft.nl/Proceedings/2004/22310568.pdf . Alignment-preserving representation is a design reference; no B*-tree implementation is claimed here.
- SMTCell: https://github.com/ckchengucsd/SMTCellUCSD-MH .
- OpenROAD macro/global/detailed placement: https://openroad.readthedocs.io/en/latest/main/src/mpl/README.html ; https://openroad.readthedocs.io/en/latest/main/src/gpl/README.html ; https://openroad.readthedocs.io/en/latest/main/src/dpl/README.html .

Synthetic tests verify real upstream dispatch, baseline preservation, budgets,
source endpoint invariants and hard-candidate selection. They do not qualify a
process-specific layout, routing, DRC, LVS, body supply or electrical behavior.
