"""Clean-room reader for anchor pointer draft 1.1 (mechanism opentimestamps, chain bitcoin;
evm-log shape checks only). Python 3 standard library only.

Written from the draft 0, draft 1 and draft 1.1 README text and vector files
(aos-standard/catalog 5294818, docs/runs/anchor-pointer-draft1.1/), and from the public
OpenTimestamps serialization format, recalled from memory, not copied. The catalog's own
checker was not read.

First failure is the result, in this order (draft 1.1 README, "Check order"):

  1 malformed  2 unsupported_mechanism  3 unsupported_select  4 select_out_of_range
  5 set_digest_mismatch  (3 to 5 only when anchored_set is present and the resource was given)
  opentimestamps:
  6 proof_sha_mismatch  7 proof_unparseable  8 proof_for_other_digest  9 pending
  10 height_not_in_proof  11 header_unavailable
  12 root_mismatch: the claimed block first, then every other attestation height with a
     supplied header, lowest first. The result carries failed_height.
  13 anchored, with earliest_height (smallest verified height), verified_heights and
     proof_heights.

Every result carries set_checked: true only when the step 5 digest comparison ran.

Interpretations where the README is silent (see README.md of this repo, "Interpretations"):
  I1  A height is verified only if every bitcoin attestation at that height in the proof
      matches the supplied root.
  I2  Supplied roots are compared in display byte order (as block explorers print them)
      against the attestation message reversed, case-insensitive.
  I3  An opentimestamps pointer with no proof bytes supplied raises ValueError: the draft
      defines no result code for it.
  I4  A well-formed evm-log pointer that passes steps 1 to 5 returns evm_log_needs_rpc, which
      is not a draft result code. This reader does not verify EVM logs.
  I5  A select of an unknown kind is not shape-checked beyond `kind` being a string, so it
      reaches unsupported_select rather than malformed.
"""
import hashlib
import re

ORDER = [
    "malformed",
    "unsupported_mechanism",
    "unsupported_select",
    "select_out_of_range",
    "set_digest_mismatch",
    "proof_sha_mismatch",
    "proof_unparseable",
    "proof_for_other_digest",
    "pending",
    "height_not_in_proof",
    "header_unavailable",
    "root_mismatch",
    "anchored",
]

HEX64 = re.compile(r"^[0-9a-f]{64}$")
EVM_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
EVM_TX = re.compile(r"^0x[0-9a-fA-F]{64}$")
CAIP2_EIP155 = re.compile(r"^eip155:[0-9]+$")
KNOWN_MECHANISMS = ("opentimestamps", "evm-log")
KNOWN_SELECT_KINDS = ("line",)


# ---------------------------------------------------------------- OTS parsing

OTS_MAGIC = (b"\x00OpenTimestamps\x00\x00Proof\x00"
             b"\xbf\x89\xe2\xe8\x84\xe8\x92\x94")
TAG_BITCOIN = bytes.fromhex("0588960d73d71901")
TAG_PENDING = bytes.fromhex("83dfe30d2ef90c8e")
MAX_MSG = 4096
MAX_DEPTH = 256


class Unparseable(Exception):
    pass


class _Buf:
    def __init__(self, b):
        self.b, self.i = b, 0

    def byte(self):
        if self.i >= len(self.b):
            raise Unparseable("eof")
        v = self.b[self.i]
        self.i += 1
        return v

    def take(self, n):
        if self.i + n > len(self.b):
            raise Unparseable("eof")
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def varuint(self):
        v, shift = 0, 0
        while True:
            c = self.byte()
            v |= (c & 0x7F) << shift
            if not c & 0x80:
                return v
            shift += 7
            if shift > 63:
                raise Unparseable("varuint too long")

    def varbytes(self, maxlen):
        n = self.varuint()
        if n > maxlen:
            raise Unparseable("varbytes too long")
        return self.take(n)


def _ripemd160(m):
    try:
        h = hashlib.new("ripemd160")
        h.update(m)
        return h.digest()
    except (ValueError, TypeError):
        raise Unparseable("ripemd160 not available in this Python")


