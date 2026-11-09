#!/usr/bin/env python3
"""K069 exact GF(2) ANF resynthesis of whole reversible blocks.

Search contiguous unconditional X/CX/CCX regions, derive complete small
truth tables, and replace single-target degree<=2 Boolean functions with
star-factored XOR/AND networks. Exhaustively prove each replacement.
Preserve all measurement, condition, phase, and register boundaries.
Helios circuit remains credited third-party reference, not original work.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OP=re.compile(r'^\s*(X|CX|CCX)\s+(q\d+)(?:\s+(q\d+))?(?:\s+(q\d+))?\s*$',re.I)
ARITY={'X':1,'CX':2,'CCX':3}
def parse(s):
 m=OP.fullmatch(s.strip())
 if not m:return None
 op=m[1].upper();qs=[v for v in m.groups()[1:] if v]
 if len(qs)!=ARITY[op]:return None
 q=tuple(int(v[1:]) for v in qs)
 return (op,q) if len(set(q))==len(q) else None
def perm(gates,wires):
 pos={q:i for i,q in enumerate(wires)}
 out=list(range(1<<len(wires)))
 for op,qs in gates:
  indexes=[pos[q] for q in qs];t=indexes[-1];controls=indexes[:-1]
  for i,v in enumerate(out):
   if all((v>>c)&1 for c in controls):out[i]=v^(1<<t)
 return out
def anf(truth):
 v=list(truth);n=(len(v)-1).bit_length()
 for i in range(n):
  for mask in range(1<<n):
   if mask&(1<<i):v[mask]^=v[mask^(1<<i)]
 return [m for m,x in enumerate(v) if x]
def synth(block,max_qubits):
 wires=tuple(sorted({q for op,qs in block for q in qs}))
 if not 3<=len(wires)<=max_qubits:return None
 mapping=perm(block,wires)
 changed=[i for i in range(len(wires)) if any(((x^y)>>i)&1 for x,y in enumerate(mapping))]
 if len(changed)!=1:return None
 ti=changed[0];target=wires[ti];controls=tuple(q for q in wires if q!=target)
 pos={q:i for i,q in enumerate(wires)};truth=[]
 for x in range(1<<len(controls)):
  state=sum(((x>>i)&1)<<pos[q] for i,q in enumerate(controls))
  f=(mapping[state]>>ti)&1
  if ((mapping[state^(1<<ti)]>>ti)&1)!=(f^1):return None
  truth.append(f)
 terms=anf(truth)
 if any(t.bit_count()>2 for t in terms):return None
 out=[]
 if 0 in terms:out.append(('X',(target,)))
 edges=set()
 for t in terms:
  degree=t.bit_count()
  if degree==1:out.append(('CX',(controls[t.bit_length()-1],target)))
  elif degree==2:
   nodes=tuple(sorted(controls[i] for i in range(len(controls)) if (t>>i)&1))
   edges.add(nodes)
 stars=0
 while edges:
  degrees=collections.Counter(v for e in edges for v in e)
  center,degree=max(degrees.items(),key=lambda kv:(kv[1],-kv[0]))
  if degree<2:
   e=min(edges);out.append(('CCX',(*e,target)));edges.remove(e);continue
  leaves=sorted(next(iter(set(e)-{center})) for e in edges if center in e)
  pivot=leaves[0]
  out.extend(('CX',(q,pivot)) for q in leaves[1:])
  out.append(('CCX',(center,pivot,target)))
  out.extend(('CX',(q,pivot)) for q in reversed(leaves[1:]))
  for q in leaves:edges.remove(tuple(sorted((center,q))))
  stars+=1
 assert perm(block,wires)==perm(out,wires),'exhaustive Boolean equivalence mismatch'
 before=collections.Counter(op for op,_ in block)
 after=collections.Counter(op for op,_ in out)
 if after['CCX']>=before['CCX']:return None
 return {'gates':out,'CCX_saved':before['CCX']-after['CCX'],
   'wires':wires,'target':target,'ANF_terms':terms,'stars':stars,
   'CCX_before':before['CCX'],'CCX_after':after['CCX']}
def optimize(lines,max_qubits,max_gates):
 ops=[parse(s) for s in lines];runs=[];i=0
 while i<len(ops):
  if ops[i] is None:i+=1;continue
  j=i
  while j<len(ops) and ops[j] is not None:j+=1
  runs.append((i,j));i=j
 candidates=[];examined=0
 for a,b in runs:
  ccx=[i for i in range(a,b) if ops[i][0]=='CCX']
  for idx,start in enumerate(ccx):
   for end in ccx[idx+1:idx+9]:
    if end-start+1>max_gates:break
    block=ops[start:end+1]
    if len({q for _,qs in block for q in qs})>max_qubits:continue
    examined+=1
    ans=synth(block,max_qubits)
    if ans:ans.update({'start':start,'end':end+1});candidates.append(ans)
 chosen=[]
 for c in sorted(candidates,key=lambda c:(-c['CCX_saved'],c['start'])):
  if any(c['start']<v['end'] and v['start']<c['end'] for v in chosen):continue
  chosen.append(c)
 chosen.sort(key=lambda c:c['start'])
 output=[];cursor=0
 for c in chosen:
  output+=lines[cursor:c['start']]
  output += [op+' '+' '.join('q'+str(q) for q in qs)+'\n' for op,qs in c['gates']]
  cursor=c['end']
 output+=lines[cursor:]
 return output,chosen,{'runs':len(runs),'windows_tested':examined,
                       'possible_blocks':len(candidates)}
def selftest():
 truth=[(((x>>0)&1)&((x>>1)&1))^(((x>>0)&1)&((x>>2)&1))^((x>>3)&1) for x in range(16)]
 assert set(anf(truth))=={3,5,8}
 block=[('CCX',(0,1,4)),('CCX',(0,2,4)),('CX',(3,4))]
 result=synth(block,6)
 assert result and result['CCX_saved']==1 and result['stars']==1
 assert perm(block,(0,1,2,3,4))==perm(result['gates'],(0,1,2,3,4))
 block=[('CX',(0,1)),('CCX',(1,2,4)),('CX',(0,1)),('CCX',(1,2,4))]
 result=synth(block,6)
 assert result and result['CCX_saved']==1
 assert perm(block,(0,1,2,4))==perm(result['gates'],(0,1,2,4))
 lines=['REGISTER r0\n','CCX q0 q1 q4\n','CCX q0 q2 q4\n','HMR q9 b1\n']
 output,chosen,scan=optimize(lines,6,60)
 assert len(chosen)==1 and chosen[0]['CCX_saved']==1 and output[-1]==lines[-1]
 print('K069_SELFTEST PASS: exact ANF, reversible resynthesis, control restoration, barriers',flush=True)
def verify(path,full,timeout):
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 fp=ROOT/'competition/k031/k031_full_domain_repair.py'
 spec=importlib.util.spec_from_file_location('k031_k069',fp)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 jobs=[('prefix',64,12345)]
 if full:jobs.extend([('full_12345',m.FULL_X,12345),('full_23456',m.FULL_X,23456)])
 result={}
 for label,n,seed in jobs:
  result[label]=m.verify(path,n,seed,timeout)
  if result[label].get('status')!='PASS' or result[label].get('exit_code')!=0:break
 return result
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--source',action='append',type=Path)
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k069/results')
 ap.add_argument('--max-qubits',type=int,default=6)
 ap.add_argument('--max-gates',type=int,default=60)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--timeout',type=int,default=600)
 ap.add_argument('--self-test',action='store_true')
 args=ap.parse_args()
 if args.self_test:selftest();return
 if not 3<=args.max_qubits<=9:raise SystemExit('--max-qubits must be 3..9')
 args.out.mkdir(parents=True,exist_ok=True)
 paths=args.source or [ROOT/'competition/k059/results'/(x+'.kmx') for x in
                        ('helios_public','k040_ours','k056_bounded_ours')]
 results=[]
 for p in paths:
  if not p.is_file():print('K069_MISSING',p,flush=True);continue
  lines=p.read_text().splitlines(keepends=True)
  try:new,chosen,scan=optimize(lines,args.max_qubits,args.max_gates)
  except Exception as e:
   print('K069_SCAN_ERROR',str(p),repr(e),flush=True);continue
  row={'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
       'attribution':'Helios third-party public reference' if 'helios' in p.name else 'CaMaLabs',
       'scan':scan,'blocks_replaced':len(chosen),
       'CCX_saved':sum(c['CCX_saved'] for c in chosen),
       'examples':[{k:v for k,v in c.items() if k!='gates'} for c in chosen[:20]]}
  print('K069_SCAN',json.dumps({k:row[k] for k in ('source','scan','blocks_replaced','CCX_saved')},sort_keys=True),flush=True)
  if not chosen:row['status']='NO_MATCHES'
  else:
   try:
    import kickmix as km
    target=args.out/(p.stem+'_anf.kmx');target.write_text(''.join(new))
    circuit=km.Circuit.from_file(str(target),format='kmx')
    binary=target.with_suffix('.kmb');circuit.to_file(str(binary),format='kmb')
    row['candidate_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    row['num_qubits']=circuit.num_qubits
    full=args.full and 'k056' not in p.stem
    row['official']=verify(binary,full,args.timeout)
    passed=all(r.get('status')=='PASS' and r.get('exit_code')==0 for r in row['official'].values())
    row['status']='PASS_FULL' if passed and full and len(row['official'])==3 else 'PASS_BOUNDED' if passed else 'FAIL'
   except Exception as e:row['status']='ERROR';row['error']=repr(e)
  results.append(row)
  print('K069_RESULT',json.dumps({'source':str(p),'status':row['status'],
      'CCX_saved':row['CCX_saved'],'official':row.get('official'),
      'error':row.get('error')},sort_keys=True),flush=True)
 dest=args.out/'results.json'
 dest.write_text(json.dumps({'results':results},indent=2,default=str))
 print('K069_SAVED',dest,flush=True)
if __name__=='__main__':main()
