"""Exact multi-output rank-one nonlinear resynthesis, Clifford basis changes.
Generalizes single-target ANF factoring. Each adopted window is exhaustively
compared on every input, so phase-free permutation equality holds coherently.
"""
import collections

def affine_circuit(rows,constant,wires):
 rows=list(rows);n=len(rows);ops=[]
 for col in range(n):
  pivot=next((j for j in range(col,n) if rows[j]>>col&1),None)
  if pivot is None:return None
  if pivot!=col:
   rows[pivot],rows[col]=rows[col],rows[pivot];ops.extend([('CX',(wires[pivot],wires[col])),('CX',(wires[col],wires[pivot])),('CX',(wires[pivot],wires[col]))])
  for j in range(n):
   if j!=col and rows[j]>>col&1:
    rows[j]^=rows[col];ops.append(('CX',(wires[col],wires[j])))
 assert rows==[1<<i for i in range(n)]
 return list(reversed(ops))+[('X',(wires[i],)) for i in range(n) if constant>>i&1]

def synth(block,anf,quad,max_wires=8):
 wires=tuple(sorted({q for _,qs in block for q in qs}));n=len(wires)
 old=sum(op=='CCX' for op,_ in block)
 if old<2 or n>max_wires:return None
 mapping=anf.perm(block,wires)
 polys=[set(anf.anf([(v>>i)&1 for v in mapping])) for i in range(n)]
 nonlinear=[{m for m in p if m.bit_count()>1} for p in polys]
 nonempty={frozenset(p) for p in nonlinear if p}
 if len(nonempty)!=1:return None
 if any(m.bit_count()>2 for m in next(iter(nonempty))):return None
 active=[i for i,p in enumerate(nonlinear) if p];t=active[0]
 elim=[('CX',(wires[t],wires[j])) for j in active[1:]]
 # Apply output elimination to all truth tables / ANF polynomials.
 for j in active[1:]:polys[j]^=polys[t]
 rows=[sum(m for m in p if m.bit_count()==1) for p in polys]
 const=sum((0 in p)<<i for i,p in enumerate(polys))
 # Controls are affine and must have rank n-1. Choose any completion.
 for r in [rows[t]]+[1<<i for i in range(n)]:
  trial=rows.copy();trial[t]=r
  prefix=affine_circuit(trial,const,wires)
  if prefix is not None:break
 else:return None
 zmap=anf.perm(prefix,wires);values=[0]*(1<<n)
 for x,z in enumerate(zmap):values[z]=((mapping[x]>>t)&1)^((z>>t)&1)
 # h cannot depend on its own target; otherwise reject.
 if any(values[z]!=values[z^(1<<t)] for z in range(1<<n)):return None
 controls=[i for i in range(n) if i!=t]
 truth=[values[sum(((x>>j)&1)<<i for j,i in enumerate(controls))] for x in range(1<<len(controls))]
 terms=set(anf.anf(truth))
 if any(v.bit_count()>2 for v in terms):return None
 ex={'target':wires[t],'wires':tuple(wires[i] for i in controls),'polynomial':terms,'controls':[]}
 folded,_=quad.quadratic_synth(ex)
 candidate=prefix+folded+list(reversed(elim))
 new=sum(op=='CCX' for op,_ in candidate)
 if new>=old:return None
 assert anf.perm(candidate,wires)==mapping,'multi-output exhaustive equality failed'
 return {'gates':candidate,'saved':old-new,'before':old,'after':new,'wires':list(wires)}

