#!/usr/bin/env python3
"""Branch-aware exact Boolean propagation and certified-zero wire recycling.
HMR outcomes remain independent unknowns. Classical feed-forward is explicitly
modeled, including condition stacks. Large polynomials become opaque symbols;
only proved zero states end a lifetime. No measurement/control is discarded by
assuming a sampled result. Registers keep their original physical wires.
"""
import argparse,collections,hashlib,heapq,itertools,json,re,time
from pathlib import Path
Q=re.compile(r'\bq(\d+)\b');B=re.compile(r'\bb(\d+)\b')
ZERO=frozenset();ONE=frozenset({frozenset()})
class Model:
 def __init__(self,width=22,cap=256):
  self.counter=itertools.count(width);self.q={i:frozenset({frozenset({i})}) for i in range(width)};self.bits={};self.guard=ONE;self.stack=[];self.cap=cap;self.opaque={};self.stats=collections.Counter()
 def fresh(self):return frozenset({frozenset({next(self.counter)})})
 def opaque_value(self,key):
  if key not in self.opaque:self.opaque[key]=self.fresh();self.stats['opaque_nodes']+=1
  return self.opaque[key]
 def xor(self,a,b):
  if a==b:return ZERO
  v=a^b
  return v  # Keep XOR exact; only nonlinear distribution is budgeted.
 def mul(self,a,b):
  if not a or not b:return ZERO
  if a==ONE:return b
  if b==ONE or a==b:return a
  if len(a)*len(b)>4096:return self.opaque_value(('and',frozenset((a,b))))
  v=set()
  for x in a:
   for y in b:
    z=x|y
    if z in v:v.remove(z)
    else:v.add(z)
  return frozenset(v) if len(v)<=self.cap else self.opaque_value(('and',frozenset((a,b))))
 def getq(self,q):return self.q.get(q,ZERO)
 def getb(self,b):
  if b not in self.bits:self.bits[b]=ZERO  # invsqrt has no classical input registers
  return self.bits[b]
 def step(self,line):
  s=line.strip();op=s.split()[0] if s else '';qs=list(map(int,Q.findall(s)));bs=list(map(int,B.findall(s)));active=self.mul(self.guard,self.getb(bs[-1])) if ' if ' in s else self.guard
  writes=set();keep=True
  if op=='PUSH_CONDITION':self.stack.append(self.guard);self.guard=active
  elif op=='POP_CONDITION':self.guard=self.stack.pop()
  elif op in ('X','CX','CCX'):
   effect=active
   for q in qs[:-1]:effect=self.mul(effect,self.getq(q))
   t=qs[-1];self.q[t]=self.xor(self.getq(t),effect);writes.add(t)
   if not effect:keep=False;self.stats[op+'_zero_effect']+=1
  elif op in ('SWAP','CSWAP'):
   a,b=qs[-2:];effect=self.mul(active,self.xor(self.getq(a),self.getq(b)))
   if op=='CSWAP':effect=self.mul(effect,self.getq(qs[0]))
   qa,qb=self.getq(a),self.getq(b);self.q[a]=self.xor(qa,effect);self.q[b]=self.xor(qb,effect);writes.update((a,b))
   if not effect:keep=False;self.stats[op+'_zero_effect']+=1
  elif op in ('Z','CZ','CCZ','Z_POW'):
   effect=active
   for q in qs:effect=self.mul(effect,self.getq(q))
   if not effect:keep=False;self.stats[op+'_zero_phase']+=1
  elif op in ('HMR','R'):
   t=qs[0];old=self.getq(t);self.q[t]=self.mul(old,self.xor(ONE,active));writes.add(t)
   if op=='HMR':
    b=bs[0];oldb=self.getb(b);rnd=self.fresh();self.bits[b]=self.xor(oldb,self.mul(active,self.xor(oldb,rnd)))
  elif op in ('BIT_STORE0','BIT_STORE1'):
   b=bs[0];old=self.getb(b);new=ONE if op=='BIT_STORE1' else ZERO;self.bits[b]=self.xor(old,self.mul(active,self.xor(old,new)))
  elif op=='BIT_INVERT':b=bs[0];self.bits[b]=self.xor(self.getb(b),active)
  elif op in ('NEG','REGISTER','APPEND_TO_REGISTER') or not op:pass
  else:raise ValueError('unsupported opcode: '+s)
  return qs,writes,keep

