"""earliest_height probe: rewrite the unverified earlier attestation in NENRIN entry 120's
proof from 972141 to 972140, then ask the reader for the pointer claimed at 972145 with only
972145's root supplied.

Usage: python3 -I probe.py <vectors.json>

The probe builds its own rewritten proof from the untampered blob. It then compares the
result with the catalog's AP-27 blob, which is the same probe carried as a vector.
Exit 0 when every case gives its expected output, 1 otherwise.
"""
import base64
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reader  # noqa: E402


def varuint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def rewrite_height(proof, old, new):
    """Replace the one bitcoin attestation naming `old` with `new` (same varuint length)."""
    old_att = reader.TAG_BITCOIN + varuint(len(varuint(old))) + varuint(old)
    new_att = reader.TAG_BITCOIN + varuint(len(varuint(new))) + varuint(new)
    assert len(old_att) == len(new_att) and proof.count(old_att) == 1
    return proof.replace(old_att, new_att)


def main():
    d = json.load(open(sys.argv[1], "rb"))
    blobs = {k: base64.b64decode(v) for k, v in d["blobs"].items()}
    vec = {v["id"]: v for v in d["vectors"]}
    base = vec["AP-24"]  # claimed 972145, only 972145's root supplied
    tampered = rewrite_height(blobs["nenrin_120_ots"], 972141, 972140)
    t_sha = hashlib.sha256(tampered).hexdigest()
    pointer = json.loads(json.dumps(base["pointer"]))
    pointer["proof"]["sha256"] = t_sha
    root_972141 = vec["AP-23"]["headers"]["972141"]
    root_972145 = base["headers"]["972145"]
    cases = [
        ("P1 rewritten proof, only 972145 supplied", {"972145": root_972145},
         {"result": "anchored", "earliest_height": 972145, "verified_heights": [972145],
          "proof_heights": [972140, 972145], "set_checked": True}),
        ("P2 rewritten proof, wrong root supplied for 972140", {"972145": root_972145, "972140": "00" * 32},
         {"result": "root_mismatch", "failed_height": 972140, "set_checked": True}),
        ("P3 rewritten proof, 972141's real root supplied under the key 972140",
         {"972145": root_972145, "972140": root_972141},
         {"result": "anchored", "earliest_height": 972140, "verified_heights": [972140, 972145],
          "proof_heights": [972140, 972145], "set_checked": True}),
    ]
    ok = True
    same = tampered == blobs["nenrin_120_ots_tampered_972140"]
    print("untampered proof sha256 %s" % hashlib.sha256(blobs["nenrin_120_ots"]).hexdigest())
    print("rewritten proof sha256  %s" % t_sha)
    print("byte-identical to catalog AP-27 blob: %s" % same)
    ok &= same and t_sha == vec["AP-27"]["pointer"]["proof"]["sha256"]
    for name, headers, want in cases:
        got = reader.check(pointer, blobs["nenrin_120"], tampered, headers)
        good = got == want
        ok &= good
        print("%s: %s\n  got  %s" % (name, "ok" if good else "FAIL", json.dumps(got, sort_keys=True)))
        if not good:
            print("  want %s" % json.dumps(want, sort_keys=True))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
