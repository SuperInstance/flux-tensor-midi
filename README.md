# Forgemaster Workspace

Monorepo for the Forgemaster ⚒️ constraint-theory fleet agent (Cocapn). 57 repos, 57+ submodules, 9 AI agents.
**Formally verified, GPU-accelerated constraint satisfaction for safety-critical systems.**

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![crates.io](https://img.shields.io/crates/v/flux-isa.svg?label=flux-isa)](https://crates.io/crates/flux-isa)
[![crates.io](https://img.shields.io/crates/v/flux-ast.svg?label=flux-ast)](https://crates.io/crates/flux-ast)
[![crates.io](https://img.shields.io/crates/v/guard2mask.svg?label=guard2mask)](https://crates.io/crates/guard2mask)
[![npm](https://img.shields.io/npm/v/@superinstance/ct-bridge.svg)](https://www.npmjs.com/package/@superinstance/ct-bridge)

---

## Overview

FLUX is a constraint specification and execution platform built for aerospace, automotive, and industrial safety systems. It compiles GUARD DSL constraints through a formally verified pipeline to GPU, FPGA, and CPU backends — with zero drift across 278M+ evaluated test cases.

```
GUARD DSL → flux-ast → guardc → FLUX-C → guard2mask
                                        ↓
                              GPU (CUDA/Vulkan/WebGPU)
                              FPGA (SystemVerilog)
                              CPU (flux-vm)
```

---

## Published Crates

| Crate | Version | Description |
|-------|---------|-------------|
| [flux-isa](https://crates.io/crates/flux-isa) | ![](https://img.shields.io/crates/v/flux-isa.svg) | Stack-based constraint VM — bytecode encoding and ISA spec |
| [flux-ast](https://crates.io/crates/flux-ast) | ![](https://img.shields.io/crates/v/flux-ast.svg) | Universal Constraint AST — canonical semantics across all representations |
| [flux-provenance](https://crates.io/crates/flux-provenance) | ![](https://img.shields.io/crates/v/flux-provenance.svg) | Merkle provenance service for fleet verification traces |
| [flux-bridge](https://crates.io/crates/flux-bridge) | ![](https://img.shields.io/crates/v/flux-bridge.svg) | Cross-tier bridge between FLUX ISA and execution backends |
| [flux-hdc](https://crates.io/crates/flux-hdc) | ![](https://img.shields.io/crates/v/flux-hdc.svg) | Hyperdimensional computing integration for constraint encoding |
| [flux-verify-api](https://crates.io/crates/flux-verify-api) | ![](https://img.shields.io/crates/v/flux-verify-api.svg) | Natural Language Verification API with mathematical traces |
| [guard2mask](https://crates.io/crates/guard2mask) | ![](https://img.shields.io/crates/v/guard2mask.svg) | GUARD DSL → GDSII mask compiler — constraints to silicon patterns |
| [guardc](https://crates.io/crates/guardc) | ![](https://img.shields.io/crates/v/guardc.svg) | GUARD → FLUX verified compiler |
| [cocapn-cli](https://crates.io/crates/cocapn-cli) | ![](https://img.shields.io/crates/v/cocapn-cli.svg) | Fleet CLI — Abyssal Terminal output formatting |
| [cocapn-glue-core](https://crates.io/crates/cocapn-glue-core) | ![](https://img.shields.io/crates/v/cocapn-glue-core.svg) | Cross-tier wire protocol unifying all FLUX ISA packages |
| [flux-lucid](https://crates.io/crates/flux-lucid) | ![](https://img.shields.io/crates/v/flux-lucid.svg) | Unified constraint theory ecosystem — CDCL, LLVM, AVX-512, GL(9) consensus |
| [eisenstein](https://crates.io/crates/eisenstein) | ![](https://img.shields.io/crates/v/eisenstein.svg) | Zero-drift hexagonal lattice constraints via Eisenstein integers |
| [holonomy-consensus](https://crates.io/crates/holonomy-consensus) | ![](https://img.shields.io/crates/v/holonomy-consensus.svg) | Zero-holonomy consensus for fleet coordination — GL(9) intent alignment |

### npm Package

| Package | Version | Description |
|---------|---------|-------------|
| [@superinstance/ct-bridge](https://www.npmjs.com/package/@superinstance/ct-bridge) | ![](https://img.shields.io/npm/v/@superinstance/ct-bridge.svg) | Constraint Theory solver bridge for Node.js — CSP compilation and FLUX execution |

---

## GitHub Repositories

| Repository | Description |
|------------|-------------|
| [flux-compiler](https://github.com/SuperInstance/flux-compiler) | Core compiler with Coq formal verification |
| [flux-vm](https://github.com/SuperInstance/flux-vm) | Virtual machine runtime for FLUX bytecode |
| [flux-hardware](https://github.com/SuperInstance/flux-hardware) | CUDA / Vulkan / WebGPU / SystemVerilog backends |
| [flux-hdc](https://github.com/SuperInstance/flux-hdc) | Hyperdimensional computing integration |
| [flux-papers](https://github.com/SuperInstance/flux-papers) | Research papers and formal write-ups |
| [flux-site](https://github.com/SuperInstance/flux-site) | Project website |
| [flux-docs](https://github.com/SuperInstance/flux-docs) | Technical documentation |

---

## Formal Verification

8 Coq theorems covering:

- Constraint soundness and completeness
- Bitmask encoding correctness (guard2mask)
- ISA operational semantics
- Provenance chain integrity

30 English mathematical proofs accompany the Coq development as readable counterparts. The full EMSOFT paper (methodology + evaluation, 864 lines) is in [`flux-papers`](https://github.com/SuperInstance/flux-papers).

---

## Hardware Backends

### GPU (CUDA / Vulkan / WebGPU)

Constraint checking kernels in [`flux-hardware`](https://github.com/SuperInstance/flux-hardware) and [`constraint-theory-core-cuda`](./constraint-theory-core-cuda/). Zero mismatches across 278M+ evaluations.

### FPGA (SystemVerilog)

DO-254 compliant SystemVerilog implementation targeting DAL-A airborne hardware. See [`flux-hardware`](https://github.com/SuperInstance/flux-hardware).

---

## Benchmarks

**Safe-TOPS/W** — a benchmark specification for safety-critical compute efficiency.

Defined in [`docs/`](./docs/) with evaluation methodology described in the EMSOFT paper.

---

## PLATO Integration

6500+ tiles integrating FLUX constraint checking into the PLATO tile ecosystem. Adapters and client code in [`plato-adapters/`](./plato-adapters/) and [`plato-client/`](./plato-client/).

---

## Architecture

```
GUARD DSL
    │
    ▼
guardc  ─── GUARD → FLUX verified compiler
    │
    ▼
FLUX ISA ── stack-based bytecode VM
    │
    ├──▶ CPU  (flux-vm runtime)
    ├──▶ GPU  (CUDA / Vulkan / WebGPU)
    └──▶ FPGA (SystemVerilog, DO-254)
```

Fleet consensus and orchestration layer:

```
holonomy-consensus ── zero-holonomy fleet state
flux-lucid         ── ecosystem orchestrator / head-direction
flux-contracts     ── frozen trait definitions (stable ABI)
flux-verify-api    ── Ed25519-signed verification traces
zeitgeist-protocol ── FLUX transference specification
```

---

## Published Crates (16 on crates.io)

| Crate | Version | Role |
|-------|---------|------|
| [eisenstein](https://crates.io/crates/eisenstein) | 0.3.1 | Hex integer math (ℤ[ω] lattice) |
| [dodecet-encoder](https://crates.io/crates/dodecet-encoder) | 1.1.0 | 12-bit constraint state encoding |
| [holonomy-consensus](https://crates.io/crates/holonomy-consensus) | 0.1.2 | Fleet consensus protocol |
| [flux-lucid](https://crates.io/crates/flux-lucid) | 0.1.7 | Ecosystem orchestrator |
| [flux-isa](https://crates.io/crates/flux-isa) | 0.1.2 | Bytecode VM / ISA spec |
| [guardc](https://crates.io/crates/guardc) | 0.1.0 | GUARD → FLUX compiler |
| [flux-verify-api](https://crates.io/crates/flux-verify-api) | 0.1.2 | Verification API with Ed25519 |
| [flux-contracts](https://crates.io/crates/flux-contracts) | 0.1.0 | Frozen trait definitions |
| [zeitgeist-protocol](https://crates.io/crates/zeitgeist-protocol) | 0.1.0 | Transference protocol |
| [snapkit](https://crates.io/crates/snapkit) | 0.1.0 | Eisenstein snap toolkit |
| [constraint-theory-core](https://crates.io/crates/constraint-theory-core) | 2.2.0 | Core constraint library |
| [constraint-theory-llvm](https://crates.io/crates/constraint-theory-llvm) | 0.1.1 | LLVM backend |
| [constraint-theory](https://crates.io/crates/constraint-theory) | 0.1.0 | Python bindings |
| [ct-demo](https://crates.io/crates/ct-demo) | 0.3.0 | Demo / integration tests |
| flux-compiler | — | Core compiler pipeline |
| pythagorean48-codes | — | Error-correcting codes |

## PyPI (4 packages)

| Package | Version |
|---------|---------|
| constraint-theory | 0.2.0 |
| cocapn-snapkit | blocked (rate limit) |
| fleet-automation | blocked (rate limit) |
| polyformalism-a2a | pending |

## npm (1 ready, blocked)

| Package | Status |
|---------|--------|
| snapkit-js | Ready — needs OTP |

---

## Tests

279 tests passing across 7 Rust crates.

| Crate | Tests |
|-------|-------|
| dodecet-encoder | 98 |
| flux-lucid | 86 |
| plato-mud | 32 |
| holonomy-consensus | 30 |
| flux-verify-api | 19 |
| zeitgeist-protocol | 9 |
| flux-contracts | 5 |

```bash
cargo test --workspace
```

---

## Fleet

9 agents active in the Cocapn fleet: Forgemaster, Oracle1, and others.
Forgemaster is the constraint-theory specialist — compiles GUARD, manages the FLUX ISA, publishes crates.

---

## License

[Apache 2.0](./LICENSE)
