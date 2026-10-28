"""Run reader.py over the anchor pointer draft 1.2 (or 1.1) vectors and write a results file.

Usage: python3 -I run_all.py <vectors.json> <out results.json> [<supplemental.json>]

For every vector, every field in its `expected` object is compared with the reader's
output, type-sensitive (true is not 1, 972141 is not "972141", list order counts). An
expected field the reader does not return is a failure. An expected field outside the
draft 1.2 output contract is a failure. A bare-string `expected` means {"result": ...}.
A vector without `proof_bytes` is run with no proof (draft 1.2 AP-30).

The supplemental file (supplemental.json next to this file unless a path is given) holds
assertions this repository wrote itself, not the draft. They pin set_checked,
proof_heights, verified_heights and failed_height where the vectors leave them unpinned
and the draft rule fixes the value. They are reported apart from the draft's expected
fields.

Structural checks run on every vector as well: allowed fields and types, earliest_height
and verified_heights only on anchored, failed_height only on root_mismatch, proof_heights
exactly on height_not_in_proof, header_unavailable, root_mismatch and anchored (I6).
Wherever proof_heights appears it must equal the Bitcoin attestation heights found by
scan_heights() in the proof bytes, which does not use reader.py. On anchored,
verified_heights must be those heights that had a root supplied.

Exit 0 when every vector matches and passes the contract and every blob hash matches,
1 otherwise.
"""
import base64
import hashlib
import json
import os
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reader  # noqa: E402

CONTRACT_FIELDS = ("result", "set_checked", "earliest_height", "verified_heights",
                   "proof_heights", "failed_height")
ANCHORED_ONLY = ("earliest_height", "verified_heights")
PROOF_HEIGHTS_ON = ("height_not_in_proof", "header_unavailable", "root_mismatch", "anchored")
RESULT_CODES = tuple(reader.ORDER)
MISSING = object()
BTC_ATTESTATION = b"\x00" + bytes.fromhex("0588960d73d71901")


def scan_heights(proof):
    """Bitcoin attestation heights in an OTS proof, by byte search for the attestation tag
    and its length-prefixed varuint payload. Independent of reader.py's tree walk."""
    def varuint(b, i):
        v = shift = 0
        while i < len(b):
            c = b[i]
            i += 1
            v |= (c & 0x7F) << shift
            if not c & 0x80:
                return v, i
            shift += 7
        return None, i
    found, i = set(), proof.find(BTC_ATTESTATION)
    while i != -1:
        n, j = varuint(proof, i + len(BTC_ATTESTATION))
        if n is not None:
            h, k = varuint(proof, j)
            if h is not None and k == j + n:
                found.add(h)
        i = proof.find(BTC_ATTESTATION, i + 1)
    return sorted(found)


