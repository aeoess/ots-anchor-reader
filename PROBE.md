# The `earliest_height` probe

## Question

NENRIN's JIDEC ledger entry 120 has one OpenTimestamps proof that reaches two Bitcoin blocks, 972141 and 972145.
Draft 1 vector AP-24 claimed 972145, supplied only that block's merkle root, and expected `earliest_height` 972141.
The 972141 attestation was never checked against anything. So what does a reader report if that unchecked
attestation is rewritten to name a different block?

## Construction

`probe.py` takes the untampered proof blob (`nenrin_120_ots`) from `vectors/vectors.json`. It finds the one Bitcoin
attestation that names 972141 and rewrites its height to 972140. Both heights encode as three-byte varuints, so the
proof keeps its length and its other bytes. The pointer is AP-24's, with `proof.sha256` set to the rewritten proof's
hash. The anchored resource is unchanged.

The rewritten proof is byte-identical to the catalog's AP-27 blob (`nenrin_120_ots_tampered_972140`). That is
expected, because AP-27 is this probe carried into draft 1.1 as a vector. It is also why AP-27 is not an independent
test of this reader.

## Outputs

`python3 -I probe.py vectors/vectors.json`, Python 3.14.6, exit 0:

```
untampered proof sha256 58fa0262f86d0e9237175cc6a326e3e4e5b15317fd549479658fec5aebd62d97
rewritten proof sha256  76ee00041a1b9447ffa82cd064cfa818247ae0626e60ffc599e639f97acdfcc4
byte-identical to catalog AP-27 blob: True
P1 rewritten proof, only 972145 supplied: ok
  got  {"earliest_height": 972145, "proof_heights": [972140, 972145], "result": "anchored", "set_checked": true, "verified_heights": [972145]}
P2 rewritten proof, wrong root supplied for 972140: ok
  got  {"failed_height": 972140, "result": "root_mismatch", "set_checked": true}
P3 rewritten proof, 972141's real root supplied under the key 972140: ok
  got  {"earliest_height": 972140, "proof_heights": [972140, 972145], "result": "anchored", "set_checked": true, "verified_heights": [972140, 972145]}
```

## Reading

- P1 is the original probe. Under draft 1 our earlier reader reported `earliest_height` 972140 here, a height nothing
  had checked. Under draft 1.1 the reader reports 972145, the only height whose root was supplied and matched. The
  rewritten 972140 still appears in `proof_heights`, which records what the proof names.
- P2 supplies a wrong root for 972140. Draft 1.1 checks every attestation that has a supplied root, so the pointer
  fails with `root_mismatch` and `failed_height` 972140.
- P3 supplies block 972141's real merkle root under the key 972140. The rewritten attestation still commits to that
  root, so it matches, and the reader reports `earliest_height` 972140. This is the trust boundary in the README. The
  reader takes the height-to-root map as given and does not authenticate the Bitcoin chain. Whoever supplies the
  roots decides which heights can be confirmed.

For contrast, the draft 1 version of this reader (not in this repository) returned
`{"set_checked": true, "result": "anchored", "earliest_height": 972140, "bitcoin_heights_in_proof": [972140, 972145]}`
on P1.
