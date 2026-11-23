"""Full-input research screen for invsqrt rotation refits and predicate swaps."""

import argparse
from dataclasses import dataclass
from fractions import Fraction
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sqlite3

import numpy as np

from ..autonomous.core import EIGHTH, TURN, Gate, parse, sha
from ..autonomous.kickmix_trace import load_program, physical_lines
from ..autonomous.phase_margin import fit_phase, rotation_price
from ..autonomous.verification import better, validate_contract, verify

TRANSCRIPTS = ("zero", 31)
MAX_X = 3_133_452
UNIT = TURN >> 64


@dataclass(frozen=True)
class Circuit:
    lines: list
    source_lines: list
    ops: list
    inputs: list
    width: int
    rotations: dict


def load_backend(path):
    spec = spec_from_file_location("qrr_phase_profile_backend", path)
    if spec is None or spec.loader is None:
        raise ValueError("Expected the path to qhdl_bitsim.py")
    backend = module_from_spec(spec)
    spec.loader.exec_module(backend)
    if backend.MAX_X != MAX_X:
        raise ValueError("Profile backend uses a different invsqrt domain")
    return backend


def circuit(source, backend):
    text = source.decode("utf-8")
    lines = physical_lines(text)
    program, pinned = load_program(text)
    header = [line.split("#", 1)[0].split() for line in lines]
    declarations = [tokens for tokens in header if tokens[:1] == ["REGISTER"]]
    appends = [tokens for tokens in header if tokens[:1] == ["APPEND_TO_REGISTER"]]
    if len(declarations) != 1 or declarations[0][2:] != ['"x"'] or len(appends) != 22 or len(pinned) != 22:
        raise ValueError('Expected one 22-qubit register named "x"')
    if any(tokens[2] != declarations[0][1] for tokens in appends):
        raise ValueError("Unexpected register membership")
    inputs = [int(tokens[1][1:]) for tokens in appends]
    source_lines = [instruction.line - 1 for instruction in program]
    ops = [backend.parse_line(lines[index].split("#", 1)[0].strip()) for index in source_lines]
    rotations = {}
    for index, instruction in enumerate(program):
        if instruction.opcode != "Z_POW":
            continue
        tokens = ops[index].text.split()
        gate = parse(" ".join(tokens[:3]))
        if gate is None or instruction.guard is not None:
            raise ValueError("Guarded or unsupported rotation syntax")
        if gate.angle % EIGHTH:
            rotations[index] = gate
    width = max(pinned | {wire for instruction in program for wire in instruction.qubits}) + 1
    if width > 512:
        raise ValueError("The full-domain bitset screen supports at most 512 wires")
    return Circuit(lines, source_lines, ops, inputs, width, rotations)


def simulate(backend, parsed, transcript, *, rows=None, snaps=(), on_snap=None):
    sim = backend.BitSim(parsed.ops, rows=rows, num_qubits=parsed.width,
                         x_qubits=parsed.inputs, outcome=transcript)
    return sim.run(snaps=list(snaps), on_snap=on_snap)


def signed_residual(sim, target):
    if not sim.x_restored() or not sim.scratch_clean() or sim.dirty:
        raise ValueError("Profile failed to restore the input, clear scratch, or justify a reset")
    return (sim.phase_units() - target).view(np.int64)


def profile(backend, parsed, target):
    count = len(parsed.rotations)
    if not 1 <= count <= 62:
        raise ValueError("Expected 1 to 62 fine rotations")
    index = {op: slot for slot, op in enumerate(parsed.rotations)}
    baseline = None
    for transcript in TRANSCRIPTS:
        masks = np.zeros(MAX_X, dtype=np.uint64)

        def record(op, sim):
            if sim.stack:
                raise ValueError("Fine rotation inside a captured guard")
            wire = parsed.rotations[op].q[0]
            masks[backend.unpack_bits(sim.q[wire], MAX_X)] |= np.uint64(1 << index[op])

        sim = simulate(backend, parsed, transcript, snaps=index, on_snap=record)
        residual = signed_residual(sim, target)
        if baseline is not None and not all(
            np.array_equal(a, b) for a, b in zip((masks, residual), baseline)
        ):
            raise ValueError("Rotation predicates or baseline phase differ across tested transcripts")
        baseline = masks, residual
    return baseline