def jeq(a, b):
    """JSON equality that does not let bool equal int or int equal float."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(jeq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(jeq(a[k], b[k]) for k in a)
    return a == b


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def contract_errors(got, headers, proof):
    e = []
    extra = set(got) - set(CONTRACT_FIELDS)
    if extra:
        e.append("fields outside contract: %s" % sorted(extra))
    if got.get("result") not in RESULT_CODES:
        e.append("unknown result %r" % got.get("result"))
    if not isinstance(got.get("set_checked"), bool):
        e.append("set_checked not a bool")
    r = got.get("result")

    def height_list(name):
        lst = got.get(name)
        if not (isinstance(lst, list) and lst and all(is_int(x) for x in lst)
                and lst == sorted(set(lst))):
            e.append("%s not a non-empty ascending list of distinct ints" % name)
            return None
        return lst

    scanned = scan_heights(proof) if proof is not None else []
    if r in PROOF_HEIGHTS_ON:
        ph = height_list("proof_heights")
        if ph is not None and ph != scanned:
            e.append("proof_heights %s, the proof bytes name %s" % (ph, scanned))
    elif "proof_heights" in got:
        e.append("proof_heights present on %s" % r)
    if r == "anchored":
        eh, vh = got.get("earliest_height"), height_list("verified_heights")
        if vh is not None:
            if not is_int(eh) or eh != vh[0]:
                e.append("earliest_height is not the smallest verified height")
            want_v = [h for h in scanned if str(h) in headers]
            if vh != want_v:
                e.append("verified_heights %s, expected every proof height with a supplied "
                         "header %s" % (vh, want_v))
    else:
        for k in ANCHORED_ONLY:
            if k in got:
                e.append("%s present on %s" % (k, r))
    if r == "root_mismatch":
        fh = got.get("failed_height")
        if not is_int(fh) or str(fh) not in headers:
            e.append("failed_height missing or not a height with a supplied header")
    elif "failed_height" in got:
        e.append("failed_height present on %s" % r)
    return e


def compare(exp, got):
    diffs = []
    for k in sorted(exp):
        if k not in CONTRACT_FIELDS:
            diffs.append({"field": k, "expected": exp[k], "got": got.get(k, "<absent>"),
                          "why": "expected field outside the draft 1.2 contract"})
        elif got.get(k, MISSING) is MISSING:
            diffs.append({"field": k, "expected": exp[k], "got": "<absent>", "why": "missing"})
        elif not jeq(got[k], exp[k]):
            diffs.append({"field": k, "expected": exp[k], "got": got[k], "why": "differs"})
    return diffs


def run(path, supp_path):
    raw = open(path, "rb").read()
    d = json.loads(raw)
    supp_raw = open(supp_path, "rb").read()
    supp = json.loads(supp_raw).get("assertions", {})
    ids = set(v["id"] for v in d["vectors"])
    supp_errors = sorted("supplemental names unknown vector %s" % k for k in supp if k not in ids)
    blobs = {k: base64.b64decode(v) for k, v in d["blobs"].items()}
    blob_errors = sorted(k for k, v in blobs.items() if hashlib.sha256(v).hexdigest() != d["blob_sha256"][k])
    rows = []
    for v in d["vectors"]:
        exp = v["expected"] if isinstance(v["expected"], dict) else {"result": v["expected"]}
        headers = v.get("headers", {})
        ab = blobs[v["anchored_bytes"]] if "anchored_bytes" in v else None
        pb = blobs[v["proof_bytes"]] if "proof_bytes" in v else None
        try:
            got = reader.check(v["pointer"], ab, pb, headers)
        except Exception as ex:  # a crash is a failure, not a pass
            got = {"exception": "%s: %s" % (type(ex).__name__, ex)}
        diffs = compare(exp, got)
        sexp = supp.get(v["id"], {}).get("expected", {})
        sdiffs = compare(sexp, got)
        for k in sorted(set(sexp) & set(exp)):
            if not jeq(sexp[k], exp[k]):
                sdiffs.append({"field": k, "expected": sexp[k], "got": exp[k],
                               "why": "supplemental contradicts the draft's expected value"})
        cerr = contract_errors(got, headers, pb) if "exception" not in got else [got["exception"]]
        rows.append({"id": v["id"], "expected": exp, "compared_fields": sorted(exp), "got": got,
                     "field_diffs": diffs, "supplemental_expected": sexp,
                     "supplemental_fields": sorted(sexp), "supplemental_diffs": sdiffs,
                     "contract_errors": cerr, "match": not diffs and not sdiffs and not cerr})
    return raw, d, rows, blob_errors, supp_raw, supp_errors


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    path, out = sys.argv[1:3]
    here = os.path.dirname(os.path.abspath(__file__))
    supp_path = sys.argv[3] if len(sys.argv) == 4 else os.path.join(here, "supplemental.json")
    raw, d, rows, blob_errors, supp_raw, supp_errors = run(path, supp_path)
    ids = [r["id"] for r in rows]
    passed = sum(r["match"] for r in rows)
    ok = passed == len(rows) and not blob_errors and not supp_errors and len(set(ids)) == len(ids)
    res = {
        "reader_sha256": hashlib.sha256(open(os.path.join(here, "reader.py"), "rb").read()).hexdigest(),
        "run_all_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "vectors_file": os.path.basename(path),
        "vectors_sha256": hashlib.sha256(raw).hexdigest(),
        "vectors_label": d.get("anchor_pointer_vectors"),
        "python": platform.python_version(),
        "supplemental_file": os.path.basename(supp_path),
        "supplemental_sha256": hashlib.sha256(supp_raw).hexdigest(),
        "supplemental_errors": supp_errors,
        "supplemental_field_count": sum(len(r["supplemental_fields"]) for r in rows),
        "blob_sha256_errors": blob_errors,
        "passed": passed, "total": len(rows), "all_ok": ok,
        "vectors": rows,
    }
    with open(out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")
    print("vectors %s sha256 %s (%s)" % (res["vectors_file"], res["vectors_sha256"], res["vectors_label"]))
    print("reader.py sha256 %s, Python %s" % (res["reader_sha256"], res["python"]))
    print("%s sha256 %s, %d assertions (ours, not the draft's)" % (
        res["supplemental_file"], res["supplemental_sha256"], res["supplemental_field_count"]))
    for r in rows:
        g = r["got"]
        print("%-6s %-4s result=%-22s compared=%s supplemental=%s" % (
            r["id"], "ok" if r["match"] else "FAIL", g.get("result", g.get("exception")),
            ",".join(r["compared_fields"]), ",".join(r["supplemental_fields"]) or "-"))
        print("       got %s" % json.dumps({k: g[k] for k in sorted(g) if k != "result"}))
        for df in r["field_diffs"]:
            print("       DIFF %s: expected %s got %s (%s)" % (
                df["field"], json.dumps(df["expected"]), json.dumps(df["got"]), df["why"]))
        for df in r["supplemental_diffs"]:
            print("       SUPP DIFF %s: expected %s got %s (%s)" % (
                df["field"], json.dumps(df["expected"]), json.dumps(df["got"]), df["why"]))
        for ce in r["contract_errors"]:
            print("       CONTRACT %s" % ce)
    for se in supp_errors:
        print("SUPP %s" % se)
    print("passed %d/%d, blob errors %s" % (passed, len(rows), blob_errors or "none"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
