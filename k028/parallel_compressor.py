"""Staged 3:2 Wallace-tree compression for reversible unsigned multiplication.

Each compression round consumes only the previous round's bits, so carries
cannot cause an accidental serial ripple through every column. Overflow past
`width` is omitted for the specified modulo 2**width arithmetic.
"""

def wallace_multiply(c, a, b, width):
    zero = c.wire()
    columns = [[] for _ in range(width)]
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            if i + j < width:
                columns[i + j].append(c.and_(ai, bj))

    rounds = 0
    while any(len(col) > 2 for col in columns):
        incoming = [[] for _ in range(width)]
        # Do not reuse any output produced during this compression round.
        for position, bits in enumerate(columns):
            complete = len(bits) // 3
            for n in range(complete):
                x, y, z = bits[3*n:3*n+3]
                summed, carry = c.full(x, y, z)
                incoming[position].append(summed)
                if position+1 < width:
                    incoming[position+1].append(carry)
            incoming[position].extend(bits[complete*3:])
        columns = incoming
        rounds += 1

    row_a = [col[0] if col else zero for col in columns]
    row_b = [col[1] if len(col) > 1 else zero for col in columns]
    return c.ripple(row_a, row_b, width), rounds
