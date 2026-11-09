#!/usr/bin/env python3
"""K070: conservative quantum/classical SSA dependency cones for KMX.
Read-only analysis; not a proof of equivalence or quantum-channel simulation.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
Q=re.compile(r'\bq(\d+)\b'); B=re.compile(r'\bb(\d+)\b')
PHASE={'Z','CZ','CCZ','Z_POW','NEG'}
GATES={'X','Y','H','S','T','R','CX','SWAP','CCX','CSWAP'}
META={'REGISTER','APPEND_TO_REGISTER','INFO_TAG'}
def parse(line,lineno):
 s=line.strip()
 if not s or s.startswith('#'):return None
 return lineno,s.split()[0].upper(),tuple(map(int,Q.findall(s))),tuple(map(int,B.findall(s))),s
class Graph:
 def __init__(self):
  self.nodes=[];self.q={};self.b={};self.scopes=[];self.sinks=[]
  self.counts=collections.Counter();self.unknown=collections.Counter()
 def add(self,kind,op,line,deps=(),desc=''):
  i=len(self.nodes);self.nodes.append((kind,op,line,tuple(dict.fromkeys(deps)),desc));return i
 def qv(self,q):
  if q not in self.q:self.q[q]=self.add('q_source','INPUT',0,desc='q'+str(q))
  return self.q[q]
 def bv(self,b):
  if b not in self.b:self.b[b]=self.add('b_source','UNKNOWN_BIT',0,desc='b'+str(b))
  return self.b[b]
 def event(self,item):
  if not item:return
  line,op,qs,bs,text=item;self.counts[op]+=1
  cond=tuple(bs[-1:] if ' if b' in text else ())
  controls=[self.bv(b) for b in self.scopes+list(cond)]
  if op in META:return
  if op=='PUSH_CONDITION':
   if bs:self.scopes.append(bs[-1])
   return
  if op=='POP_CONDITION':
   if self.scopes:self.scopes.pop()
   return
  if op in ('BIT_STORE0','BIT_STORE1'):
   if bs:self.b[bs[0]]=self.add('classical',op,line,controls)
   return
  if op=='BIT_INVERT':
   if len(bs)>=2:self.b[bs[0]]=self.add('classical',op,line,[self.bv(bs[0]),self.bv(bs[1])]+controls)
   return
  if op=='HMR':
   if qs:
    m=self.add('measurement',op,line,[self.qv(qs[0])]+controls)
    if bs:self.b[bs[0]]=m
    self.q[qs[0]]=self.add('post_measure','POST_HMR',line,[m])
   return
  if op in PHASE:
   deps=[self.qv(q) for q in qs]+controls
   sink=self.add('phase',op,line,deps,text[:160]);self.sinks.append(sink)
   # Store original states before overwriting outputs.
   old={q:self.qv(q) for q in qs}
   for q in qs:self.q[q]=self.add('quantum_phase_state',op,line,[old[q],sink])
   return
  if op in GATES:
   deps=[self.qv(q) for q in qs]+controls
   gate=self.add('quantum',op,line,deps)
   for q in qs:self.q[q]=self.add('quantum_state',op,line,[gate])
   return
  self.unknown[op]+=1
  gate=self.add('unknown',op,line,[self.qv(q) for q in qs]+[self.bv(b) for b in bs])
  for q in qs:self.q[q]=self.add('quantum_unknown',op,line,[gate])
  if op.startswith('BIT_') and bs:self.b[bs[0]]=gate
def ancestors(g,sink):
 seen=set();todo=[sink]
 while todo:
  i=todo.pop()
  if i not in seen:
   seen.add(i);todo.extend(g.nodes[i][3])
 return seen
def overview(g,ids):
 h=collections.Counter(g.nodes[i][1] for i in ids if g.nodes[i][0] in ('quantum','phase','measurement','classical'))
 return {'nodes':len(ids),'CCX':h['CCX'],'CCZ':h['CCZ'],
         'CSWAP':h['CSWAP'],'HMR':h['HMR'],'BIT_INVERT':h['BIT_INVERT'],
         'origin_qubits':sum(g.nodes[i][0]=='q_source' for i in ids),
         'unknown_classical_sources':sum(g.nodes[i][0]=='b_source' for i in ids)}
def selftest():
 g=Graph()
 for i,s in enumerate(('CCX q0 q1 q2','HMR q2 b4','BIT_STORE0 b5','BIT_INVERT b5 if b4','Z q3 if b5'),1):g.event(parse(s,i))
 ids=ancestors(g,g.sinks[-1]);o=overview(g,ids)
 assert o['CCX']==1 and o['HMR']==1 and o['BIT_INVERT']==1 and o['origin_qubits']>=2
 h=Graph();h.event(parse('CZ q0 q1 if b99',1))
 assert overview(h,ancestors(h,h.sinks[0]))['unknown_classical_sources']==1
 assert o['CCX']<=g.counts['CCX'] and o['HMR']<=g.counts['HMR']
 print('K070_SELFTEST PASS unique event counts, dependencies and unknown controls',flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--source',type=Path,default=ROOT/'competition/k059/results/helios_public.kmx')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k070/results')
 p.add_argument('--focus-start',type=int,default=25762)
 p.add_argument('--focus-end',type=int,default=25955)
 p.add_argument('--examples',type=int,default=4)
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 if a.self_test:selftest();return
 if not a.source.is_file():raise SystemExit('Missing KMX '+str(a.source))
 g=Graph()
 with a.source.open(errors='replace') as f:
  for i,s in enumerate(f,1):g.event(parse(s,i))
 focus=[i for i in g.sinks if a.focus_start<=g.nodes[i][2]<=a.focus_end]
 union=set()
 for i in focus:union.update(ancestors(g,i))
 assert overview(g,union)['CCX']<=g.counts['CCX']
 assert overview(g,union)['CSWAP']<=g.counts['CSWAP']
 report={'source':str(a.source),'sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
         'attribution':'Helios third-party benchmark' if 'helios' in a.source.name else 'CaMaLabs',
         'nodes':len(g.nodes),'instructions':sum(g.counts.values()),
         'focus_lines':[a.focus_start,a.focus_end],
         'phase_count':len(focus),
         'phase_opcodes':dict(collections.Counter(g.nodes[i][1] for i in focus)),
         'union_cone':overview(g,union),'unknown_opcodes':dict(g.unknown),
         'phase_samples':[{'line':g.nodes[i][2],'instruction':g.nodes[i][4],
                            'cone':overview(g,ancestors(g,i))}
                          for i in focus if g.nodes[i][1]=='Z_POW'][:a.examples],
         'warning':'Conservative overapproximation; phase and measurement dependencies are not equivalent to an exact channel model.'}
 a.out.mkdir(parents=True,exist_ok=True)
 (a.out/'dependency_cones.json').write_text(json.dumps(report,indent=2))
 print('K070_RESULT',json.dumps({k:report[k] for k in ('nodes','instructions','phase_count','phase_opcodes','union_cone','unknown_opcodes')},sort_keys=True),flush=True)
 for v in report['phase_samples']:print('K070_PHASE_CONE',json.dumps(v,sort_keys=True),flush=True)
 print('SAVED',a.out/'dependency_cones.json',flush=True)
if __name__=='__main__':main()
