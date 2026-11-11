"""Executable relative scopes over one retained leaf circuit; geometry-only backend."""
import copy
from runtime import atomic, artifact, evidence, event, identity, read, require, transaction
from search.model import evaluate, state_from_placements, number

SCHEMA = 'hierarchical-placement-v1'
OPERATIONS = ('refine', 'compose', 'translate')
NODE_FIELDS = {'id', 'origin_um', 'children', 'ports'}
LEAF_FIELDS = {'id', 'origin_um', 'source', 'cell', 'width_um', 'height_um', 'ports'}

def exact(obj, required, label):
    require(isinstance(obj, dict) and set(obj) == set(required), 'Invalid '+label+' fields')

def validate(tree, problem):
    exact(tree, ('schema','goal','root','nodes','frontier','must','claims'), 'hierarchy')
    require(tree['schema']==SCHEMA and tree['goal'] in ('sram','dcim'), 'Unknown hierarchy schema/goal')
    require(isinstance(tree['nodes'],list) and 1<=len(tree['nodes'])<=128, 'Bounded hierarchy nodes required')
    nodes={}
    for n in tree['nodes']:
        exact(n, NODE_FIELDS if 'children' in n else LEAF_FIELDS, 'hierarchy node')
        key=n['id']; require(isinstance(key,str) and key and key not in nodes, 'Duplicate hierarchy ID')
        require(isinstance(n['origin_um'],list) and len(n['origin_um'])==2, 'Translation must have two coordinates')
        for x in n['origin_um']:
            require(type(x) in (int,float) and __import__('math').isfinite(x), 'Finite local translation required')
        require(isinstance(n['ports'],dict), 'Explicit port mapping required')
        nodes[key]=n
    require(tree['root'] in nodes and 'children' in nodes[tree['root']], 'Group root required')
    parents={}; visited=set()
    def visit(key, stack):
        require(key in nodes and key not in stack, 'Missing child or hierarchy cycle')
        require(key not in visited, 'Multiply parented hierarchy object')
        visited.add(key); n=nodes[key]
        if 'children' in n:
            cs=n['children'];require(isinstance(cs,list) and cs and len(cs)==len(set(cs)), 'Unique nonempty children required')
            for c in cs:
                parents[c]=key;visit(c,stack+[key])
            aliases=[]
            for port,ref in n['ports'].items():
                require(isinstance(port,str) and port.strip(), 'Group port name must be a nonempty string')
                exact(ref,('object','port'),'group endpoint')
                aliases.append((ref['object'],ref['port']))
                require(ref['object'] in cs and ref['port'] in nodes[ref['object']]['ports'], 'Port must map to immediate child endpoint')
            require(len(aliases)==len(set(aliases)), 'Group ports alias the same child terminal')
        else:
            for port,ref in n['ports'].items():
                exact(ref,('net','xy_um'),'leaf endpoint')
                require(isinstance(port,str) and port and isinstance(ref['net'],str) and ref['net'], 'Leaf endpoint identity required')
                require(isinstance(ref['xy_um'],list) and len(ref['xy_um'])==2, 'Local pin anchor required')
                for axis,x in enumerate(ref['xy_um']):
                    number(x,'pin coordinate');require(x<=n['width_um' if axis==0 else 'height_um'],'Pin outside retained leaf')
    visit(tree['root'],[])
    require(visited==set(nodes), 'Disconnected hierarchy object')
    blocks={b['id']:b for b in problem['blocks']}
    leaves={k:n for k,n in nodes.items() if 'children' not in n}
    require(set(leaves)==set(blocks), 'Hierarchy must retain every actual leaf')
    for key,n in leaves.items():
        require(all(n[k]==blocks[key][k] for k in ('source','cell','width_um','height_um')), 'Hierarchy leaf/master identity mismatch')
        require(blocks[key].get('orientations',[0])==[0], 'Hierarchy backend supports translation only')
    netowners={}
    for key,n in leaves.items():
        for ref in n['ports'].values():netowners.setdefault(ref['net'],set()).add(key)
    require(all(set(net) in list(netowners.values()) for net in problem.get('nets',[])), 'Hierarchy endpoints do not cover declared block net incidence')
    frontier=tree['frontier']
    require(isinstance(frontier,list) and len(frontier)==len(set(frontier)) and set(frontier)<=set(nodes), 'Invalid hierarchy frontier')
    def desc(k):
        return {k} if 'children' not in nodes[k] else set().union(*(desc(c) for c in nodes[k]['children']))
    def endpoint_net(k,port):
        ref=nodes[k]['ports'][port]
        return endpoint_net(ref['object'],ref['port']) if 'children' in nodes[k] else ref['net']
    all_endpoints={}
    for key,n in leaves.items():
        for port,ref in n['ports'].items():all_endpoints.setdefault(ref['net'],[]).append((key,port))
    for key,n in nodes.items():
        if 'children' not in n:continue
        inside=desc(key)
        boundary={net for net,ends in all_endpoints.items()
                  if any(k in inside for k,p in ends) and
                  (len(ends)==1 or any(k not in inside for k,p in ends))}
        exposed={endpoint_net(key,port) for port in n['ports']}
        require(boundary<=exposed, 'Group interface hides a boundary net')
    sets=[desc(k) for k in frontier]
    require(set().union(*sets)==set(leaves) and sum(len(x) for x in sets)==len(leaves), 'Frontier must partition all leaf objects')
    all_record_ids=set()
    for family in ('must','claims'):
        require(isinstance(tree[family],list), 'Explicit '+family+' records required')
        ids=set()
        for record in tree[family]:
            exact(record,('id','owner','depends_on','checks','status','evidence'),family+' record')
            require(isinstance(record['id'],str) and record['id'] and record['id'] not in ids, 'Duplicate condition ID')
            require(record['id'] not in all_record_ids, 'Condition IDs must be globally unique')
            ids.add(record['id']);all_record_ids.add(record['id'])
            require(record['owner'] in nodes and isinstance(record['depends_on'],list) and record['depends_on'] and set(record['depends_on'])<=set(nodes), 'Unknown condition dependency')
            require(isinstance(record['checks'],list) and record['checks'] and all(isinstance(x,str) and x for x in record['checks']), 'Required checks cannot be empty')
            require(record['status'] in ('passed','failed','unknown','stale'), 'Invalid condition evidence status')
            require(isinstance(record['evidence'],list) and all(isinstance(x,str) for x in record['evidence']), 'Evidence IDs required')
            require(record['status']!='passed' or record['evidence'], 'Passed evidence requires immutable evidence IDs')
    require(tree['must'], 'MUST obligations required')
    return nodes, parents, desc

