#!/usr/bin/env python3
import argparse, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit.library import QFTGate
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    try:
        from qiskit_ibm_runtime.circuit import MidCircuitMeasure
    except Exception:
        MidCircuitMeasure = None
except Exception:
    print('Missing Qiskit dependencies.', file=sys.stderr)
    print('Install with:', file=sys.stderr)
    print('  python -m pip install "qiskit~=2.5.2" "qiskit-ibm-runtime~=0.47.0"', file=sys.stderr)
    raise

SCRIPT_REVISION = '2026-09-13-shared-layout-fix4'
DEFAULT_PHASES = [0.125, 0.3125, 0.6875]

def make_service():
    instance = os.getenv('IBM_QUANTUM_INSTANCE')
    if instance:
        return QiskitRuntimeService(instance=instance)
    token = os.getenv('IBM_QUANTUM_API_KEY')
    if token:
        return QiskitRuntimeService(token=token, plans_preference=['open'], region='us-east')
    return QiskitRuntimeService(plans_preference=['open'], region='us-east')

def backend_has_measure2(backend):
    try:
        return 'measure_2' in backend.supported_instructions
    except Exception:
        return False

def select_backend(service, min_qubits, backend_name=None):
    if backend_name:
        backend = service.backend(backend_name)
        status = backend.status()
        if not status.operational:
            raise SystemExit(f'Backend {backend_name} is not operational.')
        if backend.num_qubits < min_qubits:
            raise SystemExit(f'Backend {backend_name} has only {backend.num_qubits} qubits; {min_qubits} are required.')
        return backend
    return service.least_busy(operational=True, simulator=False, dynamic_circuits=True, min_num_qubits=min_qubits)

def mid_measure(qc, qubit, clbit, use_measure2):
    if use_measure2 and MidCircuitMeasure is not None:
        qc.append(MidCircuitMeasure(), [qubit], [clbit])
    else:
        qc.measure(qubit, clbit)

def build_feedback_probe(use_measure2=True):
    q = QuantumRegister(1, 'q')
    first = ClassicalRegister(1, 'first')
    final = ClassicalRegister(1, 'final')
    qc = QuantumCircuit(q, first, final, name='dynamic_feedback_probe')
    qc.h(q[0])
    mid_measure(qc, q[0], first[0], use_measure2)
    with qc.if_test((first[0], 1)):
        qc.x(q[0])
    qc.measure(q[0], final[0])
    return qc

def build_wide_qpe(phi, bits):
    q = QuantumRegister(bits + 1, 'q')
    phase = ClassicalRegister(bits, 'phase')
    qc = QuantumCircuit(q, phase, name=f'wide_qpe_{bits}b_phi_{phi:.6f}')
    system = q[bits]
    qc.x(system)
    for k in range(bits):
        qc.h(q[k])
        qc.cp(2 * math.pi * phi * (2 ** k), q[k], system)
    qc.append(QFTGate(bits).inverse(), list(q[:bits]))
    qc.measure(list(q[:bits]), list(phase))
    return qc

def build_iterative_qpe(phi, bits, use_measure2=True, park_system_ground=True):
    q = QuantumRegister(2, 'q')
    phase = ClassicalRegister(bits, 'phase')
    qc = QuantumCircuit(q, phase, name=f'iterative_2q_{bits}b_phi_{phi:.6f}')
    anc, system = q[0], q[1]

    # Park the known system eigenstate in |0> during relatively slow
    # mid-circuit measurement/reset/feed-forward intervals. Excite it to |1>
    # only around the controlled phase kickback operation.
    if not park_system_ground:
        qc.x(system)

    for k in range(bits - 1, -1, -1):
        dest = bits - 1 - k
        qc.reset(anc)
        qc.h(anc)

        if park_system_ground:
            qc.x(system)
            qc.cp(2 * math.pi * phi * (2 ** k), anc, system)
            qc.x(system)
        else:
            qc.cp(2 * math.pi * phi * (2 ** k), anc, system)

        for j in range(k + 1, bits):
            prior_c = bits - 1 - j
            angle = -2 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)

        qc.h(anc)
        mid_measure(qc, anc, phase[dest], use_measure2)

    return qc

