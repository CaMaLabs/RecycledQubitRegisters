#!/usr/bin/env python3
"""A82: public-data reversible XOR basis search for A44 modular multipliers.

This is an encoding experiment, not a scalable factoring algorithm.
The A44 permutation synthesis itself scales exponentially in work-register bits.
No factors or multiplicative order are supplied to the candidate search.
"""
import argparse, json, math, random, sys, time
from pathlib import Path
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import MCXVChain
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware"))
from qrr_a44_generic_modular_multiplier import exchanges, mapping
from qrr_a79_semiprime_frontier import is_semiprime

def encode(x, rows):
    return sum(((x & row).bit_count() & 1) << i for i, row in enumerate(rows))

def random_basis(width, rng, steps):
    rows = [1 << i for i in range(width)]
    for _ in range(steps):
        i = rng.randrange(width)
        j = rng.randrange(width - 1)
        if j >= i:
            j += 1
        rows[i] ^= rows[j]
    return tuple(rows)

def conjugated_mapping(n, factor, rows):
    size = 1 << n.bit_length()
    out = [None] * size
    for x, y in enumerate(mapping(n, factor)):
        out[encode(x, rows)] = encode(y, rows)
    assert sorted(out) == list(range(size))
    return out

def path_cost(perm):
    # Number of multiqubit-controlled Gray edge swaps, not transpiled CX.
    return sum(2 * ((u ^ v).bit_count()) - 1 for u, v in exchanges(perm))

def build_multiplier(perm, width):
    circuit = QuantumCircuit(2 * width - 1)
    work = list(range(1, width + 1))
    scratch = list(range(width + 1, 2 * width - 1))
    frame = 0
    for a, b in exchanges(perm):
        path = [a]
        for j in range(width):
            if (a ^ b) & (1 << j):
                path.append(path[-1] ^ (1 << j))
        edges = list(range(len(path) - 1)) + list(range(len(path) - 3, -1, -1))
        for k in edges:
            u, v = path[k], path[k + 1]
            bit = (u ^ v).bit_length() - 1
            mask = sum(1 << j for j in range(width) if j != bit and not (u & (1 << j)))
            for j in range(width):
                if (frame ^ mask) & (1 << j):
                    circuit.x(work[j])
            frame = mask
            control = [0] + [work[j] for j in range(width) if j != bit]
            circuit.append(MCXVChain(width, dirty_ancillas=False,
                                     relative_phase=False, action_only=False),
                           control + [work[bit]] + scratch)
    for j in range(width):
        if frame & (1 << j):
            circuit.x(work[j])
    return circuit

def qpe(n, base, bits, rows):
    w = n.bit_length()
    p = QuantumRegister(1, "phase")
    work = QuantumRegister(w, "work")
    aux = QuantumRegister(w - 2, "scratch")
    readout = ClassicalRegister(bits, "readout")
    qc = QuantumCircuit(p, work, aux, readout)
    initial = encode(1, rows)
    for j in range(w):
        if (initial >> j) & 1:
            qc.x(work[j])
    blocks = {}
    for j in range(bits - 1, -1, -1):
        power = pow(base, 1 << j, n)
        qc.h(p[0])
        if power != 1:
            if power not in blocks:
                blocks[power] = build_multiplier(conjugated_mapping(n, power, rows), w)
            qc.compose(blocks[power], qubits=list(p) + list(work) + list(aux), inplace=True)
        for t in range(bits - 1, j, -1):
            with qc.if_test((readout[bits - 1 - t], 1)):
                qc.p(-2 * math.pi / (1 << (t - j + 1)), p[0])
        qc.h(p[0])
        qc.measure(p[0], readout[bits - 1 - j])
        if j > 0:
            qc.reset(p[0])
    return qc

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=247)
    ap.add_argument("--base", type=int, default=8)
    ap.add_argument("--bits", type=int, default=16)
    ap.add_argument("--candidates", type=int, default=128)
    ap.add_argument("--seed", type=int, default=8201)
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--shots", type=int, default=0)
    ap.add_argument("--output", default="results/a82_xor_encoding.json")
    a = ap.parse_args()
    if not is_semiprime(a.n) or math.gcd(a.n, a.base) != 1:
        ap.error("N must be semiprime and base coprime")
    w = a.n.bit_length()
    if not (2 <= a.bits <= 2 * w) or not (0 <= a.shots <= 64) or a.candidates < 0:
        ap.error("invalid bits, shots, or candidates")
    if a.shots and not a.compile:
        ap.error("--shots requires --compile")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    powers = sorted({pow(a.base, 1 << j, a.n) for j in range(a.bits)} - {1})
    def score(rows):
        return sum(path_cost(conjugated_mapping(a.n, power, rows)) for power in powers)
    identity = tuple(1 << i for i in range(w))
    baseline = score(identity)
    rng = random.Random(a.seed)
    best, best_cost = identity, baseline
    seen = {identity}
    started = time.perf_counter()
    for _ in range(a.candidates):
        rows = random_basis(w, rng, rng.randint(1, 4 * w))
        if rows in seen:
            continue
        seen.add(rows)
        cost = score(rows)
        if cost < best_cost:
            best, best_cost = rows, cost
    # Exhaustive public-domain conjugation check over all work states.
    for power in powers:
        m = mapping(a.n, power)
        e = conjugated_mapping(a.n, power, best)
        assert all(e[encode(x, best)] == encode(m[x], best) for x in range(1 << w))
    report = dict(experiment="A82_XOR_REGISTER_ENCODING", n=a.n, base=a.base,
                  bits=a.bits, candidates_checked=len(seen),
                  baseline_gray_mcx=baseline, best_gray_mcx=best_cost,
                  improvement_fraction=(baseline - best_cost) / baseline if baseline else 0,
                  best_rows=list(best), exact_permutation_checks=True,
                  known_factor_or_order_oracle=False, status="PASS_PERMUTATION_ONLY",
                  elapsed_seconds=round(time.perf_counter() - started, 3))
    print("A82 PROXY", baseline, best_cost, "gain", round(100 * report["improvement_fraction"], 2), "%", flush=True)
    if a.compile:
        sim = AerSimulator(method="matrix_product_state", max_parallel_threads=2,
                           max_memory_mb=8000)
        for label, rows in (("binary", identity), ("xor", best)):
            qc = qpe(a.n, a.base, a.bits, rows)
            compiled = transpile(qc, sim, optimization_level=0, seed_transpiler=82)
            report[label] = dict(qubits=qc.num_qubits, cx=compiled.count_ops().get("cx", 0),
                                 depth=compiled.depth())
            print("A82 COMPILED", label, report[label], flush=True)
            if a.shots:
                result = sim.run(compiled, shots=a.shots, memory=True,
                                 seed_simulator=a.seed).result()
                report[label]["frequencies"] = [
                    int(v.replace(" ", ""), 2) for v in result.get_memory(compiled)]
                print("A82 SHOTS", label, report[label]["frequencies"], flush=True)
        report["status"] = "PASS_COMPILED_AND_SAMPLED" if a.shots else "PASS_COMPILED"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("A82 STATUS", report["status"], "SAVED", out, flush=True)

if __name__ == "__main__":
    main()
