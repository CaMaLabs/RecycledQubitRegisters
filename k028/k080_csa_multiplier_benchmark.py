#!/usr/bin/env python3
"""K080: isolated signed reversible multiplier A/B architecture benchmark.
Row-adder control uses K034; candidate uses coherent 3:2 carry-save
compression, final carry propagation, copy-out, and clean uncomputation.
All integer arithmetic is verified exhaustively at small widths.
KMX counts are resource proxies, NOT an official invsqrt verification.
"""
import argparse,collections,hashlib,importlib.util,itertools,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def signed(x,w):return x-(1<<w) if x>>(w-1) else x
def arithmetic_check():
 checks=0
 for w in range(2,7):
  for tb in range(3,7):
   pw=w+tb;mod=(1<<pw)-1
   for a,t in itertools.product(range(1<<w),range(1<<tb)):
    rows=[((signed(a,w)*((t>>j)&1))<<j)&mod for j in range(tb)]
    while len(rows)>2:
     new=[]
     for j in range(0,len(rows),3):
      if j+2>=len(rows):new+=rows[j:];continue
      x,y,z=rows[j:j+3]
      new.extend(((x^y^z)&mod,(((x&y)|((x^y)&z))<<1)&mod))
     rows=new
    assert sum(rows)&mod==(signed(a,w)*t)&mod,(w,tb,a,t)
    checks+=1
 return checks
def load():
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 p=ROOT/'competition/k034/k034_row_local_scratch.py'
 if not p.is_file():raise FileNotFoundError(p)
 s=importlib.util.spec_from_file_location('k034_k080',p)
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
 return km,m
def AND(b,km,x,y):
 a=b.alloc_qubits(1)
 b.init_and(x,km.array([y]),km.array([a[0]]))
 return a
def UNAND(b,km,x,y,a):
 b.del_and(x,km.array([y]),km.array([a[0]]));b.free(a)
def row_new(b,km,a,t,w,pw,j):
 r=b.alloc_qubits(pw)
 for i in range(w):
  b.init_and(t,km.array([a[i]]),km.array([r[i+j]]))
 for i in range(j+w,pw):b.cx(r[j+w-1],r[i])
 return r
def row_clear(b,km,r,a,t,w,pw,j):
 for i in reversed(range(j+w,pw)):b.cx(r[j+w-1],r[i])
 for i in reversed(range(w)):
  b.del_and(t,km.array([a[i]]),km.array([r[i+j]]))
 b.free(r)
def compressor(b,km,x,y,z,pw,undo=False,s=None,c=None):
 if not undo:s=b.alloc_qubits(pw);c=b.alloc_qubits(pw)
 indices=reversed(range(pw)) if undo else range(pw)
 for i in indices:
  if not undo:
   for q in (x[i],y[i],z[i]):b.cx(q,s[i])
  if i+1<pw:
   tmp=b.alloc_qubits(1)
   b.cx(x[i],tmp[0]);b.cx(y[i],tmp[0])
   xy=AND(b,km,x[i],y[i]);tc=AND(b,km,tmp[0],z[i])
   b.cx(xy[0],c[i+1]);b.cx(tc[0],c[i+1])
   UNAND(b,km,tmp[0],z[i],tc);UNAND(b,km,x[i],y[i],xy)
   b.cx(y[i],tmp[0]);b.cx(x[i],tmp[0]);b.free(tmp)
  if undo:
   for q in (z[i],y[i],x[i]):b.cx(q,s[i])
 if undo:b.free(c);b.free(s)
 else:return s,c
def build_row(km,k034,w,tb,path):
 pw=w+tb;b=km.CircuitBuilder()
 a=b.create_quantum_register(w,name='a')
 t=b.create_quantum_register(tb,name='t')
 scratch=b.alloc_qubits(pw);out=b.alloc_qubits(pw)
 counts={'rows':0,'allocated_sum':0,'max_row_width':0}
 row=k034.local_row('compact',counts)
 def partial(j,inv):
  row(b,inv,t[j],[(a[i],i+j) for i in range(w-1)],scratch,km.array([]),subtract=False)
  row(b,inv,t[j],[(a[w-1],j+w-1)],scratch,km.array([]),subtract=True)
 for j in range(tb):partial(j,False)
 for i in range(pw):b.cx(scratch[i],out[i])
 for j in reversed(range(tb)):
  row(b,True,t[j],[(a[w-1],j+w-1)],scratch,km.array([]),subtract=True)
  row(b,True,t[j],[(a[i],i+j) for i in range(w-1)],scratch,km.array([]),subtract=False)
 b.free(scratch);circ=b.finish_circuit();circ.to_file(str(path),format='kmx')
 return {'num_qubits':circ.num_qubits,'row_count':counts['rows']}
