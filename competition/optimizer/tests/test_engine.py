import argparse
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from competition.optimizer.autonomous.core import Gate, canonical, commute, cost, parse, prove, sha, signature
from competition.optimizer.autonomous.passes import PLUGINS, affine, cancellation, factor, mitm
from competition.optimizer.autonomous.store import Store
from competition.optimizer.autonomous.verification import better, parse_receipt, run_process, validate_contract, verify
from competition.optimizer.autonomous.model import calibrate, estimate
from competition.optimizer.autonomous.controller import regions, choose

BUDGET={'span':32,'depth':6,'max_states':10000,'seconds':.1,'wires':6}

class ExactTests(unittest.TestCase):
    def test_parser_barriers(self):
        for s in ['X q0 if b0','HMR q0 b0','PUSH_CONDITION b1','POP_CONDITION',
                  'Z_POW q0 angle','R q0','CCX q0 q0 q1','X q0 extra','X q-1','X q١']:
            self.assertIsNone(parse(s),s)
        self.assertEqual(parse('CCX q2 q0 q1'),Gate('CCX',(0,2,1)))

    def test_phase_is_preserved(self):
        self.assertEqual(prove([Gate('T',(0,)),Gate('T_DAG',(0,))],[])['status'],'EXACT')
        self.assertEqual(prove([Gate('Z',(0,))],[])['status'],'REJECTED')
        self.assertEqual(prove([Gate('CCZ',(0,1,2))],[])['status'],'REJECTED')

    def test_cswap_arbitrary_dirty_inputs(self):
        g=Gate('CSWAP',(0,1,2))
        self.assertEqual(prove([g,g],[])['basis_states'],8)
        self.assertEqual(prove([g,g],[])['status'],'EXACT')

    def test_commutation_is_sound_exhaustively(self):
        gates=[Gate('X',(i,)) for i in range(3)]
        gates += [Gate('CX',q) for q in itertools.permutations(range(3),2)]
        gates += [Gate('CCX',tuple(sorted(set(range(3))-{t}))+(t,)) for t in range(3)]
        gates += [Gate('Z',(i,)) for i in range(3)] + [Gate('CZ',(0,1)),Gate('CCZ',(0,1,2))]
        for a,b in itertools.product(gates,repeat=2):
            if commute(a,b): self.assertEqual(signature([a,b],range(3)),signature([b,a],range(3)))

    def test_shared_factor_removes_scored_gate(self):
        gates=[Gate('CCX',(0,1,3)),Gate('CCX',(0,2,3))]
        p=factor(gates,BUDGET,1)
        self.assertEqual(cost(p.gates)[0],1)
        self.assertEqual(prove(gates,p.gates)['status'],'EXACT')

    def test_factor_dependency_blocks(self):
        gates=[Gate('CCX',(0,1,3)),Gate('CX',(3,2)),Gate('CCX',(0,2,3))]
        self.assertIsNone(factor(gates,BUDGET,1))

    def test_random_affine_resynthesis(self):
        rng=random.Random(901)
        for _ in range(100):
            gates=[rng.choice([Gate('X',(0,)),Gate('X',(2,)),Gate('SWAP',(0,1)),
                              Gate('CX',(0,1)),Gate('CX',(1,2)),Gate('CX',(2,0))]) for _ in range(20)]
            p=affine(gates,BUDGET,1)
            if p: self.assertEqual(prove(gates,p.gates)['status'],'EXACT')

    def test_mitm_finds_empty_implementation(self):
        gates=[Gate('CCX',(0,1,2))]*2
        p=mitm(gates,BUDGET,1)
        self.assertIsNotNone(p)
        self.assertEqual(prove(gates,p.gates)['status'],'EXACT')
        self.assertLess(cost(p.gates),cost(gates))

    def test_smt_finds_factoring_with_independent_proof(self):
        try: import z3
        except ImportError: self.skipTest('Optional Z3 not installed')
        from competition.optimizer.autonomous.smt import synthesize
        gates=[Gate('CCX',(0,1,3)),Gate('CCX',(0,2,3))]
        p=synthesize(gates,dict(BUDGET,seconds=3,max_states=200000,depth=4),12345)
        self.assertEqual(cost(p.gates)[0],1)
        self.assertEqual(prove(gates,p.gates)['status'],'EXACT')

    def test_search_and_proof_caps(self):
        self.assertIsNone(mitm([Gate('CCX',(0,1,3)),Gate('X',(2,))],BUDGET,1))
        self.assertEqual(prove([Gate('X',(i,)) for i in range(11)],[])['status'],'UNPROVED_WIDTH_LIMIT')

    def test_all_plugins_random_proposals(self):
        rng=random.Random(15)
        alphabet=[Gate('X',(0,)),Gate('CX',(0,1)),Gate('CCX',(0,1,2)),Gate('SWAP',(1,2))]
        for name,plugin in PLUGINS.items():
            for _ in range(8):
                gates=[rng.choice(alphabet) for _ in range(8)]
                p=plugin(gates,dict(BUDGET,seconds=.02,max_states=200),47)
                if p: self.assertEqual(prove(gates,p.gates)['status'],'EXACT',name)

    def test_regions_never_cross_measurement_or_guards(self):
        lines=['X q0\n','X q0\n','HMR q0 b0\n','X q0\n','X q0\n','POP_CONDITION\n']
        self.assertEqual({(a,b) for a,b,_,_ in regions(lines,BUDGET,'cancel',20)}, {(0,2),(3,5)})

    def test_wire_renaming_dedup(self):
        self.assertEqual(canonical([Gate('CCX',(0,1,2))]),canonical([Gate('CCX',(5,7,9))]))

