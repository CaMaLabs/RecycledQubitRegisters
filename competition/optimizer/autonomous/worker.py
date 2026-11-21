"""Isolated plugin execution, with exact postcondition proof."""
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from .core import Gate, cost, prove
from .passes import PLUGINS


def main():
    task=json.loads(Path(sys.argv[1]).read_text())
    gates=[Gate(g['op'],tuple(g['q'])) for g in task['gates']]
    try:
        proposal=PLUGINS[task['method']](gates,task['budget'],task['seed'])
        if proposal is None:
            result={'status':'NO_IMPROVEMENT','reason':'Bounded search exhausted or no applicable identity; no optimality claim'}
        elif proposal.detail.get('solver_status')=='UNAVAILABLE':
            result={'status':'UNAVAILABLE','reason':proposal.detail['reason'],'detail':proposal.detail}
        else:
            proof=prove(gates,proposal.gates)
            if proof['status']!='EXACT':
                result={'status':'PROOF_REJECT','reason':'Exact basis/phase comparison failed','proof':proof}
            elif cost(proposal.gates)>=cost(gates):
                result={'status':'NO_IMPROVEMENT','reason':'No static resource reduction','proof':proof,'detail':proposal.detail}
            else:
                result={'status':'LOCAL_IMPROVEMENT','reason':'Exact local proof; official result pending',
                        'proof':proof,'gates':[asdict(g) for g in proposal.gates],
                        'detail':proposal.detail,'before_cost':cost(gates),'after_cost':cost(proposal.gates)}
    except Exception:
        result={'status':'ERROR','reason':traceback.format_exc()[-4000:]}
    dest=Path(sys.argv[2]); temp=dest.with_suffix('.tmp')
    temp.write_text(json.dumps(result)); temp.replace(dest)

if __name__=='__main__': main()