def bitstring_to_int(s):
    return int(s.replace(' ', ''), 2)

def nearest_phase_integer(phi, bits):
    return int(round((phi % 1.0) * (2 ** bits))) % (2 ** bits)

def summarize_counts(counts, phi=None, bits=None):
    total = sum(counts.values())
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    out = {'shots': total, 'top': [{'bitstring': k, 'count': int(v), 'prob': v / total} for k, v in ordered[:8]]}
    if phi is not None and bits is not None:
        target = nearest_phase_integer(phi, bits)
        good = sum(v for k, v in counts.items() if bitstring_to_int(k) == target)
        out.update({'target_integer': target, 'target_bitstring': format(target, f'0{bits}b'), 'target_probability': good / total})
    return out

def get_register_counts(pub_result, register_name):
    return getattr(pub_result.data, register_name).get_counts()

def safe_usage(service):
    try:
        return service.usage()
    except Exception as exc:
        return {'unavailable': str(exc)}

def safe_metrics(job):
    try:
        return job.metrics()
    except Exception as exc:
        return {'unavailable': str(exc)}

def _inst_props(backend, name, qubits):
    try:
        p = backend.target[name][tuple(qubits)]
        return {'duration_s': None if p.duration is None else float(p.duration), 'error': None if p.error is None else float(p.error)}
    except Exception:
        return {'duration_s': None, 'error': None}

def _cz_edges(backend):
    edges = set()
    try:
        for qargs in backend.target['cz'].keys():
            if qargs is None or len(qargs) != 2:
                continue
            a, b = int(qargs[0]), int(qargs[1])
            edges.add((a, b))
    except Exception:
        pass
    return edges

def _best_shared_region(backend, nqubits):
    edges = _cz_edges(backend)
    if not edges:
        raise RuntimeError('Backend exposes no CZ edges.')

    undirected = {}
    for a, b in edges:
        undirected.setdefault(a, set()).add(b)
        undirected.setdefault(b, set()).add(a)

    def edge_error(a, b):
        vals = []
        for e in ((a, b), (b, a)):
            p = _inst_props(backend, 'cz', e)
            if p['error'] is not None:
                vals.append(p['error'])
        return min(vals) if vals else 1.0

    def mcm_error(q):
        p = _inst_props(backend, 'measure_2', (q,))
        if p['error'] is not None:
            return p['error']
        p = _inst_props(backend, 'measure', (q,))
        return p['error'] if p['error'] is not None else 1.0

    def mcm_duration(q):
        p = _inst_props(backend, 'measure_2', (q,))
        return p['duration_s'] if p['duration_s'] is not None else 1.0

    candidates = []
    seen_undirected = set()
    for a, b in edges:
        key = tuple(sorted((a, b)))
        if key in seen_undirected:
            continue
        seen_undirected.add(key)
        for anc, system in ((a, b), (b, a)):
            region = [anc, system]
            while len(region) < nqubits:
                frontier = []
                for u in region:
                    for v in undirected.get(u, ()):
                        if v in region:
                            continue
                        frontier.append((edge_error(u, v), u, v))
                if not frontier:
                    break
                frontier.sort()
                _, _, v = frontier[0]
                region.append(v)
            if len(region) < nqubits:
                continue

            local_edge_errors = []
            for u in region:
                for v in undirected.get(u, ()):
                    if v in region and u < v:
                        local_edge_errors.append(edge_error(u, v))
            pair_err = edge_error(anc, system)
            read_err = mcm_error(anc)
            read_dur = mcm_duration(anc)
            local_mean = sum(local_edge_errors) / len(local_edge_errors) if local_edge_errors else 1.0
            score = 5.0 * pair_err + 3.0 * read_err + 0.5 * local_mean + 0.05 * (read_dur / 1e-6)
            candidates.append((score, anc, system, region))

    if not candidates:
        raise RuntimeError('Could not find a connected shared region.')
    candidates.sort(key=lambda x: x[0])
    score, anc, system, region = candidates[0]
    calibration = {
        'score': score,
        'ancilla_physical': anc,
        'system_physical': system,
        'region': region,
        'ancilla_measure_2': _inst_props(backend, 'measure_2', (anc,)),
        'ancilla_measure': _inst_props(backend, 'measure', (anc,)),
        'pair_cz_forward': _inst_props(backend, 'cz', (anc, system)),
        'pair_cz_reverse': _inst_props(backend, 'cz', (system, anc)),
    }
    return region, anc, system, calibration

