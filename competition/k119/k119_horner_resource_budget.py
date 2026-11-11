#!/usr/bin/env python3
"""K119 conservative resource break-even screen for K118 polynomial.

No simulated quantum costs are fabricated. Computes *allowable* cost
budgets from the officially measured baseline, with configurable
non-Horner overhead and phase-rotation budgets. Separately prints
naive multiplier AND-product counts as an illustrative construction,
not a proven lower bound or scored Toffoli count.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
BASE_SCORE=95369.00696815242
BASE_Q=62
BASE_TOFFOLI=1243.118965920014
BASE_ROT=41.0
BASE_T_EQ=BASE_SCORE/BASE_Q
BASE_NON_TOFFOLI_EQ=BASE_T_EQ-BASE_TOFFOLI
STAGES=9

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--widths',default='62,60,58,56,54,50,46,42,38')
    p.add_argument('--fraction-bits',type=int,default=32)
    p.add_argument('--degree',type=int,default=9)
    p.add_argument('--other-toffoli',type=float,default=0)
    p.add_argument('--other-t-equivalent',type=float,default=0)
    p.add_argument('--rotation-equivalent',type=float,default=BASE_NON_TOFFOLI_EQ,
                   help='Cost of rotations/T gates in Toffoli equivalents. Default baseline observed.')
    p.add_argument('--output',type=Path,default=Path('competition/k119/results/break_even.json'))
    a=p.parse_args()
    if a.degree<=0 or a.fraction_bits<=0:p.error('degree, fraction-bits positive')
    widths=sorted({int(x) for x in a.widths.split(',')},reverse=True)
    if any(w<=0 for w in widths):p.error('widths positive')
    rows=[]
    for w in widths:
        total_eq=BASE_SCORE/w
        available=total_eq-a.rotation_equivalent-a.other_toffoli-a.other_t_equivalent
        rows.append({'qubits':w,'baseline_score_to_beat':BASE_SCORE,
            'max_total_toffoli_equivalent':total_eq,
            'assumed_non_horner_toffoli':a.other_toffoli,
            'assumed_rotation_and_T_equivalent':a.rotation_equivalent+a.other_t_equivalent,
            'available_for_all_multiply_stages':available,
            'average_toffoli_equivalent_budget_per_stage':available/a.degree,
            'feasible_at_nonnegative_budget':available>0})
    # Truncated schoolbook n x n fixed-point product retains output
    # columns n..2*n-1; cross-term count only an illustrative accounting.
    n=a.fraction_bits
    retained_pairs=sum(1 for i in range(n) for j in range(n) if n<=i+j<2*n)
    report={'status':'BUDGET_ONLY','baseline':{'qubits':BASE_Q,
       'score':BASE_SCORE,'executed_toffoli_count':BASE_TOFFOLI,
       'toffoli_equivalent':BASE_T_EQ,
       'observed_rotation_and_T_equivalent':BASE_NON_TOFFOLI_EQ,
       'rotation_count':BASE_ROT},'degree':a.degree,
       'fraction_bits':n,'scenarios':rows,
       'naive_schoolbook_product_pairs_for_upper_half':retained_pairs,
       'warnings':[
        'Upper-half binary products are not a cost bound: fixed-point Horner includes rounding, carries and signed coefficients.',
        'No concrete Kickmix multiplier circuit synthesized; 1 product pair is NOT reliably equal to 1 executed Toffoli.',
        'Actual widths, cleanup, input restoration, conditions, and dynamic gate probabilities must be measured.',
        'Baseline rotation cost is held constant as an assumption, not an established implementation property.',
        'Numerical K118 success is not evidence of quantum resource improvement.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('K119_BASE',json.dumps(report['baseline']))
    for row in rows:print('K119_BUDGET',json.dumps(row),flush=True)
    print('K119_RESULT',json.dumps({'status':report['status'],
       'retained_product_pairs_illustrative':retained_pairs,'out':str(a.output)}),flush=True)
if __name__=='__main__':main()
