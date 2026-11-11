#!/usr/bin/env python3
"""K133: weighted source-cost heatmap for the pinned Helios Kickmix circuit.

NEW MECHANISM: prioritize code regions by their potentially executed scored gate
budget, not by identity/cancellation tests. This is a static *upper-bound screen*;
conditional execution, measurement branches, and verifier-specific gate weights
require dynamic profiling before any optimization claim.

Creates fixed-width line windows and HMR-delimited regions with independent
unconditional vs conditional counts for CCX, CCZ, CSWAP, Z_POW and T gates.
Does not change baseline or reuse previous optimization searches.
"""
import argparse,collections,hashlib,json
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
SCORABLE=('CCX','CCZ','CSWAP','Z_POW','T','T_DAG')
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k133/results/source_cost_regions.json'))
 p.add_argument('--window',type=int,default=512)
 p.add_argument('--top',type=int,default=20)
 a=p.parse_args()
 if a.window<32 or a.top<1:p.error('window >= 32; top >= 1')
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit(f'Immutable baseline mismatch {sha}')
 lines=raw.decode().splitlines();stack=[];blocks={};hmr_regions=[]
 counts=collections.Counter();source_max=collections.Counter();source_uncond=collections.Counter()
 def empty_window(idx):return {'start':idx*a.window+1,'end':min(len(lines),(idx+1)*a.window),'count':collections.Counter(),'unconditional':collections.Counter(),'conditional':collections.Counter(),'opcode_histogram':collections.Counter(),'hmr_count':0}
 def empty_region(start):return {'start':start,'end':start,'count':collections.Counter(),'unconditional':collections.Counter(),'conditional':collections.Counter(),'hmr_count':0}
 regional=empty_region(1)
 for ix,line in enumerate(lines):
  t=line.strip().split()
  if not t or t[0].startswith(('#','//')):continue
  op=t[0].upper();counts[op]+=1
  if op=='PUSH_CONDITION':
   if len(t)<3 or t[1].lower()!='if':raise ValueError(f'unknown condition shape line {ix+1}')
   stack.append(t[2]);continue
  if op=='POP_CONDITION':
   if not stack:raise ValueError('condition underflow')
   stack.pop();continue
  guarded=bool(stack) or 'if' in [x.lower() for x in t]
  win=blocks.setdefault(ix//a.window,empty_window(ix//a.window))
  win['opcode_histogram'][op]+=1
  regional['end']=ix+1
  if op=='HMR':
   win['hmr_count']+=1;regional['hmr_count']+=1
   hmr_regions.append(regional);regional=empty_region(ix+2)
  if op not in SCORABLE:continue
  group='conditional' if guarded else 'unconditional'
  win['count'][op]+=1;win[group][op]+=1
  regional['count'][op]+=1;regional[group][op]+=1
  source_max[op]+=1
  if not guarded:source_uncond[op]+=1
 if stack:raise ValueError('unbalanced stack')
 if regional['end']>=regional['start']:hmr_regions.append(regional)
 def score(d):
  # Source sites are NOT dynamically executed gate counts. Keep opcodes separate.
  return sum(d['count'][op] for op in ('CCX','CCZ','CSWAP'))
 def convert(d):
  return {k:(dict(v) if isinstance(v,collections.Counter) else v) for k,v in d.items()}|{'toffoli_class_source_sites':score(d),'phase_source_sites':d['count']['Z_POW']}
 windows=[convert(v) for v in blocks.values()];regions=[convert(v) for v in hmr_regions]
 windows.sort(key=lambda r:(-r['toffoli_class_source_sites'],-r['phase_source_sites'],r['start']))
 regions.sort(key=lambda r:(-r['toffoli_class_source_sites'],-r['phase_source_sites'],r['start']))
 result={'experiment':'K133','status':'STATIC_HOTSPOT_SCREEN','baseline_sha256':sha,'source_lines':len(lines),
   'window_size':a.window,'source_counts':dict(counts),'scorable_source_counts':dict(source_max),
   'unconditionally_scheduled_sites':dict(source_uncond),
   'top_source_windows':windows[:a.top],'top_hmr_delimited_regions':regions[:a.top],
   'all_window_count':len(windows),'hmr_delimited_region_count':len(hmr_regions),
   'warnings':['This does NOT instrument actual executed cost or perform any verifier run.',
    'Source counts, including unconditional sites, may differ from verifier resource accounting.',
    'HMR-delimited regions are execution locality units, not proven independent functional blocks.',
    'The ranked areas require dynamic verifier execution-frequency evidence before optimization.']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K133_SUMMARY',json.dumps({k:result[k] for k in ('status','source_lines','scorable_source_counts','unconditionally_scheduled_sites','all_window_count','hmr_delimited_region_count')}),flush=True)
 for row in windows[:a.top]:
  print('K133_HOT_WINDOW',json.dumps({k:row[k] for k in ('start','end','toffoli_class_source_sites','phase_source_sites','count','conditional','unconditional')}),flush=True)
 print('K133_RESULT',json.dumps({'out':str(a.out),'status':result['status']}),flush=True)
if __name__=='__main__':main()
