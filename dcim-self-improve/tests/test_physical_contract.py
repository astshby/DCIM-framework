"""Synthetic exact-pair seam contracts; no PDK rules or physical signoff claims."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from physical_contract import (validate_contract,evaluate_contract,verify_contract_evidence,
                               master,transformed_boundary)
from search.model import evaluate,validate_problem


def problem():
    return {'blocks':[{'id':key,'source':'source-'+key,'cell':'unit',
                       'width_um':4,'height_um':3,'orientations':[0,90]}
                      for key in ('a','b')],
            'gap_um':0,'max_width_um':20,'max_height_um':20,'grid_um':.25,
            'nets':[['a','b']],
            'physical_contract':{
                'schema':'block-physical-contract-v1',
                'boundaries':[{'id':key,'rect_um':[0,0,4,2]} for key in ('a','b')],
                'alignments':[{'axis':'x','anchors':[{'id':'a','at':'min'},{'id':'b','at':'min'}]}],
                'tracks':[{'axis':'y','pitch_um':2,'offset_um':0,
                           'anchors':[{'id':'a','at':'min'},{'id':'b','at':'min'}]}],
                'repetitions':[{'first':'a','second':'b','delta_um':[0,2],'rotations':[0,0],
                                'evidence':{'artifact':'seam','sha256':'0'*64}}],
                'regions':[{'id':'complete-envelope','rect_um':[0,0,4,5],'members':['a','b']}]}}


def captured(root,state,key,value,kind='evidence'):
    data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8')
    sha=hashlib.sha256(data).hexdigest();destination=root/'objects'/sha
    destination.write_bytes(data)
    state['artifacts'][key]={'kind':kind,'sha256':sha,'object':str(destination.relative_to(root))}
    return sha


class PhysicalContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'objects').mkdir();self.state={'artifacts':{}}
        self.p=problem();self.initial=((0,0,0),(0,2,0))
        for key in ('a','b'):
            captured(self.root,self.state,'source-'+key,{'synthetic_master':key},'reference_layout')
        supporting=captured(self.root,self.state,'raw-check',{'scope':'synthetic exact pair only','results':[]})
        self.cert={'schema':'native-seam-evidence-v1','scope':'exact_pair_transform',
            'masters':[master(self.p,key,self.state['artifacts']['source-'+key]['sha256']) for key in ('a','b')],
            'delta_um':[0,2],'rotations':[0,0],
            'checks':{'seam_geometry':'passed','source_connectivity':'passed','body_supply':'passed'},
            'dependencies':[{'artifact':'raw-check','sha256':supporting}]}
        self.save_cert()

    def save_cert(self):
        sha=captured(self.root,self.state,'seam',self.cert)
        self.p['physical_contract']['repetitions'][0]['evidence']['sha256']=sha

    def test_native_pitch_requires_contract_and_retains_entire_masks(self):
        p=copy.deepcopy(self.p);p.pop('physical_contract')
        self.assertFalse(evaluate(p,self.initial)['feasible'])
        valid=evaluate(self.p,self.initial)
        self.assertTrue(valid['feasible'],valid['violations'])
        self.assertEqual((valid['width_um'],valid['height_um'],valid['area_um2']),(4,5,20))
        self.assertEqual(valid['placements'][1]['height_um'],3)
        self.assertEqual(valid['qualification'],'proxy_only')
        self.assertEqual(valid['constraint_evidence'],'requires_runtime_binding')
        bindings=verify_contract_evidence(self.root,self.state,self.p)
        self.assertEqual(bindings[0]['artifact'],'seam')

    def test_box_height_is_not_a_substitute_for_native_pitch(self):
        result=evaluate(self.p,((0,0,0),(0,3,0)))
        self.assertFalse(result['feasible']);self.assertIn('native_pitch:0',result['violations'])
        p=copy.deepcopy(self.p);p['physical_contract']['regions']=[]
        result=evaluate(p,((0,0,0),(0,2.25,0)))
        self.assertIn('native_pitch:0',result['violations'])
        self.assertIn('spacing:a:b',result['violations'])

    def test_certified_pair_does_not_exempt_other_overlaps(self):
        p=copy.deepcopy(self.p)
        p['blocks'].append(dict(p['blocks'][0],id='c',source='source-c'))
        p['physical_contract']['boundaries'].append({'id':'c','rect_um':[0,0,4,2]})
        result=evaluate(p,self.initial+((1,0,0),))
        self.assertFalse(result['feasible']);self.assertIn('spacing:a:c',result['violations'])
        self.assertIn('spacing:b:c',result['violations'])

    def test_exact_transform_and_boundary_touch_are_both_required(self):
        p=copy.deepcopy(self.p);p['physical_contract']['repetitions'][0]['delta_um']=[0,1]
        result=evaluate(p,((0,0,0),(0,1,0)))
        self.assertIn('native_boundary:0',result['violations'])
        self.assertIn('spacing:a:b',result['violations'])
        result=evaluate(self.p,((0,0,0),(0,2,90)))
        self.assertFalse(result['feasible']);self.assertIn('native_pitch:0',result['violations'])

    def test_alignment_and_track_are_separate_hard_relations(self):
        p=copy.deepcopy(self.p);p['physical_contract']['repetitions']=[];p['physical_contract']['regions']=[]
        result=evaluate(p,((0,0,0),(5,2,0)))
        self.assertIn('alignment:0',result['violations'])
        result=evaluate(p,((0,0,0),(0,4.25,0)))
        self.assertIn('track:0',result['violations'])
        self.assertNotIn('off_grid:b',result['violations'])

    def test_region_contains_full_mask_not_smaller_placement_boundary(self):
        p=copy.deepcopy(self.p);p['physical_contract']['regions'][0]['rect_um']=[0,0,4,4]
        result=evaluate(p,self.initial)
        self.assertIn('region:complete-envelope:b',result['violations'])

    def test_rotated_boundary_uses_full_master_transform(self):
        b=self.p['blocks'][0]
        actual=transformed_boundary(b,{'x_um':10,'y_um':20,'rotation_deg':90},[1,.5,4,2])
        self.assertEqual(actual,[11,21,12.5,24])

    def test_strict_dimensions_reject_equality_and_accept_actual_less(self):
        p=copy.deepcopy(self.p);p.pop('physical_contract');p['grid_um']=1e-10
        p.update(max_width_um=10,max_height_um=10,width_strict=True,height_strict=True)
        self.assertIn('width_strict_bound',evaluate(p,((0,0,0),(6,0,0)))['violations'])
        self.assertIn('height_strict_bound',evaluate(p,((0,0,0),(0,7,0)))['violations'])
        result=evaluate(p,((0,0,0),(6-5e-10,0,0)))
        self.assertTrue(result['feasible'],result['violations'])
        p['width_strict']=False
        self.assertTrue(evaluate(p,((0,0,0),(6,0,0)))['feasible'])

    def test_unknown_or_misspelled_constraint_fields_fail_closed(self):
        for location,key in [('problem','native_repeat_pitch_um'),('problem','must_ppnp_abut'),
                             ('block','must_height'),('contract','must_implants')]:
            p=copy.deepcopy(self.p)
            target=p if location=='problem' else p['blocks'][0] if location=='block' else p['physical_contract']
            target[key]=True
            with self.subTest(location=location,key=key),self.assertRaises(ValueError):validate_problem(p)
        for flags in ({'width_strict':1},{'height_strict':'true'}):
            p=copy.deepcopy(self.p);p.update(flags)
            with self.assertRaises(ValueError):validate_problem(p)

    def test_missing_duplicate_and_outside_contract_geometry_rejected(self):
        for change in ('missing','duplicate','outside','unknown_block','unsupported_rotation','bad_track'):
            p=copy.deepcopy(self.p);c=p['physical_contract']
            if change=='missing':c.pop('tracks')
            if change=='duplicate':c['boundaries'][1]=copy.deepcopy(c['boundaries'][0])
            if change=='outside':c['boundaries'][0]['rect_um']=[0,0,5,2]
            if change=='unknown_block':c['repetitions'][0]['second']='missing'
            if change=='unsupported_rotation':c['repetitions'][0]['rotations']=[180,0]
            if change=='bad_track':c['tracks'][0]['offset_um']=2
            with self.subTest(change=change),self.assertRaises(ValueError):validate_problem(p)

    def test_boolean_or_nonfinite_numbers_cannot_be_geometry(self):
        for value in (True,float('nan'),float('inf')):
            p=copy.deepcopy(self.p);p['blocks'][0]['width_um']=value
            with self.assertRaises(ValueError):validate_problem(p)
            p=copy.deepcopy(self.p);p['physical_contract']['repetitions'][0]['delta_um'][1]=value
            with self.assertRaises(ValueError):validate_problem(p)
        p=copy.deepcopy(self.p);p['blocks'][0]['orientations']=[False]
        with self.assertRaises(ValueError):validate_problem(p)

    def test_certificate_binds_exact_sources_boundaries_and_transform(self):
        good=copy.deepcopy(self.cert)
        for change in ('source','boundary','delta','rotation','scope','extra_field'):
            cert=copy.deepcopy(good)
            if change=='source':cert['masters'][0]['source_sha256']='f'*64
            if change=='boundary':cert['masters'][0]['placement_boundary_um']=[0,0,4,3]
            if change=='delta':cert['delta_um']=[0,3]
            if change=='rotation':cert['rotations']=[0,90]
            if change=='scope':cert['scope']='any_pair'
            if change=='extra_field':cert['waiver']=True
            self.cert=cert;self.save_cert()
            with self.subTest(change=change),self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)

    def test_certificate_requires_all_scoped_checks_and_dependencies(self):
        good=copy.deepcopy(self.cert)
        for change in ('missing_check','failed','missing_dep','duplicate_dep','self_dep','source_dep','wrong_dep_hash'):
            self.cert=copy.deepcopy(good)
            if change=='missing_check':self.cert['checks'].pop('body_supply')
            if change=='failed':self.cert['checks']['source_connectivity']='incomplete'
            if change=='missing_dep':self.cert['dependencies']=[]
            if change=='duplicate_dep':self.cert['dependencies']*=2
            if change=='self_dep':self.cert['dependencies']=[{'artifact':'seam','sha256':'0'*64}]
            if change=='source_dep':self.cert['dependencies']=[{'artifact':'source-a','sha256':self.state['artifacts']['source-a']['sha256']}]
            if change=='wrong_dep_hash':self.cert['dependencies'][0]['sha256']='f'*64
            self.save_cert()
            with self.subTest(change=change),self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)

    def test_object_bytes_and_artifact_kind_are_checked_at_runtime(self):
        record=self.state['artifacts']['raw-check'];original=(self.root/record['object']).read_bytes()
        (self.root/record['object']).write_bytes(b'changed')
        with self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)
        (self.root/record['object']).write_bytes(original)
        self.state['artifacts']['seam']['kind']='reference_layout'
        with self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)

    def test_wrong_certificate_hash_or_missing_source_cannot_be_used(self):
        self.p['physical_contract']['repetitions'][0]['evidence']['sha256']='f'*64
        with self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)
        self.save_cert();self.state['artifacts'].pop('source-b')
        with self.assertRaises(ValueError):verify_contract_evidence(self.root,self.state,self.p)

    def test_contract_evaluation_and_verification_do_not_mutate_inputs(self):
        before=copy.deepcopy((self.p,self.state,self.initial))
        evaluate(self.p,self.initial);verify_contract_evidence(self.root,self.state,self.p)
        self.assertEqual((self.p,self.state,self.initial),before)
        p=copy.deepcopy(self.p);p.pop('physical_contract')
        self.assertEqual(verify_contract_evidence(self.root,self.state,p),[])


if __name__=='__main__':unittest.main()