UNARY = {
    0x08: lambda m: hashlib.sha256(m).digest(),
    0x02: lambda m: hashlib.sha1(m).digest(),
    0x03: _ripemd160,
    0x67: None,  # keccak256: not in stdlib; treated as unparseable if met
    0xF2: lambda m: m[::-1],                   # reverse
    0xF3: lambda m: m.hex().encode("ascii"),   # hexlify
}
BINARY = {
    0xF0: lambda m, a: m + a,  # append
    0xF1: lambda m, a: a + m,  # prepend
}


def _parse_timestamp(buf, msg, depth, out):
    """Walk the timestamp tree rooted at msg. Append (kind, payload, msg) for every
    attestation reached. kind is 'bitcoin', 'pending' or 'other'."""
    if depth > MAX_DEPTH:
        raise Unparseable("too deep")

    def one(tag):
        if tag == 0x00:
            atag = buf.take(8)
            payload = buf.varbytes(8192)
            if atag == TAG_BITCOIN:
                pb = _Buf(payload)
                h = pb.varuint()
                if pb.i != len(payload):
                    raise Unparseable("trailing bytes in bitcoin attestation")
                out.append(("bitcoin", h, msg))
            elif atag == TAG_PENDING:
                out.append(("pending", payload, msg))
            else:
                out.append(("other", atag.hex(), msg))
        elif tag in BINARY:
            arg = buf.varbytes(MAX_MSG)
            nm = BINARY[tag](msg, arg)
            if len(nm) > MAX_MSG:
                raise Unparseable("message too long")
            _parse_timestamp(buf, nm, depth + 1, out)
        elif tag in UNARY:
            fn = UNARY[tag]
            if fn is None:
                raise Unparseable("keccak256 not supported")
            nm = fn(msg)
            if len(nm) > MAX_MSG:
                raise Unparseable("message too long")
            _parse_timestamp(buf, nm, depth + 1, out)
        else:
            raise Unparseable("unknown tag 0x%02x" % tag)

    tag = buf.byte()
    while tag == 0xFF:
        one(buf.byte())
        tag = buf.byte()
    one(tag)


FILE_HASH_LEN = {0x08: 32, 0x02: 20, 0x03: 20, 0x67: 32}


def parse_ots(data):
    """Return (file_hash_op_tag, file_digest, attestations)."""
    buf = _Buf(data)
    if buf.take(len(OTS_MAGIC)) != OTS_MAGIC:
        raise Unparseable("bad magic")
    if buf.varuint() != 1:
        raise Unparseable("unknown version")
    op = buf.byte()
    if op not in FILE_HASH_LEN:
        raise Unparseable("unknown file hash op")
    digest = buf.take(FILE_HASH_LEN[op])
    atts = []
    _parse_timestamp(buf, digest, 0, atts)
    if buf.i != len(data):
        raise Unparseable("trailing bytes")
    return op, digest, atts


# ---------------------------------------------------------------- shape checks

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _shape_error(p):
    """Return None if well formed, else a reason string."""
    if not isinstance(p, dict):
        return "pointer not an object"
    if p.get("anchor_pointer") not in ("0", "1"):
        return "anchor_pointer"
    d = p.get("anchored_digest")
    if not isinstance(d, dict) or d.get("alg") != "sha-256" or not isinstance(d.get("hex"), str) \
            or not HEX64.match(d["hex"]):
        return "anchored_digest"
    mech = p.get("mechanism")
    if not isinstance(mech, str):
        return "mechanism"
    c = p.get("claimed")
    if not isinstance(c, dict):
        return "claimed"
    if "anchored_set" in p:
        s = p["anchored_set"]
        if not isinstance(s, dict) or not isinstance(s.get("locator"), str):
            return "anchored_set"
        if "select" in s:
            sel = s["select"]
            if not isinstance(sel, dict) or not isinstance(sel.get("kind"), str):
                return "select"
            if sel["kind"] == "line":
                if not _is_int(sel.get("index")) or sel["index"] < 0:
                    return "select.index"
            # unknown kinds: fields not validated here (I5)
    if mech == "opentimestamps":
        pr = p.get("proof")
        if not isinstance(pr, dict) or not isinstance(pr.get("locator"), str) \
                or not isinstance(pr.get("sha256"), str) or not HEX64.match(pr["sha256"]):
            return "proof"
        if c.get("chain") != "bitcoin":
            return "claimed.chain"
        if not _is_int(c.get("height")) or c["height"] < 0:
            return "claimed.height"
    elif mech == "evm-log":
        if "proof" in p:
            return "evm-log has no proof"
        if not isinstance(c.get("chain"), str) or not CAIP2_EIP155.match(c["chain"]):
            return "claimed.chain (CAIP-2 eip155)"
        if not isinstance(c.get("contract"), str) or not EVM_ADDR.match(c["contract"]):
            return "claimed.contract"
        if not isinstance(c.get("tx"), str) or not EVM_TX.match(c["tx"]):
            return "claimed.tx"
        if not _is_int(c.get("log_index")) or c["log_index"] < 0:
            return "claimed.log_index"
        if not _is_int(c.get("height")) or c["height"] < 0:
            return "claimed.height"
    return None


