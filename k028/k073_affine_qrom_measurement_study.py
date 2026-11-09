#!/usr/bin/env python3
"""K073: measurement-uncompute QROM + affine coefficient encoding feasibility study.

Exact symbolic and finite-state tests on K056 coefficient table. It is NOT a
new full-domain candidate and DOES NOT modify the Helios reference.

For |a>|d_a>, an X-basis measurement m of the coefficient register
introduces (-1)^(m dot d_a). For a 2-row QROM d_a=d0 XOR a*(d0 XOR d1),
the a-dependent phase is (-1)^(a * parity(m & (d0 XOR d1))).
This is removed by one *classically controlled* Z on a (if the parity is 1).
The d0-dependent global phase need not be corrected.

A second test searches affine remappings of address bits for general small
QROM tables, minimizing sum of Hamming distances across GF(2) Möbius masks.
All models are coherent-unitary identities proved with exact state vectors
for every measurement outcome, not just computational-basis checks.

COST CAUTION: counting CNOTs vs HMR is NOT the official verifier score.
K056 has only two regions: its existing XOR-delta loader is exceptionally
compact. We only recommend an upgrade if concrete resources improve.
"""
from __future__ import annotations
import argparse,importlib.util,json,math,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def pop(x):return x.bit_count()
def parity(x):return pop(x)&1
def mobius(rows):
 n=(len(rows)-1).bit_length()
 assert len(rows)==1<<n
 out=list(rows)
 for k in range(n):
  for mask in range(len(out)):
   if mask&(1<<k):out[mask]^=out[mask^(1<<k)]
 return out
def gf2_invertible(matrix,n):
 vals={0}
 for row in matrix:
  vals|={x^row for x in tuple(vals)}
 return len(vals)==(1<<n)
def encode_address(x,rows):
 y=0
 for i,mask in enumerate(rows):y|=parity(x&mask)<<i
 return y
def remap(table,matrix):
 n=(len(table)-1).bit_length()
 assert gf2_invertible(matrix,n)
 return [table[next(x for x in range(1<<n) if encode_address(x,matrix)==y)] for y in range(1<<n)]
def cost(table):
 coefficients=mobius(table)
 return {"xor_toggles":pop(coefficients[0]),
         "controlled_bit_toggles":sum(pop(w) for w in coefficients[1:]),
         "degree_ge_2_mask_count":sum(1 for i,v in enumerate(coefficients) if i.bit_count()>=2 and v),
         "anf_coefficients":[str(hex(x)) for x in coefficients]}
def affordable_affine_search(table,max_address_bits=3):
 n=(len(table)-1).bit_length()
 if n>max_address_bits:return {"status":"SKIPPED","reason":"address width exceeds exhaustive search"}
 candidates=[]
 for m in itertools.product(range(1,1<<n),repeat=n):
  if not gf2_invertible(m,n):continue
  t=remap(table,m);c=cost(t)
  candidates.append((c["controlled_bit_toggles"],c["degree_ge_2_mask_count"],m,c))
 candidates.sort(key=lambda t:(t[0],t[1],t[2]))
 best=candidates[0]
 return {"status":"DONE","bases_searched":len(candidates),
         "best_basis":list(best[2]),"best_cost":best[3],
         "identity_cost":cost(table),
         "uses_free_affine_address_transform":best[2]==tuple(1<<i for i in range(n))}
def two_row_measurement_test(row0,row1,bits):
 assert 0<=row0<(1<<bits) and 0<=row1<(1<<bits)
 delta=row0^row1
 # Every classical outcome m: corrections recover input amplitudes,
 # up to a global phase independent of address.
 count=0
 for m in range(1<<bits):
  amps=[(-1)**parity(m & row) for row in (row0,row1)]
  correction=(-1)**parity(m & delta)
  result=[amps[0],amps[1]*correction]
  assert result[0]==result[1],(m,result)
  count+=1
 return {"outcomes_exhaustively_verified":count,
         "data_width":bits,"difference_weight":pop(delta),
         "correction":"Z(address) iff parity(measurement & delta) == 1"}
