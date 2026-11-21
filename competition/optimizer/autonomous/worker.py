"""Isolated plugin execution, with exact postcondition proof."""
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from .core import Gate, Proposal, gate_from_record, cost, prove
from .passes import PLUGINS


def main():
    task=json.loads(Path(sys.argv[1]).read_text())
    gates=[gate_from_record(g) for g in task['gates']]
    try:
        cached = task.get('cached')
        if cached is None:
            proposal = PLUGINS[task['method']](gates,task['budget'],task['seed'])
        elif cached['status'] == 'UNSAT':
            proposal = Proposal(gates, {**cached['detail'], 'semantic_cache_hit':True})
        else:
            remapped = [Gate(g['op'], tuple(task['wire_order'][i] for i in g['q']), g.get('angle'))
                        for g in cached['gates']]
            proposal = Proposal(remapped, {**cached['detail'], 'semantic_cache_hit':True})
        if proposal is None:
            result={'status':'NO_IMPROVEMENT','reason':'Bounded search exhausted or no applicable identity; no optimality claim'}
        elif proposal.detail.get('solver_status')=='UNAVAILABLE':
            result={'status':'UNAVAILABLE','reason':proposal.detail['reason'],'detail':proposal.detail}
        elif proposal.detail.get('solver_status') in {'UNSAT', 'UNKNOWN', 'TIMEOUT'}:
            result={'status': proposal.detail['solver_status'], 'reason':'Bounded synthesis result',
                    'detail':proposal.detail}
        else:
            proof=prove(gates,proposal.gates)
            if proof['status']!='EXACT':
                result={'status':'PROOF_REJECT','reason':'Exact basis/phase comparison failed','proof':proof}
            elif cost(proposal.gates)>=cost(gates):
                result={'status':'NO_IMPROVEMENT','reason':'No static resource reduction','proof':proof,'detail':proposal.detail}
            else:
                before_cost, after_cost = cost(gates), cost(proposal.gates)
                resources = ('toffoli_class','non_clifford_phase','instruction_count')
                gains = [before-after for before,after in zip(before_cost,after_cost)]
                result={'status':'LOCAL_IMPROVEMENT','reason':'Exact local proof; official result pending',
                        'proof':proof,'gates':[asdict(g) for g in proposal.gates],
                        'detail':proposal.detail,'before_cost':before_cost,'after_cost':after_cost,
                        'estimated_official_score':None, 'static_resource_delta':dict(zip(resources,gains))}
    except Exception:
        result={'status':'ERROR','reason':traceback.format_exc()[-4000:]}
    dest=Path(sys.argv[2]); temp=dest.with_suffix('.tmp')
    temp.write_text(json.dumps(result)); temp.replace(dest)

if __name__=='__main__': main()
