#!/usr/bin/env python3
"""K098: Score-aware Helios rotation simplification and precision-margin probes.

Official invsqrt score: Q * (mean_executed_CCX_CCZ_CSWAP
 + (base_T + mean_executed_rotations * rotation_T(eps))/4),
 where eps depends on the smallest verified numerical-error margin.

Exact track: merge *unconditional* Z_POW angles when intervening gates
provably commute; never cross measurements, conditions or bit mutations.
Numerical track: probe small relative changes to the 26-stage q28 phase
ladder. These are APPROXIMATE; only a two-seed full-domain verifier PASS
certifies admissibility, and only a lower official score is an improvement.

Third-party Helios reference is SHA-256 pinned and left immutable.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,math,re,sys,time
from pathlib import Path
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[2]
PIN='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE_SCORE=95369.00696815242
BASE_ROT_COUNT=41.0
BASE_EPS=2.434041480874084e-13
BASE_TOFFOLI=1243.118965920014
BASE_Q=62

ZPOW=re.compile(r'^Z_POW\s+q(\d+)\s+([^\s]+)$',re.I)
Q=re.compile(r'\bq(\d+)\b')
OPS={'X','Y','Z','CX','CZ','SWAP','CCX','CCZ','CSWAP','Z_POW','S','S_DAG','T','T_DAG'}
DIAGONAL={'Z','CZ','CCZ','Z_POW','S','S_DAG','T','T_DAG'}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise FileNotFoundError(str(path))
 mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
 spec.loader.exec_module(mod);return mod

def bits(line):
 return tuple(map(int,Q.findall(line)))

def commutes_with_zpow(line,q):
 """Strictly unconditional unitary only, diagonal on q or disjoint from q."""
 s=line.strip()
 if not s or s.startswith(('#','//')) or ' if ' in s.lower():return False
 tokens=s.split()
 op=tokens[0].upper()
 if op not in OPS:return False
 qs=bits(s)
 if not qs:return False
 return q not in qs or op in DIAGONAL

def find_merge(lines,distance):
 for j,line in enumerate(lines):
  m=ZPOW.fullmatch(line.strip())
  if not m:continue
  q=int(m[1])
  try:b=Decimal(m[2])
  except Exception:continue
  for i in range(j-1,max(-1,j-distance-1),-1):
   prior=lines[i].strip()
   p=ZPOW.fullmatch(prior)
   if p and int(p[1])==q:
    try:a=Decimal(p[2])
    except Exception:break
    return i,j,q,a,b
   if not commutes_with_zpow(lines[i],q):break
 return None

def merged_angle(a,b):
 # Decimal input angles combine without binary-float rounding.
 value=(Decimal(str(a))+Decimal(str(b)))%Decimal(2)
 if value>1:value-=2
 if value<=-1:value+=2
 return value

def exact_merge(lines,distance):
 out=list(lines);events=[]
 for _ in range(512):
  hit=find_merge(out,distance)
  if hit is None:break
  i,j,q,a,b=hit
  angle=merged_angle(a,b)
  if angle==0:
   del out[j];del out[i]
  else:
   out[i]=f'Z_POW q{q} {format(angle,"f")}\n'
   del out[j]
  events.append({'first_line':i+1,'second_line':j+1,
                 'qubit':q,'angles':[str(a),str(b)],'combined':str(angle)})
 return out,events

def ladder(lines):
 events=[]
 for i,line in enumerate(lines):
  match=ZPOW.fullmatch(line.strip())
  if match and int(match[1])==28:
   try:events.append((i,float(match[2])))
   except ValueError:continue
 groups=[];cur=[]
 for item in events:
  if cur and item[0]-cur[-1][0]>24:
   groups.append(cur);cur=[]
  cur.append(item)
 if cur:groups.append(cur)
 matches=[g for g in groups if len(g)>=20 and g[0][1]<1e-9 and
          all(g[i+1][1]>g[i][1] for i in range(len(g)-1))]
 if len(matches)!=1:raise RuntimeError(f'Expected one q28 ladder, got {len(matches)}')
 return matches[0]

def tweak(lines,index,multiplier):
 out=list(lines);m=ZPOW.fullmatch(lines[index].strip())
 if not m:raise RuntimeError('Selected line is not Z_POW')
 q=int(m[1]);old=Decimal(m[2])
 factor=Decimal(str(multiplier))
 new=old*factor
 # Kickmix's decimal-angle parser rejects exponent notation.
 # Use exact decimal arithmetic and fixed-point text, including tiny angles.
 out[index]=f'Z_POW q{q} {format(new,"f")}\n'
 return out,{'line':index+1,'qubit':q,'original':str(old),
             'adjusted':format(new,"f"),'multiplier':str(factor)}

def predicted_sensitivity():
 # Marginal score impact of doubling synthesis-error budget.
 gain=BASE_Q*(BASE_ROT_COUNT*0.56/4)
 return {'score_improvement_if_eps_doubles':gain,
         'one_rotation_saved_at_baseline_eps':
           BASE_Q*(0.56*math.log2(1/BASE_EPS)+5.3)/4,
         'one_executed_toffoli_saved':BASE_Q}

def selftest():
 tests=[
  (['Z_POW q0 0.125\n','CZ q0 q1\n','Z_POW q0 0.25\n'],1),
  (['Z_POW q0 0.125\n','CX q1 q2\n','Z_POW q0 0.25\n'],1),
  (['Z_POW q0 0.125\n','CX q0 q2\n','Z_POW q0 0.25\n'],0),
  (['Z_POW q0 0.125\n','HMR q3 b0\n','Z_POW q0 0.25\n'],0),
  (['Z_POW q0 0.125\n','CZ q0 q1 if b0\n','Z_POW q0 0.25\n'],0),
  (['Z_POW q0 0.125\n','PUSH_CONDITION if b1\n','Z_POW q0 0.25\n'],0),
  (['Z_POW q0 0.125\n','Z_POW q0 -0.125\n'],1)]
 for src,count in tests:
  out,events=exact_merge(src,20)
  assert len(events)==count,(src,events)
  if count:
   assert sum(bool(ZPOW.fullmatch(x.strip())) for x in out)==(
       0 if src[-1].endswith('-0.125\n') else 1)
 assert merged_angle(Decimal('0.125'),Decimal('0.25'))==Decimal('0.375')
 tiny=['Z_POW q28 0.00000000023283064365386962890625\n']
 candidate,info=tweak(tiny,0,'0.984375')
 assert re.fullmatch(r'Z_POW q28 -?[0-9]+\\.[0-9]+\\n',candidate[0])
 assert 'e' not in candidate[0].split()[-1].lower()
 assert Decimal(candidate[0].split()[-1])==Decimal(tiny[0].split()[-1])*Decimal('0.984375')

 assert abs(predicted_sensitivity()['score_improvement_if_eps_doubles']-355.88)<0.001
 print('K098_SELFTEST PASS strict phase-commutation barriers, rotation cost, angle composition',flush=True)

def good(r):return r.get('status')=='PASS' and r.get('exit_code')==0
def compact(r):
 return {k:r.get(k) for k in ('status','score','toffoli_count','rotation_count',
     'rotation_eps','worst_x','worst_error_over_tolerance','num_qubits',
     't_count','exit_code','error','reason','stderr_tail','stdout_tail','worst_error_over_tolerance')}

def verify_case(ver,path,screen,prefix,timeout,full):
 result={'screen':ver.verify(path,screen,12345,timeout)}
 if good(result['screen']) and prefix>screen:
  result['prefix']=ver.verify(path,prefix,12345,timeout)
 elif good(result['screen']):result['prefix']=result['screen']
 if full and good(result.get('prefix',{})):
  result['full_12345']=ver.verify(path,ver.FULL_X,12345,timeout)
  if good(result['full_12345']):
   result['full_23456']=ver.verify(path,ver.FULL_X,23456,timeout)
 return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k098/results')
 p.add_argument('--screen',type=int,default=256)
 p.add_argument('--prefix',type=int,default=4095)
 p.add_argument('--timeout',type=int,default=1200)
 p.add_argument('--full',action='store_true')
 p.add_argument('--self-test',action='store_true')
 p.add_argument('--max-candidates',type=int,default=16)
 p.add_argument('--phase-indices',type=int,nargs='*',default=[0,1,2,3,4,5])
 p.add_argument('--factors',type=str,nargs='*',
                default=[0.984375,1.015625])
 p.add_argument('--include-drop-first',action='store_true')
 args=p.parse_args()
 selftest()
 if args.self_test:return
 if sha(args.base)!=PIN:raise RuntimeError('Original public Helios circuit SHA-256 mismatch')
 if not 161<=args.screen<=args.prefix:raise ValueError('screen must include worst_x=161 and be <=prefix')
 ver=load('k031_k098',ROOT/'competition/k031/k031_full_domain_repair.py')
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 args.out.mkdir(parents=True,exist_ok=True)
 original=km.Circuit.from_file(str(args.base),format='kmb')
 source=args.out/'helios_immutable.kmx';original.to_file(str(source),format='kmx')
 lines=source.read_text().splitlines(keepends=True)
 stages=ladder(lines)
 print('K098_BASE',json.dumps({'sha256':PIN,'qubits':original.num_qubits,
    'ladder_count':len(stages),'ladder_lines':[stages[0][0]+1,stages[-1][0]+1],
    'baseline_score':BASE_SCORE,'sensitivity':predicted_sensitivity()},sort_keys=True),flush=True)
 pool=[]
 exact,merges=exact_merge(lines,256)
 print('K098_EXACT_SCAN',json.dumps({'merges':len(merges),'examples':merges[:8]}),flush=True)
 if merges:pool.append(('exact_merge',exact,{'type':'exact','merges':merges}))
 for idx in args.phase_indices:
  if idx<0 or idx>=len(stages):continue
  position,angle=stages[idx]
  for factor in args.factors:
   if Decimal(str(factor))==1:continue
   out,details=tweak(lines,position,factor)
   pool.append((f'phase_{idx:02d}_factor_{str(factor).replace(".","p")}',out,
                {'type':'approximate','ladder_index':idx,**details}))
 if args.include_drop_first:
  for count in (1,2):
   subset={stages[i][0] for i in range(count)}
   pool.append((f'drop_first_{count}',
      [s for i,s in enumerate(lines) if i not in subset],
      {'type':'approximate','removed_ladder_indices':list(range(count))}))
 pool=pool[:args.max_candidates]
 report={'source':'public third-party Helios; CaMaLabs phase-cost experiment',
         'baseline_sha256':PIN,'baseline_score':BASE_SCORE,
         'cost_model':'Q * (mean_executed_nonlinear + (mean_base_T + n_rot*(0.56 log2(1/eps)+5.3))/4)',
         'cost_model_caveat':'n_rot and eps are from official verifier, and depend on numerical error',
         'sensitivity':predicted_sensitivity(),'merges':merges,'cases':[]}
 for name,variant,details in pool:
  record={'case':name,'transform':details,'status':'NOT_RUN',
          'full_domain_verified':False}
  start=time.monotonic()
  try:
   kmx=args.out/(name+'.kmx');kmx.write_text(''.join(variant))
   compiled=km.Circuit.from_file(str(kmx),format='kmx')
   binary=args.out/(name+'.kmb');compiled.to_file(str(binary),format='kmb')
   record.update(candidate_sha=sha(binary),num_qubits=compiled.num_qubits)
   if compiled.num_qubits>BASE_Q:raise ValueError('Qubit increase exceeds baseline')
   official=verify_case(ver,binary,args.screen,args.prefix,args.timeout,args.full)
   record['official']=official
   record['cost_probe']={label:compact(x) for label,x in official.items()}
   record['stage_outcome']={label:x.get('status') for label,x in official.items()}
   if not good(official['screen']):record['status']='FAIL_SCREEN'
   elif not good(official.get('prefix',{})):record['status']='FAIL_PREFIX'
   elif args.full and good(official.get('full_12345',{})) and good(official.get('full_23456',{})):
    record['status']='PASS_FULL'
    record['full_domain_verified']=True
    record['score']=official['full_12345']['score']
    record['score_delta']=record['score']-BASE_SCORE
   elif args.full:record['status']='FAIL_FULL'
   else:record['status']='PASS_PREFIX_ONLY'
  except Exception as e:record.update(status='ERROR',error=repr(e))
  record['elapsed_s']=round(time.monotonic()-start,2)
  report['cases'].append(record)
  (args.out/(name+'.json')).write_text(json.dumps(record,indent=2,default=str))
  print('K098_CASE',json.dumps({'case':name,'type':details['type'],
       'status':record['status'],'screen':record.get('cost_probe',{}).get('screen'),
       'prefix':record.get('cost_probe',{}).get('prefix'),
       'full':record.get('cost_probe',{}).get('full_12345'),
       'score_delta':record.get('score_delta'),'error':record.get('error')},sort_keys=True),flush=True)
 passes=[r for r in report['cases'] if r['status']=='PASS_FULL']
 winner=min(passes,key=lambda r:r['score']) if passes else None
 report['winner']=({'case':winner['case'],'score':winner['score'],
                    'delta':winner['score_delta']} if winner else None)
 (args.out/'summary.json').write_text(json.dumps(report,indent=2,default=str))
 print('K098_RESULT',json.dumps({'tested':len(report['cases']),
       'full_passes':len(passes),'winner':report['winner'],
       'beats_baseline':bool(winner and winner['score']<BASE_SCORE)},sort_keys=True),flush=True)
 print('SAVED',args.out/'summary.json',flush=True)
if __name__=='__main__':main()