def circuit_identity(tree):
    # All master, endpoint and parent/child identities remain; pose/view/evidence may change.
    return identity({'goal':tree['goal'],'root':tree['root'],'nodes':[
        {k:v for k,v in n.items() if k!='origin_um'} for n in sorted(tree['nodes'],key=lambda n:n['id'])],
        'must':[{k:v for k,v in x.items() if k not in ('status','evidence')} for x in tree['must']],
        'claims':[{k:v for k,v in x.items() if k not in ('status','evidence')} for x in tree['claims']]})

def flatten(tree, problem):
    nodes,parents,desc=validate(tree,problem);out=[]
    def walk(key,xy):
        n=nodes[key]; pos=[xy[i]+n['origin_um'][i] for i in range(2)]
        if 'children' in n:
            for c in n['children']:walk(c,pos)
        else:
            out.append(dict(id=key,source=n['source'],cell=n['cell'],width_um=n['width_um'],
                height_um=n['height_um'],x_um=pos[0],y_um=pos[1],rotation_deg=0))
    walk(tree['root'],[0,0])
    state=state_from_placements(problem,out)
    return evaluate(problem,state)['placements']

def interfaces(tree, problem):
    nodes,parents,desc=validate(tree,problem);origins={}
    def origin(k):
        if k not in origins:
            parent=origin(parents[k]) if k in parents else [0,0]
            origins[k]=[parent[i]+nodes[k]['origin_um'][i] for i in range(2)]
        return origins[k]
    def resolve(k,port):
        n=nodes[k];ref=n['ports'][port]
        if 'children' in n:return resolve(ref['object'],ref['port'])
        return {'leaf':k,'port':port,'net':ref['net'],'xy_um':[origin(k)[i]+ref['xy_um'][i] for i in range(2)]}
    return {k:{port:resolve(k,port) for port in n['ports']} for k,n in nodes.items()}

