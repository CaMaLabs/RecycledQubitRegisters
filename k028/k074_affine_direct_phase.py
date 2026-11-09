#!/usr/bin/env python3
"""K074 exact 4-bit affine QROM phase oracle, bounded x=1..15 only."""
import argparse,itertools,math,json,sys,importlib.util,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BITS=36;N=4;MASK=(1<<BITS)-1
def parity(x):return x.bit_count()&1
def addr(x,rows):return sum(parity(x&r)<<i for i,r in enumerate(rows))
def rank(rows):
 b={}
 for r in rows:
  v=r
  while v:
   j=v.bit_length()-1
   if j in b:v^=b[j]
   else:b[j]=v;break
 return len(b)
def mobius(table):
 out=list(table)
 for k in range(N):
  for i in range(1<<N):
   if i&(1<<k):out[i]^=out[i^(1<<k)]
 return out
def transform(rows):
 work=list(rows);ops=[]
 for c in range(N):
  if not (work[c]>>c)&1:
   j=next(j for j in range(c+1,N) if (work[j]>>c)&1)
   for dest,source in ((c,j),(j,c),(c,j)):
    work[dest]^=work[source];ops.append((dest,source))
  for j in range(N):
   if j!=c and ((work[j]>>c)&1):
    work[j]^=work[c];ops.append((j,c))
 assert work==[1<<i for i in range(N)]
 return list(reversed(ops))
def phase_table():
 return [0]+[round((1/math.sqrt(x))*(1<<BITS))&MASK for x in range(1,16)]
def assess(table,rows):
 mapped=[0]*16
 for x,v in enumerate(table):mapped[addr(x,rows)]=v
 anf=mobius(mapped)
 cx=sum(v.bit_count() for v in anf[1:])
 andcost=sum((m.bit_count()-1)*2 for m,v in enumerate(anf) if v and m.bit_count()>1)
 ops=transform(rows)
 return dict(basis=list(rows),anf=[hex(x) for x in anf],cost_proxy=2*(cx+andcost+len(ops)),
             lookup_controlled_cx_one_way=cx,and_compute_uncompute_one_way=andcost,
             basis_cx_one_way=len(ops),transform_ops=ops)
def search(table):
 ident=assess(table,(1,2,4,8));best=ident;count=0
 for rows in itertools.product(range(1,16),repeat=4):
  if rank(rows)!=4:continue
  count+=1;r=assess(table,rows)
  if (r['cost_proxy'],r['lookup_controlled_cx_one_way'],r['basis_cx_one_way'])<(best['cost_proxy'],best['lookup_controlled_cx_one_way'],best['basis_cx_one_way']):best=r
 assert count==20160
 return ident,best,count
def simulated(x,m):
 y=addr(x,m['basis']);v=0
 for i,s in enumerate(m['anf']):
  if (y&i)==i:v^=int(s,16)
 return v
def validate(table,m):
 for x,w in enumerate(table):
  assert simulated(x,m)==w
  if x:
   phase=simulated(x,m)/(1<<BITS);true=1/math.sqrt(x)
   assert min(abs(phase-true-k) for k in (-1,0,1))/(true*2**-24)<0.5
def build(m,path):
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 b=km.CircuitBuilder();x=b.create_quantum_register(22,name='x');a=x[:4]
 for t,s in m['transform_ops']:b.cx(a[s],a[t])
 word=b.alloc_qubits(BITS)
 def load():
  for mask,hexword in enumerate(m['anf']):
   v=int(hexword,16)
   if not v:continue
   cs=[a[j] for j in range(4) if mask&(1<<j)]
   if not cs:
    for k in range(BITS):
     if v&(1<<k):b.x(word[k])
   elif len(cs)==1:
    for k in range(BITS):
     if v&(1<<k):b.cx(cs[0],word[k])
   else:
    anc=[];c=cs[0]
    for other in cs[1:]:
     q=b.alloc_qubits(1)
     b.init_and(c,km.array([other]),km.array([q[0]]))
     anc.append((c,other,q));c=q[0]
    for k in range(BITS):
     if v&(1<<k):b.cx(c,word[k])
    for u,v,q in reversed(anc):
     b.del_and(u,km.array([v]),km.array([q[0]]));b.free(q)
 load()
 for k in range(BITS):b.z_pow(word[k],2**(k+1-BITS))
 load();b.free(word)
 for t,s in reversed(m['transform_ops']):b.cx(a[s],a[t])
 circuit=b.finish_circuit();circuit.to_file(str(path),format='kmb')
 return {'num_qubits':circuit.num_qubits,'file_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def verify(path,timeout):
 modpath=ROOT/'competition/k031/k031_full_domain_repair.py'
 spec=importlib.util.spec_from_file_location('k031_k074',modpath)
 mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
 return mod.verify(path,15,12345,timeout)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--self-test',action='store_true')
 p.add_argument('--build',action='store_true')
 p.add_argument('--timeout',type=int,default=300)
 p.add_argument('--out',type=Path,default=ROOT/'competition/k074/results')
 a=p.parse_args();table=phase_table();identity,best,count=search(table)
 validate(table,identity);validate(table,best)
 print('K074_SELFTEST PASS 20160 GL4 affine bases; exact lookup truth table and modulo-one accuracy',flush=True)
 if a.self_test:return
 a.out.mkdir(parents=True,exist_ok=True)
 report={'status':'ARCHITECTURE_ONLY','domain':'x=1..15 ONLY','identity':identity,'best':best,
         'cost_proxy_saving':identity['cost_proxy']-best['cost_proxy'],
         'warning':'This does not cover all 22-bit inputs. Gate proxy is NOT official score.'}
 if a.build:
  for label,model in (('identity',identity),('optimized',best)):
   try:
    dest=a.out/(label+'.kmb');circuit=build(model,dest);result=verify(dest,a.timeout)
    report[label+'_official']={'build':circuit,'verification':result}
    print('K074_VERIFY',json.dumps({'label':label,'circuit':circuit,'official':result},default=str,sort_keys=True),flush=True)
   except Exception as e:
    report[label+'_error']=repr(e)
    print('K074_ERROR',json.dumps({'label':label,'error':repr(e)}),flush=True)
  report['status']='BUILT_AND_CHECKED_BOUNDED'
 (a.out/'report.json').write_text(json.dumps(report,indent=2,default=str))
 print('K074_RESULT',json.dumps({'status':report['status'],'bases_tested':count,
        'identity_proxy':identity['cost_proxy'],'best_proxy':best['cost_proxy'],
        'best_basis':best['basis'],'basis_cx':best['basis_cx_one_way'],
        'saving_proxy':report['cost_proxy_saving']},sort_keys=True),flush=True)
 print('SAVED',a.out/'report.json',flush=True)
if __name__=='__main__':main()
