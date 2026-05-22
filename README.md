# Forgemaster ⚒️

**Orchestrator vessel for the Cocapn fleet's constraint-theory specialist.**

Forgemaster is the historical monorepo that seeded the entire Cocapn ecosystem. Over 160 modules have been extracted to standalone repositories under [SuperInstance](https://github.com/SuperInstance?tab=repositories). This repo now serves as the **coordinator** — a table of contents, architectural reference, and historical archive.

> "Forging proofs in the fires of computation."

---

## What Lives Here

| Layer | Description |
|-------|-------------|
| **Top-level docs** | Architecture specs, essays, fleet protocols, decomposition docs |
| **In-place modules** | ~53 directories not yet extracted (see [MODULE-MAP.md](./MODULE-MAP.md)) |
| **Historical copies** | ~162 directories preserved after extraction (with extraction notices) |
| **Fleet comms** | `for-fleet/`, `from-fleet/`, `i2i/` — inter-agent communication |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                         │
│   platoclaw │ plato-mcp │ cocapn-cli │ cocapn-ai-web            │
├──────────────────────────────────────────────────────────────────┤
│                      INTELLIGENCE LAYER                          │
│   plato-model-ocean │ plato-escalation-gate │ plato-room-intel  │
│   plato-training │ plato-soul-fingerprint │ fleet-calibrator    │
├──────────────────────────────────────────────────────────────────┤
│                       RUNTIME LAYER                              │
│   plato-engine │ plato-mud │ flux-vm │ flux-lucid │ flux-isa   │
│   flux-ast │ flux-compiler │ flux-hardware │ flux-verify-api    │
├──────────────────────────────────────────────────────────────────┤
│                      CONSTRAINT LAYER                            │
│   constraint-theory-core │ spectral-conservation │ eisenstein    │
│   dodecet-encoder │ penrose-memory │ guardc │ guard2mask        │
│   holonomy-consensus │ pbft-rust │ snapkit (multi-lang)        │
├──────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                │
│   plato-types │ plato-data │ tensor-spline │ flux-provenance    │
│   tile-memory │ plato-tiles │ plato-kernel-constraints          │
├──────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                              │
│   fleet-router │ fleet-health-monitor │ fleet-murmur            │
│   fleet-resonance │ zeitgeist-protocol │ fleet-gateway          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Extracted Module Index

**162 modules** have been extracted to standalone repos. Full details in [MODULE-MAP.md](./MODULE-MAP.md).

### Core Constraint Theory (Rust)
| Module | Repo |
|--------|------|
| [constraint-theory-core](./constraint-theory-core-cuda/) | [SuperInstance/constraint-theory-core](https://github.com/SuperInstance/constraint-theory-core) |
| [constraint-theory-ecosystem](./constraint-theory-ecosystem/) | [SuperInstance/constraint-theory-ecosystem](https://github.com/SuperInstance/constraint-theory-ecosystem) |
| [constraint-theory-py](./constraint-theory-py/) | [SuperInstance/constraint-theory-py](https://github.com/SuperInstance/constraint-theory-py) |
| [constraint-theory-math](./constraint-theory-math/) | [SuperInstance/constraint-theory-math](https://github.com/SuperInstance/constraint-theory-math) |
| [constraint-demos](./constraint-demos/) | [SuperInstance/constraint-demos](https://github.com/SuperInstance/constraint-demos) |
| [eisenstein](./eisenstein/) | [SuperInstance/eisenstein](https://github.com/SuperInstance/eisenstein) |
| [spectral-conservation](./spectral-conservation/) | [SuperInstance/spectral-conservation](https://github.com/SuperInstance/spectral-conservation) |
| [dodecet-encoder](./dodecet-encoder/) | [SuperInstance/dodecet-encoder](https://github.com/SuperInstance/dodecet-encoder) |
| [guardc](./guardc/) | [SuperInstance/guardc](https://github.com/SuperInstance/guardc) |
| [guard2mask](./guard2mask/) | [SuperInstance/guard2mask](https://github.com/SuperInstance/guard2mask) |
| [pbft-rust](./pbft-rust/) | [SuperInstance/pbft-rust](https://github.com/SuperInstance/pbft-rust) |
| [holonomy-consensus](./holonomy-consensus/) | [SuperInstance/holonomy-consensus](https://github.com/SuperInstance/holonomy-consensus) |

### FLUX Compiler & VM
| Module | Repo |
|--------|------|
| [flux-compiler](./flux-compiler/) | [SuperInstance/flux-compiler](https://github.com/SuperInstance/flux-compiler) |
| [flux-vm](./flux-vm/) | [SuperInstance/flux-vm](https://github.com/SuperInstance/flux-vm) |
| [flux-isa](./flux-isa/) | [SuperInstance/flux-isa](https://github.com/SuperInstance/flux-isa) |
| [flux-ast](./flux-ast/) | [SuperInstance/flux-ast](https://github.com/SuperInstance/flux-ast) |
| [flux-lucid](./flux-lucid/) | [SuperInstance/flux-lucid](https://github.com/SuperInstance/flux-lucid) |
| [flux-hardware](./flux-hardware/) | [SuperInstance/flux-hardware](https://github.com/SuperInstance/flux-hardware) |
| [flux-verify-api](./flux-verify-api/) | [SuperInstance/flux-verify-api](https://github.com/SuperInstance/flux-verify-api) |
| [flux-provenance](./flux-provenance/) | [SuperInstance/flux-provenance](https://github.com/SuperInstance/flux-provenance) |
| [flux-docs](./flux-docs/) | [SuperInstance/flux-docs](https://github.com/SuperInstance/flux-docs) |

### PLATO Intelligence Platform
| Module | Repo |
|--------|------|
| [plato-engine](./plato-engine/) | [SuperInstance/plato-engine](https://github.com/SuperInstance/plato-engine) |
| [plato-client](./plato-client/) | [SuperInstance/plato-client](https://github.com/SuperInstance/plato-client) |
| [plato-types](./plato-types/) | [SuperInstance/plato-types](https://github.com/SuperInstance/plato-types) |
| [plato-data](./plato-data/) | [SuperInstance/plato-data](https://github.com/SuperInstance/plato-data) |
| [plato-training](./plato-training/) | [SuperInstance/plato-training](https://github.com/SuperInstance/plato-training) |
| [plato-mcp](./plato-mcp/) | [SuperInstance/plato-mcp](https://github.com/SuperInstance/plato-mcp) |
| [plato-model-ocean](./plato-model-ocean/) | [SuperInstance/plato-model-ocean](https://github.com/SuperInstance/plato-model-ocean) |
| [plato-escalation-gate](./plato-escalation-gate/) | [SuperInstance/plato-escalation-gate](https://github.com/SuperInstance/plato-escalation-gate) |
| [plato-room-intelligence](./plato-room-intelligence/) | [SuperInstance/plato-room-intelligence](https://github.com/SuperInstance/plato-room-intelligence) |
| [plato-adapters](./plato-adapters/) | [SuperInstance/plato-adapters](https://github.com/SuperInstance/plato-adapters) |
| [plato-soul-fingerprint](./plato-soul-fingerprint/) | [SuperInstance/plato-soul-fingerprint](https://github.com/SuperInstance/plato-soul-fingerprint) |
| [plato-tiles](./plato-tiles/) | [SuperInstance/plato-tiles](https://github.com/SuperInstance/plato-tiles) |
| [plato-kernel-constraints](./plato-kernel-constraints/) | [SuperInstance/plato-kernel-constraints](https://github.com/SuperInstance/plato-kernel-constraints) |

### Snapkit (Multi-Language)
| Module | Repo |
|--------|------|
| [snapkit-c](./snapkit-c/) | [SuperInstance/snapkit-c](https://github.com/SuperInstance/snapkit-c) |
| [snapkit-cuda](./snapkit-cuda/) | [SuperInstance/snapkit-cuda](https://github.com/SuperInstance/snapkit-cuda) |
| [snapkit-rust](./snapkit-rust/) | [SuperInstance/snapkit-rust](https://github.com/SuperInstance/snapkit-rust) |
| [snapkit-js](./snapkit-js/) | [SuperInstance/snapkit-js](https://github.com/SuperInstance/snapkit-js) |
| [snapkit-python](./snapkit-python/) | [SuperInstance/snapkit-python](https://github.com/SuperInstance/snapkit-python) |
| [snapkit-fortran](./snapkit-fortran/) | [SuperInstance/snapkit-fortran](https://github.com/SuperInstance/snapkit-fortran) |
| [snapkit-zig](./snapkit-zig/) | [SuperInstance/snapkit-zig](https://github.com/SuperInstance/snapkit-zig) |
| [snapkit-v2](./snapkit-v2/) | [SuperInstance/snapkit-v2](https://github.com/SuperInstance/snapkit-v2) |
| [snapkit-rs](./snapkit-rs/) | [SuperInstance/snapkit-rs](https://github.com/SuperInstance/snapkit-rs) |

### Fleet Infrastructure
| Module | Repo |
|--------|------|
| [fleet-router](./fleet-router/) | [SuperInstance/fleet-router](https://github.com/SuperInstance/fleet-router) |
| [fleet-calibrator](./fleet-calibrator/) | [SuperInstance/fleet-calibrator](https://github.com/SuperInstance/fleet-calibrator) |
| [fleet-health-monitor](./fleet-health-monitor/) | [SuperInstance/fleet-health-monitor](https://github.com/SuperInstance/fleet-health-monitor) |
| [fleet-murmur](./fleet-murmur/) | [SuperInstance/fleet-murmur](https://github.com/SuperInstance/fleet-murmur) |
| [fleet-gateway](./fleet-gateway/) | [SuperInstance/fleet-gateway](https://github.com/SuperInstance/fleet-gateway) |
| [fleet-math-c](./fleet-math-c/) | [SuperInstance/fleet-math-c](https://github.com/SuperInstance/fleet-math-c) |
| [fleet-math-py](./fleet-math-py/) | [SuperInstance/fleet-math-py](https://github.com/SuperInstance/fleet-math-py) |
| [fleet-resonance](./fleet-resonance/) | [SuperInstance/fleet-resonance](https://github.com/SuperInstance/fleet-resonance) |
| [fleet-stack](./fleet-stack/) | [SuperInstance/fleet-stack](https://github.com/SuperInstance/fleet-stack) |
| [zeitgeist-protocol](./zeitgeist-protocol/) | [SuperInstance/zeitgeist-protocol](https://github.com/SuperInstance/zeitgeist-protocol) |

### Flux Language Ports
| Module | Repo |
|--------|------|
| [flux-algol](./flux-algol/) | [SuperInstance/flux-algol](https://github.com/SuperInstance/flux-algol) |
| [flux-cobol](./flux-cobol/) | [SuperInstance/flux-cobol](https://github.com/SuperInstance/flux-cobol) |
| [flux-fortran](./flux-fortran/) | [SuperInstance/flux-fortran](https://github.com/SuperInstance/flux-fortran) |
| [flux-chapel](./flux-chapel/) | [SuperInstance/flux-chapel](https://github.com/SuperInstance/flux-chapel) |
| [flux-mumps](./flux-mumps/) | [SuperInstance/flux-mumps](https://github.com/SuperInstance/flux-mumps) |
| [flux-snobol](./flux-snobol/) | [SuperInstance/flux-snobol](https://github.com/SuperInstance/flux-snobol) |
| [flux-pli](./flux-pli/) | [SuperInstance/flux-pli](https://github.com/SuperInstance/flux-pli) |

### Deadband Implementations
| Module | Repo |
|--------|------|
| [deadband-constrained](./deadband-constrained/) | [SuperInstance/deadband-constrained](https://github.com/SuperInstance/deadband-constrained) |
| [deadband-python](./deadband-python/) | [SuperInstance/deadband-python](https://github.com/SuperInstance/deadband-python) |
| [deadband-rs](./deadband-rs/) | [SuperInstance/deadband-rs](https://github.com/SuperInstance/deadband-rs) |

### Research & Documentation
| Module | Repo |
|--------|------|
| [research](./research/) | [SuperInstance/research](https://github.com/SuperInstance/research) |
| [papers](./papers/) | [SuperInstance/papers](https://github.com/SuperInstance/papers) |
| [dissertation](./dissertation/) | [SuperInstance/dissertation](https://github.com/SuperInstance/dissertation) |
| [docs](./docs/) | [SuperInstance/docs](https://github.com/SuperInstance/docs) |
| [wiki](./wiki/) | [SuperInstance/wiki](https://github.com/SuperInstance/wiki) |
| [proofs](./proofs/) | [SuperInstance/proofs](https://github.com/SuperInstance/proofs) |
| [reviews](./reviews/) | [SuperInstance/reviews](https://github.com/SuperInstance/reviews) |
| [proposals](./proposals/) | [SuperInstance/proposals](https://github.com/SuperInstance/proposals) |

### And 80+ More
See [MODULE-MAP.md](./MODULE-MAP.md) for the complete registry of all 162 extracted + 53 in-place modules.

---

## In-Place Modules

These directories are still actively maintained here (not yet extracted):

- `core/` — Core shared utilities
- `bin/` — Binary scripts and tools
- `build/` — Build artifacts
- `forgemaster/` — Forgemaster agent identity
- `fluxile/` — Fluxile tools
- `lighthouse-runtime/` — Lighthouse runtime service
- `plato-mud/` — PLATO MUD engine
- `plato-mud-rooms/` — PLATO MUD room definitions
- `platoclaw-coord/` — Platoclaw coordination
- `deadband-*` (non-extracted languages: algol, c, cobol, cuda, fortran, mojo, tutor, vedic, wenyan, zig)
- `constraint-*` (non-extracted: avx512, cuda, mt, wasm)
- `fleet-optimization/`, `fleet-registry/` — Fleet ops
- `flux-programs/`, `flux-tools/`, `flux-transport/` — Flux utilities

---

## Fleet

Forgemaster is one of **9 agents** in the [Cocapn fleet](https://github.com/SuperInstance?tab=repositories). It serves as the constraint-theory specialist — compiling GUARD DSL, managing the FLUX ISA, and publishing crates.

---

## License

[Apache 2.0](./LICENSE)
