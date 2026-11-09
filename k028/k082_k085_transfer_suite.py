#!/usr/bin/env python3
"""K082-085 isolated quantum compiler transfer experiments.
Not a 22-bit invsqrt circuit and not an official full-domain score.
K082 semantic address factoring; K083 exponent phase polynomial;
K084 RCCX phase-exact clean latch; K085 fail-closed synthesis summary.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[2]
def km_import():
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 return km
def counts(path):
 c=collections.Counter()
 for line in path.read_text().splitlines():
  line=line.strip()
  if line and not line.startswith('#'):c[line.split()[0]]+=1
 return {'operations':sum(c.values()),**{n:c[n] for n in ('CCX','CCZ','HMR','CZ','CX','Z_POW')}}
def AND(b,km,c,t):
 a=b.alloc_qubits(1);b.init_and(c,km.array([t]),km.array([a[0]]));return a
def UNAND(b,km,c,t,a):
 b.del_and(c,km.array([t]),km.array([a[0]]));b.free(a)
def table(bits):
 import numpy as np
 s=1<<bits;t=np.arange(s+1,dtype=float)
 rows=[]
 for p in (0,1):
  vals=np.rint(2**(-p/2)/np.sqrt(1+t/s)*(1<<38)).astype('int64')
  rows.append([(int(vals[j]),int(vals[j+1]-vals[j])) for j in range(s)])
 return rows
def k082(out,bits,frac):
 km=km_import();tab=table(bits);result={}
 for mode in ('independent','factored'):
  b=km.CircuitBuilder();p=b.create_quantum_register(1,name='parity')
  seg=b.create_quantum_register(bits,name='segment')
  res=b.create_quantum_register(frac,name='residual')
  requested={'and':0,'rotations':0}
  def conj(c,t):
   requested['and']+=1;return AND(b,km,c,t)
  def rotate(q,turns):
   if turns:b.z_pow(q,2*turns);requested['rotations']+=1
  for j in range(1<<bits):
   flip=[i for i in range(bits) if not(j>>i)&1]
   for i in flip:b.x(seg[i])
   shared=[];control=seg[0]
   if mode=='factored':
    for i in range(1,bits):
     a=conj(control,seg[i]);shared.append((control,seg[i],a));control=a[0]
   for parity in (0,1):
    if parity==0:b.x(p[0])
    chain=[];active=control
    if mode=='independent':
     for i in range(1,bits):
      a=conj(active,seg[i]);chain.append((active,seg[i],a));active=a[0]
    a=conj(active,p[0]);chain.append((active,p[0],a));active=a[0]
    base,delta=tab[parity][j]
    rotate(active,Fraction(base%(1<<38),1<<38))
    for i in range(frac):
     if delta:
      q=conj(active,res[i])
      rotate(q[0],Fraction(delta*(1<<i),1<<(38+frac)))
      UNAND(b,km,active,res[i],q)
    for u,v,q in reversed(chain):UNAND(b,km,u,v,q)
    if parity==0:b.x(p[0])
   for u,v,q in reversed(shared):UNAND(b,km,u,v,q)
   for i in reversed(flip):b.x(seg[i])
  target=out/f'k082_{mode}_b{bits}.kmx'
  circ=b.finish_circuit();circ.to_file(str(target),format='kmx')
  result[mode]={'qubits':circ.num_qubits,'counts':counts(target),
                'source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'requested':requested}
 # Both variants compute the same exact rational phase function on all
 # address/frac computational bases. This is NOT a complete channel proof.
 for p in (0,1):
  for j in range(1<<bits):
   base,delta=tab[p][j]
   for f in range(1<<frac):
    direct=Fraction(base,1<<38)+Fraction(delta*f,1<<(38+frac))
    shared=Fraction(tab[p][j][0],1<<38)+Fraction(tab[p][j][1]*f,1<<(38+frac))
    assert direct==shared
 return {'status':'COMPILED_SYMBOLIC_PHASE_CHECK_ONLY','address_bits':bits,
  'cases':2*(1<<bits)*(1<<frac),'independent':result['independent'],'factored':result['factored'],
  'delta_CCX':result['factored']['counts']['CCX']-result['independent']['counts']['CCX'],
  'delta_qubits':result['factored']['qubits']-result['independent']['qubits']}
def k083(out):
 km=km_import()
 vals=[Fraction(1,16*(1<<i)) for i in range(4)]
 co=[vals[0],vals[1]-vals[0],vals[2]-vals[0],vals[3]-vals[2]-vals[1]+vals[0]]
 report={}
 for mode in ('equality','mobius'):
  b=km.CircuitBuilder();e=b.create_quantum_register(2,name='exponent');q=b.create_quantum_register(1,name='phase_bit')
  if mode=='equality':
   for i,alpha in enumerate(vals):
    flips=[j for j in (0,1) if not(i>>j)&1]
    for j in flips:b.x(e[j])
    anc=AND(b,km,e[0],e[1]);control=AND(b,km,anc[0],q[0])
    b.z_pow(control[0],2*alpha)
    UNAND(b,km,anc[0],q[0],control);UNAND(b,km,e[0],e[1],anc)
    for j in reversed(flips):b.x(e[j])
  else:
   b.z_pow(q[0],2*co[0])
   for i in (0,1):
    anc=AND(b,km,q[0],e[i]);b.z_pow(anc[0],2*co[1<<i]);UNAND(b,km,q[0],e[i],anc)
   anc=AND(b,km,e[0],e[1]);control=AND(b,km,q[0],anc[0])
   b.z_pow(control[0],2*co[3]);UNAND(b,km,q[0],anc[0],control);UNAND(b,km,e[0],e[1],anc)
  path=out/f'k083_{mode}.kmx';c=b.finish_circuit();c.to_file(str(path),format='kmx')
  report[mode]={'qubits':c.num_qubits,'counts':counts(path)}
 for e in range(4):
  v=co[0]+co[1]*(e&1)+co[2]*((e>>1)&1)+co[3]*((e&1)*((e>>1)&1))
  assert v==vals[e]
 return {'status':'COMPILED_EXACT_RATIONAL_PHASE_IDENTITY','basis_cases':8,
   'equality':report['equality'],'mobius':report['mobius'],
   'delta_CCX':report['mobius']['counts']['CCX']-report['equality']['counts']['CCX'],
   'warning':'2 exponent bits only, not a full invsqrt circuit'}
def k084():
 try:
  from qiskit import QuantumCircuit,transpile
  from qiskit.circuit.library import RCCXGate
  from qiskit.quantum_info import Operator
  import numpy as np
 except ImportError as e:return {'status':'SKIPPED_MISSING_QISKIT','reason':str(e)}
 a=QuantumCircuit(4);a.ccx(0,1,2);a.cx(2,3);a.ccx(0,1,2)
 b=QuantumCircuit(4);g=RCCXGate();b.append(g,[0,1,2]);b.cx(2,3);b.append(g.inverse(),[0,1,2])
 error=float(np.max(np.abs(Operator(a).data-Operator(b).data)))
 if error>1e-12:raise AssertionError('relative-phase identity failed: '+str(error))
 basis=['cx','h','t','tdg','s','sdg','x']
 x=transpile(a,basis_gates=basis,optimization_level=0)
 y=transpile(b,basis_gates=basis,optimization_level=0)
 return {'status':'EXACT_COMPLEX_OPERATOR_EQUIVALENCE','max_matrix_error':error,
         'exact_gate_counts':dict(x.count_ops()),'relative_phase_gate_counts':dict(y.count_ops()),
         'warning':'Qiskit 4-qubit clean-latch proof, not a Kickmix substitution or full circuit'}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--only',nargs='+',choices=['K082','K083','K084','K085'],default=['K082','K083','K084','K085'])
 p.add_argument('--bits',nargs='+',type=int,default=[3,4,5])
 p.add_argument('--fraction-bits',type=int,default=4)
 p.add_argument('--out',type=Path,default=ROOT/'competition/k082_085/results')
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 records={};errors={}
 for task in a.only:
  if task=='K085':continue
  try:
   if task=='K082':
    if any(not 2<=b<=6 for b in a.bits):raise ValueError('bits must be 2..6')
    records[task]={'cases':[k082(a.out,b,a.fraction_bits) for b in a.bits]}
    for row in records[task]['cases']:
     print('K082_CASE',json.dumps({'bits':row['address_bits'],'ccx_delta':row['delta_CCX'],
       'qubit_delta':row['delta_qubits']}),flush=True)
   elif task=='K083':records[task]=k083(a.out)
   elif task=='K084':records[task]=k084()
   print(task+'_RESULT',json.dumps(records[task],sort_keys=True),flush=True)
  except Exception as e:
   errors[task]=repr(e);print(task+'_ERROR',repr(e),flush=True)
 if 'K085' in a.only:
  records['K085']={'status':'ANALYSIS_ONLY','full_domain_verified':False,
   'promotion':'BLOCKED_UNTIL_OFFICIAL_FULL_DOMAIN_VERIFICATION',
   'completed':list(records),'failures':errors}
  print('K085_RESULT',json.dumps(records['K085'],sort_keys=True),flush=True)
 path=a.out/'suite.json';path.write_text(json.dumps({'results':records,'errors':errors},indent=2))
 print('SAVED',path,flush=True)
 if errors:sys.exit(2)
if __name__=='__main__':main()
