# End-to-end small-RSA recovery demo

This repository now includes a complete synthetic RSA key-recovery demonstration built on the residue-conditioned Shor/order-finding path.

## What the demo does

The default public RSA key is:

```text
N = 713
e = 17
```

The attack path is given only the public key, ciphertext, a public Shor base, and simulated QPE measurement results.

The public selector uses:

```text
a = 19
ell = 5
N mod 5 = 3
b = a^5 mod N = 563
```

The built-in ideal QPE simulator has validation-only access to the synthetic factors and true order so it can stand in for a quantum device. Those values are not passed to the factor-recovery routine.

For the default instance:

```text
validation-only baseline order:    330
validation-only transformed order:  66
order reduction:                    5x
```

The public recovery routine then uses only measured phase integers, continued fractions, public modular exponentiation, and the standard Shor gcd step to recover the factors. From those recovered factors it reconstructs `phi(N)` and the RSA private exponent `d`, then decrypts the ciphertext.

The default plaintext is:

```text
DARK STAR RSA
```

Encryption is intentionally byte-wise textbook RSA for a transparent small-modulus demonstration. It is not representative of production RSA padding/encoding.

## Run

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull
python3 hardware/dark_star_rsa_end_to_end_demo.py
```

A successful run should end with a block beginning:

```text
===== END-TO-END RSA RECOVERY DEMO =====
```

and should report:

```text
decryption_match=True
```

The exact stopping precision and sampled phase-work path are deterministic for the default seed `8776`.

You can change the message without changing the attack instance:

```bash
python3 hardware/dark_star_rsa_end_to_end_demo.py --message "HELLO QUANTUM"
```

## Simulator/attack separation

The script deliberately separates two roles.

### Simulator boundary

The simulator receives the synthetic factors and true multiplicative order only to generate idealized QPE measurements. This stands in for future QPU hardware.

### Public attack path

The recovery function receives only:

- public `N`;
- the public Shor base;
- phase precision `m`;
- measured phase integer `y`.

It does not receive `p`, `q`, `lambda(N)`, or the true order. A continued-fraction denominator must verify using public modular exponentiation before standard Shor factor extraction is attempted.

## Claim boundary

A successful run establishes a genuine end-to-end **small synthetic RSA private-key reconstruction** inside the repository's idealized order-finding model:

```text
public RSA key
    -> ciphertext
    -> residue-conditioned Shor base
    -> ideal QPE measurements
    -> public continued-fraction/order verification
    -> recovered factors
    -> reconstructed private exponent
    -> decrypted plaintext
```

It does **not** establish:

- practical RSA-2048 capability;
- scalable reversible modular arithmetic;
- measured QPU factoring of `N=713`;
- a fault-tolerant resource advantage;
- an asymptotic improvement to Shor's algorithm.

The next hardware-facing step is to compile the `N=713, ell=5` and `N=781, ell=7` scout cases to an IBM backend target and measure native two-qubit-gate/depth cost before considering QPU submission.
