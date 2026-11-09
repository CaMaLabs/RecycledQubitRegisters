#!/usr/bin/env python3
"""K097: inspect official scoring source and Helios measurement/feedback paths.
Static depth is diagnostic, NOT Kickmix's measured reaction depth.
Never mutate the pinned third-party reference or claim a score improvement.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE=95369.00696815242
BIT=re.compile(r'\bb(\d+)\b',re.I)
QBIT=re.compile(r'\bq(\d+)\b',re.I)
SOURCE_PATTERN=re.compile(r'\b(def\s+(score|compute_score|cost|estimate_cost|score_submission|compute_resources)|score\s*=|["\']score["\']\s*:|["\']score["\']\]\s*=)',re.I)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def source_audit(root,limit):
 rows=[];scanned=0
 if not root.is_dir():return {'status':'MISSING','root':str(root),'files_scanned':0,'findings':[]}
 for file in sorted(root.rglob('*.py')):
  if any(p in ('__pycache__','.venv','site-packages') for p in file.parts):continue
  if scanned>=limit:break
  scanned+=1
  try:lines=file.read_text(errors='replace').splitlines()
  except OSError:continue
  matches=[i for i,s in enumerate(lines) if SOURCE_PATTERN.search(s)]
  for i in matches[:12]:
   rows.append({'file':str(file),'line':i+1,'excerpt':[
    {'line':j+1,'text':lines[j][:240]} for j in
    range(max(0,i-2),min(len(lines),i+7))]})
 return {'status':'OK','root':str(root),'files_scanned':scanned,
         'total_score_candidates':len(rows),'findings':rows[:60]}
def static_path(lines):
 depth=collections.defaultdict(int);classical=collections.defaultdict(int)
 counter=collections.Counter();critical=[];scope=[];hmrs=[];reader=collections.Counter()
 unresolved=collections.Counter()
 for idx,line in enumerate(lines,1):
  s=line.strip()
  if not s or s.startswith(('#','//')):continue
  op=s.split()[0].upper();counter[op]+=1
  q=list(dict.fromkeys(map(int,QBIT.findall(s))))
  bits=list(dict.fromkeys(map(int,BIT.findall(s))))
  refs=list(map(int,re.findall(r'\bif\s+b(\d+)',s,re.I)))
  active=[b for _,b in scope]
  if op=='PUSH_CONDITION':
   if bits:scope.append((idx,bits[0]))
   else:unresolved['condition_push_without_bit']+=1
   continue
  if op=='POP_CONDITION':
   if scope:scope.pop()
   else:unresolved['condition_pop_without_push']+=1
   continue
  if op in ('BIT_STORE0','BIT_STORE1','BIT_INVERT','BIT_COPY','BIT_XOR'):
   if bits:
    t=bits[0]
    dep=[classical[b] for b in (bits[1:]+refs+active)]
    if op=='BIT_INVERT':dep.append(classical[t])
    classical[t]=max(dep,default=classical[t])+1
   else:unresolved['bit_op_without_bit']+=1
   continue
  if not q:
   unresolved['nonquantum_unknown']+=1
   continue
  val=max([depth[x] for x in q]+[classical[b] for b in refs+active]+[0])+1
  for x in q:depth[x]=val
  if op=='HMR':
   if not bits:unresolved['hmr_without_destination']+=1
   for b in bits:
    classical[b]=val+1
    hmrs.append({'line':idx,'q':q[0],'bit':b,'path_depth':val+1})
  for b in refs:reader[b]+=1
  critical.append((val,idx,op,tuple(q),tuple(refs)))
 critical.sort(reverse=True)
 return {'instruction_count':sum(counter.values()),'op_counts':dict(counter),
   'static_qwire_depth':max(depth.values(),default=0),
   'static_classical_depth':max(classical.values(),default=0),
   'warning':'Conservative wire/classical-bit dependency proxy, NOT official score/reaction depth',
   'hmr_count':len(hmrs),'condition_reads':sum(reader.values()),
   'measurement_hotspots':sorted(hmrs,key=lambda x:x['path_depth'],reverse=True)[:16],
   'critical_events':[{'depth':d,'line':i,'op':op,'qubits':list(q),'bits':list(bits)}
      for d,i,op,q,bits in critical[:20]],
   'bit_fanout':reader.most_common(20),'unresolved':dict(unresolved),
   'unclosed_scopes':len(scope)}
def receipts(root):
 rows=[]
 for p in (root/'competition/k092/results/summary.json',
           root/'competition/k093/results/summary.json',
           root/'competition/k091/results/summary.json'):
  if not p.exists():continue
  try:body=json.loads(p.read_text())
  except (ValueError,OSError):continue
  for key in ('cases','all_results','records'):
   if not isinstance(body.get(key),list):continue
   for case in body[key]:
    if not isinstance(case,dict):continue
    if case.get('status')!='PASS_FULL' and not case.get('full_domain_verified'):continue
    score=case.get('score')
    if isinstance(score,(int,float)):
     rows.append({'file':str(p),'case':case.get('case',case.get('variant')),
                  'score':score,'delta':score-BASE,'status':case.get('status')})
 return rows
def selftest():
 a=static_path(['X q0','HMR q0 b2','CX q1 q3 if b2',
                'PUSH_CONDITION b2','CCX q1 q3 q4','POP_CONDITION'])
 assert a['hmr_count']==1 and a['condition_reads']==1
 assert a['static_qwire_depth']>=3 and a['unclosed_scopes']==0
 assert callable(sha) and callable(source_audit) and callable(receipts)
 print('K097_SELFTEST PASS static measurement and classical-condition dependency test',flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k097/results')
 ap.add_argument('--verifiers',type=Path,default=ROOT/'competition/k001/private/official/verifiers')
 ap.add_argument('--max-source-files',type=int,default=500)
 ap.add_argument('--self-test',action='store_true')
 a=ap.parse_args();selftest()
 if a.self_test:return
 if sha(a.base)!=PIN:raise RuntimeError('Pinned public Helios KMB SHA mismatch')
 sys.path.insert(0,str(a.verifiers))
 import kickmix as km
 a.out.mkdir(parents=True,exist_ok=True)
 orig=km.Circuit.from_file(str(a.base),format='kmb')
 text=a.out/'helios_pinned.kmx';orig.to_file(str(text),format='kmx')
 lines=text.read_text().splitlines()
 source=source_audit(a.verifiers,a.max_source_files)
 path=static_path(lines);samples=receipts(ROOT)
 report={'baseline':{'sha256':PIN,'score':BASE,'qubits':orig.num_qubits,
                     'instructions':len(lines),'attribution':'Helios third-party'},
   'source_audit':source,'static_path':path,'paired_full_domain_samples':samples,
   'prior_evidence':{
     'k092':'Full-domain score unchanged after large CX/CZ reductions',
     'k093':'Full-domain score unchanged after CSWAP-to-CCX re-encoding',
     'caveat':'These observations do not uniquely identify the scoring formula'},
   'next_step':'Inspect source findings; pursue exact, full-domain verified changes to the actual weighted critical resource'}
 (a.out/'audit.json').write_text(json.dumps(report,indent=2,default=str))
 print('K097_BASE',json.dumps(report['baseline'],sort_keys=True),flush=True)
 print('K097_SOURCE',json.dumps({'status':source['status'],'files_scanned':source['files_scanned'],
    'matches':source.get('total_score_candidates',0),
    'files':list(dict.fromkeys(x['file'] for x in source['findings']))[:18]},sort_keys=True),flush=True)
 print('K097_PATH',json.dumps({'static_qwire_depth':path['static_qwire_depth'],
    'static_classical_depth':path['static_classical_depth'],'hmr_count':path['hmr_count'],
    'condition_reads':path['condition_reads'],'critical_events':path['critical_events'][:6]},sort_keys=True),flush=True)
 print('K097_RESULT',json.dumps({'paired_valid_scores':len(samples),
    'score_source_matches':source.get('total_score_candidates',0),
    'report':str(a.out/'audit.json')},sort_keys=True),flush=True)
if __name__=='__main__':main()