def decode(tree, problem, decision):
    exact(decision,('goal','scope','region','actions','frozen','algorithm','budget','decisive_checks'), 'scope decision')
    require(decision['goal']==tree['goal'] and decision['scope'] in ('fine','coarse','joint'), 'Scope cannot replace complete module goal')
    require(decision['algorithm']=='explicit_actions', 'Only explicit_actions is executed by the scope decoder')
    exact(decision['budget'],('actions',),'scope budget')
    require(type(decision['budget']['actions']) is int and 1<=decision['budget']['actions']<=64, 'Bounded action count required')
    require(isinstance(decision['actions'],list) and 1<=len(decision['actions'])<=decision['budget']['actions'], 'Action budget exceeded')
    nodes,parents,desc=validate(tree,problem)
    require(decision['region'] in nodes, 'Unknown editable region')
    require(isinstance(decision['frozen'],list) and len(decision['frozen'])==len(set(decision['frozen'])) and set(decision['frozen'])<=set(nodes), 'Unknown frozen object')
    required=sorted(set(c for r in tree['must'] for c in r['checks']))
    require(isinstance(decision['decisive_checks'],list) and set(required)<=set(decision['decisive_checks']), 'MUST checks cannot be dropped')
    result=copy.deepcopy(tree);nn={n['id']:n for n in result['nodes']}
    changed=set();moved=set()
    for action in decision['actions']:
        require(isinstance(action,dict) and action.get('operation') in OPERATIONS, 'Unsupported hierarchy operation')
        op=action['operation'];target=action.get('object')
        exact(action,('operation','object','delta_um') if op=='translate' else ('operation','object'), 'hierarchy action')
        require(target in nodes and desc(target)<=desc(decision['region']), 'Action outside selected region')
        if op=='translate':
            require(target in result['frontier'], 'Translate an active frontier object; refine first')
            is_group='children' in nodes[target];scope='coarse' if is_group else 'fine'
            require(decision['scope'] in (scope,'joint'), 'Action granularity differs from decision')
            require(not any(desc(target)&desc(k) for k in moved), 'Overlapping ancestor/descendant moves require separate decisions')
            require(not any(desc(target)&desc(k) for k in decision['frozen']), 'Frozen object would move')
            delta=action['delta_um'];require(isinstance(delta,list) and len(delta)==2,'Two translation components required')
            for x in delta:require(type(x) in (int,float) and __import__('math').isfinite(x),'Finite delta required')
            nn[target]['origin_um']=[nn[target]['origin_um'][i]+delta[i] for i in range(2)]
            moved.add(target)
            if any(x!=0 for x in delta):changed.update(desc(target))
        else:
            require('children' in nodes[target], 'View operation requires a group')
            under=set(k for k in result['frontier'] if desc(k)<=desc(target))
            if op=='refine':
                require(decision['scope'] in ('fine','joint'), 'Refinement requires fine or joint scope')
                require(target in result['frontier'], 'Refine an active group')
                result['frontier']=[x for x in result['frontier'] if x!=target]+nn[target]['children']
            else:
                require(decision['scope'] in ('coarse','joint'), 'Composition requires coarse or joint scope')
                require(under and set().union(*(desc(k) for k in under))==desc(target), 'Compose requires the full child frontier')
                result['frontier']=[x for x in result['frontier'] if x not in under]+[target]
    before=flatten(tree,problem);after=flatten(result,problem)
    baseline=state_from_placements(problem,before);pose=state_from_placements(problem,after)
    measurement=evaluate(problem,pose,baseline)
    require(measurement['feasible'], 'Hierarchy action violates retained placement/MUST geometry')
    require(circuit_identity(tree)==circuit_identity(result), 'Circuit or obligation identity changed')
    # Actual source-net incidence expands geometric changes to remote endpoints.
    changed_nets={ref['net'] for key in changed for ref in nodes[key]['ports'].values()}
    connected={key for key,n in nodes.items() if 'children' not in n and
               any(ref['net'] in changed_nets for ref in n['ports'].values())}
    affected=set(changed)|connected
    for key in list(affected):
        while key in parents:key=parents[key];affected.add(key)
    invalid=[]
    for family in ('must','claims'):
        for record in result[family]:
            # Unknown geometric/routing influence: every pose-dependent record is conservatively stale.
            deps=set().union(*(desc(k) for k in record['depends_on']))
            # Only these declared local proofs have bounded geometric influence.
            # Every other check, including unknown/custom semantics, is conservative.
            local_checks={'geometry','leaf_identity','relative_transforms','pin_anchor_mapping'}
            if changed and (deps & changed or record['owner'] in affected or
                            not set(record['checks'])<=local_checks):
                record['status']='stale';record['evidence']=[];invalid.append(record['id'])
    required=sorted(set(required)|{c for f in ('must','claims') for record in result[f] if record['id'] in invalid for c in record['checks']})
    require(set(required)<=set(decision['decisive_checks']), 'Decisive checks omit invalidated evidence requirements')
    validate(result,problem)
    return result,measurement,{'changed_leaves':sorted(changed),'affected_objects':sorted(affected),'changed_nets':sorted(changed_nets),'connected_leaves':sorted(connected),
        'invalidated_records':sorted(invalid),'required_checks':required,'circuit_identity':circuit_identity(result),
        'interfaces_before':interfaces(tree,problem),'interfaces_after':interfaces(result,problem),
        'qualification':'declared pin-anchor geometry only; physical evidence not generated'}