def transform(lines,cap=256,borrow_inputs=False):
 model=Model(cap=cap);reserved={int(q) for s in lines if s.startswith('APPEND_TO_REGISTER') for q in Q.findall(s)};segments=[];active={};bindings={};filtered=[];zero_closures=collections.Counter()
 if reserved!=set(range(22)):raise ValueError('adapter requires the 22-qubit invsqrt x register and no other quantum registers')
 if borrow_inputs:
  for q in sorted(reserved):active[q]=len(segments);segments.append([0,0,q])
 for original,line in enumerate(lines):
  qs,writes,keep=model.step(line)
  if not keep:continue
  i=len(filtered);filtered.append(line)
  for q in qs:
   if q in reserved and not borrow_inputs:continue
   if q not in active:active[q]=len(segments);segments.append([i,i,q])
   j=active[q];segments[j][1]=i;bindings[i,q]=j
  for q in qs:
   if (q not in reserved or borrow_inputs) and q in active and not model.getq(q):
    active.pop(q);zero_closures['reset' if line.startswith(('HMR','R ')) else 'algebraic']+=1
 end=len(filtered)
 unproved={q:segments[j][1] for q,j in active.items()}
 for j in active.values():segments[j][1]=end
 events=collections.Counter()
 for start,stop,q in segments:events[start]+=1;events[stop+1]-=1
 live=0;peak=0;peak_line=0
 for line,delta in sorted(events.items()):
  live+=delta
  if live>peak:peak=live;peak_line=line
 assert reserved==set(range(len(reserved)))
 free=[];busy=[];mapping={};nextq=len(reserved)
 fixed={q:[] for q in reserved}
 if borrow_inputs:
  for j,(start,stop,q) in enumerate(segments):
   if q in reserved:fixed[q].append((start,stop));mapping[j]=q
  for q in fixed:fixed[q].sort()
 def collides(wire,start,stop):
  if wire not in fixed:return False
  import bisect
  ranges=fixed[wire];k=bisect.bisect_right(ranges,(stop,10**20))-1
  return k>=0 and ranges[k][1]>=start
 intervals=[(j,v) for j,v in enumerate(segments) if not (borrow_inputs and v[2] in reserved)]
 for j,(start,stop,q) in sorted(intervals,key=lambda v:v[1][0]):
  while busy and busy[0][0]<start:
   _,wire=heapq.heappop(busy);heapq.heappush(free,wire)
  if borrow_inputs:
   occupied={wire for _,wire in busy}
   available=next((wire for wire in range(nextq) if wire not in occupied and not collides(wire,start,stop)),None)
   if available is None:wire=nextq;nextq+=1
   else:wire=available
  elif free:wire=heapq.heappop(free)
  else:wire=nextq;nextq+=1
  mapping[j]=wire;heapq.heappush(busy,(stop,wire))
 out=[]
 for i,line in enumerate(filtered):out.append(Q.sub(lambda m:'q'+str(int(m[1]) if int(m[1]) in reserved else mapping[bindings[i,int(m[1])]]),line))
 report={'qubits':nextq,'segments':len(segments),'zero_closures':dict(zero_closures),'statistics':dict(model.stats),'opaque_operations':dict(collections.Counter(key[0] for key in model.opaque)),'remaining_unproved_scratch':sum(q not in reserved for q in active),'active_registered_wires':sum(q in reserved for q in active),'cap':cap,'interval_clique_bound':peak,'peak_line':peak_line+1,'unproved_final_wires':unproved,'input_registers_reserved':sorted(reserved),'borrow_input_zero_gaps':borrow_inputs}
 return out,report

def selftest():
 # Branch-dependent X operations cancel only with the same unknown outcome.
 m=Model();m.step('HMR q22 b0');m.step('X q23 if b0');assert m.getq(23);m.step('X q23 if b0');assert not m.getq(23)
 m=Model();m.step('HMR q22 b0');m.step('PUSH_CONDITION if b0');m.step('X q23');m.step('POP_CONDITION');m.step('X q23 if b0');assert not m.getq(23)
 m=Model();m.step('HMR q22 b0');m.step('BIT_STORE0 b1');m.step('BIT_INVERT b1 if b0');m.step('X q23 if b0');m.step('X q23 if b1');assert not m.getq(23)
 # Every Boolean polynomial operation is independently checked on all 3-bit assignments.
 import random
 rng=random.Random(97097)
 def val(p,x):return sum(int(all((x>>i)&1 for i in mon)) for mon in p)%2
 for _ in range(200):
  a=frozenset(frozenset(i for i in range(3) if mask>>i&1) for mask in range(8) if rng.randrange(2));b=frozenset(frozenset(i for i in range(3) if mask>>i&1) for mask in range(8) if rng.randrange(2));m=Model()
  for x in range(8):assert val(m.mul(a,b),x)==(val(a,x)&val(b,x)) and val(m.xor(a,b),x)==(val(a,x)^val(b,x))
 return {'branch_identities':'PASS','polynomial_pairs':200,'assignments_each':8}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cap',type=int,default=256);p.add_argument('--borrow-inputs',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print(selftest(),flush=True);t=time.monotonic();new,r=transform(a.source.read_text().splitlines(keepends=True),a.cap,a.borrow_inputs);(a.out/'candidate.kmx').write_text(''.join(new));r['elapsed_s']=time.monotonic()-t;(a.out/'lifetime_report.json').write_text(json.dumps(r,indent=2));print('K097_LIFETIME',json.dumps(r),flush=True)
