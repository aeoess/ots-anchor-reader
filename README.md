# ots-anchor-reader

A separately written reader for the anchor pointer draft 1.2 OpenTimestamps vectors, pinned to
[aos-standard/catalog `53e44de`](https://github.com/aos-standard/catalog/tree/53e44de0584d6d85365b774408575486561c90e7/docs/runs/anchor-pointer-draft1.2).
Python standard library only. The draft 1.1 run (28/28 at catalog `5294818`, commit `2d721cb` of this repository) is
kept as a record: `vectors/`, `supplemental.json`, `results.json`, `run.log`, `probe.log` and `mutate.log` are the
draft 1.1 files, unchanged.

Anchor pointer is a proposal by Tetsurohhori (Tetsuroh Hori) in the AOS catalog. A pointer names a digest, the resource
it was taken from, and where that digest was anchored. Draft 1.1 fixed what a reader reports and the order in which it
reports the first failure. Draft 1.2 answers the four questions this repository's draft 1.1 README put to the author
and adds three vectors. This repository is a second reader for that draft, written by aeoess from the draft text and
its vectors.

## What it does

`reader.check(pointer, anchored_bytes, proof_bytes, headers)` returns a result code and the fields draft 1.2 asks for.

- `result`, the first failure in the draft's check order. Always one of the draft's codes. This reader reads the
  `opentimestamps` mechanism only, so a well-formed `evm-log` pointer gets `unsupported_mechanism` at step 2, as draft
  1.2 says for a reader that does not read that mechanism
- `set_checked`, true only when the digest comparison on the anchored resource ran
- `proof_heights`, every Bitcoin height the proof names, on every result reached once the proof has been parsed and
  names a height: `height_not_in_proof`, `header_unavailable`, `root_mismatch`, `anchored` (see I6 below)
- on `anchored`: `earliest_height` (the smallest height whose supplied root matched) and `verified_heights`
- on `root_mismatch`: `failed_height`, the first height whose supplied root did not match. The claimed block is
  checked first, then every other height with a supplied root, lowest first. Every attestation at a height must match

The OpenTimestamps proof format is parsed by `reader.py` itself, written from memory of the public format. No
OpenTimestamps library is used.

## What changed from draft 1.1 to draft 1.2, and in this reader

Draft 1.2 names four changes. The diff of the two catalog directories at `53e44de` shows one more. AP-01 to AP-28 are
byte-identical in both `vectors.json` files.

| | draft 1.2 | this reader at `2d721cb` (draft 1.1) | change here |
|---|---|---|---|
| I1 | every attestation at a height with a supplied header must match, else `root_mismatch` naming that height. AP-29 | already so | none in the check. AP-29 passes on the result and `failed_height` |
| I3 | new code `proof_unavailable`, step 6, before `proof_sha_mismatch`, with `set_checked` as for every code. AP-30 | raised `ValueError` | returns `proof_unavailable` after step 5 |
| I4 | `unsupported_mechanism` at step 2 means "this reader does not read this mechanism", draft-defined or not. No offline vector | returned `evm_log_needs_rpc`, outside the draft's codes | a well-formed `evm-log` pointer returns `unsupported_mechanism`. Step 1 still applies the draft's `evm-log` shape rules, because AP-20 to AP-22 expect `malformed` |
| I5 | for a `select` of a kind the reader does not implement only `kind` must be a string, then `unsupported_select`, not `malformed`. AP-31 | already so | none in the check. AP-31 passes |
| not named | AP-29 expects `proof_heights` on a `root_mismatch` result. Draft 1.1's and draft 1.2's README text list `proof_heights` under `anchored` only, and this repository's draft 1.1 runner rejected it elsewhere | `proof_heights` on `anchored` only | I6: `proof_heights` on every result from step 11 on, and the runner's contract follows |

The unchanged `2d721cb` reader on the draft 1.2 vectors: 29/31. AP-29 fails only on the missing `proof_heights`
(result and `failed_height` were already right), AP-30 fails with the `ValueError`, AP-31 passes.

## How it was written

The reader was written from the draft 0, draft 1, draft 1.1 and draft 1.2 READMEs and from the vector files. The
catalog's checkers (`anchor_pointer_check*.py`), its vector builders and its lax-reader batteries were not opened.
That is our own account. For the draft 1.2 update, the files read in the catalog are listed with their hashes in
[vectors-1.2/SOURCE.md](vectors-1.2/SOURCE.md). They include the catalog reader's per-vector output record
`run_output.txt`, read to see on which results that reader prints `proof_heights` (the open question below), and not
its code. For the draft 1.1 update the tool-call record of the working session showed only the four files listed in
[vectors/SOURCE.md](vectors/SOURCE.md). For the first version it rests on our statement alone.

The first version targeted draft 1 and passed its 24 vectors at catalog `fda940c`. That run raised three points, which
draft 1.1 took. The draft 1.1 version raised four more (I1, I3, I4, I5 below), which draft 1.2 takes. This version
updates the reader to draft 1.2. The proof parser, the shape checks and the check sequence are carried over. The
changes are the two listed above and `proof_heights` on more results.

Where the draft text is silent, the reader makes a choice and says so. See [Interpretations](#interpretations).

## Files

| file | what |
|---|---|
| `reader.py` | the reader |
| `run_all.py` | runs every vector, compares every field in each `expected` and in the supplemental file, writes a results file |
| `supplemental-1.2.json` | extra assertions written by this repository for the draft 1.2 vectors, not by the draft, see [Results](#results) |
| `probe.py` | the `earliest_height` probe, see [PROBE.md](PROBE.md) |
| `mutate.py` | changes one expected field, one of our assertions or one line of the reader at a time, and confirms `run_all.py` fails |
| `vectors-1.2/vectors.json` | the draft 1.2 vectors, byte for byte from catalog `53e44de` (CC0-1.0) |
| `vectors-1.2/SHA256SUMS`, `vectors-1.2/SOURCE.md` | the `vectors.json` line from the catalog's own `SHA256SUMS`, and where the vectors came from |
| `results-1.2.json`, `run-1.2.log` | output of `run_all.py` on the draft 1.2 vectors |
| `probe-1.2.log`, `mutate-1.2.log` | output of `probe.py` and `mutate.py` on the draft 1.2 vectors |
| `results-1.1-rerun.json`, `run-1.1-rerun.log`, `probe-1.1-rerun.log`, `mutate-1.1-rerun.log` | this reader on the draft 1.1 vectors with the draft 1.1 supplemental file |
| `vectors/`, `supplemental.json`, `results.json`, `run.log`, `probe.log`, `mutate.log` | the draft 1.1 record from `2d721cb`, unchanged |

## Reproduce

The published outputs were produced with Python 3.13.18 on Linux.

```sh
python3 --version
(cd vectors-1.2 && sha256sum -c SHA256SUMS)          # shasum -a 256 -c on macOS
python3 -I -B run_all.py vectors-1.2/vectors.json results-1.2.json supplemental-1.2.json
python3 -I -B probe.py vectors-1.2/vectors.json
python3 -I -B mutate.py vectors-1.2/vectors.json supplemental-1.2.json
# the same reader on the draft 1.1 vectors
python3 -I -B run_all.py vectors/vectors.json results-1.1-rerun.json supplemental.json
python3 -I -B probe.py vectors/vectors.json
python3 -I -B mutate.py vectors/vectors.json supplemental.json
```

Each script exits 0 when every check passes and 1 otherwise. To compare the pinned vectors with the catalog:

```sh
curl -sSfL https://raw.githubusercontent.com/aos-standard/catalog/53e44de/docs/runs/anchor-pointer-draft1.2/vectors.json | shasum -a 256
# 00a75863556c158ad05fb39459797501824ac4bb786223211f8e6c5cdc2e2fbd
```

## Results

31 of 31 draft 1.2 vectors match, and the same reader matches 28 of 28 draft 1.1 vectors. `run_all.py` checks three
things on each vector.

1. **The draft's expected fields.** Every field in the vector's `expected` is compared, with JSON types kept apart
   (`true` is not `1`, `972141` is not `"972141"`, list order counts). A field the reader does not return is a failure.
   A field outside the draft 1.2 output contract is a failure. A bare-string `expected` is read as the result alone. A
   vector without `proof_bytes` is run with no proof (AP-30).
2. **Our supplemental assertions.** The draft's vectors leave some output fields unpinned. `supplemental-1.2.json`
   pins 39 of them where the draft 1.2 README rule, or our I6, fixes the value: `set_checked` on the 21 vectors whose
   `expected` does not carry it, `proof_heights` and `verified_heights` on the anchored vectors, `failed_height` on
   AP-13 and AP-14, and `proof_heights` on AP-11 to AP-14 and AP-26 (I6). These are our reading of the draft, worked out
   by hand from the inputs and the quoted rule, and each entry says why. They are not the draft author's, and the corpus
   file is unchanged. A supplemental value that contradicts the draft's `expected` is a failure. Supplemental failures
   are reported as `SUPP DIFF`.
3. **Structural checks.** The result code is known, `set_checked` is a boolean, `earliest_height` and
   `verified_heights` appear only on `anchored`, `failed_height` only on `root_mismatch` with a supplied root, and
   `proof_heights` exactly on `height_not_in_proof`, `header_unavailable`, `root_mismatch` and `anchored`. Wherever
   `proof_heights` appears it must equal the Bitcoin attestation heights found in the proof bytes by `scan_heights()`
   in `run_all.py`. That function is a byte search for the attestation tag and its height, separate from the reader's
   parser. On `anchored`, `verified_heights` must be those heights that had a root supplied, and `earliest_height` the
   smallest of them.

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
| AP-11 | `height_not_in_proof` | `result` | `proof_heights`: [972227], `set_checked`: true | none |
| AP-12 | `header_unavailable` | `result` | `proof_heights`: [972227], `set_checked`: true | none |
| AP-13 | `root_mismatch` | `result` | `failed_height`: 972227, `proof_heights`: [972227], `set_checked`: true | none |
| AP-14 | `root_mismatch` | `result` | `failed_height`: 972227, `proof_heights`: [972227], `set_checked`: true | none |
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
| AP-26 | `root_mismatch` | `failed_height`, `result` | `proof_heights`: [972141, 972145], `set_checked`: true | none |
| AP-27 | `anchored` | `earliest_height`, `proof_heights`, `result`, `set_checked` | `verified_heights`: [972145] | none |
| AP-28 | `select_out_of_range` | `result`, `set_checked` | none | none |
| AP-29 | `root_mismatch` | `failed_height`, `proof_heights`, `result`, `set_checked` | none | none |
| AP-30 | `proof_unavailable` | `result`, `set_checked` | none | none |
| AP-31 | `unsupported_select` | `result`, `set_checked` | none | none |

Every field the reader returns on the 31 vectors is pinned by the draft or by us. On the draft 1.1 rerun with the
draft 1.1 supplemental file, `proof_heights` on AP-11 to AP-14 and AP-26 is pinned by neither (that file predates I6)
and is checked only structurally against the proof bytes.

`mutate.py` runs three sets of changes, each on temporary copies, plus one informational mutant.

- 22 single changes to the draft's expected fields across 12 vectors. The 16 from draft 1.1 cover `failed_height`,
  `proof_heights`, `verified_heights`, `set_checked`, `earliest_height` and the result code, plus type-only changes, a
  wrong list order and a misspelled field name. The 6 new ones set AP-29, AP-30 and AP-31 to the draft 1.1 reader's
  answers and to neighbouring wrong values.
- 8 single changes to our supplemental assertions, including one that contradicts a draft value and two to the I6 pins.
- 7 one-line changes to `reader.py`. R1 to R3 are draft 1.1's. R4 reverts I1 (`all` to `any`): AP-29 fails, result
  `anchored`. R5 removes I3 (no proof bytes read as empty bytes): AP-30 fails, result `proof_sha_mismatch`. R6 reverts
  I5 (an `index` member shape-checked for every `select` kind): AP-31 fails, result `malformed`. R7 drops
  `proof_heights` from `root_mismatch`: AP-29 fails on the draft's expected field.
- X1, information only: accepting `evm-log` at step 2 (I4 reverted) fails no vector, because no offline vector has a
  well-formed `evm-log` pointer. The draft says so itself.

`run_all.py` exits 1 on all 37 and names the vector. Two controls exit 0: the unmodified files, and AP-25 with the
correct `verified_heights` added to the draft's expected fields. The full table is in `mutate-1.2.log`. On the draft
1.1 vectors the ten draft 1.2 mutations are skipped and the other 27 are caught (`mutate-1.1-rerun.log`).

## Limits

- Verification uses supplied Bitcoin block-root values and does not authenticate the Bitcoin chain. The reader checks
  that the proof reaches the merkle root given for a height. It does not check block headers, proof of work, or
  whether a block is on the main chain. The roots in the vectors were supplied by the draft author. Case P3 in
  [PROBE.md](PROBE.md) shows the consequence: a root supplied under the wrong height is accepted.
- The reader was written separately from the draft author's checker. Our own run is still author-produced evidence of
  our reader. No third party has rerun it at the time of this commit.
- AP-27 originated as our probe, and AP-29, AP-30 and AP-31 were built to the four questions this repository asked, so
  none of the four is an independent test of our reader's choices. AP-29 and AP-31 test behaviour the `2d721cb`
  reader already had.
- The supplemental assertions are ours. They check that the reader agrees with our reading of the draft, not with
  the draft author's. Where that reading could differ, it is listed below as a question.
- This reader does not read `evm-log`. AP-20 to AP-22 are shape checks on malformed `evm-log` pointers. A well-formed
  `evm-log` pointer returns `unsupported_mechanism` (draft 1.2, I4) and nothing about it is verified.
- Python standard library only. No proof in the corpus uses ripemd160, which some Python builds lack.

## Interpretations

Draft 1.2 settled I1, I3, I4 and I5 as this reader had them, except that I3 now has a result code and I4 a draft code.
Two choices remain this repository's.

- I2. Supplied roots are compared in display byte order, as block explorers print them, against the attestation
  message reversed. Hex case is ignored.
- I6. `proof_heights` is reported on every result reached once the proof has been parsed, matched the pointer's
  digest and named at least one Bitcoin height: `height_not_in_proof`, `header_unavailable`, `root_mismatch`,
  `anchored`. The draft 1.2 README lists it under `anchored` only. AP-29 expects it on `root_mismatch`. Both are
  consistent with I6. On the 31 vectors, only AP-29's expectation depends on it.

## Questions for the draft author

| | question | this reader's choice |
|---|---|---|
| Q1 | AP-29 expects `proof_heights` on `root_mismatch`, and the README text lists it only under `anchored`. On which results is `proof_heights` part of the output: `root_mismatch` only, every result from `height_not_in_proof` on, or every result after the proof parses (so `[]` on `pending`)? The catalog reader's `run_output.txt` prints it from `height_not_in_proof` on | I6: from `height_not_in_proof` on, never on `pending` or earlier |
| Q2 | Draft 1.2 says `unsupported_mechanism` is the answer of a reader that does not read a mechanism. AP-20 to AP-22 still expect `malformed` for `evm-log` pointers whose faults are `evm-log` specific (a `proof` member, a non CAIP-2 `chain`, a missing `log_index`). Must a reader that does not read `evm-log` know and apply the `evm-log` shape rules at step 1, or may it answer `unsupported_mechanism` on those three? | Applies the `evm-log` shape rules at step 1, so AP-20 to AP-22 are `malformed` |
| Q3 | `proof_unavailable` is defined for `opentimestamps`. The `evm-log` branch has no step 6 equivalent, which is consistent with `evm-log` having no proof member. Is that the intent, so that a reader never reports `proof_unavailable` for `evm-log`? | Not reachable here: `evm-log` stops at step 2 |
| Q4 | AP-30 supplies the headers of AP-01. `proof_unavailable` comes before any header is looked at, so the headers do not matter. Is a vector with no `proof_bytes` and no `headers` meant to give the same result? | Yes: steps 7 to 14 are not reached, headers are not read |

## Credit

The anchor pointer drafts, the check order and the vectors are by Tetsurohhori, published under CC0 in
[aos-standard/catalog at `53e44de`](https://github.com/aos-standard/catalog/tree/53e44de0584d6d85365b774408575486561c90e7/docs/runs/anchor-pointer-draft1.2).
The vectors carry material from babyblueviper1's decision-receipt slot log and NENRIN's JIDEC ledger entry 120, both
placed under CC0 by their owners on aeoess/agent-governance-vocabulary#217.

## License

The code is Apache-2.0, see `LICENSE`. `vectors/vectors.json` and `vectors-1.2/vectors.json` are CC0-1.0, copied
unchanged from the catalog.