class PreservedROMTests(unittest.TestCase):
    def test_k168_exact_lookup(self):
        from competition.optimizer.autonomous.vendor.k168 import circuit,execute,lookup_values
        gates,segments,resource=circuit()
        for address,value in enumerate(lookup_values()):
            for target in (0,32767,12345):
                initial=address | (target<<6)
                expected=address | ((target^value)<<6)
                self.assertEqual(execute(initial,gates),expected)
        self.assertEqual(resource['scratch'],4)

class ReceiptTests(unittest.TestCase):
    contract={'full_shots':3133452,'fields':{'toffoli':'toffoli_count'}}
    def receipt(self,**updates):
        return {'status':'PASS','score':95000.,'verified_shots':3133452,'toffoli_count':1000,**updates}
    def test_partial_never_promotes(self):
        r=parse_receipt(json.dumps(self.receipt(verified_shots=4095)),0,self.contract)
        self.assertEqual(r['status'],'PARTIAL_OR_UNKNOWN_DOMAIN')
    def test_nonzero_exit_never_promotes(self):
        self.assertEqual(parse_receipt(json.dumps(self.receipt()),1,self.contract)['status'],'FAIL')
    def test_nan_and_bool_never_promote(self):
        for x in (float('nan'),float('inf'),True):
            self.assertEqual(parse_receipt(json.dumps(self.receipt(score=x)),0,self.contract)['status'],'INVALID_SCORE')
    def test_missing_metrics_never_promote(self):
        r=self.receipt();r.pop('toffoli_count')
        self.assertEqual(parse_receipt(json.dumps(r),0,self.contract)['status'],'INCOMPLETE_METRICS')
    def test_only_structured_pass(self):
        self.assertEqual(parse_receipt('All tests PASS',0,self.contract)['status'],'UNPARSEABLE')
        self.assertEqual(parse_receipt('banner\n'+json.dumps(self.receipt(),indent=2),0,self.contract)['status'],'PASS_FULL')
    def test_nested_pass_cannot_override_failure(self):
        r={'status':'FAIL','debug':self.receipt()}
        self.assertEqual(parse_receipt(json.dumps(r),0,self.contract)['status'],'FAIL')

    def test_direction_explicit(self):
        self.assertTrue(better(96000,95368,'maximize'))
        self.assertTrue(better(95000,95368,'minimize'))
    def test_empty_seeds_rejected(self):
        with self.assertRaises(ValueError):validate_contract({'direction':'minimize','seeds':[]})
    def test_timeout_kills_process(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_process([sys.executable,'-c','import time; time.sleep(20)'],Path(d)/'log',.1,256,1)
            self.assertEqual(r['status'],'TIMEOUT')
    def test_mock_verifier_pipeline_and_hash_pin(self):
        # A deliberately fake verifier tests plumbing; never a competition receipt.
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); script=d/'mock.py';candidate=d/'candidate.kmx'
            candidate.write_text('X q0\nX q0\n')
            script.write_text('import json\nprint('+repr(json.dumps(self.receipt()))+')\n')
            c=dict(self.contract,script=str(script),script_sha256=sha(script.read_bytes()),
                   seeds=[1,2],direction='minimize',argv=['{python}','{script}','{candidate}'])
            r=verify(candidate,d/'out',c,2,256,1,10)
            self.assertEqual(r['status'],'PASS_FULL');self.assertEqual(len(r['runs']),2)
            script.write_text('print("PASS")')
            self.assertEqual(verify(candidate,d/'out2',c,2,256,1,10)['status'],'VERIFIER_SHA_MISMATCH')

