# ots-anchor-reader

A separately written reader for the anchor pointer draft 1.1 OpenTimestamps vectors, pinned to
[aos-standard/catalog `5294818`](https://github.com/aos-standard/catalog/tree/52948180524a66c6fa68a5377d7880861bf55373/docs/runs/anchor-pointer-draft1.1).
Python standard library only.

Anchor pointer is a proposal by Tetsurohhori (Tetsuroh Hori) in the AOS catalog. A pointer names a digest, the resource
it was taken from, and where that digest was anchored. Draft 1.1 fixes what a reader reports and the order in which
it reports the first failure. This repository is a second reader for that draft, written by aeoess from the draft text
and its vectors.

## What it does

`reader.check(pointer, anchored_bytes, proof_bytes, headers)` returns a result code and the fields draft 1.1 asks for.

- `result`, the first failure in the draft's check order. For OpenTimestamps pointers this is always one of the
  draft's codes. A well-formed `evm-log` pointer gets `evm_log_needs_rpc`, which is not a draft code (see I4 below)
- `set_checked`, true only when the digest comparison on the anchored resource ran
- on `anchored`: `earliest_height` (the smallest height whose supplied root matched), `verified_heights` and
  `proof_heights` (every Bitcoin height the proof names)
- on `root_mismatch`: `failed_height`, the first height whose supplied root did not match. The claimed block is
  checked first, then every other height with a supplied root, lowest first

The OpenTimestamps proof format is parsed by `reader.py` itself, written from memory of the public format. No
OpenTimestamps library is used.

## How it was written

The reader was written from the draft 0, draft 1 and draft 1.1 READMEs and from the vector files. The catalog's
checker (`anchor_pointer_check*.py`), its vector builder and its lax-reader battery were not opened. That is our own
account. For the draft 1.1 update, the tool-call record of the working session shows only the four files listed in
[vectors/SOURCE.md](vectors/SOURCE.md) fetched from the catalog. For the first version it rests on our statement
alone.

The first version targeted draft 1 and passed its 24 vectors at catalog `fda940c`. That run raised three points about
`earliest_height`, `set_checked` and the place of the selector checks in the order. Draft 1.1 takes all three. This
version updates that reader to draft 1.1. The proof parser and the shape checks are carried over from the first
version. The check sequence and the output fields are rewritten.

Where the draft text is silent, the reader makes a choice and says so. See [Interpretations](#interpretations).

## Files

| file | what |
|---|---|
| `reader.py` | the reader |
| `run_all.py` | runs every vector, compares every field in each `expected` and in `supplemental.json`, writes `results.json` |
| `supplemental.json` | extra assertions written by this repository, not by the draft, see [Results](#results) |
| `probe.py` | the `earliest_height` probe, see [PROBE.md](PROBE.md) |
| `mutate.py` | changes one expected field, one of our assertions or one line of the reader at a time, and confirms `run_all.py` fails |
| `vectors/vectors.json` | the draft 1.1 vectors, byte for byte from catalog `5294818` (CC0-1.0) |
| `vectors/SHA256SUMS` | the `vectors.json` line from the catalog's own `SHA256SUMS` |
| `vectors/SOURCE.md` | where the vectors came from and how to compare them with the catalog |
| `results.json`, `run.log` | output of `run_all.py` |
| `probe.log`, `mutate.log` | output of `probe.py` and `mutate.py` |

## Reproduce

The published outputs were produced with Python 3.14.6 on macOS. The same commands also passed under Python 3.9.6,
with identical per-vector output.

```sh
python3 --version
(cd vectors && shasum -a 256 -c SHA256SUMS)          # sha256sum -c on Linux
python3 -I -B run_all.py vectors/vectors.json results.json
python3 -I -B probe.py vectors/vectors.json
python3 -I -B mutate.py vectors/vectors.json
```

Each script exits 0 when every check passes and 1 otherwise. To compare the pinned vectors with the catalog:

```sh
curl -sSfL https://raw.githubusercontent.com/aos-standard/catalog/5294818/docs/runs/anchor-pointer-draft1.1/vectors.json | shasum -a 256
# 0b0b3efb16d230825610ad7cf501ecc0a0bfdaa3d6f182c6e2446957e22fef84
```

## Results

28 of 28 vectors match. `run_all.py` checks three things on each vector.

1. **The draft's expected fields.** Every field in the vector's `expected` is compared, with JSON types kept apart
   (`true` is not `1`, `972141` is not `"972141"`, list order counts). A field the reader does not return is a failure.
   A field outside the draft 1.1 output contract is a failure. A bare-string `expected` is read as the result alone.
2. **Our supplemental assertions.** The draft's vectors leave some output fields unpinned. `supplemental.json` pins
   34 of them where the draft 1.1 README rule fixes the value: `set_checked` on the 21 vectors whose `expected` does
   not carry it, `proof_heights` and `verified_heights` on the anchored vectors (both lists in full on AP-25, and AP-27's
   `proof_heights` is already the draft's), and
   `failed_height` on AP-13 and AP-14. These are our reading of the draft, worked out by hand from the inputs and the
   quoted rule, and each entry says why. They are not the draft author's, and the corpus file is unchanged. A
   supplemental value that contradicts the draft's `expected` is a failure. Supplemental failures are reported as
   `SUPP DIFF`.
3. **Structural checks.** The result code is known, `set_checked` is a boolean, anchored-only fields appear only on
   `anchored` and `failed_height` only on `root_mismatch` with a supplied root. On `anchored`, `proof_heights` must
   equal the Bitcoin attestation heights found in the proof bytes by `scan_heights()` in `run_all.py`. That function
   is a byte search for the attestation tag and its height, separate from the reader's parser. `verified_heights`
   must be those heights that had a root supplied, and `earliest_height` the smallest of them.

The structural checks do not establish `set_checked` or `failed_height` from the inputs. Those two rest on the
draft's vectors and on our supplemental assertions. The byte search would also count the attestation tag if those
nine bytes appeared by chance inside an operation argument. On every proof in the corpus that the reader parses, the
byte search and the reader's parser find the same heights.

| vector | result | draft's expected fields | our supplemental fields | other output fields |
|---|---|---|---|---|
| AP-01 | `anchored` | `earliest_height`, `result`, `set_checked` | `proof_heights`: [972227], `verified_heights`: [972227] | none |
| AP-02 | `malformed` | `result` | `set_checked`: false | none |
| AP-03 | `malformed` | `result` | `set_checked`: false | none |
| AP-04 | `malformed` | `result` | `set_checked`: false | none |
| AP-05 | `unsupported_mechanism` | `result` | `set_checked`: false | none |
| AP-06 | `set_digest_mismatch` | `result` | `set_checked`: true | none |
| AP-07 | `proof_sha_mismatch` | `result` | `set_checked`: true | none |
| AP-08 | `proof_unparseable` | `result` | `set_checked`: true | none |
| AP-09 | `proof_for_other_digest` | `result` | `set_checked`: true | none |
| AP-10 | `pending` | `result` | `set_checked`: true | none |
| AP-11 | `height_not_in_proof` | `result` | `set_checked`: true | none |
| AP-12 | `header_unavailable` | `result` | `set_checked`: true | none |
| AP-13 | `root_mismatch` | `result` | `failed_height`: 972227, `set_checked`: true | none |
| AP-14 | `root_mismatch` | `result` | `failed_height`: 972227, `set_checked`: true | none |
| AP-15 | `anchored` | `earliest_height`, `result`, `set_checked` | `proof_heights`: [972677], `verified_heights`: [972677] | none |
| AP-16 | `set_digest_mismatch` | `result` | `set_checked`: true | none |
| AP-17 | `set_digest_mismatch` | `result` | `set_checked`: true | none |
| AP-18 | `select_out_of_range` | `result` | `set_checked`: false | none |
| AP-19 | `unsupported_select` | `result` | `set_checked`: false | none |
| AP-20 | `malformed` | `result` | `set_checked`: false | none |
| AP-21 | `malformed` | `result` | `set_checked`: false | none |
| AP-22 | `malformed` | `result` | `set_checked`: false | none |
| AP-23 | `anchored` | `earliest_height`, `result`, `set_checked` | `proof_heights`: [972141, 972145], `verified_heights`: [972141] | none |
| AP-24 | `anchored` | `earliest_height`, `result`, `set_checked` | `proof_heights`: [972141, 972145], `verified_heights`: [972145] | none |
| AP-25 | `anchored` | `earliest_height`, `result`, `set_checked` | `proof_heights`: [972141, 972145], `verified_heights`: [972141, 972145] | none |
| AP-26 | `root_mismatch` | `failed_height`, `result` | `set_checked`: true | none |
| AP-27 | `anchored` | `earliest_height`, `proof_heights`, `result`, `set_checked` | `verified_heights`: [972145] | none |
| AP-28 | `select_out_of_range` | `result`, `set_checked` | none | none |

Every field the reader returns on the 28 vectors is pinned by the draft or by us.

`mutate.py` runs three sets of changes, each on temporary copies.

- 16 single changes to the draft's expected fields across 10 vectors. They cover `failed_height`, `proof_heights`,
  `verified_heights`, `set_checked`, `earliest_height` and the result code, plus type-only changes, a wrong list
  order and a misspelled field name.
- 6 single changes to our supplemental assertions, including one that contradicts a draft value.
- 3 one-line changes to `reader.py`. R1 forces `set_checked` false on `set_digest_mismatch`. R2 cuts both height
  lists to their smallest member when more than one height is verified, which only AP-25 reaches. R3 sets
  `set_checked` true on `malformed`. An earlier, unpublished `run_all.py`, without the supplemental file and the byte
  search, passed all three at 28/28.

`run_all.py` exits 1 on all 25 and names the vector. R1 and R3 are caught only by the supplemental assertions. R2 is
caught by both the supplemental assertions and the structural check against the proof bytes. Two controls exit 0:
the unmodified files, and AP-25 with the correct `verified_heights` added to the draft's expected fields. The full
table is in `mutate.log`.

## Limits

- Verification uses supplied Bitcoin block-root values and does not authenticate the Bitcoin chain. The reader checks
  that the proof reaches the merkle root given for a height. It does not check block headers, proof of work, or
  whether a block is on the main chain. The roots in the vectors were supplied by the draft author. Case P3 in
  [PROBE.md](PROBE.md) shows the consequence: a root supplied under the wrong height is accepted.
- The reader was written separately from the draft author's checker. Our own run is still author-produced evidence of
  our reader. No third party has rerun it at the time of this commit.
- AP-27 originated as our probe, so it is not an independent test of our reader.
- The supplemental assertions are ours. They check that the reader agrees with our reading of the draft, not with
  the draft author's. Where that reading could differ, it is listed below as a question.
- The EVM cases (AP-20 to AP-22) are shape checks, not EVM anchor verification. All three are `malformed` pointers. A
  well-formed `evm-log` pointer returns `evm_log_needs_rpc`, which is not a draft result code.
- Python standard library only. No proof in the corpus uses ripemd160, which some Python builds lack.

## Interpretations

The draft text does not settle these. None of them changes a result on the 28 vectors.

- I1. A height counts as verified only if every Bitcoin attestation at that height matches the supplied root.
- I2. Supplied roots are compared in display byte order, as block explorers print them, against the attestation
  message reversed. Hex case is ignored.
- I3. An `opentimestamps` pointer with no proof bytes raises `ValueError`.
- I4. A well-formed `evm-log` pointer that passes steps 1 to 5 returns `evm_log_needs_rpc`.
- I5. A `select` of an unknown kind is shape-checked only for `kind` being a string, so it reaches
  `unsupported_select` rather than `malformed`.

## Questions for the draft author

Four of these are open questions about draft 1.1. Each lists the choice this reader makes until the draft answers.

| | question | this reader's choice |
|---|---|---|
| I1 | If a proof has two Bitcoin attestations at the same height and only one matches the supplied root, is that height verified, or is it `root_mismatch`? | Every attestation at the height must match, so it is `root_mismatch` naming that height. No proof in the corpus has two attestations at one height, so the vectors do not test this |
| I3 | What is the result for an `opentimestamps` pointer when no proof bytes are supplied? Check order has no code for it | Raise `ValueError` and report no draft result. The caller must supply the proof or handle the error |
| I4 | What should a reader that cannot reach an EVM node report for a well-formed `evm-log` pointer? AP-05's note suggests `unsupported_mechanism` may be meant | Return `evm_log_needs_rpc`, outside the draft's codes, after steps 1 to 5. This reader does not verify EVM logs |
| I5 | Should a `select` of an unknown kind have its other fields shape-checked before `unsupported_select`? | Check only that `kind` is a string, then return `unsupported_select`. Extra fields are not inspected. This is not support for any other selector |

## Credit

The anchor pointer drafts, the check order and the vectors are by Tetsurohhori, published under CC0 in
[aos-standard/catalog at `5294818`](https://github.com/aos-standard/catalog/tree/52948180524a66c6fa68a5377d7880861bf55373/docs/runs/anchor-pointer-draft1.1).
The vectors carry material from babyblueviper1's decision-receipt slot log and NENRIN's JIDEC ledger entry 120, both
placed under CC0 by their owners on aeoess/agent-governance-vocabulary#217.

## License

The code is Apache-2.0, see `LICENSE`. `vectors/vectors.json` is CC0-1.0, copied unchanged from the catalog.
