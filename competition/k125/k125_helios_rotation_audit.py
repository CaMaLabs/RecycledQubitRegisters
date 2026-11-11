#!/usr/bin/env python3
"""K125 Helios phase-site/control-context audit (read-only, no unsafe rewrites).

Pinned baseline only. Reports R and Z_POW source sites, conditions, target
patterns, contiguous same-target pairs and boundaries; does not equate
source operations to dynamically executed rotations or assume a merge is
valid. Source-level candidates require Kickmix semantic review and official
verification before attempting replacement.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
ROT={'R','Z_POW'}
def parse(line):
 s=line.strip()
 if not s or s.startswith('#'):return '',[],s
 tokens=s.split()
 return tokens[0].upper(),tokens[1:],s
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k125/results/rotation_audit.json')
 p.add_argument('--window',type=int,default=8)
 a=p.parse_args()
 raw=a.baseline.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 if digest!=PIN:raise SystemExit(f'Baseline SHA mismatch {digest} expected {PIN}')
 lines=raw.decode('utf-8').splitlines()
 parsed=[parse(z) for z in lines]
 sites=[];stack=[];warnings=[];balances=collections.Counter()
 for idx,(op,args,s) in enumerate(parsed):
  if op=='PUSH_CONDITION':
   stack.append({'line':idx+1,'expression':s})
  elif op=='POP_CONDITION':
   if stack:stack.pop()
   else:warnings.append({'line':idx+1,'issue':'POP_WITHOUT_PUSH'})
  if op not in ROT:continue
  # Do not invent rotation semantics: retain full raw arguments and all wires.
  qubits=re.findall(r'\bq\d+\b',s)
  site={'line':idx+1,'opcode':op,'text':s,'qubits':qubits,
      'condition_depth':len(stack),
      'condition_context':[v['expression'] for v in stack],
      'context_start_lines':[v['line'] for v in stack],
      'before':[{'line':j+1,'text':lines[j].strip()} for j in range(max(0,idx-a.window),idx)
                if lines[j].strip()],
      'after':[{'line':j+1,'text':lines[j].strip()} for j in range(idx+1,min(len(lines),idx+a.window+1))
               if lines[j].strip()]}
  sites.append(site);balances[op]+=1
 if stack:warnings.append({'issue':'UNCLOSED_CONDITIONS','count':len(stack)})
 by_target=collections.defaultdict(list)
 for s in sites:
  key=tuple(s['qubits'])
  by_target[str(key)].append(s['line'])
 # Only syntactically adjacent rotation lines, no intervening op.
 adjacent=[]
 for lhs,rhs in zip(sites,sites[1:]):
  if rhs['line']==lhs['line']+1:
   same_ctx=lhs['condition_context']==rhs['condition_context']
   same_wires=lhs['qubits']==rhs['qubits']
   adjacent.append({'lines':[lhs['line'],rhs['line']],
     'same_condition_context':same_ctx,'same_wire_tokens':same_wires,
     'requires_semantic_and_phase_check':True})
 report={'status':'READ_ONLY_AUDIT','source_file':str(a.baseline),
   'sha256':digest,'total_source_lines':len(lines),
   'source_rotation_counts':dict(balances),'source_rotation_site_count':len(sites),
   'unique_wire_token_patterns':len(by_target),
   'wire_token_groups':dict(by_target),
   'syntactically_adjacent_rotation_pairs':adjacent,
   'sites':sites,'warnings':warnings,
   'limitations':['Source R/Z_POW count does not equal dynamically executed verifier rotations.',
      'Z_POW may be an exact Clifford/T-like phase: numerical T-cost depends on parsed semantics.',
      'No source transform, candidate score, or semantic merging is claimed.',
      'Do not merge across conditional context or noncommuting operations.',
      'Verification must preserve all input states, clean scratch, and phase error.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+'\n')
 counts=collections.Counter(s['condition_depth'] for s in sites)
 print('K125_CENSUS',json.dumps({'source_lines':len(lines),
   'rotations':dict(balances),'condition_depth_histogram':dict(counts),
   'wire_patterns':len(by_target),'adjacent_rotation_pairs':len(adjacent),
   'warnings':warnings}),flush=True)
 for s in sites:
  print('K125_ROTATION',json.dumps({k:s[k] for k in
   ('line','opcode','text','qubits','condition_depth','context_start_lines')}),flush=True)
 for pair in adjacent:print('K125_ADJACENT',json.dumps(pair),flush=True)
 print('K125_RESULT',json.dumps({'status':'READ_ONLY_AUDIT','out':str(a.out)}),flush=True)
if __name__=='__main__':main()
