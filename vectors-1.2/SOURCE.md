# Vector source

- Repository: aos-standard/catalog
- Commit: `53e44de0584d6d85365b774408575486561c90e7` (`53e44de`)
- Path: `docs/runs/anchor-pointer-draft1.2/vectors.json`
- License: CC0-1.0, by Tetsurohhori, as stated in the file's `license` field
- sha256: `00a75863556c158ad05fb39459797501824ac4bb786223211f8e6c5cdc2e2fbd`
- git blob: `54a7cdee4bcf7171813a285142f9f248a979e2c3`

The other files read from that directory, not copied here:

| file | sha256 |
|---|---|
| `README.md` (the draft 1.2 text) | `c3d0f0e551ee96f2990a45962dfe018ba24e86bc737446be0cd47462162c5f86` |
| `FROZEN.txt` | `402583b6dd477ac8647a73913a24e377ef590a622e3444a2afdbffd1a9c2c453` |
| `SHA256SUMS` | `1f2255f292a1332478f56ab84e11264677180fa2988dc426e7951a5d3e27ce18` |
| `run_output.txt` (the catalog reader's per-vector output record, read for the open question on `proof_heights`) | `c8bc63f64298c98b4022df922608ce49f7bfedddcac468aefe17d1b371693c60` |
| `lax_battery_output.txt` | `503a2eed475dd59b204a3c35093759f9d683ebe8089ea056a5087e5ab0f1fc2e` |

Not opened: `anchor_pointer_check_d12.py`, `build_vectors_d12.py`, `lax_battery_d12.py`, `run.json`,
`run_nenrin.json`, `run_nenrin_output.txt`, `nenrin_ea658bd/`. The draft 1.1 directory at the same commit was read
for the diff against draft 1.2 (`README.md`, `ADDENDUM-2d721cb.md`, `vectors.json`, whose sha256 is still
`0b0b3efb16d230825610ad7cf501ecc0a0bfdaa3d6f182c6e2446957e22fef84`); its `.py` files were not opened.

`../supplemental-1.2.json` is not from the catalog. It holds assertions written by this repository.

`SHA256SUMS` here is the `vectors.json` line copied from the catalog's own `SHA256SUMS` at that commit. The file is
not modified. To compare with the catalog:

```sh
curl -sSfL https://raw.githubusercontent.com/aos-standard/catalog/53e44de/docs/runs/anchor-pointer-draft1.2/vectors.json | shasum -a 256
```

The draft README in that directory is dated 2026-10-28. The commit is timestamped 2026-10-28T21:17:30+09:00. Pin by commit.

AP-01 to AP-28 are byte-identical to draft 1.1's (`scripts` diff in the working session: no changed vector, one
added blob `nenrin_120_ots_dup_972141`, three added vectors AP-29, AP-30, AP-31, `anchor_pointer_vectors` and
`sources` updated).
