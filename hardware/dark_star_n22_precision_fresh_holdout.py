#!/usr/bin/env python3
"""Fresh blinded 8-case n22 high-precision QPE test. NOT fitted on old results.

Reuses frozen numerical method (131072 samples, exact QPE FFT <=18,
65 centered bins and variance-adaptive empirical Bernstein). New independent
public N/base sample MUST be committed before running this file.
Research lead Chase Lunsford / CaMaLabs. Zero QPU jobs.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib,json,math,time
from pathlib import Path

import dark_star_n22_numerical_precision_audit as prec
import dark_star_n22_full_tail_qpe_holdout as old
import dark_star_n22_precision_fresh_public_manifest as manifest_code
import dark_star_n22_selector_vs_cube as public_cascade
import dark_star_recycled_scalable_arithmetic_audit as model

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n22_precision_fresh_public_manifest.json"
PREVIOUS=(ROOT/"dark_star_n22_public_manifest.json",
          ROOT/"dark_star_n22_full_tail_public_manifest.json")
N_EACH=4
FAMILY=8*2*21*2*2 # N * bases * m stages * H/T * two tails
ALPHA=.01
assert FAMILY==1344

# Only necessary parametric correction: simultaneous union family now 8 N
# instead of 4 N. All code, arithmetic, models, PRNG salt and sample sizes
# are reused without tuning from a previously inspected signal.
prec.TOTAL_TESTS=FAMILY
prec.DELTA=ALPHA/FAMILY
prec.LOG=math.log(2/prec.DELTA)


def selftest():
    t=prec.check_selftests()
    assert t["passed"] and prec.N_SAMPLES==131072
    assert prec.EXACT_M==18 and prec.W==32
    assert prec.SALT=="QRR-n22-precision-audit-iid-20261015"
    assert prec.TOTAL_TESTS==FAMILY
    return t


def new_row(public_entry,phasecache):
    n=public_entry["N"]
    a=public_entry["base"]
    b=public_entry["public_policies"]["cube"]
    assert b==pow(a,3,n)
    # All public factorization and proper d certificate work first.
    classical=public_cascade.public_additional_classical(n)
    public_a=old.public_factor_certificates(n,a)
    public_b=old.public_factor_certificates(n,b)
    # p, q and multiplicative orders are synthetic VALIDATION ONLY.
    p,q=old.validation_factors(n)
    lam=math.lcm(p-1,q-1)
    ra=model.multiplicative_order_from_lambda(a,n,lam)
    rb=model.multiplicative_order_from_lambda(b,n,lam)
    assert rb==ra//math.gcd(ra,3)
    gatecache={}
    plain=prec.score_base(n,a,ra,public_a,gatecache,phasecache)
    cube=prec.score_base(n,b,rb,public_b,gatecache,phasecache)
    result=old.classify(plain,cube)
    return {**public_entry,"additional_public_classical":classical,
        "validation_only":{"p":p,"q":q,"order_plain":ra,"order_cube":rb,
           "odd_power_order_identity_verified":True},
        "plain":plain,"cube":cube,"cube_vs_plain":result,
        "strictly_independent_of_previous_N22_N":True,"zero_QPU":True}


def run(group):
    frozen=json.loads(MANIFEST.read_text())
    canonical=manifest_code.canonical(frozen["selected_public_rows"])
    sha=hashlib.sha256(canonical.encode()).hexdigest()
    assert sha==frozen["selected_sha256"]
    assert frozen["zero_QPU"] and frozen["qpu_jobs_submitted"]==0
    exclusions=set()
    for prior_path in PREVIOUS:
        prior=json.loads(prior_path.read_text())
        exclusions.update(r["N"] for r in prior["selected_public_rows"])
    assert len(exclusions)==16
    keys=frozen["selected_public_rows"]
    assert len(keys)==8 and len({x["N"] for x in keys})==8
    assert not exclusions.intersection(x["N"] for x in keys)
    entries=[r for r in keys if r["group"]==group]
    assert len(entries)==N_EACH
    t=selftest()
    out=dict(experiment="dark_star_n22_genuinely_new_precision_holdout_v1",
        preregistration="docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md",
        public_manifest_sha256=sha,group=group,
        is_fresh_disjoint_public_N_population=True,
        phase_samples=prec.N_SAMPLES,exact_all_bin_FFT_max_m=prec.EXACT_M,
        centered_window=prec.W,
        simultaneous_alpha=ALPHA,union_budget_tests=FAMILY,
        EB_log_factor=prec.LOG,
        public_screen=frozen["public_screenings"][group],
        complete=False,
        zero_QPU=True,qpu_jobs_submitted=0,
        selftests=t,rows=[],summary={},
        claim_boundary="strict public-only n22 sample + abstract ideal-QPE CCX with nominal IID phase confidence and analytic omitted-outcome tails; all classically solvable; no QPU")
    phasecache={}
    print("NEW INDEPENDENT FROZEN N22",sha,group,
        "num cases",len(entries),"N phase",prec.N_SAMPLES,
        "empirical Bernstein union tests",FAMILY,flush=True)
    for i,entry in enumerate(entries,1):
        begin=time.process_time()
        row=new_row(entry,phasecache)
        out["rows"].append(row)
        print(f"[{i}/{N_EACH}] N={entry['N']} order="
            f"{row['validation_only']['order_plain']}->{row['validation_only']['order_cube']} "
            f"classic={row['additional_public_classical']['first_factor_source']} "
            f"public_CF_d_plain/cube="
            f"{row['plain']['strict_public_CF_certificate_count']}/"
            f"{row['cube']['strict_public_CF_certificate_count']} "
            f"ratio={row['cube_vs_plain']['ratio']} "
            f"status={row['cube_vs_plain']['status']} "
            f"CPU={time.process_time()-begin:.1f}s",flush=True)
    result=Counter(r["cube_vs_plain"]["status"] for r in out["rows"])
    eligible=sum(not r["plain"]["exact_factor_incapable"] and not r["cube"]["exact_factor_incapable"]
                 for r in out["rows"])
    plain_coverage=sum(not r["plain"]["exact_factor_incapable"] for r in out["rows"])
    cube_coverage=sum(not r["cube"]["exact_factor_incapable"] for r in out["rows"])
    wins=result.get("cube_model_win",0)
    out["summary"]={"selected":len(entries),"screened":len(out["public_screen"]),
        "B31_public_factored":sum(r["public_B31_factored"] for r in out["public_screen"]),
        "classically_factored_after_B31":sum(r["additional_public_classical"]["classically_factored"] for r in out["rows"]),
        "factor_capable_both":eligible,"factor_capable_plain":plain_coverage,
        "factor_capable_cube":cube_coverage,
        "classifications":dict(result),
        "strict_predeclared_trigger_gate_passed":(
           (eligible>=3 and cube_coverage>=plain_coverage and wins>=3)
           if group=="trigger" else None)}
    width=model.arithmetic_width(entries[0]["N"])
    out["logical_width"]={"arithmetic_workspace":width["arithmetic_qubits_excluding_phase"],
        "wide_peak":width["arithmetic_qubits_excluding_phase"]+44,
        "recycled_peak":width["recycled_logical_qubits"]}
    out["complete"]=True
    dst=ROOT/f"dark_star_n22_fresh_precision_{group}.json"
    dst.write_text(json.dumps(out,indent=2)+"\n")
    print("===== NEW N22 FROZEN PRECISION HOLDOUT =====",flush=True)
    print("group",group,"summary",out["summary"],"ZERO QPU. receipt",dst,flush=True)
    return out


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--group",choices=("trigger","control"),required=True)
    args=ap.parse_args()
    run(args.group)
