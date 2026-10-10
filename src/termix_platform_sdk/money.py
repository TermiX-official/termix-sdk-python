"""Money helpers. Amounts are decimal STRINGS on the wire; never use float."""
from __future__ import annotations

from decimal import Decimal, getcontext

getcontext().prec = 80


def to_base_units(amount: str, decimals: int) -> int:
    """Decimal string -> integer base units at the given token decimals."""
    scaled = Decimal(str(amount)) * (Decimal(10) ** decimals)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{amount} has more precision than {decimals} decimals")
    return int(scaled)


def from_base_units(base: int, decimals: int) -> str:
    """Integer base units -> canonical decimal string (no trailing zeros)."""
    neg = base < 0
    v = abs(int(base))
    if decimals == 0:
        return ("-" if neg else "") + str(v)
    s = str(v).rjust(decimals + 1, "0")
    int_part = s[:-decimals]
    frac = s[-decimals:].rstrip("0")
    out = int_part + ("." + frac if frac else "")
    return ("-" if neg else "") + out
