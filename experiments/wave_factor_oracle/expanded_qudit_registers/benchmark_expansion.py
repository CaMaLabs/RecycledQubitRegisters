#!/usr/bin/env python3
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
from pathlib import Path
import resource
from expanded_registers import ExpandedRegisters


def main():
    results=[]
    # Same physical carrier count in all three expanded configurations.
    # Fixed iteration counts are diagnostic, chosen for two ordered solutions.
    for d,m,n,k in [(8,2,3599,34),(16,2,59989,140),(32,2,1040399,567)]:
        ex=ExpandedRegisters(n,d,m)
        r=ex.run(k,shots=2000)
        r['peak_process_rss_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        r['iteration_policy']='Diagnostic fixed count, using known solution multiplicity 2'
        r['success_probability']=r['success_history'][-1]
        results.append(r)
        print(json.dumps({key:r[key] for key in ['N','levels_per_qudit',
              'total_physical_qudits_model','factor_capacity','iterations',
              'success_probability','accepted_counts','simulation_seconds']}),flush=True)
    # Matched dimensions vs original binary logical grouping.
    reference=ExpandedRegisters(3599,2,6).run(34,100)
    assert abs(reference['success_history'][-1]-results[0]['success_probability']) < 1e-12
    Path('expansion_results.json').write_text(json.dumps({
        'scope':'Ideal structured simulation; physical product register retained',
        'runs':results,
        'matched_binary_reference':{
            'qubits':reference['total_physical_qudits_model'],
            'capacity':reference['factor_capacity'],
            'probability':reference['success_history'][-1]},
        'fair_comparison':'8 eight-level carriers and 24 qubits have identical Hilbert dimension',
    },indent=2)+'\n')


if __name__=='__main__':
    main()