def optimize(lines,anf,quad,max_wires=8,max_span=120):
 parsed=[anf.parse(s) for s in lines];hits=[];tested=0;i=0
 while i<len(parsed):
  if parsed[i] is None:i+=1;continue
  j=i+1
  while j<len(parsed) and parsed[j] is not None:j+=1
  indexes=[k for k in range(i,j) if parsed[k][0]=='CCX']
  for a,start in enumerate(indexes):
   for stop in indexes[a+1:a+9]:
    if stop-start>max_span:break
    if len({q for _,qs in parsed[start:stop+1] for q in qs})>max_wires:break
    tested+=1;r=synth(parsed[start:stop+1],anf,quad,max_wires) or shear_synth(parsed[start:stop+1],anf,quad,max_wires)
    if r:r.update(start=start,stop=stop+1);hits.append(r)
  i=j
 selected=[]
 for r in sorted(hits,key=lambda r:-r['saved']):
  if not any(r['start']<s['stop'] and s['start']<r['stop'] for s in selected):selected.append(r)
 out=[];cursor=0
 for r in sorted(selected,key=lambda r:r['start']):
  out+=lines[cursor:r['start']];out+=['%s %s\n'%(op,' '.join('q'+str(q) for q in qs)) for op,qs in r['gates']];cursor=r['stop']
 out+=lines[cursor:]
 return out,{'windows':tested,'hits':len(hits),'selected':len(selected),'ccx_saved':sum(r['saved'] for r in selected)}

def selftest(anf,quad):
 import random
 planted=[('CCX',(0,1,3)),('CCX',(0,2,3)),('CX',(3,4))]
 r=synth(planted,anf,quad);assert r and r['saved']==1
 rng=random.Random(96096)
 for _ in range(120):
  b=[]
  for j in range(rng.randrange(2,12)):
   op=rng.choice(('X','CX','CCX'));qs=tuple(rng.sample(range(5),{'X':1,'CX':2,'CCX':3}[op]));b.append((op,qs))
  synth(b,anf,quad);shear_synth(b,anf,quad)
 shared=[('CCX',(0,1,3)),('CCX',(0,2,3)),('CCX',(0,1,4))]
 shared_r=shear_synth(shared,anf,quad);assert shared_r and shared_r['saved']==1
 return {'planted_saved':r['saved'],'random_cases':120}

def shear_synth(block,anf,quad,max_wires=8):
 """Several nonlinear targets with a shared affine control subspace.
 Output Gaussian elimination combines quadratic functions before factorization.
 This covers QRR common-product/XOR sharing beyond a single target.
 """
 wires=tuple(sorted({q for _,qs in block for q in qs}));n=len(wires);old=sum(op=='CCX' for op,_ in block)
 if old<2 or n>max_wires:return None
 mapping=anf.perm(block,wires);polys=[set(anf.anf([(v>>i)&1 for v in mapping])) for i in range(n)];elim=[];basis={};targets=[]
 for j in range(n):
  while True:
   nonlinear={m for m in polys[j] if m.bit_count()>1}
   if not nonlinear:break
   pivot=max(nonlinear)
   if pivot not in basis:basis[pivot]=j;targets.append(j);break
   source=basis[pivot];polys[j]^=polys[source];elim.append(('CX',(wires[source],wires[j])))
 if not targets or n-len(targets)<2:return None
 rows=[sum(m for m in p if m.bit_count()==1) for p in polys];constant=sum((0 in p)<<i for i,p in enumerate(polys))
 prefix=affine_circuit(rows,constant,wires)
 if prefix is None:return None
 zmap=anf.perm(prefix,wires);ymap=anf.perm(block+elim,wires);controls=[j for j in range(n) if j not in targets];out=list(prefix)
 for t in targets:
  values=[0]*(1<<n)
  for x,z in enumerate(zmap):values[z]=((ymap[x]>>t)&1)^((z>>t)&1)
  if any(values[z]!=values[z^(1<<v)] for v in targets for z in range(1<<n)):return None
  truth=[values[sum(((x>>j)&1)<<i for j,i in enumerate(controls))] for x in range(1<<len(controls))];terms=set(anf.anf(truth))
  if any(m.bit_count()>2 for m in terms):return None
  folded,_=quad.quadratic_synth({'target':wires[t],'wires':tuple(wires[i] for i in controls),'polynomial':terms,'controls':[]});out+=folded
 out+=list(reversed(elim));new=sum(op=='CCX' for op,_ in out)
 if new>=old:return None
 assert anf.perm(out,wires)==mapping,'multi-target shear equality failed'
 return {'gates':out,'saved':old-new,'before':old,'after':new,'wires':list(wires)}
