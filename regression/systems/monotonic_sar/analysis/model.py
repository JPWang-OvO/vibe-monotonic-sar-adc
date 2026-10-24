"""Charge-conserving top-plate sampled, downward monotonic SAR reference."""
from dataclasses import dataclass, asdict
from fractions import Fraction
import json
from pathlib import Path

from regression.common.project import ROOT
PARAMS=json.loads((ROOT/'config/architecture.json').read_text())

@dataclass
class Step:
    bit: int
    vp: float
    vn: float
    differential: float
    common_mode: float
    decision: int
    switched_side: str
    switched_weight: int
    charge_p: float
    charge_n: float

def convert(vinp, vinn):
    # Rational arithmetic makes equality explicit without numerical tie windows.
    vp, vn=Fraction(str(vinp)), Fraction(str(vinn))
    refp=Fraction(str(PARAMS['vrefp']))
    refn=Fraction(str(PARAMS['vrefn']))
    weights=PARAMS['weights']+[PARAMS['dummy_weight']]
    total=sum(weights)
    bp=[refp]*len(weights)
    bn=[refp]*len(weights)
    def charge(v,bottom):
        return sum(w*(v-b) for w,b in zip(weights,bottom))
    qp,qn=charge(vp,bp),charge(vn,bn)
    trace=[]
    code=0
    for bit in range(PARAMS['bits']-1,-1,-1):
        decision=int(vp>=vn)
        code=(code<<1)|decision
        weight=weights[PARAMS['bits']-1-bit] if bit else 0
        trace.append(Step(bit,float(vp),float(vn),float(vp-vn),float((vp+vn)/2),
            decision,('p' if decision else 'n') if bit else 'none',weight,
            float(charge(vp,bp))*PARAMS['unit_cap_f'],
            float(charge(vn,bn))*PARAMS['unit_cap_f']))
        if bit:
            index=PARAMS['bits']-1-bit
            # Preserve top-plate charge explicitly after changing a bottom plate.
            if decision:
                bp[index]=refn
                vp=(qp+sum(w*b for w,b in zip(weights,bp)))/total
            else:
                bn[index]=refn
                vn=(qn+sum(w*b for w,b in zip(weights,bn)))/total
        assert charge(vp,bp)==qp and charge(vn,bn)==qn
    return code,[asdict(s) for s in trace]

def ideal_reference(diff):
    span=Fraction(str(PARAMS['vrefp']))-Fraction(str(PARAMS['vrefn']))
    value=(Fraction(str(diff))+span)*(2**PARAMS['bits'])/(2*span)
    return min(2**PARAMS['bits']-1,max(0,value.numerator//value.denominator))