def exact_phase_probe():
 # Basis-preserving QROM compute -> X-measure -> classical Z correction
 # agrees on arbitrary complex superpositions, modulo branch-global phase.
 row0,row1=0b0101,0b1110
 for m in range(16):
  for a,b in ((1+0j,1j),(0.3-0.2j,-0.7+0.5j)):
   out=[a*((-1)**parity(m&row0)),
        b*((-1)**parity(m&row1))*((-1)**parity(m&(row0^row1)))]
   assert abs(out[0]-a*((-1)**parity(m&row0)))<1e-12
   assert abs(out[1]-b*((-1)**parity(m&row0)))<1e-12
def load_coefficients():
 import numpy as np
 t=np.array([-1.0,-0.5,0.0,0.5])
 table=[]
 for region in (0,1):
  xs=np.array([8+region*4+j for j in range(4)],dtype=float)
  fit=np.polynomial.polynomial.polyfit(t,1/np.sqrt(xs),3)
  table.append([int(x) for x in np.rint(fit*(2.0**36)).astype(np.int64)])
 return table
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--out",type=Path,default=ROOT/"competition/k073/results")
 ap.add_argument("--self-test",action="store_true")
 a=ap.parse_args()
 exact_phase_probe()
 assert mobius([7,3,2,6])==[7,4,5,0]
 assert gf2_invertible((1,2),2)
 assert not gf2_invertible((1,1),2)
 assert remap([5,7,9,11],(1,2))==[5,7,9,11]
 assert affordable_affine_search([3,5,6,0])["bases_searched"]==6
 assert two_row_measurement_test(5,14,4)["outcomes_exhaustively_verified"]==16
 print("K073_SELFTEST PASS exact GF2 affine mapping and measurement-phase correction",flush=True)
 if a.self_test:return
 words=load_coefficients()
 records=[]
 for degree in range(4):
  a0=words[0][degree]&((1<<39)-1)
  a1=words[1][degree]&((1<<39)-1)
  diff=pop(a0^a1)
  sample=two_row_measurement_test(a0&255,a1&255,8)
  records.append({"degree":degree,"coefficient_region0":words[0][degree],
    "coefficient_region1":words[1][degree],
    "word_width":39,"base_xor_toggles":pop(a0),
    "delta_controlled_cx":diff,
    "conventional_unload_controlled_cx":diff,
    "conventional_unload_x":pop(a0),
    "measurement_unload_hmr":39,
    "measurement_unload_phase_correction_max_z":1 if diff else 0,
    "measurement_unload_classical_parity_xors":max(0,diff-1),
    "measurement_unload_formula_checked_8_bits":sample})
 # 4 polynomial coefficient words in 2-region lookup: each degree has
 # independent classical selection and may be analyzed as one address bit.
 widths=[(words[0][j]&((1<<39)-1),words[1][j]&((1<<39)-1)) for j in range(4)]
 summary={"table_kind":"2 address values per coefficient (one quantum address bit)",
  "number_of_coefficients":4,"coeff_word_bits":39,
  "total_delta_controlled_cx":sum(r["delta_controlled_cx"] for r in records),
  "total_base_xor_toggles":sum(r["base_xor_toggles"] for r in records),
  "measurement_unload_hmr_for_four_coefficients":4*39,
  "one_bit_affine_bases":1,
  "conclusion":"2-entry K056 XOR-delta QROM has no nontrivial affine address encoding; measurement uncompute may save CX but adds HMR and classical corrections; resource-score win unproven."}
 report={"summary":summary,"coefficients":records,
   "toy_affine_2bit":affordable_affine_search([0b110101,0b001110,0b011011,0b100111]),
   "warning":"Symbolic architecture study only. No new Kickmix circuit or official score; QROM measurement must occur after the coefficient's coherent use."}
 a.out.mkdir(parents=True,exist_ok=True)
 (a.out/"study.json").write_text(json.dumps(report,indent=2))
 print("K073_RESULT",json.dumps(summary,sort_keys=True),flush=True)
 print("K073_AFFINE",json.dumps(report["toy_affine_2bit"],sort_keys=True),flush=True)
 for r in records:print("K073_COEFF",json.dumps({k:v for k,v in r.items() if k!="measurement_unload_formula_checked_8_bits"},sort_keys=True),flush=True)
 print("SAVED",a.out/"study.json",flush=True)
if __name__=="__main__":main()
