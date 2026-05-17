# README Audit — spectral-conservation

**Date:** 2026-05-17 | **Reviewer:** Forgemaster ⚒️

## Scores

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| WHAT it is | ✅ | "Spectral first integral I(x) = γ(x) + H(x) conservation tracker" — clear |
| WHY you'd use it | ❌ | Assumes reader knows why spectral conservation matters. No "use this when…" |
| HOW to install | ❌ | No `cargo add` or Cargo.toml snippet anywhere |
| HOW to use (code) | ✅ | Good Quick Start with working Rust code, shows core functions + monitor |
| Links / context | ❌ | No links to paper, related repos (flux-lucid depends on this), or ecosystem |

**Total: 2.5/5**

## Issues

1. **No install command.** A Rust crate README must have `cargo add spectral-conservation` or a `[dependencies]` block.
2. **No "Why" section.** Reader encounters "spectral first integral" with zero motivation. Needs a 2-sentence "Use this when you need to verify that coupled dynamics haven't drifted into pathological regimes" type intro.
3. **No ecosystem links.** This crate feeds into `flux-lucid` and the broader PLATO fleet. Should link to SuperInstance org and related crates.
4. **Reference section** mentions "Draft v4, 5130 words" but no link to the paper in `papers/` or anywhere.

## Action Taken

- ✅ README rewritten with install, why, and links sections added