def apply_review(tree, review):
    updated=copy.deepcopy(tree)
    records=review.get('hierarchy_checks',{})
    for family in ('must','claims'):
        for record in updated[family]:
            if record['id'] in records:
                check=records[record['id']]
                record['status']={'passed':'passed','failed':'failed','incomplete':'unknown'}[check['status']]
                record['evidence']=check['evidence']
    return updated

def review_records(root,state,payload):
    route=state['routes'].get((state.get('task') or {}).get('route'),{})
    physical=(state.get('task') or {}).get('execution')=='physical_adapter' and bool(route.get('hierarchy',{}).get('physical'))
    if physical:
        from physical_builder import contract as physical_contract
        physical_contract(root,state,state['task'])
        candidate=state.get('last_result',{}).get('baseline_candidate')
        require(candidate,'Physical hierarchy review needs actual candidate')
        evidence(root,state,[candidate]);manifest=read(root/state['artifacts'][candidate]['object'])
        require(manifest.get('physical_hierarchy')=='physical-hierarchy-consumer-v1','Physical hierarchy output not finalized')
    if route.get('hierarchy') and not physical:
        # This materializer draws retained geometry only. Reviewer testimony cannot
        # convert its output into physical/electrical verification.
        allowed={'geometry','hierarchy_identity','interface','pin_anchor_mapping',
                 'leaf_identity','constraint_inheritance','scope_consumption',
                 'evidence_invalidation','relative_transforms'}
        require(all(status!='passed' or check in allowed
                    for check,status in payload['checks'].items()),
                'Hierarchy geometry backend cannot pass physical or electrical checks')
    records=payload.get('hierarchy_checks')
    if records is None:return
    require(isinstance(records,dict), 'Hierarchy review must map record IDs')
    candidate=state.get('last_result',{}).get('baseline_candidate')
    require(candidate,'Hierarchy review requires an actual baseline candidate')
    manifest=read(root/state['artifacts'][candidate]['object'])
    require('hierarchy_state.json' in manifest['files'],'Candidate lacks hierarchy state')
    key=manifest['files']['hierarchy_state.json'];evidence(root,state,[key])
    tree=read(root/state['artifacts'][key]['object'])
    definitions={r['id']:r for f in ('must','claims') for r in tree[f]}
    require(set(records)<=set(definitions),'Unknown hierarchy reviewed record')
    for key,check in records.items():
        exact(check,('status','evidence'),'hierarchy review')
        require(check['status'] in ('passed','failed','incomplete'),'Invalid hierarchy review status')
        require(isinstance(check['evidence'],list) and check['evidence'] and
                set(check['evidence'])<=set(payload['evidence']), 'Hierarchy recheck evidence must be reviewed')
        evidence(root,state,check['evidence'])
        require(all(state['artifacts'][e]['round']==state['round'] for e in check['evidence']), 'Recheck needs current-round evidence')
        statuses=[payload['checks'].get(c) for c in definitions[key]['checks']]
        require(check['status']!='passed' or all(s=='passed' for s in statuses),'Cannot restore a missing or failed MUST check')
        require(check['status']!='failed' or 'failed' in statuses,'Failed record needs failed required check')
    return tree

