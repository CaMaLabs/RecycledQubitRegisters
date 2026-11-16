#!/usr/bin/env python3
"""K169: audit K168 measured lookup costs; do not infer affine gate counts from CSD terms."""
import argparse, json, pathlib, re, subprocess, sys

PREFIX = re.compile(r'^(K168_[A-Z_]+)\s+(\{.*\})$')

def run_k168(python, script):
    result = subprocess.run([python, str(script)], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'K168 failed ({result.returncode}):\n{result.stdout}\n{result.stderr}')
    parsed = {}
    for line in result.stdout.splitlines():
        m = PREFIX.match(line.strip())
        if m:
            parsed.setdefault(m.group(1), []).append(json.loads(m.group(2)))
    if 'K168_LOOKUP' not in parsed or len(parsed.get('K168_SEGMENT', [])) != 8:
        raise RuntimeError('Unexpected K168 output; refusing to infer missing costs.\n' + result.stdout)
    if 'K168_SELFTEST PASS' not in result.stdout:
        raise RuntimeError('K168 selftest did not pass')
    return parsed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--k168', default='competition/k168/k168_q14_cost.py')
    ap.add_argument('--affine-costs', help='JSON file: {"0": {"CCX": 12, "CX": 50, "verified": true}, ...}; costs must be independently measured')
    ap.add_argument('--out', default='competition/k169/results/audit.json')
    args = ap.parse_args()
    data = run_k168(args.python, args.k168)
    lookup = data['K168_LOOKUP'][0]
    costs = json.loads(pathlib.Path(args.affine_costs).read_text()) if args.affine_costs else {}
    rows = []
    for seg in sorted(data['K168_SEGMENT'], key=lambda x: x['segment']):
        idx = str(seg['segment'])
        candidate = costs.get(idx)
        verified = isinstance(candidate, dict) and candidate.get('verified') is True
        if verified:
            for k in ('CCX', 'CX'):
                if type(candidate.get(k)) is not int or candidate[k] < 0:
                    raise ValueError(f'Segment {idx}: invalid {k}')
        choose_affine = verified and candidate['CCX'] < seg['lookup_CCX']
        rows.append({
            'segment': seg['segment'], 'affine_CSD_terms': seg['affine_CSD_terms'],
            'lookup_CCX': seg['lookup_CCX'], 'lookup_CX': seg['lookup_CX'],
            'affine_verified': verified,
            'affine_CCX': candidate['CCX'] if verified else None,
            'affine_CX': candidate['CX'] if verified else None,
            'choice': 'affine' if choose_affine else 'lookup',
            'chosen_CCX': candidate['CCX'] if choose_affine else seg['lookup_CCX'],
            'chosen_CX': candidate['CX'] if choose_affine else seg['lookup_CX'],
        })
    total_ccx = sum(r['chosen_CCX'] for r in rows)
    total_cx = sum(r['chosen_CX'] for r in rows)
    segment_lookup_cx = sum(r['lookup_CX'] for r in rows)
    cx_overhead = lookup['CX'] - segment_lookup_cx
    if cx_overhead < 0:
        raise RuntimeError('K168 segment CX exceeds total CX; cannot reconcile accounting')
    total_cx += cx_overhead
    result = {
        'source': str(args.k168), 'k168_selftest': 'PASS',
        'lookup': lookup, 'rows': rows,
        'lookup_segment_CX_sum': segment_lookup_cx,
        'selector_or_shared_CX_overhead': cx_overhead,
        'hybrid_estimated_CCX': total_ccx, 'hybrid_estimated_CX': total_cx,
        'CCX_saved_vs_lookup': lookup['CCX'] - total_ccx,
        'all_affine_choices_verified': all(r['affine_verified'] for r in rows),
        'hybrid_coherence_verified': False,
        'full_helios_candidate': False,
        'warning': 'Affine gate counts must be independently verified for arbitrary target XOR, superpositions and clean ancillas. This is a cost audit, not a constructed hybrid circuit.'
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    for r in rows:
        print('K169_SEGMENT', json.dumps(r, sort_keys=True))
    print('K169_RESULT', json.dumps({k: result[k] for k in ('hybrid_estimated_CCX', 'hybrid_estimated_CX', 'CCX_saved_vs_lookup', 'hybrid_coherence_verified', 'full_helios_candidate')}, sort_keys=True))
    print('K169_WRITTEN', out)

if __name__ == '__main__':
    main()
