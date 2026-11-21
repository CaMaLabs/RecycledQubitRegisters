"""Executable adaptation of COMP-N-SUB circuit I, not the full paper divider.

Source: Mukhopadhyay, Gheorghiu & Krovi, arXiv:2603.18110v2,
Section 2.2.1, steps 1-8, printed p.11. Own transcription into X/CX/CCX.
The authors' zero controls on Z in step 5 are implemented using X conjugation.
Use within our existing P,N,R,Q wrapper to isolate the arithmetic primitive.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'optimized_divisor_oracle'))
import baseline as reference


def comp_n_sub_i(a,b,underflow):
    """|a,b,0> -> |a,b-a,0> if b>=a, else |a,b,1>, k>=2."""
    k=len(a)
    if k<2 or len(b)!=k:
        raise ValueError('Equal operand widths >=2 required')
    ops=[('x',bit) for bit in b]
    ops.extend(('cx',a[i],b[i]) for i in range(1,k))
    ops.append(('cx',a[-1],underflow))
    ops.extend(('cx',a[i],a[i+1]) for i in reversed(range(1,k-1)))
    ops.extend(('ccx',b[i],a[i],a[i+1]) for i in range(k-1))
    ops.append(('ccx',b[-1],a[-1],underflow))
    # Step 5 uses a ZERO control on underflow, throughout the entire step.
    ops.extend([('x',underflow),('ccx',underflow,a[-1],b[-1])])
    for i in reversed(range(k-1)):
        ops.extend([('ccx',b[i],a[i],a[i+1]),('ccx',underflow,a[i],b[i])])
    ops.append(('x',underflow))
    ops.extend(('cx',a[i],a[i+1]) for i in range(1,k-1))
    ops.extend(('cx',a[i],b[i]) for i in range(1,k))
    ops.extend(('x',bit) for bit in b)
    return ops


def build(nbits,pbits):
    """Our streaming divider with the published primitive substituted in place.

    Same input preservation, quotient width, validity flags and readout as ours.
    This intentionally does NOT claim to implement the paper's in-place N/Q
    layout, smaller iteration schedule or optimized Clifford+T synthesis.
    """
    if nbits<3 or pbits<2:
        raise ValueError('Require nbits>=3 and pbits>=2')
    c=reference.Circuit()
    p=c.reg('P',pbits)
    n=c.reg('N',nbits)
    r=c.reg('R',pbits+1)
    q=c.reg('Q',nbits)
    vp=c.reg('P_at_least_2',1)[0]
    vq=c.reg('Q_at_least_2',1)[0]
    flag=c.reg('good',1)[0]
    shared=c.reg('mcx_scratch',max(len(r),nbits-3,pbits-3,1))
    # Padding is zero and restored by each COMP-N-SUB. Share the physical
    # qubit with phase/validity scratch at non-overlapping lifetimes.
    padded=p+[shared[0]]
    ops=reference.nontrivial(p,vp,shared)
    for i in reversed(range(nbits)):
        for j in reversed(range(1,len(r))):
            a,b=r[j],r[j-1]
            ops.extend([('cx',a,b),('cx',b,a),('cx',a,b)])
        ops.append(('cx',n[i],r[0]))
        ops.extend(comp_n_sub_i(padded,r,q[i]))
        ops.append(('x',q[i]))
    ops.extend(reference.nontrivial(q,vq,shared))
    flips=[('x',bit) for bit in r]
    mark=flips+reference.mcx([vp,vq,*r],flag,shared)+flips[::-1]
    oracle=ops+mark+[('z',flag)]+mark[::-1]+ops[::-1]
    return c,ops,mark,oracle