class StorageTests(unittest.TestCase):
    def test_resume_recovery_dedup_and_candidate_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db')
            key=s.add('parent','factor',{},[0,2],'canonical',42)
            s.db.execute("UPDATE experiments SET status='RUNNING' WHERE key=?",(key,));s.db.commit()
            s.recover()
            self.assertEqual(s.db.execute('SELECT status FROM experiments').fetchone()[0],'PENDING')
            self.assertEqual(s.add('newparent','factor',{},[3,5],'canonical',42),key)
            self.assertEqual(s.db.execute('SELECT parent FROM experiments').fetchone()[0],'newparent')
            s.candidate('child','parent','path',{'status':'EXACT'})
            s.receipt('child',{'status':'PASS_FULL','score':1})
            s.finish(key,'LOCAL_IMPROVEMENT','exact',candidate='child')
            self.assertIsNotNone(s.db.execute('SELECT verifier_result FROM experiments').fetchone()[0])
            s.close()
    def test_no_result_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db');k=s.add('p','factor',{},[0,2],'x',1)
            s.finish(k,'NO_IMPROVEMENT','bounded')
            s.add('q','factor',{},[4,6],'x',1)
            self.assertEqual(s.db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0],1);s.close()
    def test_scheduler_ignores_pending_disabled_methods(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db');s.add('p','cancel',{'level':0,'priority':1},[0,2],'x',1)
            self.assertIsNone(choose(s,'p',['smt']));s.close()

    def test_score_model_calibrates_only_aggregates(self):
        self.assertEqual(calibrate([{'score':620,'num_qubits':62,'toffoli_equivalent':10}])['status'],'CALIBRATED_AGGREGATE_QC')
        self.assertEqual(estimate({'num_qubits':62,'toffoli_equivalent':10},delta_rotations=-1)['status'],'UNKNOWN')

class IntegrationTests(unittest.TestCase):
    def test_cli_real_subprocess_resume_and_exact_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source.kmx';out=d/'run';config=d/'config.json'
            source.write_text('CCX q0 q1 q3\nCCX q0 q2 q3\nHMR q4 b0\nX q0\nX q0\n')
            config.write_text(json.dumps({'methods':['factor','cancel'],'max_regions':10,'levels':1,'max_jobs':8,'concurrency':2,'cpus':2}))
            cmd=[sys.executable,'competition/optimizer/run_autonomous.py','--source',str(source),
                 '--expected-sha',sha(source.read_bytes()),'--out',str(out),'--config',str(config)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            summary=json.loads((out/'summary.json').read_text())
            self.assertFalse(summary['success']);self.assertIsNone(summary['best_official'])
            self.assertIn('HMR q4 b0', (out/(summary['current_exact_candidate']+'.kmx')).read_text())
            from competition.optimizer.autonomous.store import Store
            s=Store(out/'experiments.sqlite3')
            successes=s.db.execute("SELECT COUNT(*) FROM experiments WHERE status='LOCAL_IMPROVEMENT'").fetchone()[0]
            self.assertGreaterEqual(successes,2);s.close()
            before=sha(source.read_bytes())
            p=subprocess.run(cmd+['--resume'],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            self.assertEqual(sha(source.read_bytes()),before)
    def test_mock_official_promotion(self):
        # This validates orchestration with a fake oracle, not Kaggle correctness.
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source.kmx';script=d/'mock.py';out=d/'run'
            source.write_text('CCX q0 q1 q3\nCCX q0 q2 q3\n')
            script.write_text("import sys,json\nfrom pathlib import Path\nn=sum(x.startswith('CCX') for x in Path(sys.argv[1]).read_text().splitlines())\nprint(json.dumps({'status':'PASS','score':n*500,'verified_shots':5,'toffoli_count':n}))\n")
            contract=d/'contract.json'
            contract.write_text(json.dumps({'script':str(script),'script_sha256':sha(script.read_bytes()),
                'direction':'minimize','seeds':[12345,23456],'full_shots':5,
                'fields':{'toffoli':'toffoli_count'},'argv':['{python}','{script}','{candidate}']}))
            config=d/'config.json';config.write_text(json.dumps({'methods':['factor'],'levels':1,'max_jobs':2}))
            cmd=[sys.executable,'competition/optimizer/run_autonomous.py','--source',str(source),
                 '--expected-sha',sha(source.read_bytes()),'--out',str(out),'--config',str(config),
                 '--reference-score','400','--contract',str(contract)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['best_official']['score'],500)
            self.assertEqual(summary['measured_baseline_score'],1000)
            self.assertTrue(summary['success'])
            self.assertFalse(summary['beats_reference'])
            from competition.optimizer.replay_candidate import replay
            result=replay(out/'experiments.sqlite3',source,summary['current_exact_candidate'],d/'replayed.kmx')
            self.assertEqual(result['exact_steps'],1)

    def test_portable_database_rebuilds_candidate_files(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source.kmx';source.write_text('CCX q0 q1 q3\nCCX q0 q2 q3\n')
            config=d/'config.json';config.write_text(json.dumps({'methods':['factor'],'levels':1,'max_jobs':2}))
            out=d/'original';portable=d/'portable'
            common=[sys.executable,'competition/optimizer/run_autonomous.py','--source',str(source),
                    '--expected-sha',sha(source.read_bytes()),'--config',str(config)]
            p=subprocess.run(common+['--out',str(out)],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr)
            portable.mkdir();shutil.copyfile(out/'experiments.sqlite3',portable/'experiments.sqlite3')
            p=subprocess.run(common+['--out',str(portable),'--resume'],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            summary=json.loads((portable/'summary.json').read_text())
            self.assertTrue((portable/(summary['current_exact_candidate']+'.kmx')).is_file())

    def test_immutable_baseline_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.kmx';source.write_text('X q0\n')
            p=subprocess.run([sys.executable,'competition/optimizer/run_autonomous.py','--source',str(source),'--expected-sha','0'*64],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('SHA_MISMATCH',p.stderr)

    def test_k191_pin_applies_to_external_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'competition/k191/results/helios_k191.kmx'
            source.parent.mkdir(parents=True)
            source.write_text('X q0\n')
            result = subprocess.run(
                [sys.executable, 'competition/optimizer/run_autonomous.py',
                 '--source', str(source), '--out', str(Path(tmp) / 'run')],
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('BASELINE_SHA_MISMATCH', result.stderr)


if __name__=='__main__': unittest.main()
