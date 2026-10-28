# Vector source

- Repository: aos-standard/catalog
- Commit: `52948180524a66c6fa68a5377d7880861bf55373` (`5294818`)
- Path: `docs/runs/anchor-pointer-draft1.1/vectors.json`
- License: CC0-1.0, by Tetsurohhori, as stated in the file's `license` field
- sha256: `0b0b3efb16d230825610ad7cf501ecc0a0bfdaa3d6f182c6e2446957e22fef84`
- git blob: `e5b6edfd0bb1bfbfdceba28b06aacd21dc758dc4`

The other files read from that directory, not copied here:

| file | sha256 |
|---|---|
| `README.md` (the draft 1.1 text) | `8a93d7e71fed76837957a6152d35a58f4464d3b84e8078b34edc24115cd1f28a` |
| `FROZEN.txt` | `457789d1d68cd7e893212c25dabbe941662b652eab6170fd64f633374f774bac` |
| `SHA256SUMS` | `72f71e0945ad6a28aaea37ee3735657a41b987bd3e78fecb35f0f7a809ec0c91` |

`../supplemental.json` is not from the catalog. It holds assertions written by this repository.

`SHA256SUMS` here is the `vectors.json` line copied from the catalog's own `SHA256SUMS` at that commit. The file is
not modified. To compare with the catalog:

```sh
curl -sSfL https://raw.githubusercontent.com/aos-standard/catalog/5294818/docs/runs/anchor-pointer-draft1.1/vectors.json | shasum -a 256
```

The draft README in that directory is dated 2026-10-28. The commit is timestamped 2026-10-27T22:57:18Z. Pin by commit.
