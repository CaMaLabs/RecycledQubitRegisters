#!/usr/bin/env python3
"""Expanded-memory dense runs; resource-limited subprocesses, no algorithm change."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


def child(n, d, digits, k):
    # This process may allocate up to 5 GiB of address space, never unrestricted.
    resource.setrlimit(resource.RLIMIT_AS, (5*1024**3, 5*1024**3))
    from qudit_factor import Experiment
    start = time.perf_counter()
    ex = Experiment(n, d, digits, max_amplitudes=45_000_000)
    result = ex.run(k, shots=1000, seed=12345)
    assert abs(result['success_history'][-1]-result['grover_prediction']) < 1e-9
    assert abs(result['scratch_zero_probability_before_readout']-1) < 1e-9
    for pair in result['solution_weights']:
        assert pair['p']*pair['q'] == n
    row = {'N':n, 'd':d, 'digits':digits, 'iterations':k,
           'candidate_range':result['candidate_range'],
           'amplitudes':result['resources']['dense_state_amplitudes'],
           'logical_qudits':result['resources']['logical_d_level_qudits'],
           'baseline_probability':result['success_history'][0],
           'final_probability':result['success_history'][-1],
           'accepted_shots':result['accepted_shots'],
           'accepted_counts':result['accepted_counts'],
           'seconds':time.perf_counter()-start,
           'peak_rss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
           'policy':'Fixed diagnostic iteration count; not unknown-count search'}
    print(json.dumps(row), flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--child', nargs=4, type=int)
    args=parser.parse_args()
    if args.child:
        child(*args.child)
        return
    rows=[]
    for case in [(3721,2,6,48), (6241,3,4,62), (5767,3,4,43)]:
        result=subprocess.run([sys.executable,__file__,'--child',*map(str,case)],
                              text=True,capture_output=True,timeout=300)
        if result.returncode != 0:
            row={'case':case,'status':'FAILED','returncode':result.returncode,
                 'stderr':result.stderr[-3000:]}
        else:
            row=json.loads(result.stdout)
            row['status']='PASS'
        rows.append(row)
        Path('stress_results.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(row),flush=True)


if __name__=='__main__':
    main()
