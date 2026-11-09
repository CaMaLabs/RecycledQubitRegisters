"""QRR-style exact involution cancellation with control-aware commutation.
No measurement, classical-write, conditional-scope or unknown barrier is crossed.
"""
import collections

def normalized(g):
 op,q=g
 if op in ('CCZ','CZ'):q=tuple(sorted(q))
 if op=='CCX':q=tuple(sorted(q[:2]))+q[2:]
 if op=='CSWAP':q=q[:1]+tuple(sorted(q[1:]))
 return op,q

def commute(a,b):
 ao,aq=a;bo,bq=b
 if not(set(aq)&set(bq)):return True
 diag={'Z','CZ','CCZ','Z_POW','S','S_DAG','T','T_DAG'}
 if ao in diag and bo in diag:return True
 def writes(o,q):
  if o in diag:return set()
  if o in ('CX','CCX','X'):return {q[-1]}
  return set(q)
 xor={'X','CX','CCX'}
 if ao in xor and bo in xor:return not ({aq[-1]}&set(bq[:-1]) or {bq[-1]}&set(aq[:-1]))
 if ao in diag:return not(set(aq)&writes(bo,bq))
 if bo in diag:return not(set(bq)&writes(ao,aq))
 if ao=='CSWAP' and bo in xor:return not(set(aq[1:])&set(bq) or {bq[-1]}&set(aq))
 if bo=='CSWAP' and ao in xor:return commute(b,a)
 return normalized(a)==normalized(b)

def optimize(lines,parser):
 removed=collections.Counter()
 for _ in range(20):
  p=[parser(x) for x in lines];deleted=set()
  for i,g in enumerate(p):
   if i in deleted or not g or g[0] not in {'X','CX','CZ','CCX','CCZ','CSWAP','SWAP'}:continue
   for j in range(i-1,max(-1,i-10001),-1):
    if j in deleted:continue
    h=p[j]
    if not h:break
    if normalized(g)==normalized(h):deleted|={i,j};removed[g[0]]+=2;break
    if not commute(g,h):break
  if not deleted:break
  lines=[x for i,x in enumerate(lines) if i not in deleted]
 return lines,dict(removed)

def selftest():
 # Exhaustively prove every accepted pair of reversible/diagonal generators
 # on at most four wires, including their phases.
 import itertools
 gates=[]
 for op,n in [('X',1),('Z',1),('CX',2),('CZ',2),('CCX',3),('CCZ',3),('CSWAP',3),('SWAP',2)]:
  gates += [(op,q) for q in itertools.permutations(range(4),n)]
 def apply(g,v):
  op,q=g;phase=0
  if op=='X':v^=1<<q[0]
  elif op=='CX':v^=((v>>q[0])&1)<<q[1]
  elif op=='CCX':v^=(((v>>q[0])&1)&((v>>q[1])&1))<<q[2]
  elif op in ('SWAP','CSWAP'):
   a,b=q[-2:]
   if (op=='SWAP' or (v>>q[0])&1) and ((v>>a)&1)!=((v>>b)&1):v^=(1<<a)|(1<<b)
  else:phase=int(all((v>>i)&1 for i in q))
  return v,phase
 checked=0
 for a in gates:
  for b in gates:
   if not commute(a,b):continue
   for v in range(16):
    x,p=apply(a,v);x,r=apply(b,x);y,s=apply(b,v);y,t=apply(a,y)
    assert (x,p^r)==(y,s^t),(a,b,v)
   checked+=1
 return {'pair_identities':checked,'basis_states_per_pair':16}
