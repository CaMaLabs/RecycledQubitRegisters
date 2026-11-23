"""Project known operations into the engine while carrying opaque instructions through."""

from collections import Counter
from io import BytesIO
from pathlib import Path
import re
from tempfile import NamedTemporaryFile, TemporaryDirectory

from .core import parse, sha

QASM_HEADER = re.compile(r"\A(?:\s|//[^\n]*\n|/\*.*?\*/)*OPENQASM\s+([23])\b", re.S)


def detect_format(source, requested):
    if requested != "auto":
        return requested
    suffix = source.suffix.lower()
    if suffix in {".kmx", ".qpy"}:
        return suffix[1:]
    if suffix in {".qasm", ".qasm2", ".qasm3"}:
        match = QASM_HEADER.match(source.read_text(encoding="utf-8-sig"))
        if match:
            return "qasm" + match[1]
        if suffix != ".qasm":
            return suffix[1:]
    raise ValueError("Specify --input-format kmx, qpy, qasm2 or qasm3")


def load(source, kind, raw, index):
    from qiskit import QuantumCircuit, qasm2, qasm3, qpy

    if kind == "qpy":
        circuits = qpy.load(BytesIO(raw))
        if not 0 <= index < len(circuits):
            raise ValueError(f"QPY circuit index {index} out of range ({len(circuits)} circuits)")
        if not isinstance(circuits[index], QuantumCircuit):
            raise ValueError("The selected QPY entry must be a QuantumCircuit")
        return circuits[index]
    if index != 0:
        raise ValueError("--circuit-index applies to QPY bundles")
    if kind == "qasm2":
        # Includes resolve from the input file's directory and Qiskit's standard library.
        return qasm2.loads(raw.decode("utf-8-sig"), include_path=(source.parent,))
    return qasm3.loads(raw.decode("utf-8-sig"))


class CircuitProjection:
    def __init__(self, circuit, source_digest, index):
        from qiskit.circuit import library

        self.circuit = circuit
        self.gates = {
            name: getattr(library, cls) for name, cls in {
                "X": "XGate", "CX": "CXGate", "CCX": "CCXGate", "SWAP": "SwapGate",
                "CSWAP": "CSwapGate", "Z": "ZGate", "CZ": "CZGate", "CCZ": "CCZGate",
                "S": "SGate", "S_DAG": "SdgGate", "T": "TGate", "T_DAG": "TdgGate",
            }.items()
        }
        reverse = {cls: name for name, cls in self.gates.items()}
        self.header = f"QISKIT_SOURCE {source_digest} {index}"
        lines = [self.header]
        self.opaque = {}
        for position, item in enumerate(circuit.data):
            operation = item.operation
            name = reverse.get(operation.base_class)
            if (name and not item.clbits and operation.label is None
                    and getattr(operation, "condition", None) is None
                    and (not hasattr(operation, "ctrl_state")
                         or operation.ctrl_state == (1 << operation.num_ctrl_qubits) - 1)
                    and (not operation.mutable or operation.definition == self.gates[name]().definition)):
                qubits = [f"q{circuit.find_bit(bit).index}" for bit in item.qubits]
                lines.append(" ".join([name, *qubits]))
            else:
                self.opaque[position] = item
                lines.append(f"QISKIT_OPAQUE {position}")
        self.data = ("\n".join(lines) + "\n").encode("ascii")

    def restore(self, data):
        if data == self.data:
            return self.circuit
        lines = data.decode("ascii").splitlines()
        if not lines or lines[0] != self.header:
            raise ValueError("Circuit projection has the wrong source identity")
        result = self.circuit.copy_empty_like()
        carried = []
        for line in lines[1:]:
            if line.startswith("QISKIT_OPAQUE "):
                position = int(line.split()[1])
                result.append(self.opaque[position], copy=False)
                carried.append(position)
                continue
            gate = parse(line)
            if gate is None:
                raise ValueError(f"Invalid projected instruction {line!r}")
            result.append(self.gates[gate.op](), [result.qubits[i] for i in gate.q])
        if carried != list(self.opaque):
            raise ValueError("Opaque instruction sequence changed")
        return result

    def export(self, data, out):
        from qiskit import qpy

        result = self.restore(data)
        dest = out / "optimized.qpy"
        with NamedTemporaryFile(dir=out, delete=False) as stream:
            temp = Path(stream.name)
            try:
                qpy.dump(result, stream)
                stream.flush()
                temp.replace(dest)
            finally:
                temp.unlink(missing_ok=True)

        def describe(circuit):
            return {"operations": len(circuit.data), "depth": circuit.depth(),
                    "qubits": circuit.num_qubits, "classical_bits": circuit.num_clbits,
                    "operation_counts": dict(circuit.count_ops())}

        return {"output_circuit": str(dest), "output_format": "qpy",
                "input_metrics": describe(self.circuit), "output_metrics": describe(result),
                "preserved_opaque_operations": dict(Counter(item.operation.name for item in self.opaque.values()))}


def run_circuit(args, config, kind, executor):
    from qiskit.exceptions import QiskitError
    from types import SimpleNamespace

    source = Path(args.source)
    raw = source.read_bytes()
    digest = sha(raw)
    if args.expected_sha and digest != args.expected_sha:
        raise ValueError(f"BASELINE_SHA_MISMATCH {digest}")
    if source.is_relative_to(Path(args.out)):
        raise ValueError("Keep the immutable source outside the output directory")
    try:
        circuit = load(source, kind, raw, args.circuit_index)
        projection = CircuitProjection(circuit, digest, args.circuit_index)
        with TemporaryDirectory(prefix="optimizer-projection-") as temp:
            projected = Path(temp) / "projection.kmx"
            projected.write_bytes(projection.data)
            engine_args = SimpleNamespace(**{**vars(args), "source": str(projected),
                                           "expected_sha": sha(projection.data)})
            def export(data, out):
                return {**projection.export(data, out), "input_format": kind,
                        "original_source_sha256": digest, "circuit_index": args.circuit_index}

            return executor(engine_args, config, export=export)
    except QiskitError as exc:
        raise ValueError(f"{kind} circuit could not be processed: {exc}") from exc
