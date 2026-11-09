#!/usr/bin/env python3
"""K096 systematic cross-project compiler transfer and combination experiment.
Public circuits stay immutable. Full verification gates every resource winner.
No QPU jobs and no scoring modifications.
"""
import argparse,collections,hashlib,importlib.util,itertools,json,subprocess,sys,time
from pathlib import Path
import kickmix as km
HERE=Path(__file__).resolve().parent
REPO=HERE.parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(lines):return [s.rstrip('\r\n')+'\n' for s in lines if s.strip()]
def counts(lines):return dict(collections.Counter(s.split()[0] for s in lines if s.strip()))
def resources(c,lines):
 stats=counts(lines)
 return {'qubits':c.num_qubits,'nonlinear':sum(stats.get(g,0) for g in ('CCX','CCZ','CSWAP')),'zpow':stats.get('Z_POW',0),'instructions':len(c),'counts':stats}
def test_circuit(verifier,path,n,shots,seed,timeout):
 batch=next(i for i in range(min(6132,n*shots),0,-1) if (n*shots)%i==0)
 cmd=[sys.executable,str(verifier),str(path),'--max-x',str(n),'--shots-per-x',str(shots),'--batch-size',str(batch),'--max-workers','2','--seed',str(seed)]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
  r=json.loads(p.stdout);r.update(exit_code=p.returncode,command=cmd);return r
 except subprocess.TimeoutExpired:return {'status':'TIMEOUT','command':cmd}
 except Exception as e:return {'status':'ERROR','error':repr(e),'command':cmd}