def rank_predicates(backend, parsed, fit, count):
    if not fit.support or count == 0:
        return []
    rows = np.asarray(fit.support) + 1
    weights = np.asarray(fit.weights)
    snaps = sorted(set(np.linspace(0, len(parsed.ops) - 1, 100, dtype=int)) |
                   {i for i, op in enumerate(parsed.ops) if op.code in (backend.C_ZPOW, backend.C_HMR)})
    ranked = {}

    def collect(index, sim):
        if sim.stack:
            return
        values = np.array([backend.unpack_bits(wire, rows.size) for wire in sim.q])
        impact = np.abs(values @ weights)
        for wire in np.argsort(impact)[-count:]:
            if impact[wire] > 1e-9:
                key = backend.pack_bits(values[wire]).tobytes()
                ranked.setdefault(key, (float(impact[wire]), index, int(wire)))

    simulate(backend, parsed, "zero", rows=rows, snaps=snaps, on_snap=collect)
    return [(index, wire) for _, index, wire in sorted(ranked.values(), reverse=True)[:count]]


def predicate_columns(backend, parsed, sites):
    if not sites:
        return {}
    by_op = {}
    for op, wire in sites:
        by_op.setdefault(op, []).append(wire)
    columns = {}
    for transcript in TRANSCRIPTS:
        def record(index, sim):
            for wire in by_op[index]:
                key = index, wire
                if transcript == "zero":
                    columns[key] = sim.q[wire].copy()
                elif not np.array_equal(columns[key], sim.q[wire]):
                    columns[key] = None

        simulate(backend, parsed, transcript, snaps=sorted(by_op), on_snap=record)
    return columns


def render(parsed, delta, dropped, inserted):
    lines = parsed.lines.copy()
    for index, ((op, gate), adjustment) in enumerate(zip(parsed.rotations.items(), delta)):
        line = parsed.source_lines[op]
        if index == dropped:
            lines[line] = ""
        elif adjustment:
            lines[line] = Gate("Z_POW", gate.q, (gate.angle + adjustment*UNIT) % TURN).text()
    if inserted is not None:
        op, wire = inserted
        line = parsed.source_lines[op]
        lines[line] = Gate("Z_POW", (wire,), (delta[-1]*UNIT) % TURN).text() + lines[line]
    return "".join(lines).encode("utf-8")


def screen(source, backend, drops, predicates, seconds):
    parsed = circuit(source, backend)
    target, tolerance = backend.invsqrt_reference()
    tolerance = tolerance.astype(np.int64)
    masks, residual = profile(backend, parsed, target)
    if np.any(residual < -tolerance) or np.any(residual > tolerance):
        raise ValueError("The published model rejects the baseline on at least one legal input")
    count = len(parsed.rotations)
    original_margin = int((tolerance - np.abs(residual)).min())
    rounding = count + 4
    if original_margin <= rounding:
        raise ValueError("Published model did not establish positive baseline slack")
    angles = [round(Fraction(gate.angle, UNIT)) for gate in parsed.rotations.values()]
    # Only rotations whose deletion fits inside the local offset model are eligible.
    eligible = sorted((i for i, angle in enumerate(angles) if 0 < angle <= 1 << 35), key=angles.__getitem__)
    fixed = {i: {i: -angles[i]} for i in eligible[:drops]}
    fits = {i: fit_phase(masks, residual, tolerance, count, fixed.get(i), seconds=seconds)
            for i in [None, *fixed]}
    ranked = {i: rank_predicates(backend, parsed, fits[i], predicates) for i in [None, *eligible[:min(1, drops)]]}
    columns = predicate_columns(backend, parsed, {site for group in ranked.values() for site in group})
    trials = [(drop, None, fit) for drop, fit in fits.items()]
    for drop, sites in ranked.items():
        for site in sites:
            if columns[site] is None:
                continue
            values = backend.unpack_bits(columns[site], MAX_X).astype(np.uint64)
            extended = masks | (values << count)
            fit = fit_phase(extended, residual, tolerance, count + 1, fixed.get(drop), seconds=seconds)
            trials.append((drop, site, fit))
    records = []
    best = None
    baseline_price = rotation_price(count, original_margin + rounding)
    for drop, inserted, fit in trials:
        candidate_count = count - (drop is not None) + (inserted is not None)
        margin = fit.margin
        saving = parsed.width * (baseline_price - rotation_price(candidate_count, margin - rounding))
        record = {"dropped_slot": drop, "insertion_op_wire": inserted, "margin_units": margin,
                  "rounds": fit.rounds, "converged": fit.converged,
                  "modeled_cost_saving": saving if np.isfinite(saving) else None}
        records.append(record)
        if saving > 0 and (best is None or saving > best[0]):
            candidate = render(parsed, fit.delta, drop, inserted)
            # Keep this test within the price model's declared rotation classes.
            if len(circuit(candidate, backend).rotations) == candidate_count:
                best = saving, candidate, record

    report = {"source_sha256": sha(source), "domain_size": MAX_X, "transcripts": TRANSCRIPTS,
              "baseline_margin_units": original_margin, "baseline_fine_rotations": count,
              "trials": records, "candidate": None, "official_status": "NOT_RUN"}
    if best is None:
        return None, report
    _, candidate, record = best
    replacement = circuit(candidate, backend)
    checked_margin = min(int((tolerance - np.abs(signed_residual(
        simulate(backend, replacement, transcript), target))).min()) for transcript in TRANSCRIPTS)
    price = rotation_price(len(replacement.rotations), checked_margin - rounding)
    if price < baseline_price:
        report["candidate"] = {**record, "sha256": sha(candidate), "replayed_margin_units": checked_margin}
        return candidate, report
    return None, report