def compile_circuit(circuit, backend, optimization_level=1, initial_layout=None):
    pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level, initial_layout=initial_layout, seed_transpiler=8776)
    return pm.run(circuit)

def compile_circuits(circuits, backend, optimization_level=1):
    return [compile_circuit(c, backend, optimization_level=optimization_level) for c in circuits]

def run_probe(service, backend, shots, max_execution_time):
    use_measure2 = backend_has_measure2(backend)
    logical = build_feedback_probe(use_measure2)
    compiled = compile_circuit(logical, backend)
    sampler = SamplerV2(mode=backend, options={'max_execution_time': max_execution_time})
    job = sampler.run([compiled], shots=shots)
    print('Probe job ID:', job.job_id())
    result = job.result()[0]
    first_counts = get_register_counts(result, 'first')
    final_counts = get_register_counts(result, 'final')
    final_zero = final_counts.get('0', 0)
    return {
        'job_id': job.job_id(), 'backend': backend.name, 'measure_2_used': use_measure2,
        'shots': shots, 'first_counts': first_counts, 'final_counts': final_counts,
        'feedback_success_probability': final_zero / shots, 'metrics': safe_metrics(job),
    }

def run_comparison(service, backend, bits, shots, phases, max_execution_time, park_system_ground=True, shared_layout=False):
    use_measure2 = backend_has_measure2(backend)
    logical, metadata = [], []
    for phi in phases:
        logical.extend([build_wide_qpe(phi, bits), build_iterative_qpe(phi, bits, use_measure2, park_system_ground)])
        metadata.extend([
            {'kind': 'wide', 'phi': phi, 'bits': bits, 'register': 'phase'},
            {'kind': 'iterative_2q', 'phi': phi, 'bits': bits, 'register': 'phase'},
        ])

    print('Transpiling circuits for', backend.name, '...')
    shared_info = None
    if shared_layout:
        region, anc_phys, sys_phys, shared_info = _best_shared_region(backend, bits + 1)
        remaining = [q for q in region if q not in (anc_phys, sys_phys)]
        wide_layout = [anc_phys] + remaining[:bits - 1] + [sys_phys]
        iter_layout = [anc_phys, sys_phys]
        print('Shared physical region:', region)
        print('Wide initial layout:', wide_layout)
        print('2Q initial layout:', iter_layout)
        print('Shared-layout calibration:')
        print(json.dumps(shared_info, indent=2, default=str))
        isa = []
        for circuit, meta in zip(logical, metadata):
            layout = wide_layout if meta['kind'] == 'wide' else iter_layout
            isa.append(compile_circuit(circuit, backend, optimization_level=1, initial_layout=layout))
    else:
        isa = compile_circuits(logical, backend)

    transpiled_stats = []
    for original, compiled, meta in zip(logical, isa, metadata):
        try:
            physical_layout = compiled.layout.final_index_layout(filter_ancillas=True)
        except Exception:
            physical_layout = None
        transpiled_stats.append({
            **meta,
            'logical_qubits': original.num_qubits,
            'compiled_qubits': compiled.num_qubits,
            'physical_layout': physical_layout,
            'depth': compiled.depth(),
            'size': compiled.size(),
            'count_ops': {str(k): int(v) for k, v in compiled.count_ops().items()},
        })

    print(f'Submitting {len(isa)} circuits x {shots} shots...')
    sampler = SamplerV2(mode=backend, options={'max_execution_time': max_execution_time})
    job = sampler.run(isa, shots=shots)
    print('Comparison job ID:', job.job_id())
    pubs = job.result()

    results = []
    for pub, meta in zip(pubs, metadata):
        counts = get_register_counts(pub, meta['register'])
        results.append({**meta, 'counts': counts, 'summary': summarize_counts(counts, meta['phi'], meta['bits'])})

    paired = []
    for i in range(0, len(results), 2):
        wide, it = results[i], results[i + 1]
        paired.append({
            'phi': wide['phi'],
            'target_bitstring': wide['summary']['target_bitstring'],
            'wide_target_probability': wide['summary']['target_probability'],
            'iterative_target_probability': it['summary']['target_probability'],
            'iterative_minus_wide': it['summary']['target_probability'] - wide['summary']['target_probability'],
        })

    return {
        'job_id': job.job_id(), 'backend': backend.name, 'measure_2_used': use_measure2,
        'system_ground_parked': park_system_ground, 'shared_layout': shared_layout,
        'shared_layout_info': shared_info, 'bits': bits, 'shots': shots, 'phases': phases,
        'metrics': safe_metrics(job), 'transpiled_stats': transpiled_stats,
        'results': results, 'paired_comparison': paired,
    }

