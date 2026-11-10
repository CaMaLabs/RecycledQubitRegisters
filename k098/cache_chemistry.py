#!/usr/bin/env python3
"""QRR product reuse on the actual public chemistry ANGLE family.
Unlike invsqrt, a local extra wire may fit the 128-wire family maximum and
therefore need not raise the full block-encoding qubit cost. All preload and
reverse traversal contracts are checked by the unchanged chemistry verifier.
"""
import argparse,json,sys,shutil,hashlib
from pathlib import Path
import kickmix as km
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'k096'))
from retained_products import transform,selftest
p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--coherent',action='store_true');p.add_argument('--plain-controls',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print(selftest(),flush=True);rows=[]
for k in range(15):
 source=a.dataset/f'dfthcsos__angle_k_{k}.kmb';original=km.Circuit.from_file(str(source),format='kmb');decoded=a.out/f'original_{k}.kmx';original.to_file(str(decoded),format='kmx');lines=decoded.read_text().splitlines(keepends=True)
 new,report=transform(lines,measurement=not a.coherent,max_span=100000,affine=not a.plain_controls)
 candidate_path=a.out/f'angle_k_{k}.kmx';candidate_path.write_text(''.join(new));candidate=km.Circuit.from_file(str(candidate_path),format='kmx');r={'k':k,'original_qubits':original.num_qubits,'candidate_qubits':candidate.num_qubits,'original_nonlinear':original.operation_statistics().num_toffoli_like,'candidate_nonlinear':candidate.operation_statistics().num_toffoli_like,'report':report,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
 if candidate.num_qubits>128:r['decision']='REJECT_CAP';shutil.copy(source,a.out/f'angle_k_{k}.kmb')
 elif candidate.operation_statistics().num_toffoli_like>=original.operation_statistics().num_toffoli_like:r['decision']='NO_SAVINGS';shutil.copy(source,a.out/f'angle_k_{k}.kmb')
 else:r['decision']='CANDIDATE';candidate.to_file(str(a.out/f'angle_k_{k}.kmb'),format='kmb')
 rows.append(r);print('K098_CACHE',json.dumps({key:value for key,value in r.items() if key!='report'}),flush=True)
 candidate_path.unlink();decoded.unlink()
shutil.copy(a.dataset/'dfthcsos__submission.npz',a.out/'submission.npz');(a.out/'cache_matrix.json').write_text(json.dumps(rows,indent=2));print('K098_TOTAL_SAVED',sum(r['original_nonlinear']-r['candidate_nonlinear'] for r in rows if r['decision']=='CANDIDATE'),flush=True)