def verify_against_campaign(candidate, report, database, out, timeout):
    """Check a proposal with the matching baseline's previously pinned official contract."""
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
        best = db.execute("SELECT value FROM meta WHERE key='best'").fetchone()
        identity = json.loads(row[0]) if row else {}
        best = json.loads(best[0]) if best else {}
        previous = db.execute("SELECT official_status,score,metrics FROM candidates WHERE sha=?",
                              (best.get("sha"),)).fetchone()
    contract = identity.get("contract")
    if (identity.get("source_sha256") != report["source_sha256"] or not contract
            or not previous or previous[0] != "PASS_FULL" or previous[1] != best.get("score")):
        raise ValueError("The campaign needs a matching source pin and a full official best receipt")
    validate_contract(contract)
    previous_receipt = json.loads(previous[2])
    if previous_receipt.get("candidate_sha256") != best.get("sha"):
        raise ValueError("Stored official receipt has a different circuit digest")
    def previous_arg(token, default):
        if token not in contract["argv"]:
            return default
        index = contract["argv"].index(token)
        values = {run["argv"][index] for run in previous_receipt["runs"]}
        if len(values) != 1:
            raise ValueError(f"Stored official receipts used inconsistent values for {token}")
        return values.pop()

    workers = int(previous_arg("{workers}", 1))
    verifier_python = previous_arg("{python}", None)
    if verifier_python and not Path(verifier_python).is_file():
        raise ValueError(f"Saved verifier interpreter unavailable: {verifier_python}")
    if workers < 1 or timeout <= 0:
        raise ValueError("Saved verification workers and requested timeout must be positive")
    work = out / "verify" / report["candidate"]["sha256"]
    result = verify(candidate, work, contract, timeout, 8192, workers,
                    timeout*len(contract["seeds"]) + 1, python=verifier_python)
    report["official_status"] = result["status"]
    report["official_verifier_result"] = result
    report["previous_verified_cost"] = previous[1]
    report["verified_improvement"] = result["status"] == "PASS_FULL" and better(
        result["score"], previous[1], contract["direction"])
    reference = identity.get("reference")
    report["beats_historical_reference"] = (result["status"] == "PASS_FULL" and reference is not None
        and better(result["score"], reference, contract["direction"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True, help="Path to the public QHDL qhdl_bitsim.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--drops", type=int, choices=range(7), default=6)
    parser.add_argument("--predicates", type=int, choices=range(5), default=4)
    parser.add_argument("--seconds-per-fit", type=float, default=12)
    parser.add_argument("--campaign-db", type=Path, help="Reuse this completed campaign's official contract and receipts")
    parser.add_argument("--verifier-timeout", type=float, default=1800)
    args = parser.parse_args()
    if args.out.resolve() in args.source.resolve().parents:
        parser.error("Keep the immutable source outside the output directory")
    if not 0 < args.seconds_per_fit <= 60:
        parser.error("--seconds-per-fit must be in (0, 60]")
    backend = load_backend(args.backend)
    candidate, report = screen(args.source.read_bytes(), backend, args.drops, args.predicates, args.seconds_per_fit)
    report["backend_sha256"] = sha(args.backend.read_bytes())
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = args.out / "report.json"
    if candidate is not None:
        path = args.out / (report["candidate"]["sha256"] + ".kmx")
        path.write_bytes(candidate)
        report["candidate"]["path"] = str(path.resolve())
        if args.campaign_db:
            receipt.write_text(json.dumps(report, indent=2) + "\n")
            print(f"Checking candidate {path.name} with the saved official contract", flush=True)
            verify_against_campaign(path, report, args.campaign_db, args.out, args.verifier_timeout)
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
