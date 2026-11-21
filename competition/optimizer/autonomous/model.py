"""Receipt-calibrated Q*C model; estimates never confer correctness."""
import math


def estimate(metrics, delta_executed_toffoli=0, delta_qubits=0, delta_t=0,
             delta_rotations=0, rotation_t_cost=None):
    # Use the *measured* official aggregate, including all precision costs.
    if delta_rotations and rotation_t_cost is None:
        return {'status':'UNKNOWN','reason':'Rotation precision/headroom must be reverified'}
    q=metrics['num_qubits']+delta_qubits
    c=metrics['toffoli_equivalent']+delta_executed_toffoli+delta_t/4
    if delta_rotations: c+=delta_rotations*rotation_t_cost/4
    return {'status':'ESTIMATE','cost':q*c,'rotation_precision_unchanged':not delta_rotations,
            'reaction_depth_effect':'NOT_PRICED_UNTIL_OFFICIAL_SOURCE_CONFIRMS',
            'assumption':'Executed deltas must be measured or proved, not static source deltas'}


def calibrate(records, tolerance=1e-7):
    residuals=[]
    for m in records:
        predicted=m['num_qubits']*m['toffoli_equivalent']
        if not math.isfinite(predicted): raise ValueError('Nonfinite calibration')
        residuals.append(m['score']-predicted)
    maximum=max(map(abs,residuals),default=None)
    return {'samples':len(records),'max_absolute_residual':maximum,
            'status':'CALIBRATED_AGGREGATE_QC' if maximum is not None and maximum<=tolerance else 'UNCALIBRATED',
            'scope':'Aggregate identity only; not a dynamic execution/rotation precision predictor'}
