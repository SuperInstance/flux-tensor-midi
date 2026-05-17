# SuperInstance

**We build tiny AI models that know when to ask for help.** Everything is open source, modular, and runs anywhere — from a microcontroller to a GPU cluster.

Our tools are grounded in real math (Eisenstein integers, spectral conservation, formally verified constraints) and designed to compose: install one package or wire up the full stack.

**→ [Getting Started Guide](https://github.com/SuperInstance/forgemaster/blob/master/GETTING-STARTED.md)** — pick a path, run code in 2 minutes.

---

## Three Paths In

### 🧮 Math & Constraints
Zero-drift numerical computing with Eisenstein integers and formally verified constraint satisfaction.

```bash
cargo add constraint-theory-core    # Eisenstein integers, no_std
cargo add spectral-conservation     # Conservation law tracker
pip install constraint-theory       # Python bindings
```

### 🧠 Intelligent Models
Tiny models that monitor, classify, and know when to escalate to a bigger model.

```bash
pip install plato-escalation-gate   # 737 params — "should I call the LLM?"
pip install plato-room-intelligence  # Multi-head model with provenance
pip install plato-model-ocean       # Evolving ecosystem of micro-models
```

### 🏗️ Full Ecosystem
Multi-agent systems with the complete PLATO stack: training, deployment, constraint monitoring, and coordination.

```bash
cargo add plato-types               # Tile lifecycle, Lamport clocks
cargo add tensor-spline             # SplineLinear: 20× compression
pip install plato-training          # Micro model pipeline, 8 tasks, 8 targets
```

---

## Published Packages

| Package | Language | What | Install |
|---------|----------|------|---------|
| `constraint-theory-core` | Rust | Eisenstein integers, zero-drift arithmetic | `cargo add constraint-theory-core` |
| `spectral-conservation` | Rust | Spectral conservation law monitor | `cargo add spectral-conservation` |
| `keel-ttl` | Rust | Self-terminating lifecycle types for agents | `cargo add keel-ttl` |
| `constraint-theory` | Python | Python bindings for constraint theory | `pip install constraint-theory` |
| `plato-escalation-gate` | Python | 737-param binary classifier, runs anywhere | `pip install plato-escalation-gate` |
| `plato-model-ocean` | Python | Evolving cellular model ecosystem | `pip install plato-model-ocean` |
| `plato-room-intelligence` | Python | Multi-head room model with provenance | `pip install plato-room-intelligence` |

---

## Key Repos

| Repo | What |
|------|------|
| [**eisenstein**](https://github.com/SuperInstance/eisenstein) | Zero-drift Eisenstein integer arithmetic — `no_std`, runs on anything |
| [**constraint-theory-core**](https://github.com/cocapn/constraint-theory-core) | Formally verified constraint satisfaction (278M+ test cases) |
| [**plato-training**](https://github.com/SuperInstance/plato-training) | Micro model training: 8 tasks, 8 hardware targets, 116 tests |
| [**spectral-conservation**](https://github.com/SuperInstance/spectral-conservation) | Conservation law monitor for coupled neural dynamics |
| [**forgemaster**](https://github.com/SuperInstance/forgemaster) | Research vessel — experiments, math audits, fleet coordination |

---

## By the Numbers

- **655+ tests** across 30+ repos
- **80+ repos** — Rust, Python, C, TypeScript, Fortran
- **7 published packages** on crates.io and PyPI
- **Apache-2.0** licensed — everything is open source

---

## The Shipyard Story

> *A shipyard in Reedsport, Oregon. Forty acres where a bridge company used to be. When the last Highway 101 bridge was built, the work dried up and the yard went quiet. Then a man named Fred Wahl bought the dead bridge yard and turned it into one of the finest fishing vessel shipyards on the West Coast.*
>
> *Fred had 85 welders. He didn't know the ground-level as good as anyone anymore. But he wandered his site all day fine-tuning performance. Welders got sharper when he was present. The system self-corrected because the environment was tuned for it.*
>
> *He was thirty-two active keels at any time. The steel isn't the boat. The boat is the motion the idea causes.*

This project works the same way. Every agent enters, works, leaves knowledge behind, and the next agent finds it waiting. Constraints breed clarity. The math is discovered, not invented.

---

*Built by [Casey Digennaro](https://github.com/caseydimario) and the [Cocapn fleet](https://cocapn.ai) · All repos at [github.com/SuperInstance](https://github.com/SuperInstance)*