def plan(run, hierarchy_artifact, decision):
    """Execute Reflect's scoped decoder before freezing its ordinary request."""
    from search.baseline import previous
    with transaction(run) as (root,state):
        require(state['phase'] in ('learning','awaiting_reflect') and 'reflect-'+str(state['round']) not in state['requests'], 'Scope planning belongs before Reflect request')
        evidence(root,state,[hierarchy_artifact]);tree=read(root/state['artifacts'][hierarchy_artifact]['object']);physical=None
        if state['round']:
            snapshot,origin=previous(root,state)
            require('hierarchy' in snapshot, 'Previous actual candidate has no hierarchy decoder state')
            require(hierarchy_artifact==snapshot['hierarchy_artifact'], 'Hierarchy artifact must be from immediately previous candidate')
            require(tree==snapshot['hierarchy'], 'Scope must use immediately previous actual hierarchy')
            problem=snapshot['problem'];before=snapshot['placements'];physical=snapshot.get('physical')
        elif 'physical_initial' in state:
            binding=state['physical_initial'];evidence(root,state,[binding['descriptor'],binding['measurement']])
            descriptor=read(root/state['artifacts'][binding['descriptor']]['object'])
            require(tree==descriptor['hierarchy'],'Initial physical hierarchy differs from measured source')
            from physical_scope import measure
            outputs={k:root/state['artifacts'][v]['object'] for k,v in descriptor['outputs'].items()}
            measured,_=measure(root,descriptor['consumer'],descriptor['problem'],tree,outputs)
            problem=descriptor['problem'];before=measured['placements'];physical=descriptor
            origin={'kind':'actual_physical_initialization','round':0,'artifact':binding['descriptor'],
                    'measurement':binding['measurement'],'output_sha256':measured['output_sha256']}
        else:
            # Initial hierarchy explicitly binds the reference search snapshot.
            require('initial_search' in state, 'Capture initial flat reference plan first with bind_initial')
            base=state['initial_search'];evidence(root,state,[base])
            search=read(root/state['artifacts'][base]['object']);problem=search['problem']
            before=flatten(tree,problem);origin=search['baseline']
            require(state_from_placements(problem,before)==tuple(tuple(x) for x in search['baseline_evaluation']['state']), 'Hierarchy initial pose differs from captured reference baseline')
        original=copy.deepcopy(tree);review_id=None
        if state['round']:
            review_id=state['reviews'][str(state['round'])]['id']
            evidence(root,state,[review_id]);tree=apply_review(tree,read(root/state['artifacts'][review_id]['object']))
        for family in ('must','claims'):
            for record in tree[family]:
                if record['evidence']:evidence(root,state,record['evidence'])
        after,measurement,transition=decode(tree,problem,decision)
        key='scope-search-'+identity({'tree':tree,'decision':decision,'baseline':origin,'round':state['round']})[:16]
        if key in state['artifacts']:
            evidence(root,state,[key])
            saved=read(root/state['artifacts'][key]['object'])
            return {'artifact':key,'route':key+'-scope','transition':saved['transition'],'already_recorded':True}
        prior=[e for e in state['events'] if e['operation']=='scope_plan' and e['round']==state['round']]
        require(len(prior)<8, 'Scope planning call budget exhausted')
        result={'problem':problem,'baseline':origin,'baseline_evaluation':evaluate(problem,state_from_placements(problem,before)),
            'selected':[dict(measurement,id='scope',operation='hierarchy-decode')],'hierarchy_before':tree,'hierarchy_input':original,'hierarchy_review':review_id,
            'hierarchy':after,'scope_decision':decision,'transition':transition,'hierarchy_artifact':hierarchy_artifact,
            'qualification':'physical_construction_pending' if physical else 'geometry_only'}
        if physical:result['physical']=physical
        path=root/'requests'/(key+'.json');atomic(path,result);artifact(root,state,key,path,'search')
        rid=key+'-scope';state['routes'][rid]=dict(id=rid,source='ai',lifecycle='active',evidence=[key,hierarchy_artifact],
            plan=measurement,search=key,baseline=origin,mechanism='hierarchy scoped decoder',
            status='proxy_only',round=state['round'],hierarchy=result)
        event(state,'scope_plan',{'search':key,'route':rid,'scope':decision['scope'],'transition':transition})
        return {'artifact':key,'route':rid,'transition':transition}

