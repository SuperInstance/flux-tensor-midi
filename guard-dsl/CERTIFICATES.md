# GUARD Proof Certificates

Every compiled GUARD module produces a **Proof Certificate** alongside its FLUX bytecode. The certificate is self-contained: a verifier can recompute every hash in it from the module source and the certificate alone, with no access to the compiler.

**What that does not buy you.** Re-deriving a hash proves the artifact is *internally consistent*, not that the compiler was *honest*. Every hash in a certificate — `source_hash`, `bytecode_hash`, `trace_digest`, `merkle_root` — is computed by `guardc` itself. A buggy or malicious compiler emits whatever it likes and all of its hashes agree perfectly. See [Trusted Computing Base (TCB)](#trusted-computing-base-tcb) for what this means in practice.

## Design Goals

1. **Independence** — A safety auditor can verify the certificate with a small, trusted checker (≈ 500 lines of Rust).
2. **Reproducibility** — The same source + compiler version always yields the same certificate hash.
3. **Granularity** — Certificates are per-module, per-proof-declaration, so partial verification is possible.
4. **Traceability** — Every bytecode instruction maps back to a source range.

## Certificate Format (Native)

```json
{
  "certificate_format": "guard-native-v1",
  "module": "ThrottleLimit",
  "version": "1.0.0",
  "compiler": {
    "name": "guardc",
    "version": "1.0.0-ship",
    "target": "flux-isa-43"
  },
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "bytecode_hash": "sha256:a3c5f1e...",
  "proofs": [
    {
      "proof_id": "ThrottleSafetyProof",
      "tactics": ["interval_arithmetic", "bit_blast"],
      "status": "not_sealed",
      "verification_time_ms": 47,
      "obligations": [
        {
          "obligation_id": "inv-01",
          "kind": "invariant_preservation",
          "name": "ThrottleMustNotExceedMax",
          "source_span": "throttle.guard:13:3-15:19",
          "vc": {
            "logic": "QF_LRA",
            "formula": "(assert (<= throttle_command 1.0))",
            "status": "unknown"
          },
          "trace_digest": "obligation:bb12a9...",
          "counterexample": null
        },
        {
          "obligation_id": "inv-02",
          "kind": "invariant_preservation",
          "name": "ThrottleMustNotReverse",
          "source_span": "throttle.guard:18:3-20:19",
          "vc": {
            "logic": "QF_LRA",
            "formula": "(assert (>= throttle_command 0.0))",
            "status": "unknown"
          },
          "trace_digest": "obligation:cc23b0...",
          "counterexample": null
        },
        {
          "obligation_id": "der-01",
          "kind": "derived_rule_sanity",
          "name": "PositiveThrottleImpliesEngineEnabled",
          "source_span": "throttle.guard:24:1-27:30",
          "vc": {
            "logic": "QF_LIA",
            "formula": "(assert (=> (> throttle_command 0.0) engine_enabled))",
            "status": "unknown"
          },
          "trace_digest": "obligation:dd34c1...",
          "counterexample": null
        }
      ],
      "merkle_root": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "metadata": {
    "generated_at": "2026-05-03T08:35:51Z",
    "host_os": "linux-x86_64",
    " deterministic": true
  }
}
```

## Field Semantics

| Field | Meaning |
|-------|---------|
| `source_hash` | SHA-256 of the canonicalized source text (UTF-8, LF-only, no trailing whitespace). |
| `bytecode_hash` | SHA-256 of the emitted FLUX bytecode object. |
| `proofs` | One entry per `proof { ... }` block in the source. |
| `obligations` | Individual Verification Conditions (VCs). Each invariant and derived rule generates at least one. |
| `vc.logic` | SMT-LIB logic used (e.g., `QF_LRA` for quantifier-free linear real arithmetic, `QF_BV` for bit-vectors). |
| `vc.status` | What the solver said. `unsat` = the constraint is unsatisfiable, i.e. the property **holds**. `sat` = the constraint **is satisfiable**, i.e. a counterexample **exists**. `unknown` = not determined. **`guardc` emits only `unknown`**: it runs no solver (`Cargo.toml` has no Z3, cvc5 or Bitwuzla) and never runs the FLUX VM. Before [guardc#3](https://github.com/SuperInstance/guardc/pull/3) it emitted `sat` on every VC. |
| `trace_digest` | **Not a trace digest.** `guardc` compiles and does not execute, so there is no symbolic execution trace to digest. The field carries an *obligation digest*: `obligation:<sha256>` over `obligation_id`, `kind`, `name`, `source_span`, and the VC's `logic` and `formula` — what this VC was actually built from. The `obligation:` prefix is deliberate, so a reader cannot mistake it for a trace. Not usable for incremental verification, because it re-derives from the same inputs the certificate already states. |
| `counterexample` | Concrete assignment to state variables that violates the VC, if `status` is `unsat`. Null otherwise. |
| `merkle_root` | Merkle tree root over the obligation digests in this proof. **Attestable** — see [What the Merkle root does and does not prove](#what-the-merkle-root-does-and-does-not-prove). Not a tamper-evident seal. |

## Verification Condition Kinds

| Kind | Description |
|------|-------------|
| `invariant_preservation` | Does the invariant hold in all reachable states? |
| `invariant_initiation` | Does the invariant hold in the initial state? |
| `derived_rule_sanity` | Is the derived rule logically entailed by its premises? |
| `temporal_liveness` | Does an `eventually` property eventually occur? |
| `temporal_safety` | Does an `always` property hold forever? |
| `unit_consistency` | Are all operations dimensionally consistent? |
| `domain_membership` | Can any variable leave its declared domain? |

## Merkle Tree Construction

The Merkle root provides a compact summary of the entire proof:

```
leaf_i = SHA-256( obligation_id || trace_digest )
parent = SHA-256( left || right )
root   = reduce(leaves, parent_fn)
```

If **any** obligation changes, the `merkle_root` changes. This is true as of [guardc#1](https://github.com/SuperInstance/guardc/pull/1), and for a specific reason: `trace_digest` is a length-prefixed SHA-256 over `obligation_id`, `kind`, `name`, `source_span`, `logic` and `formula`, so changing any of them — including re-deriving the VC with a different solver or different bounds — changes the leaf, and so changes the root. The length prefixes are what stop two different field splits from colliding.

It was **not** true before that fix. `trace_digest` was then the digest of the literal bytes `placeholder` — a constant — so every obligation in every certificate ever emitted hashed to the same leaf, two genuinely different constraints produced the same root, and the root detected nothing at all. **If you are holding an older certificate, none of the above holds for it.**

## What the Merkle root does and does not prove

Following `witness-chain/1` (`SuperInstance/witness-spec` SPEC.md), a verdict must **name its linkage class** and must **count its tamper-evidence legs** before it is allowed to use the word.

**Linkage class: `chain`.** The obligations are not independent rows each carrying a checksum of its own payload; they are jointly committed by the Merkle root, and a verifier replaying the tree reproduces every linkage. That is what separates this from a `row-checksum` log, where deleting rows is invisible.

**Legs held:**

| # | leg | held? |
|---|---|---|
| 1 | chain re-derives — a verifier recomputes the root from the leaves and it matches | **yes** |
| 2 | head signed — the root carries a signature from a key the compiler does not hold | **no** |
| 3 | head published out of band — the root lives somewhere the writer does not control | **no** |

One leg out of three. Per the house table that is exactly **attestable** — "the chain re-derives". It is **not** `attested` (needs 1+2), and it is **not** `tamper-evident`, which is only earned at 1+2+3.

**What the root cannot catch.** Leg 3 is the whole of the difference, and it is the leg nobody in the fleet has built:

- **Tail truncation is invisible.** Drop the last obligation and re-reduce the tree; the remaining root is a perfectly valid root. A truncated certificate is a shorter valid certificate.
- **A whole-certificate rewrite is invisible.** Recompile with a changed constraint, and the compiler recomputes `trace_digest`, the leaves, and the root, all consistently. Every hash agrees. Detecting this needs a head someone else holds, not a hash the writer also computes.
- **The compiler is inside the boundary.** The root commits to what `guardc` said, not to what is true.

`witness-spec`'s own census found no `witness-heads/` directory and no committed `.sig` artifact anywhere in the fleet. Until a signed head is published out of band, the correct word for a GUARD certificate root is **attestable**.

## Counterexample Format

When a property fails, the certificate includes a concrete counterexample that a safety engineer can inspect:

```json
"counterexample": {
  "model": {
    "throttle_command": 1.07,
    "engine_enabled": false
  },
  "time_step": 0,
  "violated_invariant": "ThrottleMustNotExceedMax",
  "explanation": "At time step 0, throttle_command = 1.07 (107 %), which exceeds the maximum of 100 %."
}
```

## Trusted Computing Base (TCB)

A verifier relies on five things:

1. **SHA-256** implementation (or Blake3, if selected).
2. **SMT solver** (Z3, cvc5, or Bitwuzla) for re-checking VCs.
3. **FLUX VM** (≈ 300 lines) for executing the bytecode trace.
4. **Source parser** (≈ 200 lines) for confirming source-to-bytecode mapping.
5. **`guardc` itself** — which this document previously denied. See below.

### The compiler **is** in the TCB

The previous version of this document claimed the opposite: that the GUARD compiler is not in the TCB, and that a malicious or buggy compiler cannot forge a valid certificate "because the verifier re-runs the proof obligations independently".

Both halves are false today, and the second half was false even before the fix:

- **The verifier does not re-run anything.** Re-checking obligations requires an SMT solver. `guardc` has no solver dependency, and a certificate carries a `vc.status` of `unknown`, which is `guardc` saying it never solved the VC. There is nothing for a verifier to re-run.
- **The digests cannot catch a dishonest compiler, because the compiler computes them.** `trace_digest` and `merkle_root` are produced by `guardc` from data `guardc` supplies. A compiler that emits a wrong obligation and then hashes that wrong obligation produces a certificate whose every hash verifies. Before [guardc#1](https://github.com/SuperInstance/guardc/pull/1) this was worse than useless: every `trace_digest` was the constant `sha256("placeholder")`, so the field did not distinguish one obligation from another at all.

So the honest TCB is: SHA-256, an SMT solver, the FLUX VM, the source parser, **and `guardc` itself**. A verifier can prove a certificate is internally consistent. It cannot prove the compiler told the truth.

## What is NOT claimed

Stated plainly, so that nothing below has to be read charitably:

- **No execution happened.** `guardc` compiles GUARD to FLUX bytecode. It does not run the FLUX VM, so there is no execution trace and nothing was sealed against one. This is why `proofs[].status` is `not_sealed` and not `verified`.
- **Nothing was proved.** No solver runs. `vc.status` is `unknown` on every obligation. `guardc` emits verification *conditions*; it does not discharge them.
- **No property was shown to hold.** A certificate from this compiler is evidence that a module compiled and that its obligations were emitted in a well-defined form. It is not evidence that the module is safe.
- **The digests are not tamper-evidence.** They are *attestable*. See [above](#what-the-merkle-root-does-and-does-not-prove).
- **The compiler is in the TCB.** See [above](#trusted-computing-base-tcb).
- **`counterexample` is always `null`.** It is populated by no code path in `guardc`. The format below is the format it will take when a solver is integrated; today it is only ever `null`.

## Status of the vendored `guardc` copy

This repository contains a vendored copy of the compiler at [`../guardc/`](../guardc/). Its current status, so that nobody has to guess:

- It is **a pinned snapshot, not a second build.** `guardc/src/proof.rs` here is byte-identical to `SuperInstance/guardc` `master` @ `e505d3d`, git blob `343960265fbc5ada9e3b64d29f65e373e4731517`. It has not drifted.
- It is **not in this repository's Cargo workspace.** `guardc` is not listed in the root `Cargo.toml`'s `members` and not in its `exclude`, and the vendored manifest has no `[workspace]` table, so `cargo check` inside `../guardc` fails with *"current package believes it's in a workspace when it's not"*. Adding an empty `[workspace]` table to `../guardc/Cargo.toml` does make it compile, which is how its buildability was verified — but as it stands it does not build.
- **No CI job builds it.** `../guardc/.github/workflows/ci.yml` exists in the vendored tree but is inert here; the repository's own CI does not reference it.
- **Therefore edits to it here reach nothing.** Change the compiler in `SuperInstance/guardc` and re-pin deliberately, or wire it into the workspace and into CI. Do not patch it here and expect a behaviour change.

See [`../guardc/README.md`](../guardc/README.md) for the snapshot's provenance.

## Certificate Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  GUARD Source │ ──► │   guardc     │ ──► │ FLUX Bytecode│
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Prover     │  (SMT + symbolic exec)
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Certificate │  (.guardcert)
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Verifier   │  (auditor / CI)
                     └──────────────┘
```
