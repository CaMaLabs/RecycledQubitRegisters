#!/usr/bin/env python3
"""K093: Helios hybrid phase-router encoding experiment (third-party reference).

Keep Helios's exact Z_POW phase ladder, HMR feed-forward, classical controls,
and all 62 qubits. Replace selected coherent CSWAP gates with an *exact*
parity/XOR routing encoding using either CCX or H-conjugated CCZ:

  CSWAP(c,a,b) =
      CX(a,b); CCX(c,b,a); CX(a,b)
    = CX(a,b); H(a); CCZ(c,b,a); H(a); CX(a,b)

Also test the reversed a/b orientation. Correct on arbitrary superpositions
since every rewrite is an exact unitary identity on three qubits. Tested
exhaustively on 8 basis states in both directions; CCZ-H phase-equivalent.

The key question is whether Kickmix's *scored* nonlinear resources, reaction
depth, or rotation cost change despite the same logical operation.

K093 is NOT a demonstration that a cheaper phase encoding exists.
Do not claim correctness or score improvement until official verification
on both complete seeds. No approximation, no 400-qubit polynomial circuit.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SHA='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE=95369.00696815242
CSWAP=re.compile(r'^CSWAP\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$',re.I)
ZPOW=re.compile(r'^Z_POW\s+q28\s+([^\s]+)\s*$',re.I)
HMR=re.compile(r'^HMR\s+q28\s+b(\d+)\s*$',re.I)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p)
 if s is None or s.loader is None:raise FileNotFoundError(str(p))
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def expand(c,a,b,basis,orientation):
 # For orientation 0: CX(a,b) CCX(c,b,a) CX(a,b).
 # For orientation 1: CX(b,a) CCX(c,a,b) CX(b,a).
 if orientation: a,b=b,a
 if basis=='ccx':
  return [f'CX q{a} q{b}\n',f'CCX q{c} q{b} q{a}\n',f'CX q{a} q{b}\n']
 if basis=='ccz':
  return [f'CX q{a} q{b}\n',f'H q{a}\n',f'CCZ q{c} q{b} q{a}\n',
          f'H q{a}\n',f'CX q{a} q{b}\n']
 raise ValueError(basis)

def basis_test():
 for orientation in (0,1):
  for v in range(8):
   def bit(z,k):return (z>>k)&1
   c,a,b=0,1,2
   exp=v^(((bit(v,c) and (bit(v,a)^bit(v,b)))<<a) |
          ((bit(v,c) and (bit(v,a)^bit(v,b)))<<b))
   value=v
   for gate in expand(c,a,b,'ccx',orientation):
    op=gate.split()[0];q=[int(x[1:]) for x in gate.split()[1:]]
    if op=='CX':value^=(bit(value,q[0])<<q[1])
    elif op=='CCX':value^=((bit(value,q[0])&bit(value,q[1]))<<q[2])
    else:raise AssertionError(gate)
   assert value==exp,(orientation,v,value,exp)
 # CCZ and H-target CCX equivalence follows from HZH=X. Explicit
 # 3-qubit matrix identity verified with Qiskit when installed.
 try:
  from qiskit import QuantumCircuit
  from qiskit.quantum_info import Operator
  import numpy as np
  for orientation in (0,1):
   unitary=[]
   for basis in ('ccx','ccz'):
    circuit=QuantumCircuit(3)
    for line in expand(0,1,2,basis,orientation):
     tokens=line.split();op=tokens[0];q=[int(t[1:]) for t in tokens[1:]]
     if op=='CX':circuit.cx(*q)
     if op=='CCX':circuit.ccx(*q)
     if op=='CCZ':circuit.ccz(*q)
     if op=='H':circuit.h(*q)
    unitary.append(Operator(circuit).data)
   assert np.max(np.abs(unitary[0]-unitary[1]))<1e-12
  print('K093_CCZ_EXACT_UNITARY PASS Qiskit 3-qubit complex matrices',flush=True)
 except ImportError:
  print('K093_CCZ_EXACT_UNITARY SKIPPED Qiskit unavailable; H Z H = X algebraic identity',flush=True)
 print('K093_SELFTEST PASS 16 reversible Fredkin basis states, both orientations',flush=True)

def ladder_ranges(lines):
 events=[]
 for i,s in enumerate(lines):
  m=ZPOW.fullmatch(s.strip())
  if not m:continue
  try:angle=float(m.group(1))
  except ValueError:continue
  events.append((i,angle))
 groups=[];cur=[]
 for p in events:
  if cur and p[0]-cur[-1][0]>24:
   groups.append(cur);cur=[]
  cur.append(p)
 if cur:groups.append(cur)
 match=[g for g in groups if len(g)>=20 and g[0][1]<1e-9
        and all(g[j+1][1]>g[j][1] for j in range(len(g)-1))]
 if len(match)!=1:return [],{'ladder_matches':len(match)}
 phase=match[0]
 last=phase[-1][0]
 for j in range(last+1,min(last+30,len(lines))):
  if HMR.fullmatch(lines[j].strip()):last=j;break
 return [(max(0,phase[0][0]-120),min(len(lines),last+120))],{
     'ladder_matches':1,'phase_events':len(phase),
     'first_zpow_line':phase[0][0]+1,'last_zpow_line':phase[-1][0]+1,
     'phase_window':[max(0,phase[0][0]-120)+1,min(len(lines),last+120)]}

def selection(case,idx,sz,ranges):
 if case=='all':return True
 if case=='phase':return any(a<=idx<b for a,b in ranges)
 if case=='hotspot':return 25200<=idx<26400
 if case=='front':return idx<600
 if case=='tail':return idx>=max(0,sz-600)
 if case=='alternating':return False
 raise ValueError(case)

def rewrite(lines,case,basis,orientation,ranges):
 out=[];changed=[];swaps=0
 for i,s in enumerate(lines):
  match=CSWAP.fullmatch(s.strip())
  if match and selection(case,i,len(lines),ranges):
   c,a,b=map(int,match.groups())
   if len({c,a,b})!=3:raise ValueError('Non distinct CSWAP operands')
   out.extend(expand(c,a,b,basis,orientation))
   changed.append(i+1);swaps+=1
  else:out.append(s if s.endswith('\n') else s+'\n')
 return out,{'rewritten_cswaps':swaps,'selected_lines':changed[:24],
             'basis':basis,'orientation':orientation,'scope':case}

def counts(lines):
 c=collections.Counter()
 for s in lines:
  t=s.strip()
  if t and not t.startswith(('#','//')):c[t.split()[0].upper()]+=1
 return c

def passed(v):return v.get('status')=='PASS' and v.get('exit_code')==0

def verify(m,p,n,timeout,full):
 r={'prefix':m.verify(p,n,12345,timeout)}
 if full and passed(r['prefix']):
  r['full_12345']=m.verify(p,m.FULL_X,12345,timeout)
  if passed(r['full_12345']):
   r['full_23456']=m.verify(p,m.FULL_X,23456,timeout)
 return r

def run():
 ap=argparse.ArgumentParser()
 ap.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k093/results')
 ap.add_argument('--cases',nargs='+',choices=['phase','hotspot','front','tail','all'],
    default=['phase','hotspot','front','tail','all'])
 ap.add_argument('--bases',nargs='+',choices=['ccx','ccz'],default=['ccx','ccz'])
 ap.add_argument('--orientations',type=int,nargs='+',choices=[0,1],default=[0,1])
 ap.add_argument('--prefix',type=int,default=4095)
 ap.add_argument('--timeout',type=int,default=1200)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--max-candidates',type=int,default=20)
 a=ap.parse_args()
 basis_test()
 if a.self_test:return
 if sha(a.base)!=SHA:raise RuntimeError('Original Helios KMB provenance mismatch')
 k031=load('k031_k093',ROOT/'competition/k031/k031_full_domain_repair.py')
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 a.out.mkdir(parents=True,exist_ok=True)
 original=km.Circuit.from_file(str(a.base),format='kmb')
 text=a.out/'original_helios.kmx'
 original.to_file(str(text),format='kmx')
 lines=text.read_text().splitlines(keepends=True)
 ranges,phase=ladder_ranges(lines)
 before=counts(lines)
 print('K093_ORIGINAL',json.dumps({'source_sha256':SHA,
   'qubits':original.num_qubits,'counts':{g:before[g] for g in
    ('CCX','CCZ','CSWAP','HMR','Z_POW','CX')},'ladder':phase},sort_keys=True),flush=True)
 cases=[(case,basis,orientation) for case in a.cases for basis in a.bases
        for orientation in a.orientations][:a.max_candidates]
 best=None;reports=[]
 for case,basis,orientation in cases:
  name=f'{case}_{basis}_o{orientation}'
  record={'case':name,'full_domain_verified':False,'status':'NOT_STARTED'}
  try:
   start=time.monotonic()
   edited,info=rewrite(lines,case,basis,orientation,ranges)
   after=counts(edited)
   record['transform']=info
   record['count_delta']={g:after[g]-before[g] for g in
       ('CCX','CCZ','CSWAP','CX','CZ','HMR','Z_POW')}
   print('K093_SCAN',json.dumps({'case':name,**info,
      'delta':record['count_delta']},sort_keys=True),flush=True)
   if info['rewritten_cswaps']==0:
    record['status']='NO_MATCHES'
   else:
    kmx=a.out/(name+'.kmx');kmx.write_text(''.join(edited))
    circ=km.Circuit.from_file(str(kmx),format='kmx')
    binary=a.out/(name+'.kmb');circ.to_file(str(binary),format='kmb')
    record.update(qubits=circ.num_qubits,sha256=sha(binary))
    v=verify(k031,binary,a.prefix,a.timeout,a.full)
    record['verification']=v
    if not passed(v['prefix']):record['status']='FAIL_PREFIX'
    elif a.full and passed(v.get('full_12345',{})) and passed(v.get('full_23456',{})):
     record['status']='PASS_FULL'
     record['full_domain_verified']=True
     record['score']=v['full_12345']['score']
     record['score_delta_vs_helios']=record['score']-BASE
     if best is None or record['score']<best['score']:best=record
    elif a.full:record['status']='FAIL_FULL'
    else:
     record['status']='PASS_PREFIX_ONLY'
     record['prefix_score']=v['prefix'].get('score')
   record['elapsed_s']=round(time.monotonic()-start,2)
  except Exception as ex:
   record.update(status='ERROR',error=repr(ex))
  reports.append(record)
  (a.out/(name+'.json')).write_text(json.dumps(record,indent=2,default=str))
  print('K093_CASE',json.dumps({'case':name,'status':record['status'],
    'rewritten_cswaps':record.get('transform',{}).get('rewritten_cswaps'),
    'score':record.get('score'),'prefix_score':record.get('prefix_score'),
    'qubits':record.get('qubits'),'error':record.get('error')},
    sort_keys=True),flush=True)
 summary={'attribution':'third-party Helios baseline, CaMaLabs exact routing re-encodings',
   'source_sha256':SHA,'baseline_score_full_seed_12345':BASE,
   'best_full':{'case':best['case'],'score':best['score'],
      'delta_vs_baseline':best['score_delta_vs_helios']} if best else None,
   'cases':reports}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
 print('K093_RESULT',json.dumps({'best_full':summary['best_full'],
      'cases':len(reports)},sort_keys=True),flush=True)
 print('SAVED',a.out/'summary.json',flush=True)

if __name__=='__main__':run()