def main():
    ap = argparse.ArgumentParser(description='IBM hardware test for recycled 6C2Q-style dynamic QPE.')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe', action='store_true', help='Run a tiny dynamic feedback sanity check.')
    mode.add_argument('--run', action='store_true', help='Run wide-QPE vs recycled 2Q comparison.')
    ap.add_argument('--bits', type=int, default=4)
    ap.add_argument('--shots', type=int, default=128)
    ap.add_argument('--phase', type=float, action='append')
    ap.add_argument('--max-execution-time', type=int, default=30)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--legacy-system-excited', action='store_true', help='Keep iterative-QPE system qubit in |1> across feedback cycles (old behavior).')
    ap.add_argument('--backend', type=str, default=None, help='Pin execution to a specific IBM backend, e.g. ibm_fez.')
    ap.add_argument('--shared-layout', action='store_true', help='Force wide and iterative circuits into the same physical-qubit neighborhood.')
    args = ap.parse_args()
    print(f'Script revision: {SCRIPT_REVISION}')

    service = make_service()
    usage_before = safe_usage(service)
    print('Current Open Plan account usage:')
    print(json.dumps(usage_before, indent=2, default=str))

    min_qubits = 1 if args.probe else args.bits + 1
    backend = select_backend(service, min_qubits, args.backend)
    print(f'Selected backend: {backend.name} | qubits={backend.num_qubits} | measure_2={backend_has_measure2(backend)}')

    payload = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'backend': backend.name,
        'backend_num_qubits': backend.num_qubits,
        'account_usage_before': usage_before,
        'mode': 'probe' if args.probe else 'comparison',
    }

    if args.probe:
        payload['probe'] = run_probe(service, backend, args.shots, args.max_execution_time)
    else:
        phases = args.phase if args.phase else DEFAULT_PHASES
        payload['comparison'] = run_comparison(
            service, backend, args.bits, args.shots, phases, args.max_execution_time,
            park_system_ground=(not args.legacy_system_excited), shared_layout=args.shared_layout,
        )

    payload['account_usage_after'] = safe_usage(service)
    print('\nRESULT')
    print(json.dumps(payload, indent=2, default=str))

    if args.output:
        out = args.output
    else:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        label = 'probe' if args.probe else 'comparison'
        out = Path(f'ibm_6c2q_{label}_{stamp}.json')
    out.write_text(json.dumps(payload, indent=2, default=str))
    print('\nSaved:', out.resolve())

if __name__ == '__main__':
    main()
