"""Numeric engineering literals used by circuit descriptions."""
from decimal import Decimal
import re


def numeric(value):
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([TGMKkmunpf]?)", str(value))
    if not match:
        raise ValueError(f"Expected a numeric engineering literal: {value}")
    scale = {"T":12,"G":9,"M":6,"K":3,"k":3,"":0,"m":-3,"u":-6,"n":-9,"p":-12,"f":-15}
    return Decimal(match[1]) * Decimal(10) ** scale[match[2]]
