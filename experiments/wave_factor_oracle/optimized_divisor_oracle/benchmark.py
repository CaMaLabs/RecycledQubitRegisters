#!/usr/bin/env python3
"""Resource comparison; largest configuration is compiled/counted, not run."""
from collections import Counter
import json
from pathlib import Path
import baseline
import optimized_division as optimized


def main():
    rows=[]
    for n,m in [(35,3),(323,5),(1040399,10)]:
        row={'N':n,'candidate_bits':m,
             'validation_scope':'End-to-end simulation' if m<=5 else 'Circuit resource counts only'}
        for name,builder in [('before',baseline.build),('after',optimized.build)]:
            c,division,mark,oracle=builder(n.bit_length(),m)
            row[name]={'qubits':c.qubits,
                       'gate_counts':dict(Counter(g[0] for g in oracle)),
                       'oracle_gates':len(oracle),
                       **optimized.schedule_cost(oracle)}
        rows.append(row)
    rendered=json.dumps(rows,indent=2)+'\n'
    Path('resource_comparison.json').write_text(rendered)
    print(rendered)


if __name__=='__main__':
    main()