def select_lines(data, index):
    """`line`: split on LF, LF excluded, nothing else stripped, an empty segment after a
    final LF is not a line. Returns bytes, or None if out of range."""
    parts = data.split(b"\n")
    if data.endswith(b"\n"):
        parts = parts[:-1]
    if data == b"":
        parts = []
    if index >= len(parts):
        return None
    return parts[index]


# ---------------------------------------------------------------- reader

def _root_matches(msg, root_hex):
    # I2: the attestation message is the merkle root in internal byte order
    return len(msg) == 32 and isinstance(root_hex, str) and msg[::-1].hex() == root_hex.lower()


def check(pointer, anchored_bytes=None, proof_bytes=None, headers=None):
    """Return a dict with result and set_checked, plus failed_height on root_mismatch and
    earliest_height, verified_heights, proof_heights on anchored."""
    headers = headers or {}
    out = {"set_checked": False}

    def done(result, **extra):
        out["result"] = result
        out.update(extra)
        return out

    # 1, 2
    if _shape_error(pointer) is not None:
        return done("malformed")
    mech = pointer["mechanism"]
    if mech not in KNOWN_MECHANISMS:
        return done("unsupported_mechanism")

    # 3 to 5, only when anchored_set is present and the resource was supplied
    aset = pointer.get("anchored_set")
    if aset is not None and anchored_bytes is not None:
        sel = aset.get("select")
        selected = anchored_bytes
        if sel is not None:
            if sel["kind"] not in KNOWN_SELECT_KINDS:
                return done("unsupported_select")
            selected = select_lines(anchored_bytes, sel["index"])
            if selected is None:
                return done("select_out_of_range")
        out["set_checked"] = True
        if hashlib.sha256(selected).hexdigest() != pointer["anchored_digest"]["hex"]:
            return done("set_digest_mismatch")

    if mech == "evm-log":
        return done("evm_log_needs_rpc")  # I4

    # opentimestamps, 6 to 13
    if proof_bytes is None:
        raise ValueError("opentimestamps pointer without proof bytes: no draft 1.1 result (I3)")
    if hashlib.sha256(proof_bytes).hexdigest() != pointer["proof"]["sha256"]:
        return done("proof_sha_mismatch")
    try:
        op, digest, atts = parse_ots(proof_bytes)
    except Unparseable:
        return done("proof_unparseable")
    if op != 0x08 or digest.hex() != pointer["anchored_digest"]["hex"]:
        return done("proof_for_other_digest")
    btc = [(h, m) for kind, h, m in atts if kind == "bitcoin"]
    if not btc:
        return done("pending")
    proof_heights = sorted(set(h for h, _ in btc))
    claimed = pointer["claimed"]["height"]
    if claimed not in proof_heights:
        return done("height_not_in_proof")
    if str(claimed) not in headers:
        return done("header_unavailable")
    to_verify = [claimed] + [h for h in proof_heights if h != claimed and str(h) in headers]
    for h in to_verify:
        root = headers[str(h)]
        if not all(_root_matches(m, root) for hh, m in btc if hh == h):  # I1
            return done("root_mismatch", failed_height=h)
    verified = sorted(to_verify)
    return done("anchored", earliest_height=verified[0], verified_heights=verified,
                proof_heights=proof_heights)
