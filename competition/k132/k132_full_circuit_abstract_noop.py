#!/usr/bin/env python3
"""K132 full-source conservative abstract-state dead-gate screen.

Extends K131 beyond the first HMR without enumerating measurement outcomes.
Tracks each wire as definite 0, definite 1, or unknown, and each classical
bit similarly. Unknown measurements and conditions stay unknown. Candidate
removals are restricted to gates provably identity for EVERY possible input
and measurement outcome under this sound but coarse abstraction.

The HMR reset model (target -> 0 when executed) is as used in K127.
Unknown conditional events are joined across both branches. No official
verification or score improvement is claimed by this screen.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
Q=re.compile(r'^q(\d+)$',re.I)
B=re.compile(r'^b(\d+)$',re.I)
PHASE={'Z','S','S_DAG','T','T_DAG','Z_POW','CZ','CCZ'}
COUNTED={'CCX','CSWAP','CCZ','T','T_DAG','Z_POW'}
U=None
def xor(a,b):
 return a^b if a is not None and b is not None else None
def conj(*vs):
 if 0 in vs:return 0
 return 1 if all(v==1 for v in vs) else None
def neg(a):return None if a is None else 1-a
def join(a,b):return a if a==b else None

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k132/results/abstract_noop_screen.json'))
 p.add_argument('--candidate',type=Path,default=None)
 a=p.parse_args()
 raw=a.baseline.read_bytes()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit(f'Baseline mismatch {sha}')
 lines=raw.decode().splitlines()
 states=[None]*22+[0]*40
 bits={}
 stack=[]
 events=[];counts=collections.Counter();noops=collections.Counter()
 def bit(s):return bits.get(s,0)
 def condval(ts):
  guard=1
  if 'if' in ts:
   j=ts.index('if')
   if j+1>=len(ts) or not B.fullmatch(ts[j+1]):raise ValueError('unsupported condition')
   guard=conj(guard,bit(ts[j+1]))
  for v in stack:guard=conj(guard,v)
  return guard
 def update_q(k,value,guard):
  states[k]=value if guard==1 else states[k] if guard==0 else join(states[k],value)
 def update_b(k,value,guard):
  prior=bit(k)
  bits[k]=value if guard==1 else prior if guard==0 else join(prior,value)
 for i,line in enumerate(lines):
  ts=line.strip().split()
  if not ts or ts[0].startswith(('#','//')):continue
  ts=[t.lower() if t.lower()=='if' else t for t in ts]
  op=ts[0].upper();counts[op]+=1
  if op in ('REGISTER','APPEND_TO_REGISTER'):continue
  if op=='PUSH_CONDITION':
   if len(ts)!=3 or ts[1]!='if' or not B.fullmatch(ts[2]):raise ValueError(f'bad guard line {i+1}')
   stack.append(bit(ts[2]));continue
  if op=='POP_CONDITION':
   if not stack:raise ValueError(f'condition underflow line {i+1}')
   stack.pop();continue
  g=condval(ts)
  qs=[int(m.group(1)) for t in ts[1:] if (m:=Q.fullmatch(t))]
  if any(z>=len(states) for z in qs):raise ValueError(f'wire out of range {i+1}')
  v=[states[z] for z in qs]
  dead=False;reason=''
  if op=='NEG':
   # Global phase is not equivalent to no operation under official verifier.
   continue
  if op=='BIT_STORE0':update_b(ts[1],0,g);continue
  if op=='BIT_STORE1':update_b(ts[1],1,g);continue
  if op=='BIT_INVERT':update_b(ts[1],neg(bit(ts[1])),g);continue
  if op=='HMR':
   if len(qs)!=1:raise ValueError(f'bad HMR {i+1}')
   outputs=[t for t in ts[1:] if B.fullmatch(t)]
   if len(outputs)!=1:raise ValueError(f'bad HMR result {i+1}')
   # Measurement result is stochastic; do not infer a known value.
   update_b(outputs[0],None,g)
   update_q(qs[0],0,g)
   continue
  if op=='R':
   if len(qs)!=1:raise ValueError(f'bad R {i+1}')
   update_q(qs[0],0,g)
   continue
  if op in ('X','Y'):
   if len(qs)!=1:raise ValueError(f'bad {op} {i+1}')
   dead=g==0
   update_q(qs[0],neg(v[0]),g)
  elif op in ('CX','CNOT'):
   if len(qs)!=2:raise ValueError(f'bad CX {i+1}')
   dead=g==0 or v[0]==0
   update_q(qs[1],xor(v[1],v[0]),g)
  elif op=='CCX':
   if len(qs)!=3:raise ValueError(f'bad CCX {i+1}')
   d=conj(v[0],v[1])
   dead=g==0 or d==0
   update_q(qs[2],xor(v[2],d),g)
  elif op=='SWAP':
   if len(qs)!=2:raise ValueError(f'bad SWAP {i+1}')
   dead=g==0 or (v[0] is not None and v[0]==v[1])
   update_q(qs[0],v[1],g);update_q(qs[1],v[0],g)
  elif op=='CSWAP':
   if len(qs)!=3:raise ValueError(f'bad CSWAP {i+1}')
   dead=g==0 or v[0]==0 or (v[1] is not None and v[1]==v[2])
   switch=conj(v[0],g)
   # If switch unknown, join two basis branches.
   if switch==1:
    states[qs[1]]=v[2];states[qs[2]]=v[1]
   elif switch==0:pass
   else:
    states[qs[1]]=join(v[1],v[2]);states[qs[2]]=join(v[2],v[1])
  elif op in PHASE:
   required={'Z':1,'S':1,'S_DAG':1,'T':1,'T_DAG':1,'Z_POW':1,'CZ':2,'CCZ':3}[op]
   if len(qs)!=required:raise ValueError(f'bad phase opcode line {i+1}: {line}')
   dead=g==0 or 0 in v
   if op=='Z_POW' and len(ts)<3:raise ValueError(f'bad Z_POW {i+1}')
  elif op=='I':
   dead=True
  else:
   raise ValueError(f'unsupported opcode line {i+1}: {line}')
  if dead:
   reason='guard_const_zero' if g==0 else 'definite_basis_noop'
   noops[op]+=1
   events.append({'line':i+1,'opcode':op,'reason':reason,'text':line.strip(),
       'guard':g,'operand_abstract_values':v})
   if len(events)<=30:print('K132_NOOP',json.dumps(events[-1]),flush=True)
 if stack:raise ValueError('unbalanced condition stack')
 source_scored=sum(noops[k] for k in ('CCX','CSWAP','CCZ'))
 phase_sites=noops['Z_POW']
 status='SCORED_CANDIDATE_FOUND' if source_scored or phase_sites else 'NO_SCORED_CANDIDATE'
 report={'experiment':'K132','status':status,'baseline_sha256':sha,
   'source_lines':len(lines),'tracked_opcodes':dict(counts),
   'proven_source_noops':dict(noops),'noops':events,
   'source_toffoli_class_sites':source_scored,'source_z_pow_sites':phase_sites,
   'candidate_generated':False,
   'limitations':['Three-valued abstract propagation overapproximates quantum basis values; it is not full-state simulation.',
     'HMR is modeled as reset to zero when executed as in the K127 symbolic model.',
     'Source-level removals have no guaranteed executed count saving: condition guards may be rare or impossible.',
     'All output-register/phase semantics still require official verification.',
     'Only gates logically inactive under all abstract states are emitted; no angle or Boolean factoring.']}
 if a.candidate and (source_scored or phase_sites):
  excluded={e['line'] for e in events}
  a.candidate.parent.mkdir(parents=True,exist_ok=True)
  a.candidate.write_text('\n'.join(s for i,s in enumerate(lines,1) if i not in excluded)+'\n')
  report['candidate_generated']=True
  report['candidate_path']=str(a.candidate)
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('K132_RESULT',json.dumps({k:report[k] for k in (
  'status','source_lines','proven_source_noops','source_toffoli_class_sites',
  'source_z_pow_sites','candidate_generated')}),flush=True)
 print('K132_OUTPUT',str(a.out),flush=True)
if __name__=='__main__':main()
