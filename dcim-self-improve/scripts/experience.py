"""Publish reviewed lessons as immutable bundles; pin external methods without transferring passes."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import tempfile
from dcim_config import digest, is_within, load_config
from runtime import atomic, cli, evidence, identity, read, require, transaction
from memory import TEXT_FIELDS, MAX_TEXT

SCHEMA='reviewed-experience-v1'


def references(value, artifacts):
    if isinstance(value,str):
        return {value} if value in artifacts else set()
    if isinstance(value,dict):
        value=list(value.values())
    if isinstance(value,list):
        return set().union(*(references(v,artifacts) for v in value)) if value else set()
    return set()


def promote(run, ids, output):
    with transaction(run) as (root,state):
        require(isinstance(ids,list) and 1<=len(ids)<=6 and len(set(ids))==len(ids),'Promote 1..6 distinct lessons')
        destination=load_config(root/'config.json').ensure_output(Path(output))
        require(not destination.exists(),'Experience bundles are immutable; choose a new output')
        lessons={e['id']:e for e in state['memory']}
        superseded={e.get('supersedes') for e in state['memory']}
        entries=[]; pending=set()
        for key in ids:
            require(key in lessons and key not in superseded,'Select a current reviewed lesson')
            entry=lessons[key]
            require(entry['type']=='experience' and entry['status'] in ('supported','refuted'),
                    'Only reviewed supported/refuted experience can be promoted')
            review=state['reviews'].get(str(entry['round']))
            require(review and entry['review']==review['id'],'Lesson needs its Analyst review')
            require(set(entry['evidence'])<=set(review['evidence']),'Promoted evidence must be inspected in that review')
            entries.append(entry);pending.update(entry['evidence']);pending.add(review['id'])
            for extra in ('reflect-'+str(entry['round']-1),'reflect-'+str(entry['round']-1)+'-reply'):
                if extra in state['artifacts']: pending.add(extra)
        retained={}
        while pending:
            key=pending.pop()
            if key in retained: continue
            evidence(root,state,[key]); item=state['artifacts'][key]
            retained[key]=dict(item)
            path=root/item['object']
            # Follow artifact IDs in manifests/reviews/searches; raw binary stays byte-exact.
            try: linked=references(read(path),state['artifacts'])
            except (UnicodeError,ValueError): linked=set()
            pending.update(linked-set(retained))
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.experience-',dir=str(destination.parent)) as temp:
            staged=Path(temp)/'bundle';(staged/'objects').mkdir(parents=True)
            for item in retained.values():
                shutil.copyfile(root/item['object'],staged/'objects'/item['sha256'])
                item['object']='objects/'+item['sha256']
            atomic(staged/'experience.json',{'schema':SCHEMA,'created_at':datetime.now(timezone.utc).isoformat(),
                'origin_path':str(root),'technology':state['project']['technology'],'entries':entries,'artifacts':retained,
                'qualification':'source-scoped evidence only; revalidate in each receiving task'})
            staged.rename(destination)
        return {'bundle':str(destination/'experience.json'),'lessons':ids,'evidence_objects':len(retained),
                'promotion':'reviewed method publication, not cross-run qualification'}


def check_manifest(path):
    manifest=read(path)
    require(manifest.get('schema')==SCHEMA,'Unsupported experience bundle')
    entries=manifest.get('entries')
    require(isinstance(entries,list) and 1<=len(entries)<=6,'Experience bundle needs 1..6 lessons')
    require(isinstance(manifest.get('created_at'),str),'Experience timestamp missing')
    for entry in entries:
        require(entry.get('type')=='experience' and entry.get('scope') in ('general','process') and
                entry.get('status') in ('supported','refuted'),'Invalid published lesson')
        for field in (*TEXT_FIELDS,'stage','module','id'):
            require(isinstance(entry.get(field),str) and entry[field].strip() and len(entry[field])<=MAX_TEXT,'Invalid experience text')
        require(entry.get('review') in manifest['artifacts'],'Published lesson has no retained review')
        require(entry.get('evidence') and set(entry['evidence'])<=set(manifest['artifacts']),'Published evidence missing')
        if entry['scope']=='process': require(entry.get('technology')==manifest['technology'],'Process scope mismatch')
    for item in manifest['artifacts'].values():
        sha=item['sha256'];require(re.fullmatch('[0-9a-f]{64}',sha),'Invalid object identity')
        require(item['object']=='objects/'+sha,'Invalid object path')
        obj=path.parent/item['object']
        require(is_within(obj.resolve(),path.parent.resolve()) and digest(obj)==sha,'Changed experience evidence')
    return manifest


def snapshot(settings, staged):
    source=settings.path('experience_root',required=False)
    names=settings.input_files.get('experience_root',[])
    require(len(names)<=16,'At most 16 explicit experience bundles')
    result=[]
    for name in names:
        require(source is not None,'Configure experience_root')
        path=(source/name).resolve()
        require(is_within(path,source),'Experience path escapes root')
        manifest=check_manifest(path); key=digest(path)
        if any(x['sha256']==key for x in result): continue
        dest=staged/'experience'/key;(dest/'objects').mkdir(parents=True)
        shutil.copyfile(path,dest/'experience.json')
        for item in manifest['artifacts'].values():
            shutil.copyfile(path.parent/item['object'],dest/item['object'])
        # Recheck the copied closure, not just the source files.
        require(digest(dest/'experience.json')==key,'Experience changed during snapshot')
        check_manifest(dest/'experience.json')
        result.append({'sha256':key,'manifest':str((dest/'experience.json').relative_to(staged)),
                       'origin_path':str(path),'created_at':manifest['created_at']})
    return result


def select(root,state,stage=None,module=None,limit=8):
    result=[]
    for bundle in sorted(state.get('experience_bundles',[]),key=lambda x:x['created_at'],reverse=True):
        path=root/bundle['manifest'];require(digest(path)==bundle['sha256'],'Changed pinned experience manifest')
        manifest=read(path)
        for entry in reversed(manifest['entries']):
            if stage and entry['stage']!=stage or module and entry['module']!=module: continue
            if entry['scope']=='process' and entry['technology']!=state['project']['technology']: continue
            result.append(dict(entry,source_status=entry['status'],status='uncertain',
                source_bundle=bundle['manifest'],qualification='reference_only_revalidation_required'))
            if len(result)>=limit: return result
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--ids',nargs='+',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();return promote(a.run,a.ids,a.output)

if __name__=='__main__': cli(main)
