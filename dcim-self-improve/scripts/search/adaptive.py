"""Local ALNS-inspired policies. Algorithm reference: N-Wouda/ALNS docs 7.0.0.

No upstream package/code is imported or copied. Placement neighborhoods and bounded
repair below use this framework's evaluator, budgets and frozen-instance contract.
"""
from .model import dimensions, rank
from .operators import movable, snapped, reinsert

DESTROY = ('random','related','edge')
REPAIR = ('sampled','greedy')


class Selection:
    def __init__(self, decay):
        self.decay=decay
        self.weights={d+':'+r:1.0 for d in DESTROY for r in REPAIR}
        self.counts={k:0 for k in self.weights}
        self.rewards={k:0.0 for k in self.weights}

    def choose(self,rng):
        keys=list(self.weights)
        key=rng.choices(keys,weights=[self.weights[k] for k in keys])[0]
        return key.split(':')

    def update(self,d,r,reward):
        key=d+':'+r
        self.weights[key]=max(.1,self.decay*self.weights[key]+(1-self.decay)*reward)
        self.counts[key]+=1
        self.rewards[key]+=reward

    def result(self):
        return {'pair_weights':self.weights,'pair_uses':self.counts,'pair_rewards':self.rewards,
                'rule':'decayed outcome reward with positive exploration floor',
                'reference':'N-Wouda/ALNS 7.0.0 operator-selection documentation; local implementation'}


def destroy_members(problem,state,kind,size,rng):
    ids=movable(problem); size=min(size,len(ids))
    if kind=='random':
        return rng.sample(ids,size)
    if kind=='edge':
        def reach(i):
            w,h=dimensions(problem['blocks'][i],state[i][2])
            return (state[i][0]+w)/problem['max_width_um']+(state[i][1]+h)/problem['max_height_um']
        return sorted(ids,key=reach,reverse=True)[:size]
    seed=rng.choice(ids)
    related={n for net in problem.get('nets',[]) if problem['blocks'][seed]['id'] in net for n in net}
    x,y,_=state[seed]
    return sorted(ids,key=lambda i:(i!=seed,problem['blocks'][i]['id'] not in related,
                                    abs(state[i][0]-x)+abs(state[i][1]-y)))[:size]


def insertion_states(problem,state,index,limit,rng):
    """Bounded anchor enumeration including touching-gap alignments and orientations."""
    b=problem['blocks'][index]; gap=problem['gap_um']
    candidates={tuple(state)}
    for angle in b.get('orientations',[0]):
        w,h=dimensions(b,angle)
        anchors={(0,0),(state[index][0],state[index][1])}
        for j,(x,y,a) in enumerate(state):
            if j==index: continue
            ow,oh=dimensions(problem['blocks'][j],a)
            anchors.update(((x+ow+gap,y),(x,y+oh+gap),(max(0,x-w-gap),y),
                            (x,max(0,y-h-gap)),(x+ow+gap,0),(0,y+oh+gap)))
        for x,y in anchors:
            x,y=snapped(problem,x),snapped(problem,y)
            if x+w>problem['max_width_um']+1e-9 or y+h>problem['max_height_um']+1e-9:
                continue
            trial=list(state); trial[index]=(x,y,angle); candidates.add(tuple(trial))
    # Ranking anchors is cheap geometry ordering, not an uncounted call to the objective.
    def extent(key):
        return max(x+dimensions(b,a)[0] for b,(x,y,a) in zip(problem['blocks'],key))*\
               max(y+dimensions(b,a)[1] for b,(x,y,a) in zip(problem['blocks'],key))
    ordered=sorted(candidates,key=lambda key:(extent(key),key))
    elite=ordered[:max(1,limit//2)]
    remaining=[k for k in ordered if k not in elite]
    return elite+rng.sample(remaining,min(limit-len(elite),len(remaining)))


def repair(problem,current,members,kind,measure,rng,candidates,beam,destroy):
    parameters={'destroy':destroy,'repair':kind,'instances':[problem['blocks'][i]['id'] for i in members]}
    if kind=='sampled':
        key=current['state']
        for i in members: key=reinsert(problem,key,i,rng)
        item,cached=measure(key,current['id'],'adaptive_sampled',parameters)
        return item,cached,parameters
    pool=[current]
    cached_by_id={}
    for index in members:
        expanded={}
        cached_by_id={}
        for parent in pool:
            for key in insertion_states(problem,parent['state'],index,candidates,rng):
                item,cached=measure(key,parent['id'],'adaptive_repair',dict(parameters,repair_instance=problem['blocks'][index]['id']))
                expanded[item['id']]=item
                cached_by_id[item['id']]=cached
        pool=sorted(expanded.values(),key=rank)[:beam]
    return pool[0],cached_by_id[pool[0]['id']],parameters
