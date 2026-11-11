#!/usr/bin/env python3
"""K126: read-only audit of q28 Z_POW ladders in pinned Helios baseline.

Do NOT equate source opcode counts with executed verifier rotations.
No phase rewrite is produced. Fractional Z_POW exponents are half-turns;
phase-angle errors from snapping are reported in turns with conservative
whole-source upper bounds (not achievable-error estimates).
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal, getcontext
import argparse, hashlib, json, re
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
getcontext().prec=100
def opcode(line):
 s=line.strip()
 return s.split()[0].upper() if s and not s.startswith('#') else ''
def on_q28(line):
 return bool(re.search(r'(?<!\w)q28(?!\d)',line))
def analyze(lines,events):
 out=[]
 for k,(idx,angle) in enumerate(events):
  prev=events[k-1][0] if k else -1
  segment=lines[prev+1:idx]
  ops=Counter(opcode(s) for s in segment if opcode(s))
  touch=Counter(opcode(s) for s in segment if on_q28(s))
  nearest=Decimal(1)/Decimal(2)**round(-mathlog2(angle)) if angle>0 else Decimal(0)
  # nearest dyadic only if angle 0 < angle <= 2 (all target ladder angles satisfy).
  # Integer-power selection via Decimal comparisons, not float log.
  power=0
  if angle>0:
   candidate=Decimal(1)
   while candidate>angle: candidate/=2;power+=1
   larger=candidate*2
   nearest=candidate if abs(candidate-angle)<=abs(larger-angle) else larger
  diff=abs(angle-nearest)
  out.append({'line':idx+1,'z_pow_exponent':str(angle),
    'nearest_positive_power_of_two':str(nearest),
    'dyadic_abs_error_half_turns':str(diff),
    'dyadic_abs_error_turns':str(diff/2),
    'previous_q28_phase_line':prev+1 if prev>=0 else None,
    'intervening_source_lines':len(segment),
    'intervening_opcode_histogram':dict(ops),
    'q28_touching_opcode_histogram':dict(touch),
    'q28_touching_gate_count':sum(touch.values()),
    'direct_adjacent_to_prior_q28_phase':bool(prev>=0 and idx==prev+1)})
 return out
def mathlog2(x):
 # Placeholder never needed: replaced below using Decimal exact scan.
 return 0
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--output',type=Path,default=Path('competition/k126/results/phase_ladder_audit.json'))
 a=p.parse_args()
 raw=a.baseline.read_bytes()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit('Pinned baseline SHA mismatch')
 lines=raw.decode().splitlines()
 events=[]
 allphase=[]
 for i,line in enumerate(lines):
  tokens=line.strip().split()
  if len(tokens)==3 and tokens[0]=='Z_POW':
   try: angle=Decimal(tokens[2])
   except Exception:continue
   allphase.append((i,tokens[1],angle))
   if tokens[1]=='q28':events.append((i,angle))
 clusters=[]
 for idx,ang in events:
  if not clusters or idx-clusters[-1][-1][0]>200:
   clusters.append([])
  clusters[-1].append((idx,ang))
 summaries=[]
 for group in clusters:
  rows=analyze(lines,group)
  total=sum(Decimal(r['dyadic_abs_error_turns']) for r in rows)
  direct=sum(int(r['direct_adjacent_to_prior_q28_phase']) for r in rows)
  touched=sum(int(r['q28_touching_gate_count']) for r in rows)
  item={'start_line':group[0][0]+1,'end_line':group[-1][0]+1,
        'phase_sites':len(rows),'directly_adjacent_q28_phase_pairs':direct,
        'q28_touching_intervening_gates':touched,
        'sum_abs_rounding_error_turns_upper_bound':str(total),
        'max_abs_rounding_error_turns':str(max(Decimal(r['dyadic_abs_error_turns']) for r in rows)),
        'sites':rows}
  summaries.append(item)
  print('K126_LADDER',json.dumps({k:item[k] for k in item if k!='sites'}),flush=True)
  for row in rows:
   print('K126_SITE',json.dumps({k:row[k] for k in (
     'line','nearest_positive_power_of_two',
     'dyadic_abs_error_turns','intervening_source_lines',
     'q28_touching_opcode_histogram')}),flush=True)
 report={'status':'READ_ONLY','sha256':sha,
   'z_pow_site_count':len(allphase),'q28_phase_sites':len(events),
   'other_phase_sites':[{'line':i+1,'target':q,'angle':str(v)} for i,q,v in allphase if q!='q28'],
   'ladders':summaries,'caveats':[
    'Dyadic phase rounding has been explored previously; this report is diagnostic, not an optimization result.',
    'A sum of absolute coefficient changes is a conservative source-level phase upper bound, not a verifier worst-case measurement.',
    'Controlled phase implementation and intervening operation semantics require Kickmix-aware analysis.',
    'No transformed circuit or score win established.']}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(report,indent=2)+'\n')
 print('K126_RESULT',json.dumps({'status':'READ_ONLY',
   'phase_sites':len(allphase),'q28_sites':len(events),
   'clusters':len(summaries),'out':str(a.output)}),flush=True)
if __name__=='__main__':main()
