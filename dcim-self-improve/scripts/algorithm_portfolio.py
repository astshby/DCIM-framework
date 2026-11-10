"""Source-backed algorithm choices with truthful execution availability."""
import importlib.util

RUNNABLE = ('scipy_de', 'scipy_dual_annealing', 'scipy_basinhopping', 'scipy_shgo', 'scipy_powell')


def catalog():
    scipy_ok=importlib.util.find_spec('scipy') is not None
    version=None
    if scipy_ok:
        import scipy
        version=scipy.__version__
    base='https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.'
    records=[]
    for key,entry,method,choice,reference in [
        ('scipy_de','differential_evolution','Differential evolution','Bounded broad search; discrete decoded moves may use a population','Storn and Price, 1997'),
        ('scipy_dual_annealing','dual_annealing','Dual annealing','Bounded global exploration; compare actual legal decoded states','Xiang et al., 1997; Xiang and Gong, 2000'),
        ('scipy_basinhopping','basinhopping','Basin hopping','Local numerical parameters with repeated basin exploration','Wales and Doye, 1997'),
        ('scipy_shgo','shgo','SHGO','Low-dimensional bounded comparator; no global guarantee after discrete decoding','Endres, Sandrock and Focke, 2018'),
        ('scipy_powell','minimize','Powell direction-set local search','Small continuous parameter windows; weak fit for permutation-only plateaus','Powell, 1964')]:
        records.append(dict(id=key,name=method,implementation='scipy.optimize.'+entry,
            implementation_version=version,license='BSD-3-Clause (SciPy)',source=base+entry+'.html',
            reference=reference,status='available' if scipy_ok else 'dependency_missing',
            adapter_implemented=True,representations=['blocks','transistor','parameters'],choice=choice,
            scope='existing general optimizer applied through a shared EDA decoder/evaluator; not a paper-tool reproduction'))
    for key,name,dependency,url in [
        ('ortools_cp_sat','OR-Tools CP-SAT','ortools','https://developers.google.com/optimization/cp/cp_solver'),
        ('smtcell_z3','SMTCell / Z3','z3','https://github.com/ckchengucsd/SMTCellUCSD-MH'),
        ('openroad_hier_rtlmp','OpenROAD Hier-RTLMP','openroad','https://openroad.readthedocs.io/en/latest/main/src/mpl/README.html'),
        ('openroad_global','OpenROAD global placement','openroad','https://openroad.readthedocs.io/en/latest/main/src/gpl/README.html'),
        ('openroad_detailed','OpenROAD detailed placement','openroad','https://openroad.readthedocs.io/en/latest/main/src/dpl/README.html')]:
        records.append(dict(id=key,name=name,implementation=dependency,source=url,
            status='adapter_not_implemented',adapter_implemented=False,
            scope='research option only; cannot be selected for execution in this release'))
    return {'schema':'algorithm-portfolio-v1','options':records,
            'selectable':[r['id'] for r in records if r['status']=='available'],
            'selection':'Reflect chooses actions, scope and budget from evidence; algorithm names do not establish physical capability',
            'hard_constraints':'Every decoded candidate uses the common validator; only feasible candidates can be selected'}