def build_csa(km,w,tb,path):
 pw=w+tb;b=km.CircuitBuilder()
 a=b.create_quantum_register(w,name='a')
 t=b.create_quantum_register(tb,name='t')
 originals=[row_new(b,km,a,t[j],w,pw,j) for j in range(tb)]
 rows=originals.copy();history=[]
 while len(rows)>2:
  nxt=[]
  for k in range(0,len(rows),3):
   if k+2>=len(rows):nxt.extend(rows[k:]);continue
   x,y,z=rows[k:k+3]
   s,c=compressor(b,km,x,y,z,pw)
   history.append((x,y,z,s,c));nxt.extend((s,c))
  rows=nxt
 scratch=b.alloc_qubits(pw);out=b.alloc_qubits(pw)
 b.iadd(rows[0],target=scratch)
 if len(rows)>1:b.iadd(rows[1],target=scratch)
 for i in range(pw):b.cx(scratch[i],out[i])
 if len(rows)>1:b.isub(rows[1],target=scratch)
 b.isub(rows[0],target=scratch);b.free(scratch)
 for x,y,z,s,c in reversed(history):
  compressor(b,km,x,y,z,pw,undo=True,s=s,c=c)
 for j in reversed(range(tb)):
  row_clear(b,km,originals[j],a,t[j],w,pw,j)
 circ=b.finish_circuit();circ.to_file(str(path),format='kmx')
 return {'num_qubits':circ.num_qubits,'compressors':len(history)}
def counts(path):
 d=collections.Counter()
 for line in path.open():
  s=line.strip()
  if s and not s.startswith('#'):d[s.split()[0]]+=1
 return {'ops':sum(d.values()),'CCX':d['CCX'],'CCZ':d['CCZ'],
  'CSWAP':d['CSWAP'],'HMR':d['HMR'],'CX':d['CX'],'CZ':d['CZ'],
  'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--self-test',action='store_true')
 p.add_argument('--widths',type=int,nargs='+',default=[6,8])
 p.add_argument('--tb',type=int,default=5)
 p.add_argument('--out',type=Path,default=ROOT/'competition/k080/results')
 args=p.parse_args()
 n=arithmetic_check()
 print('K080_SELFTEST',json.dumps({'status':'PASS','exhaustive_cases':n}),flush=True)
 if args.self_test:return
 km,k034=load();args.out.mkdir(parents=True,exist_ok=True)
 results=[]
 for w in args.widths:
  try:
   assert 3<=w<=20 and 3<=args.tb<=20
   rb=args.out/f'row_w{w}_t{args.tb}.kmx'
   cb=args.out/f'csa_w{w}_t{args.tb}.kmx'
   reference=build_row(km,k034,w,args.tb,rb)
   candidate=build_csa(km,w,args.tb,cb)
   rc=counts(rb);cc=counts(cb)
   r={'width':w,'tb':args.tb,'status':'COMPILED_NOT_VERIFIED',
     'row':{**reference,**rc},'csa':{**candidate,**cc},
     'ccx_delta':cc['CCX']-rc['CCX'],
     'ccz_delta':cc['CCZ']-rc['CCZ'],
     'qubit_delta':candidate['num_qubits']-reference['num_qubits']}
  except Exception as exc:r={'width':w,'tb':args.tb,'status':'BUILD_ERROR','error':repr(exc)}
  results.append(r);print('K080_CASE',json.dumps(r,sort_keys=True),flush=True)
 report={'status':'RESOURCE_PROXY_ONLY','cases':results,'arithmetic_cases':n,
   'caution':'Independent arithmetic proof is not a quantum-channel proof. Compare compiled op counts only; official invsqrt verifier needed after integration.'}
 target=args.out/'report.json';target.write_text(json.dumps(report,indent=2))
 print('K080_RESULT',json.dumps({'status':report['status'],
  'cases':[{'width':v['width'],'status':v['status'],'ccx_delta':v.get('ccx_delta'),
   'qubit_delta':v.get('qubit_delta'),'error':v.get('error')} for v in results]},sort_keys=True),flush=True)
 print('SAVED',target,flush=True)
if __name__=='__main__':main()
