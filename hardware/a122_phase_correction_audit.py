#!/usr/bin/env python3
"""A122: audit phase correction omitted from A116-A121 pulse timing.

Enumerates ideal diagonal phases for sequential and two-layer transition
circuits; checks whether a single spin Z or quadratic Z evolution produces
the correction up to global phase. No hardware calibration or claim of
a minimal pulse decomposition.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
S=3.5
D=8
SEQ=tuple((k,) for k in range(6,-1,-1))
PAR=((0,2,4,6),(1,3,5))
def transition_group(edges):
    u=np.eye(D,dtype=complex)
    for k in edges:
        u[k,k]=u[k+1,k+1]=0
        u[k,k+1]=u[k+1,k]=-1j
    return u
def characterize(groups):
    u=np.eye(D,dtype=complex)
    for edges in groups:u=transition_group(edges)@u
    perm=np.argmax(abs(u),axis=0)
    order=[0]
    for i in range(D-1):
        nxt=int(perm[order[-1]])
        if nxt in order:raise AssertionError('Not a single 8-cycle')
        order.append(nxt)
    B=np.eye(D)[:,order]
    w=B.conj().T@u@B
    phases=np.array([w[(i+1)%D,i] for i in range(D)])
    correction=np.conj(np.roll(phases,1))
    if np.max(abs(np.diag(correction)@w - np.roll(np.eye(D),1,axis=0)))>1e-12:
        raise AssertionError('Correction check failed')
    # Convert logical correction to physical spin-level ordering.
    phys=np.empty(D,dtype=complex)
    phys[order]=correction
    phys=phys/phys[0]
    ratio=phys[1:]/phys[:-1]
    second=ratio[1:]/ratio[:-1]
    z_only=max(abs(ratio-ratio[0]))
    quadratic=max(abs(second-second[0]))
    return {'logical_to_physical_levels':order,
      'correction_physical_relative_to_level_0':[{'real':float(z.real),'imag':float(z.imag)} for z in phys],
      'distinct_relative_phases':len(set((round(z.real,10),round(z.imag,10)) for z in phys)),
      'linear_Z_test_max_deviation':float(z_only),
      'quadratic_Z_test_max_deviation':float(quadratic),
      'single_linear_Z_possible':bool(z_only<1e-12),
      'single_linear_plus_quadratic_Z_possible':bool(quadratic<1e-12),
      'interlevel_phase_discontinuities':int(sum(abs(ratio-1)>1e-12)),
      'note':'Tests whether diagonal phases equal exp(i*a*m+i*b*m^2) up to global phase. A failed test does not establish the minimal cost of general controls.'}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=Path('results/a122_spin_phase_correction_audit.json'))
    a=ap.parse_args()
    records={'sequential':characterize(SEQ),'two_layer':characterize(PAR)}
    result={'status':'PASS_PHASE_AUDIT','records':records,
      'interpretation':[
        'A116-A121 treated correction as ideal and free.',
        'A selective level-dependent phase gate generally requires additional control.',
        'This audit establishes whether simple global/linear/quadratic diagonal evolution suffices, but does not price additional controls.',
        'The two-layer comparison is incomplete until phase correction, noise and control-time costs are incorporated.'
      ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A122_RESULT',json.dumps({'status':result['status'],
      'sequential':records['sequential'],'two_layer':records['two_layer'],
      'output':str(a.out)}),flush=True)
if __name__=='__main__':main()
