"""Mutation check for run_all.py, in three parts, each on temporary copies:

1. change one draft expected field at a time in the vectors
2. change one assertion at a time in supplemental.json (this repository's, not the draft's)
3. change reader.py so it returns a wrong value the draft vectors do not pin

Each must make run_all.py exit 1 and name the vector. The unmodified copy and one correct
added field are controls that must exit 0. For part 3 the runner is also run with an empty
supplemental file, to show which layer catches the mutant. That column is information, not
a pass condition.

Usage: python3 -I mutate.py <vectors.json>
Exit 0 when every mutation makes run_all.py exit 1 and both controls exit 0.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DROP = object()

# (vector id, field, new value, what it tests). DROP removes the field.
MUTATIONS = [
    ("AP-26", "failed_height", 972145, "failed_height: the claimed block instead of the failing one"),
    ("AP-26", "failed_height", "972141", "failed_height: right number as a string (type)"),
    ("AP-27", "proof_heights", [972145], "proof_heights: the rewritten height dropped"),
    ("AP-27", "proof_heights", [972145, 972140], "proof_heights: right members, wrong order"),
    ("AP-25", "verified_heights", [972145], "verified_heights added: only the claimed block"),
    ("AP-24", "verified_heights", [972141, 972145], "verified_heights added: unverified height included"),
    ("AP-28", "set_checked", True, "set_checked: true after a select error"),
    ("AP-28", "set_checked", 0, "set_checked: 0 instead of false (type)"),
    ("AP-01", "set_checked", False, "set_checked: false when the comparison ran"),
    ("AP-24", "earliest_height", 972141, "earliest_height: the draft 1 unverified bound"),
    ("AP-27", "earliest_height", 972140, "earliest_height: the probe's rewritten height"),
    ("AP-01", "result", "root_mismatch", "result code on an object expected"),
    ("AP-13", "result", "header_unavailable", "result code on a bare-string expected"),
    ("AP-28", "result", "proof_sha_mismatch", "result: AP-28's second fault, wrong order"),
    ("AP-23", "failed_height", 972141, "failed_height added on an anchored vector"),
    ("AP-15", "earliest_heigth", 972677, "misspelled field outside the contract"),
]
# (vector id, field, new value, what it tests), applied to supplemental.json
SUPP_MUTATIONS = [
    ("AP-25", "verified_heights", [972145], "our pin: AP-25 verified_heights without 972141"),
    ("AP-25", "proof_heights", [972141], "our pin: AP-25 proof_heights without 972145"),
    ("AP-06", "set_checked", False, "our pin: set_checked false after the comparison ran"),
    ("AP-02", "set_checked", True, "our pin: set_checked true on malformed"),
    ("AP-13", "failed_height", 972228, "our pin: failed_height off by one"),
    ("AP-01", "set_checked", False, "our pin contradicting a field the draft already pins"),
]
# (name, exact text in reader.py, replacement, vector the runner must name, what it tests)
READER_MUTANTS = [
    ("R1", '            return done("set_digest_mismatch")',
     '            out["set_checked"] = False\n            return done("set_digest_mismatch")',
     "AP-06", "review mutant: set_checked forced false on set_digest_mismatch"),
    ("R2", "    verified = sorted(to_verify)\n",
     "    verified = sorted(to_verify)\n    if len(verified) > 1:\n"
     "        verified = proof_heights = [verified[0]]\n",
     "AP-25", "review mutant: AP-25 height lists reduced to the minimum"),
    ("R3", '        return done("malformed")',
     '        out["set_checked"] = True\n        return done("malformed")',
     "AP-02", "set_checked true on malformed"),
]
CONTROLS = [
    ("control", None, None, None, "unmodified copy"),
    ("AP-25", "verified_heights", [972141, 972145], None, "verified_heights added with the right value"),
]


def run(vectors, supp=None, reader_src=None):
    with tempfile.TemporaryDirectory() as td:
        for name in ("run_all.py", "reader.py"):
            shutil.copy(os.path.join(HERE, name), td)
        if reader_src is not None:
            with open(os.path.join(td, "reader.py"), "w") as f:
                f.write(reader_src)
        sp = os.path.join(td, "supplemental.json")
        with open(sp, "w") as f:
            json.dump(supp if supp is not None else SUPP, f)
        vp = os.path.join(td, "vectors.json")
        with open(vp, "w") as f:
            json.dump(vectors, f)
        p = subprocess.run([sys.executable, "-I", os.path.join(td, "run_all.py"), vp,
                            os.path.join(td, "results.json"), sp], capture_output=True, text=True)
        return p.returncode, p.stdout


def mutate_supp(vid, field, value):
    s = json.loads(json.dumps(SUPP))
    s["assertions"].setdefault(vid, {"expected": {}})["expected"][field] = value
    return s


def mutate(base, vid, field, value):
    d = json.loads(json.dumps(base))
    if vid == "control":
        return d
    v = next(x for x in d["vectors"] if x["id"] == vid)
    if not isinstance(v["expected"], dict):
        v["expected"] = {"result": v["expected"]}
    if value is DROP:
        del v["expected"][field]
    else:
        v["expected"][field] = value
    return d


def lines_for(out, vid):
    keep, on = [], False
    for ln in out.splitlines():
        if ln.startswith("AP-"):
            on = ln.startswith(vid + " ")
        if on and ("DIFF" in ln or "CONTRACT" in ln):
            keep.append(ln.strip())
    return keep


def main():
    global SUPP
    base = json.load(open(sys.argv[1], "rb"))
    SUPP = json.load(open(os.path.join(HERE, "supplemental.json"), "rb"))
    ok = True
    print("# 1. draft expected fields")
    print("%-8s %-17s %-22s %-5s %s" % ("vector", "field", "mutated to", "exit", "runner says"))
    for vid, field, value, why in MUTATIONS:
        code, out = run(mutate(base, vid, field, value))
        caught = code == 1 and lines_for(out, vid)
        ok &= bool(caught)
        print("%-8s %-17s %-22s %-5s %s  [%s] %s" % (vid, field, json.dumps(value), code,
              "; ".join(lines_for(out, vid)) or "(no diff)", "caught" if caught else "MISSED", why))
    print("# 2. supplemental.json assertions (ours)")
    for vid, field, value, why in SUPP_MUTATIONS:
        code, out = run(base, supp=mutate_supp(vid, field, value))
        caught = code == 1 and lines_for(out, vid)
        ok &= bool(caught)
        print("%-8s %-17s %-22s %-5s %s  [%s] %s" % (vid, field, json.dumps(value), code,
              "; ".join(x for x in lines_for(out, vid) if "DIFF" in x) or "(no diff)",
              "caught" if caught else "MISSED", why))
    print("# 3. reader.py mutants")
    src = open(os.path.join(HERE, "reader.py")).read()
    empty = {"assertions": {}}
    for name, old, new, vid, why in READER_MUTANTS:
        if src.count(old) != 1:
            print("%-8s mutation text not found once in reader.py  [MISSED] %s" % (name, why))
            ok = False
            continue
        msrc = src.replace(old, new)
        code, out = run(base, reader_src=msrc)
        failed = sorted(set(ln.split()[0] for ln in out.splitlines() if ln[:3] == "AP-" and " FAIL " in ln[:12]))
        caught = code == 1 and vid in failed
        ok &= bool(caught)
        code2, out2 = run(base, supp=empty, reader_src=msrc)
        print("%-8s exit %s, failing %s, without supplemental exit %s  [%s] %s" % (
              name, code, ",".join(failed) or "none", code2, "caught" if caught else "MISSED", why))
        for ln in lines_for(out, vid):
            if "DIFF" in ln or "CONTRACT" in ln:
                print("         %s %s" % (vid, ln))
    print("# controls")
    for vid, field, value, _, why in CONTROLS:
        code, out = run(mutate(base, vid, field, value))
        good = code == 0
        ok &= good
        print("%-8s %-17s %-22s %-5s %s  [%s] %s" % (vid, field or "-", json.dumps(value), code,
              out.strip().splitlines()[-1], "pass" if good else "FAIL", why))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
