#!/usr/bin/env python3
"""K071: inspect the 26-step q28 phase ladder and minimize exact coherent CSWAP permutations.

Works on public Helios reference as a THIRD-PARTY benchmark; no claim of
original circuit authorship. Rewrites only uninterrupted CSWAP runs sharing
one quantum control. Rewrites preserve arbitrary superpositions and entanglement.
Exhaustively checks every proposed local replacement.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CSWAP=re.compile(r'^CSWAP\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$',re.I)
ZPOW=re.compile(r'^Z_POW\s+q28\s+(\S+)\s*$',re.I)
HMR=re.compile(r'^HMR\s+q28\s+b(\d+)\s*$',re.I)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gate(s):
 m=CSWAP.fullmatch(s.strip())
 if not m:return None
 c,a,b=map(int,m.groups())
 return (c,a,b) if len({c,a,b})==3 else None
def permutation(seq):
 controls={c for c,_,_ in seq}
 assert len(controls)==1
 wires=sorted({q for _,a,b in seq for q in (a,b)})
 state={q:q for q in wires}
 for _,a,b in seq:state[a],state[b]=state[b],state[a]
 return wires,state
def synthesize(seq):
 wires,want=permutation(seq);control=seq[0][0]
 current={q:q for q in wires};out=[]
 for q in wires:
  if current[q]==want[q]:continue
  j=next(k for k in wires if current[k]==want[q])
  current[q],current[j]=current[j],current[q]
  out.append((control,q,j))
 assert current==want
 have=permutation(out)[1] if out else {}
 assert all(have.get(q,q)==want[q] for q in wires)
 return out
def apply(seq,wires,value):
 pos={q:i for i,q in enumerate(wires)}
 for c,a,b in seq:
  if (value>>pos[c])&1 and ((value>>pos[a])&1)!=((value>>pos[b])&1):
   value^=(1<<pos[a])|(1<<pos[b])
 return value
def equivalent(before,after):
 wires=sorted({q for g in before+after for q in g})
 if len(wires)>14:raise ValueError('Too many qubits for exhaustive proof')
 return all(apply(before,wires,x)==apply(after,wires,x) for x in range(1<<len(wires)))
def optimize(lines):
 candidates=[];stats=[];i=0
 while i<len(lines):
  first=gate(lines[i])
  if first is None:i+=1;continue
  j=i+1
  while j<len(lines):
   g=gate(lines[j])
   if g is None or g[0]!=first[0]:break
   j+=1
  if j-i>=2:
   original=[gate(s) for s in lines[i:j]]
   new=synthesize(original);saved=len(original)-len(new)
   item={'start_line':i+1,'end_line':j,'control_q':first[0],
         'original_swaps':len(original),'optimal_swaps':len(new),
         'CSWAP_saved':saved,'target_wires':len({q for _,a,b in original for q in (a,b)})}
   stats.append(item)
   if saved>0:
    assert equivalent(original,new)
    candidates.append((i,j,new,item))
  i=j
 output=[];cursor=0
 for start,end,new,_ in candidates:
  output.extend(lines[cursor:start])
  output.extend(f'CSWAP q{c} q{a} q{b}\n' for c,a,b in new)
  cursor=end
 output.extend(lines[cursor:])
 return output,stats,candidates
def ladder(lines):
 events=[]
 for i,s in enumerate(lines):
  m=ZPOW.fullmatch(s.strip())
  if m:
   try:events.append((i,float(m[1])))
   except ValueError:continue
 clusters=[];cur=[]
 for event in events:
  if cur and event[0]-cur[-1][0]>24:
   clusters.append(cur);cur=[]
  cur.append(event)
 if cur:clusters.append(cur)
 match=[c for c in clusters if len(c)>=20 and c[0][1]<1e-9
        and all(c[k+1][1]>c[k][1] for k in range(len(c)-1))]
 if len(match)!=1:raise RuntimeError(f'Expected one 26-step phase ladder; found {len(match)}')
 rows=[];previous=None
 for n,(idx,angle) in enumerate(match[0]):
  hmr=None;measured=None
  for j in range(idx+1,min(idx+7,len(lines))):
   m=HMR.fullmatch(lines[j].strip())
   if m:hmr=j;measured=int(m[1]);break
  start=max(0,idx-15) if previous is None else previous+1
  stop=hmr+1 if hmr is not None else idx+1
  pairs=[(start+j,gate(s)) for j,s in enumerate(lines[start:stop])]
  pairs=[(j,g) for j,g in pairs if g]
  controls=collections.Counter(g[0] for _,g in pairs)
  rows.append({'stage':n,'zpow_line':idx+1,'angle':angle,'hmr_line':hmr+1 if hmr is not None else None,
   'measurement_bit':measured,'cswap_count':len(pairs),'cswap_controls':dict(controls),
   'window_lines':[start+1,stop],'cswap_target_wires':sorted({q for _,(_,a,b) in pairs for q in (a,b)}),
   'gates':[{'line':j+1,'control':g[0],'targets':list(g[1:])} for j,g in pairs]})
  previous=hmr if hmr is not None else idx
 return rows
def verify(binary,timeout):
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 p=ROOT/'competition/k031/k031_full_domain_repair.py'
 spec=importlib.util.spec_from_file_location('k031_k071',p)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 result={}
 for label,n,seed in [('prefix',64,12345),('full_12345',m.FULL_X,12345),('full_23456',m.FULL_X,23456)]:
  result[label]=m.verify(binary,n,seed,timeout)
  if result[label].get('status')!='PASS' or result[label].get('exit_code')!=0:break
 return result
def selftest():
 cases=[[(9,0,1),(9,1,2),(9,0,1)],
        [(9,0,1),(9,2,3),(9,0,1)],
        [(9,0,1),(9,2,3),(9,1,2),(9,0,3)],
        [(9,0,1),(9,0,1)],
        [(9,0,1),(9,2,3),(9,4,5)]]
 for x in cases:
  y=synthesize(x)
  assert equivalent(x,y) and len(y)<=len(x)
 assert len(synthesize(cases[0]))==1
 src=['X q7\n','CSWAP q9 q0 q1\n','CSWAP q9 q1 q2\n',
      'CSWAP q9 q0 q1\n','HMR q8 b3\n']
 out,stats,proposals=optimize(src)
 assert len(proposals)==1 and len(out)==3
 assert out[0]==src[0] and out[-1]==src[-1]
 print('K071_SELFTEST PASS: controlled permutation, exact synthesis, measurement barriers',flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--source',type=Path,default=ROOT/'competition/k059/results/helios_public.kmx')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k071/results')
 p.add_argument('--full',action='store_true')
 p.add_argument('--timeout',type=int,default=600)
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 if a.self_test:selftest();return
 if not a.source.is_file():raise SystemExit('Missing KMX '+str(a.source))
 a.out.mkdir(parents=True,exist_ok=True)
 lines=a.source.read_text().splitlines(keepends=True)
 stages=ladder(lines);output,stats,proposals=optimize(lines)
 report={'attribution':'Helios public third-party benchmark; not CaMaLabs original work',
  'source':str(a.source),'source_sha256':sha(a.source),
  'phase_stages':stages,'permutation_runs':stats,'candidate_rewrites':len(proposals),
  'cswap_saved':sum(p[3]['CSWAP_saved'] for p in proposals),
  'warning':'Only contiguous same-coherent-control permutations optimized, never measured controls.'}
 print('K071_OVERVIEW',json.dumps({'phase_stages':len(stages),'permutation_runs':len(stats),
  'candidate_rewrites':len(proposals),'CSWAP_saved':report['cswap_saved'],
  'total_stage_CSWAP':sum(x['cswap_count'] for x in stages)},sort_keys=True),flush=True)
 for s in stages:
  print('K071_STAGE',json.dumps({k:s[k] for k in (
   'stage','zpow_line','angle','hmr_line','measurement_bit','cswap_count','cswap_controls')},sort_keys=True),flush=True)
 for s in stats:
  if s['CSWAP_saved']>0:print('K071_REWRITE',json.dumps(s,sort_keys=True),flush=True)
 if proposals:
  text=a.out/'candidate.kmx';text.write_text(''.join(output))
  report['candidate_kmx_sha256']=sha(text)
  if a.full:
   try:
    sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
    import kickmix as km
    circ=km.Circuit.from_file(str(text),format='kmx')
    binary=a.out/'candidate.kmb';circ.to_file(str(binary),format='kmb')
    report['candidate_kmb_sha256']=sha(binary)
    report['official']=verify(binary,a.timeout)
    report['status']='PASS_FULL' if len(report['official'])==3 and all(
     r.get('status')=='PASS' and r.get('exit_code')==0 for r in report['official'].values()) else 'FAIL'
   except Exception as e:report['status']='ERROR';report['error']=repr(e)
  else:report['status']='UNVERIFIED_REWRITE'
 else:report['status']='NO_CHEAPER_CONTIGUOUS_PERMUTATIONS'
 target=a.out/'report.json';target.write_text(json.dumps(report,indent=2))
 print('K071_RESULT',json.dumps({'status':report['status'],'CSWAP_saved':report['cswap_saved'],
  'official':report.get('official'),'error':report.get('error')},sort_keys=True),flush=True)
 print('SAVED',target,flush=True)
if __name__=='__main__':main()
