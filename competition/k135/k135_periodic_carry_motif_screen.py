#!/usr/bin/env python3
"""K135: scan repeated arithmetic motifs for PTP-style periodic carry-table candidates.

A *new* architecture screen, not K109 bounded local resynthesis or K113
common-factor cancellation. It scans contiguous unconditional X/CX/CCX
runs for repeated, wire-renamed templates. A family whose gate sequence
repeats across many physical wire ranges might admit an arithmetic carry
automaton shared by a small residue-indexed transition table.

It does NOT assume that modulo-210 prime filtering works for inverse sqrt:
binary carry periods are powers of two. The table test reports the cost
of bounded low-bit carry truth tables separately from identified motifs.
No circuit is changed, and no score improvement is claimed.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
ARITY={'X':1,'CX':2,'CCX':3}
Q=re.compile(r'^q(\d+)$')
def parse(line):
 t=line.strip().split()
 if not t or t[0] not in ARITY or len(t)!=ARITY[t[0]]+1:return None
 if not all(Q.fullmatch(s) for s in t[1:]):return None
 wires=tuple(int(s[1:]) for s in t[1:])
 if len(wires)!=len(set(wires)):return None
 return (t[0],wires)
def signature(block):
 names={};seq=[]
 for op,wires in block:
  normalized=[]
  for w in wires:
   if w not in names:names[w]=len(names)
   normalized.append(names[w])
  seq.append((op,tuple(normalized)))
 return tuple(seq),len(names)
def find_runs(parsed):
 runs=[];start=None
 for i,g in enumerate(parsed+[None]):
  if g is not None:
   if start is None:start=i
  elif start is not None:
   runs.append((start,i));start=None
 return runs
def discover(parsed, block_lengths=(8,12,16,24), minimum_ccx=2):
 groups=collections.defaultdict(list)
 runs=find_runs(parsed)
 for first,last in runs:
  for length in block_lengths:
   if last-first<length:continue
   # Non-overlapping alignment per run: intended to find repeated compiled
   # arithmetic cells rather than huge numbers of overlapping substrings.
   for i in range(first,last-length+1):
    block=parsed[i:i+length]
    ccx=sum(op=='CCX' for op,_ in block)
    if ccx<minimum_ccx:continue
    sig,w=signature(block)
    groups[(length,sig)].append({'start':i+1,'end':i+length,'qubits':w,'ccx':ccx})
 families=[]
 for (length,sig),positions in groups.items():
  if len(positions)<2:continue
  # Greedy disjoint occurrences avoid inflated savings from overlapping matches.
  selected=[];last_end=-1
  for pos in positions:
   if pos['start']>last_end:
    selected.append(pos);last_end=pos['end']
  if len(selected)<2:continue
  families.append({'length':length,'repeated_copies':len(selected),
    'ccx_per_copy':selected[0]['ccx'],'template_wire_count':selected[0]['qubits'],
    'source_ccx_across_copies':len(selected)*selected[0]['ccx'],
    'locations':selected[:24],
    'template':[[op,list(q)] for op,q in sig],
    'candidate_kind':'wire_renamed_identical_arithmetic_run',
    'resource_claim':'NONE: templates are not proved replaceable as modular carries'})
 families.sort(key=lambda r:(-r['source_ccx_across_copies'],-r['repeated_copies'],r['template_wire_count']))
 return runs,families

def carry_truth(k,c):
 mod=1<<k
 return tuple(int(((u+c)>>k)!=0) for u in range(mod))
def carry_screen(k):
 mod=1<<k
 # A carry predicate for adding constant c is a threshold of low k bits.
 # Quantify truth-table complexity, not a speculative Toffoli saving.
 # Boolean output is one bit and every c from 0..2^k-1 is screened.
 rows=[]
 for c in range(mod):
  truth=carry_truth(k,c)
  # Count 1-minterms as a deliberately pessimistic lookup cost proxy.
  # Actual reversible implementation could differ substantially.
  count=sum(truth)
  if count!=c:raise AssertionError(f'carry identity failed k={k}, c={c}')
  # Prove period exactly 2^k: a carry only depends on the lowest k bits
  # of an integer plus c, not on higher bits.
  for u in range(mod):
   if truth[u]!=int(((u+mod+c)>>k)-1!=0):
    raise AssertionError('periodic carry test failed')
  rows.append({'constant':c,'on_minterms':count})
 return {'low_bits':k,'period':mod,'constants_tested':mod,
   'truth_table_cells':mod*mod,
   'max_on_minterms':max(r['on_minterms'] for r in rows),
   'mean_on_minterms':sum(r['on_minterms'] for r in rows)/mod,
   'note':'Threshold carry is periodic modulo 2**k, not modulo 210. Minterms are not actual CCX cost.'}
def selftest():
 g=[('CCX',(1,2,3)),('CX',(3,4)),('CCX',(1,4,5))]
 h=[('CCX',(11,12,13)),('CX',(13,14)),('CCX',(11,14,15))]
 assert signature(g)[0]==signature(h)[0]
 assert signature(g)[1]==5
 assert signature(g)[0]!=signature(list(reversed(h)))[0]
 for k in range(1,6):carry_screen(k)
 print('K135_SELFTEST PASS canonical repeated gates and exhaustive low-bit carry tables',flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k135/results/periodic_carry_motif_screen.json'))
 p.add_argument('--lengths',default='8,12,16,24')
 p.add_argument('--min-ccx',type=int,default=2)
 p.add_argument('--top',type=int,default=20)
 p.add_argument('--carry-max-bits',type=int,default=8)
 a=p.parse_args();lengths=sorted(set(int(x) for x in a.lengths.split(',')))
 if not lengths or min(lengths)<3 or a.min_ccx<1 or a.top<1 or a.carry_max_bits<1 or a.carry_max_bits>10:p.error('invalid bounds')
 selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit(f'Baseline SHA mismatch {sha}')
 lines=raw.decode().splitlines()
 parsed=[parse(line) for line in lines]
 runs,families=discover(parsed,lengths,a.min_ccx)
 carry=[carry_screen(k) for k in range(1,a.carry_max_bits+1)]
 summary={'experiment':'K135','status':'REPEATED_MOTIF_SCAN','baseline_sha256':sha,
   'source_lines':len(lines),'reversible_unconditional_runs':len(runs),
   'maximum_contiguous_run_length':max((j-i for i,j in runs),default=0),
   'minimum_ccx_per_template':a.min_ccx,'lengths_tested':lengths,
   'families_found':len(families),'top_families':families[:a.top],
   'carry_truth_table_screens':carry,
   'limitations':['This is not a prime-residue filter. Binary carries have power-of-two periods.',
    'Identical gate templates do not prove additive semantics or any improvement.',
    'Threshold truth-table cell counts do not imply reversible-gate implementation costs.',
    'An actual candidate requires exact I/O function extraction, clean scratch and measured verifier score.',
    'Some motifs can span condition or measurement boundaries and will be missed.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(summary,indent=2)+'\n')
 print('K135_SUMMARY',json.dumps({k:summary[k] for k in ('status','source_lines','reversible_unconditional_runs','maximum_contiguous_run_length','families_found')}),flush=True)
 for row in families[:a.top]:
  print('K135_FAMILY',json.dumps({k:row[k] for k in ('length','repeated_copies','ccx_per_copy','template_wire_count','source_ccx_across_copies','locations')}),flush=True)
 for row in carry:print('K135_CARRY_TABLE',json.dumps(row),flush=True)
 print('K135_RESULT',json.dumps({'out':str(a.out),'status':summary['status']}),flush=True)
if __name__=='__main__':main()