def good(r):return r.get('status')=='PASS' and r.get('exit_code')==0

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--verifiers',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--timeout',type=int,default=1200);p.add_argument('--full-shots',type=int,default=2);p.add_argument('--self-test',action='store_true');a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=True)
 mods={k:load('k096_'+k,REPO/'k028'/v) for k,v in {
  'classical':'k067_coherence_aware_classical_compiler.py','phase':'k062_classical_parity_fold.py','cancel':'k063_nonlinear_gate_cancellation.py','xor':'k068_nonlinear_xor_factor.py','anf':'k069_block_anf_synth.py','router':'k071_phase_router_optimizer.py','bridge':'k094_cost_aware_parity_bridge.py'}.items()}
 for key,file in [('quad','quadratic_windows.py'),('multi','multioutput_anf.py'),('commute','commuting_cancellation.py'),('symbolic','symbolic_state.py'),('life','clean_lifetimes.py')]:mods[key]=load('k096_'+key,HERE/file)
 tests={'commutation':mods['commute'].selftest(),'multioutput':mods['multi'].selftest(mods['anf'],mods['quad'])};mods['quad'].selftest();mods['classical'].selftest()
 (a.out/'selftests.json').write_text(json.dumps(tests,indent=2));print('K096_SELFTEST',json.dumps(tests),flush=True)
 if a.self_test:return
 verifier=a.verifiers/'invsqrt/verify_submission_invsqrt.py'
 assert digest(verifier)=='ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a','unrecognized verifier version'
 baseline=km.Circuit.from_file(str(a.base),format='kmb');baseline.to_file(str(a.out/'baseline.kmx'),format='kmx');original=canon((a.out/'baseline.kmx').read_text().splitlines());base_r=resources(baseline,original)
 provenance={'source_sha256':digest(a.base),'verifier_sha256':digest(verifier),'source':str(a.base),'baseline_resources':base_r,'attribution':'Third-party public Helios release, experimental CaMaLabs transfers. Preserve upstream dataset CREDITS/LICENSE.'}
 (a.out/'provenance.json').write_text(json.dumps(provenance,indent=2))
 def apply(name,lines):
  if name=='classical':return mods[name].transform(lines)
  if name=='phase':return mods[name].transform(lines)
  if name=='cancel':
   z,st,it=mods[name].optimize(lines);return z,{'removed':st,'iterations':it}
  if name=='commute':return mods[name].optimize(lines,mods['cancel'].decode)
  if name=='xor':
   z,st=mods[name].factor(lines,160);return z,{'pairs':len(st)}
  if name=='quad':
   z,h,st=mods[name].candidates(lines,9,200,14);return z,{**st,'saved':sum(v['ccx_saved'] for v in h)}
  if name=='multi':return mods[name].optimize(lines,mods['anf'],mods['quad'])
  if name=='router':
   z,st,h=mods[name].optimize(lines);return z,{'blocks':len(st),'changed':len(h)}
  if name=='bridge':
   z,st=mods[name].optimize(lines,160,600);return z,{'bridges':len(st)}
  if name=='symbolic':
   z,st=mods[name].transform(lines);return z,dict(st)
  if name=='lifetime':return mods['life'].compact(lines)
  if name.startswith('encode'):
   z,st=mods['bridge'].expand_swaps(lines,'all',int(name[-1]));return z,{'cswaps_expanded':st}
  raise ValueError(name)
 names=['classical','phase','cancel','commute','xor','quad','multi','router','bridge','symbolic','lifetime','encode0','encode1']
 # Do not remove a family simply because its isolated result loses or is null.
 chains=[()] + [(k,) for k in names]+list(itertools.permutations(names,2))
 for encode in ('encode0','encode1'):
  for synth in ('xor','quad','multi','bridge'):
   chains += [(encode,'classical','phase','commute',synth,'commute','symbolic','lifetime'),('symbolic',encode,synth,'commute','phase','lifetime')]
 chains += [('classical','phase','commute','quad','multi','symbolic','lifetime'),('symbolic','classical','phase','multi','quad','commute','lifetime')]
 prefix_cache={};trans_cache={():original};records=[];unique={};full=[];started=time.monotonic()
 for index,chain in enumerate(chains):
  try:
   lines=original;meta=[]
   for j,k in enumerate(chain):
    key=chain[:j+1]
    if key in trans_cache:lines=trans_cache[key];continue
    lines,st=apply(k,list(lines));lines=canon(lines);trans_cache[key]=lines;meta.append({'method':k,'stats':st})
   key=hashlib.sha256(''.join(lines).encode()).hexdigest();record={'chain':list(chain),'text_sha256':key,'steps':meta,'status':'GENERATED'}
   if key in unique:
    record.update(status='DUPLICATE',same_as=unique[key]);records.append(record)
   else:
    tag=f'candidate_{index:03d}';unique[key]=tag;path=a.out/(tag+'.kmx');path.write_text(''.join(lines));c=km.Circuit.from_file(str(path),format='kmx');binary=a.out/(tag+'.kmb');c.to_file(str(binary),format='kmb')
    r=resources(c,lines);record.update(tag=tag,resources=r,binary_sha256=digest(binary))
    verification=test_circuit(verifier,binary,4095,2,12345,a.timeout);record['prefix']=verification
    if not good(verification):record['status']='FAIL_PREFIX'
    else:
     record['status']='PASS_PREFIX'
     structural=(r['qubits']<base_r['qubits'] or r['nonlinear']<base_r['nonlinear'] or r['zpow']<base_r['zpow'])
     record['structural_reduction']=structural
     if structural or not chain:
      record['full']={}
      for seed in (12345,23456):
       v=test_circuit(verifier,binary,3133452,a.full_shots,seed,a.timeout);record['full'][str(seed)]=v
       if not good(v):break
      record['status']='PASS_FULL' if len(record['full'])==2 and all(good(v) for v in record['full'].values()) else 'FAIL_FULL'
      if record['status']=='PASS_FULL':full.append(record)
    records.append(record)
    print('K096_UNIQUE',json.dumps({'chain':chain,'status':record['status'],'q':r['qubits'],'nonlinear':r['nonlinear'],'prefix_score':verification.get('score')}),flush=True)
  except Exception as exc:
   records.append({'chain':list(chain),'status':'ERROR','error':repr(exc)});print('K096_ERROR',records[-1],flush=True)
  (a.out/'matrix.json').write_text(json.dumps(records,indent=2,default=str))
  if index%20==0:print('K096_PROGRESS',index,len(chains),'unique',len(unique),'elapsed',round(time.monotonic()-started,1),flush=True)
 # Keep chains and hashes even when a pass produced no savings. Measurement-seed
 # cost variation alone never promotes a Clifford-only candidate.
 baseline_receipt=next((r for r in full if not r['chain']),None);wins=[]
 if baseline_receipt:
  for r in full:
   if r['chain'] and r.get('structural_reduction') and all(r['full'][str(s)]['score']<baseline_receipt['full'][str(s)]['score'] for s in (12345,23456)):wins.append({'tag':r['tag'],'chain':r['chain'],'scores':{s:v['score'] for s,v in r['full'].items()}})
 summary={'chains':len(records),'unique_circuits':len(unique),'statuses':dict(collections.Counter(r['status'] for r in records)),'verified_resource_wins':wins,'baseline':baseline_receipt,'elapsed_s':round(time.monotonic()-started,2),'full_shots_per_x':a.full_shots,'limits':'2 shots/x by default is not official default 64; no Kaggle submission made.'}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2,default=str));print('K096_RESULT',json.dumps({k:v for k,v in summary.items() if k!='baseline'}),flush=True)
if __name__=='__main__':main()
