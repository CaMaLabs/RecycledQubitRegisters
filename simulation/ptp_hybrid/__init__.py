"""Optional PTP/QRR research track.

This package is isolated from the established QRR hardware experiments. It is
for falsifiable simulation and classical preprocessing/postprocessing studies
around modulo-210 residue structure, kernel factor pairs, and composite
symmetry. No existing hardware result or historical data file depends on it.
"""

from .core import (
    BASE_PRIMES,
    MODULUS,
    ROOTS,
    factor_pair_table,
    is_ptp_candidate,
    ptp_coordinate,
    root_for_integer,
    root_index,
)
from .kernel import lfk_factor

__all__ = [
    "BASE_PRIMES",
    "MODULUS",
    "ROOTS",
    "factor_pair_table",
    "is_ptp_candidate",
    "ptp_coordinate",
    "root_for_integer",
    "root_index",
    "lfk_factor",
]
