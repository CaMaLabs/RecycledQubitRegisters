#!/usr/bin/env python3
"""Run as a script from any working directory; assets stay rooted in the repo."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from competition.optimizer.autonomous.controller import PIN, REFERENCE, run
from competition.optimizer.autonomous.verification import run_process
from competition.optimizer.autonomous.circuit_io import detect_format, run_circuit
from competition.optimizer.autonomous.core import sha


K191_SOURCE = "competition/k191/results/helios_k191.kmx"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', help='KMX, Qiskit QPY, OpenQASM 2 or OpenQASM 3 circuit; defaults to K191')
    p.add_argument('--input-format', choices=['auto','kmx','qpy','qasm2','qasm3'], default='auto')
    p.add_argument('--circuit-index', type=int, default=0, help='Select a circuit from a QPY bundle')
    p.add_argument('--expected-sha', help='Optional immutable input SHA256; K191 is pinned automatically')
    p.add_argument('--reference-score', type=float, help='Optional official reference score')
    p.add_argument('--out', help='Campaign directory; defaults to a path keyed by input')
    p.add_argument('--profile',choices=['quick','overnight','extended'],default='quick')
    p.add_argument('--config',help='JSON overrides of profile settings')
    p.add_argument('--verify',action='store_true',help='Inspect installed official defaults and verify every eligible candidate')
    p.add_argument('--score-direction',choices=['minimize','maximize'],help='Required with --verify: historical verifier score is a cost')
    p.add_argument('--official-script',default=str(ROOT/'competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py'))
    p.add_argument('--contract',help='Inspected official verifier argv, SHA, metrics and full-domain contract')
    p.add_argument('--hours',type=float)
    p.add_argument('--max-jobs',type=int)
    p.add_argument('--resume',action='store_true',help='State always resumes; retained for explicit CLI intent')
    a=p.parse_args()
    a.source = a.source or str(ROOT / K191_SOURCE)
    baseline_parts = Path(K191_SOURCE).parts
    source_parts = Path(a.source).expanduser().absolute().parts
    if source_parts[-len(baseline_parts):] == baseline_parts:
        a.expected_sha = a.expected_sha or PIN
    if a.expected_sha == PIN and a.reference_score is None:
        a.reference_score = REFERENCE
    # Resolve user paths BEFORE rooting subprocess module imports in this repo.
    for name in ('source','out','config','contract','official_script'):
        value=getattr(a,name)
        if value is not None: setattr(a,name,str(Path(value).expanduser().resolve()))
    try:
        source = Path(a.source)
        kind = detect_format(source, a.input_format)
        if not a.out:
            digest = a.expected_sha or sha(source.read_bytes())
            name = "autonomous" if digest == PIN else f"{source.stem}-{digest[:12]}-{a.circuit_index}"
            a.out = str(ROOT / "competition/optimizer/runs" / name)
        if kind == "kmx":
            if a.circuit_index != 0:
                p.error("--circuit-index applies to QPY bundles")
            a.expected_sha = a.expected_sha or sha(source.read_bytes())
        elif a.verify or a.contract:
            p.error("The official invsqrt verifier requires KMX input")
    except (OSError, ValueError) as exc:
        p.exit(2, str(exc)+"\n")
    config=json.loads((Path(__file__).parent/'profiles'/(a.profile+'.json')).read_text())
    if a.config: config.update(json.loads(Path(a.config).read_text()))
    if a.hours is not None: config['hours']=a.hours
    if a.max_jobs is not None: config['max_jobs']=a.max_jobs
    os.chdir(ROOT)
    if a.verify and not a.contract:
        if not a.score_direction: p.error('--verify requires an explicit --score-direction')
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        a.contract=str(out/'official-contract.json')
        log=out/'official-inspection.log'
        result=run_process([sys.executable,'-m','competition.optimizer.autonomous.official_contract',
                '--script',a.official_script,'--output',a.contract,'--direction',a.score_direction],
                log,min(30,config['hours']*3600),config['memory_mb'],config['cpus'])
        if result.get('exit_code')!=0:
            p.exit(2,'Official asset inspection failed; see '+str(log)+'\n')
    try:
        if kind == "kmx":
            run(a, config)
        else:
            run_circuit(a, config, kind, run)
    except ImportError as exc:
        p.exit(2, f"Install requirements-circuits.txt for this input format: {exc}\n")
    except (ValueError, OSError, KeyError) as exc:
        p.exit(2, str(exc)+'\n')

if __name__=='__main__': main()