def bind_initial(run, search_artifact):
    with transaction(run) as (root,state):
        require(state['round']==0 and 'reflect-0' not in state['requests'], 'Initial binding before Reflect0 only')
        evidence(root,state,[search_artifact]);item=read(root/state['artifacts'][search_artifact]['object'])
        require('problem' in item and item['baseline']['round']==0,'Initial reference search required')
        state['initial_search']=search_artifact
        event(state,'hierarchy_reference_binding',{'search':search_artifact})

def admit(root,state,task,route):
    data=route.get('hierarchy')
    if not data:
        require('scope_decision' not in task, 'Scope decision has no supported decoder route')
        return
    require(task.get('scope_decision')==data['scope_decision'],'Reflect task must consume exact executable scope decision')
    require(task['module']==data['hierarchy']['goal'], 'Task cannot replace complete hierarchy goal')
    if state['round'] and state.get('task') and state['phase']=='awaiting_reflect':
        require(task['stage']==state['task']['stage'], 'Scope change cannot rewrite retrieval stage')
    if data.get('physical'):
        require(task.get('execution')=='physical_adapter','Actual physical hierarchy cannot downgrade to a geometry-only backend')
        from physical_builder import contract as physical_contract
        physical_contract(root,state,task)
    else:
        require(task.get('execution')=='geometry_only', 'Hierarchy backend currently supports geometry_only; physical decoder unavailable')
    require(set(data['transition']['required_checks'])<=set(task['checks']), 'Task dropped inherited MUST checks')
    evidence(root,state,[data['hierarchy_artifact'],route['search']])
    require(read(root/state['artifacts'][data['hierarchy_artifact']]['object'])==data['hierarchy_input'],'Hierarchy input changed')
    for family in ('must','claims'):
        for record in data['hierarchy_before'][family]:
            if record['evidence']:evidence(root,state,record['evidence'])
    effective=data['hierarchy_input']
    if data['hierarchy_review']:
        evidence(root,state,[data['hierarchy_review']]);effective=apply_review(effective,read(root/state['artifacts'][data['hierarchy_review']]['object']))
    require(effective==data['hierarchy_before'], 'Reviewed hierarchy overlay changed')
    after,measured,transition=decode(effective,data['problem'],data['scope_decision'])
    require(after==data['hierarchy'] and measured==route['plan'] and transition==data['transition'],'Scoped decoder result changed')

def retain(root,state,task,route,directory,problem,actual):
    data=route.get('hierarchy')
    if not data:return None
    admit(root,state,task,route)
    tree=data['hierarchy'];flat=flatten(tree,problem)
    require(state_from_placements(problem,flat)==state_from_placements(problem,actual),'Actual leaf geometry differs from hierarchy')
    atomic(directory/'hierarchy_state.json',tree)
    atomic(directory/'scope-transition.json',data['transition'])
    atomic(directory/'hierarchy-interfaces.json',interfaces(tree,problem))
    return tree
