"""Inspect the locally installed official invsqrt API; no downloaded replacement.

Explicitly uses the official default specification at n_p=10, preserving its
shots, precision, tolerance and domain. Archived one-shot receipts are history,
not an authority for changing the official defaults.
"""
import argparse
import ast
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def inspect(script, output, direction):
    script=Path(script).resolve()
    if not script.is_file(): raise ValueError('Official verifier unavailable: '+str(script))
    raw=script.read_bytes(); tree=ast.parse(raw)
    literals={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str)}
    required={'--format','--n-p','--seed','--max-workers'}
    if not required.issubset(literals): raise ValueError('Unsupported verifier CLI; inspect its current API')
    sys.path.insert(0,str(script.parent.parent))
    spec=importlib.util.spec_from_file_location('autonomous_official_invsqrt',script)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    problem=module.ProblemSpecInvSqrt.for_n_p(10)
    domain=dataclasses.asdict(problem)
    shots=problem.num_shots
    if callable(shots): shots=shots()
    if type(shots) is not int or shots<=0: raise ValueError('Unsupported official shot-count API')
    fields={x:x for x in ['toffoli_count','rotation_count','rotation_eps','reaction_depth',
                         'num_qubits','toffoli_equivalent','worst_error_over_tolerance']}
    # These are established by archived K058 receipts. Any changed version that
    # omits fields will fail closed when baseline verification runs.
    contract={'script':str(script),'script_sha256':hashlib.sha256(raw).hexdigest(),
              'direction':direction,'seeds':[12345,23456],'full_shots':shots,
              'fields':fields,'official_spec_defaults':domain,
              'argv':['{python}','{script}','{candidate}','--format','kmx',
                      '--n-p','10','--seed','{seed}','--max-workers','{workers}'],
              'source_audit':{'ast_checked':True,'default_spec_loaded':True,
                              'score_source_read':False,'reason':'Model remains uncalibrated until fresh receipts exist'}}
    Path(output).write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--script',default='competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py')
    p.add_argument('--output',required=True)
    p.add_argument('--direction',choices=['minimize','maximize'],required=True,
                   help='Local verifier score is historically cost (minimize); leaderboard aggregate may maximize')
    a=p.parse_args()
    try: print(json.dumps(inspect(a.script,a.output,a.direction),indent=2))
    except (ValueError,AttributeError,ImportError) as exc: p.exit(2,str(exc)+'\n')

if __name__=='__main__': main()
