"""Bounded cutting-plane fit for fixed Kickmix rotation predicates."""

from dataclasses import dataclass
from math import log2, pi
import time

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class Fit:
    delta: tuple[int, ...]
    margin: int
    rounds: int
    converged: bool
    support: tuple[int, ...] = ()
    weights: tuple[float, ...] = ()


def angle_shift(mask, delta):
    """Evaluate integer phase deltas in units of 2^-64 turns across all rows."""
    shift = np.zeros(mask.size, np.int64)
    for start in range(0, len(delta), 8):
        costs = delta[start:start+8]
        table = np.zeros(1 << len(costs), dtype=np.int64)
        for bit, amount in enumerate(costs):
            size = 1 << bit
            table[size:2*size] = table[:size] + amount
        shift += table[(mask >> np.uint64(start)) & np.uint64(len(table) - 1)]
    return shift


def tightest(values, count):
    count = min(count, values.size)
    return np.argpartition(values, count - 1)[:count]


def fit_phase(mask, residual, tolerance, angle_count, fixed=None, *, seconds=30, max_rounds=30):
    """Maximize the minimum absolute slack with integer full-domain validation.

    The LP proposes floating-point offsets. Only their rounded, exhaustively
    checked versions are retained. An early stop makes no optimality claim.
    """
    if not (mask.shape == residual.shape == tolerance.shape == (mask.size,) and mask.size):
        raise ValueError("Inconsistent or empty phase profile")
    if not 1 <= angle_count <= 63:
        raise ValueError("Expected 1 to 63 independent rotation sites")
    fixed = fixed or {}
    radius = 1 << 35
    if any(i < 0 or i >= angle_count or abs(value) > radius for i, value in fixed.items()):
        raise ValueError("A fixed coefficient exceeds the local phase fitting bound")
    offsets = tuple(fixed.get(i, 0) for i in range(angle_count))
    error = residual + angle_shift(mask, offsets)
    margin = tolerance - np.abs(error)
    best = Fit(offsets, int(margin.min()), 0, False)
    rng = np.random.default_rng(1729)
    active = np.union1d(tightest(margin, 512), rng.choice(mask.size, size=min(mask.size, 512), replace=False))
    # Use units close to one in HiGHS. All acceptance checks below use ints.
    scale = max(1, int(tolerance.min()))
    bounds = [(fixed[i]/scale, fixed[i]/scale) if i in fixed else (-radius/scale, radius/scale)
              for i in range(angle_count)] + [(None, None)]
    objective = np.zeros(angle_count + 1)
    objective[-1] = -1
    columns = np.arange(angle_count, dtype=np.uint64)
    deadline = time.monotonic() + seconds
    for iteration in range(1, max_rounds + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        basis = ((mask[active, None] >> columns) & 1).astype(np.float64)
        upper = np.column_stack((basis, np.ones(active.size)))
        lower = np.column_stack((-basis, np.ones(active.size)))
        rhs = np.concatenate(((tolerance[active] - residual[active])/scale,
                              (tolerance[active] + residual[active])/scale))
        solved = linprog(objective, A_ub=np.vstack((upper, lower)), b_ub=rhs,
                         bounds=bounds, method="highs", options={"time_limit": remaining})
        if not solved.success:
            break
        offsets = tuple(fixed.get(i, round(value*scale)) for i, value in enumerate(solved.x[:-1]))
        error = residual + angle_shift(mask, offsets)
        margin = tolerance - np.abs(error)
        observed = int(margin.min())
        # Rounding each angle can cost at most half a unit per firing site.
        converged = bool(abs(solved.x[-1]*scale - observed) <= angle_count + 2)
        if observed > best.margin or (observed == best.margin and converged):
            duals = solved.ineqlin.marginals
            weights = duals[:active.size] - duals[active.size:]
            support = np.abs(weights) > 1e-10
            best = Fit(offsets, observed, iteration, converged,
                       tuple(int(row) for row in active[support]),
                       tuple(float(weight) for weight in weights[support]))
        if converged:
            break
        expanded = np.union1d(active, tightest(margin, 256))
        if expanded.size == active.size:
            break
        active = expanded
    return best


def rotation_price(count, margin):
    """Published fine-rotation T/4 contribution per shot, before qubit scaling."""
    if margin <= 0:
        return float("inf")
    if count == 0:
        return 0.0
    epsilon = pi * (margin / (1 << 64)) / count
    return count * (0.56*log2(1/epsilon) + 5.3) / 4
