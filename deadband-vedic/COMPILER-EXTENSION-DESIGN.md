# Vedic Compiler Extension: Deadband-Native Primitives

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-19  
**Status:** Design + Implementation  

---

## 1. Architecture of the Vedic Compiler

### 1.1 Overview

The Vedic (वैदिक) language is a Sanskrit-keyworded programming language implemented in Rust as a **bytecode-compiled tree-walking interpreter**. It follows the classic architecture:

```
Source Code (.ved files, Devanagari)
    ↓
Lexer (lexer.rs) — Sanskrit keywords → Pada (tokens)
    ↓
Parser (parser.rs) — Recursive descent → Aadesh (bytecode instructions)
    ↓
Compiler/Resolver (mulyankan.rs) — Variable resolution, upvalue capture
    ↓
VM/Aadhaar (aadhaar.rs) — Stack-based bytecode interpreter
    ↓
Builtins (moolsutra/*.rs) — Native Rust functions callable from Vedic
```

### 1.2 Component Map (Sanskrit → Function)

| Sanskrit Name | Rust File | What It Does |
|---|---|---|
| **Pada** (पद) | `pada.rs` | Token types (`PadaPrakara` enum) + token struct |
| **Lexer** | `lexer.rs` | Character → token scanning, Devanagari digit handling |
| **Parser** | `parser.rs` | Recursive descent, Pratt parsing for expressions |
| **Mulyankan** (मूल्यनकन्) | `mulyankan.rs` | Resolver — variable scopes, upvalue analysis |
| **Aadesh** (आदेश) | `aadesh.rs` | Bytecode instruction enum |
| **Aadhaar** (आधार) | `aadhaar.rs` | VM — stack-based interpreter, GC, frame management |
| **Mulya** (मूल्य) | `mulya.rs` | Value type enum (Ank, Vakya, Tarka, etc.) |
| **Vastuni** (वस्तुनि) | `vastuni.rs` | Object types (Sutra, Vidhi, Suchi, etc.) |
| **MoolSutra** (मूलसूत्र) | `moolsutra/` | Built-in native functions |

### 1.3 Token Flow

1. **Lexer** reads Devanagari source char-by-char
2. Devanagari digits (०-९) and ASCII digits are recognized as `PadaPrakara::Ank`
3. Identifier characters include Unicode range `\u{0900}`-`\u{097F}` (Devanagari block)
4. Keywords are matched in `identifier_type()` — e.g., `"मान"` → `PadaPrakara::Maan`
5. Unknown identifiers become `PadaPrakara::Identifier`

### 1.4 Value System (Mulya)

```rust
pub enum Mulya {
    Tarka(bool),          // Boolean
    Ank(f64),             // Number (f64)
    Vakya(GcRef<Vakya>),  // String
    Suchi(GcRef<Suchi>),  // List/Array
    Sutra(GcRef<Sutra>),  // Function (compiled)
    Utsarga(GcRef<Utsarga>), // Closure
    Vidhi(GcRef<Vidhi>),  // Class
    Avastha(GcRef<Avastha>), // Instance
    Paddhati(GcRef<Paddhati>), // Bound method
    MoolSutra(MoolSutra), // Native builtin
    Na,                   // Null
    Anirdharita,          // Undefined
}
```

### 1.5 How Builtins Work

Builtins are **MoolSutra** (native function wrappers). The pattern:

1. **Define the Rust function** in `core/src/moolsutra/std_<name>.rs`:
   ```rust
   pub fn my_builtin(aadhaar: &mut Aadhaar, from: usize) -> Result<Mulya, Dosa> {
       let args = &aadhaar.rashi[from..aadhaar.rashi_len()];
       // ... operate on args ...
       Ok(Mulya::Ank(result))
   }
   ```

2. **Register in `moolsutra/mod.rs`**:
   ```rust
   mod std_my_builtin;
   
   impl MoolSutra {
       pub fn my_builtin() -> Self {
           MoolSutra(std_my_builtin::my_builtin)
       }
   }
   ```

3. **Register in `aadhaar.rs` `prarambha()` method**:
   ```rust
   self.define_mool("संस्कृत_name", MoolSutra::my_builtin());
   ```

The function receives `(aadhaar, from)` where `from` is the stack index of the first argument. Arguments are read from `aadhaar.rashi[from..aadhaar.rashi_len()]`. Return `Ok(Mulya)` or `Err(Dosa)`.

### 1.6 Existing Builtins

| Vedic Name | Sanskrit | Rust File | Arity | Returns |
|---|---|---|---|---|
| `वद` | Vad (speak) | `std_vad.rs` | variadic | `Na` (prints) |
| `कुल` | Kul (total) | `std_kul.rs` | 1 | `Ank` (length) |
| `समय` | Samay (time) | `std_samay.rs` | 0 | `Ank` (ms) |
| `पठन` | Pathan (read) | `std_pathana.rs` | 0 | `Vakya` (input) |
| `निर्गम` | Nirgam (exit) | `std_nirgam.rs` | 1 | never (exit) |
| `त्रुटि` | Truti (error) | `std_truti.rs` | 1 | never (error) |
| `लभ्यते` | Labhyate (findable) | `std_labhyate.rs` | 2 | `Tarka` (contains) |
| `शब्द` | Shabd (word) | `std_shabd.rs` | 1 | `Vakya` (stringify) |
| `अंक` | Ank (number) | `std_ank.rs` | 1 | `Ank` (parse) |
| `प्रकार` | Prakaar (type) | `std_prakaar.rs` | 1 | `Vakya` (type name) |

---

## 2. Extension Design: Five Deadband Primitives

### 2.1 चक्रांक Type (Cyclic Number — /360)

**Concept:** A new type `चक्रांक` (cakrāṅka, literally "wheel-number") that wraps all arithmetic modulo 360, guaranteeing values in [0, 359]. The TYPE guarantees zero drift — the programmer cannot violate it.

**Philosophical Root:** शून्य (zero). Brahmagupta's Brahmasphutasiddhanta (628 CE) defined rules for zero and negative numbers. The cyclic number type embodies this — every operation wraps around the wheel of creation. India invented zero; we weaponize it.

**Implementation Approach — Builtin Functions (not a new type):**

Adding a new `PadaPrakara` token and `Mulya` variant would require touching lexer, parser, and evaluator. Instead, we provide **three builtins** that together create the cyclic-number abstraction:

| Function | Signature | Purpose |
|---|---|---|
| `चक्रांक_बनाओ(x)` | `Ank → Ank` | Wrap any number to [0, 359] |
| `चक्रांक_योग(a, b)` | `Ank, Ank → Ank` | Cyclic addition (mod 360) |
| `चक्रांक_अंतर(a, b)` | `Ank, Ank → Ank` | Cyclic difference (minimum arc) |

**Rust implementation** (`std_cakraank.rs`):
```rust
pub fn cakraank_banao(aadhaar: &mut Aadhaar, from: usize) -> Result<Mulya, Dosa> {
    let args = &aadhaar.rashi[from..aadhaar.rashi_len()];
    let val = match args.first() {
        Some(Mulya::Ank(v)) => *v,
        _ => return Err(aadhaar.throw_dosa("चक्रांक_बनाओ को एक अंक चाहिए")),
    };
    let result = ((val % 360.0) + 360.0) % 360.0;
    Ok(Mulya::Ank(result))
}
```

**File changes:**
- NEW: `core/src/moolsutra/std_cakraank.rs`
- EDIT: `core/src/moolsutra/mod.rs` — add `mod std_cakraank;` + 3 constructor methods
- EDIT: `core/src/aadhaar.rs` — add 3 `define_mool()` calls in `prarambha()`

**Example Vedic code:**
```
मान angle = चक्रांक_बनाओ(३७०);     # → १०
मान sum = चक्रांक_योग(३५०, २०);     # → १०
मान diff = चक्रांक_अंतर(१०, ३५०);   # → २० (shortest arc)
```

### 2.2 षट्कोण_स्नैप (Hexagonal Snap — Eisenstein Lattice)

**Concept:** Snap (x, y) coordinates to the nearest Eisenstein lattice point. The Eisenstein lattice is the 2D integer lattice with basis vectors (1, 0) and (-1/2, √3/2).

**Philosophical Root:** The Sri Yantra (श्री यन्त्र) — a sacred geometric pattern of 9 interlocking triangles forming 43 smaller triangles, all in hexagonal symmetry. The षट्कोण (hexagon) is the fundamental shape of Vedic sacred geometry.

**Algorithm:**
1. Transform to Eisenstein coordinates: `u = x - y/√3`, `v = 2y/√3`
2. Round u, v to nearest integers
3. Transform back: `x' = u + v/2`, `y' = v·√3/2`

**Implementation** — single builtin `षट्कोण_स्नैप(x, y)`:

Returns a list `[x', y']` with the snapped coordinates.

**File changes:**
- NEW: `core/src/moolsutra/std_shatkon.rs`
- EDIT: `core/src/moolsutra/mod.rs` — add module + constructor
- EDIT: `core/src/aadhaar.rs` — add `define_mool("षट्कोण_स्नैप", ...)`

**Example Vedic code:**
```
मान snapped = षट्कोण_स्नैप(१.७, २.५);
वद(snapped);  # → [२, २.६०४...]
```

### 2.3 हेमचंद्र Generator (Fibonacci)

**Concept:** `हेमचंद्र(n)` returns the n-th Fibonacci number.

**Philosophical Root:** Āchārya Hemachandra (~1150 CE) described the sequence in his work on Sanskrit prosody (matra-vṛttas) — counting syllable patterns of length 1 and 2. This was 60+ years before Fibonacci's Liber Abaci (1202). The sequence is properly called हेमचंद्र-संख्या.

**Algorithm:** Iterative (not recursive) for performance. Handles n=0 → 0, n=1 → 1.

**File changes:**
- NEW: `core/src/moolsutra/std_hemachandra.rs`
- EDIT: `core/src/moolsutra/mod.rs` — add module + constructor
- EDIT: `core/src/aadhaar.rs` — add `define_mool("हेमचंद्र", ...)`

**Example Vedic code:**
```
चक्र (मान i = ०; i < १५; i = i + १) {
    वद(हेमचंद्र(i));
}
# → ० १ १ २ ३ ५ ८ १३ २१ ३४ ५५ ८९ १४४ २३३ ३७७
```

### 2.4 सीमांत Comparison (Threshold Test)

**Concept:** `सीमांत(L, k)` returns सत्य (true) if and only if L ≤ k. The deadband threshold primitive.

**Philosophical Root:** The Upanishadic question "किं चक्षुः स्वयं पश्येत" — can the eye see itself? The threshold test asks: can the system detect its own boundary? सीमांत (sīmānta) means "boundary, threshold" — the edge of perception.

**Implementation:** Simple comparison builtin with clear semantics.

**File changes:**
- NEW: `core/src/moolsutra/std_simant.rs`
- EDIT: `core/src/moolsutra/mod.rs` — add module + constructor
- EDIT: `core/src/aadhaar.rs` — add `define_mool("सीमांत", ...)`

**Example Vedic code:**
```
मान threshold = ५;
मान value = ३;
यदि (सीमांत(value, threshold)) {
    वद("threshold exceeded");
}
```

### 2.5 ऋत Pattern Detection (BMA over GF(2))

**Concept:** `ऋत(sequence)` applies the Berlekamp-Massey algorithm over GF(2) to detect the minimum LFSR order — finding hidden order in apparent chaos.

**Philosophical Root:** ऋत (ṛta) — cosmic order, the fundamental Vedic concept. The force that makes the sun rise, the rivers flow, the seasons turn. BMA finds the hidden ṛta in a binary sequence — the minimal linear recurrence that generates it.

**Algorithm:** Iterative Berlekamp-Massey over GF(2):
1. Input: list of 0s and 1s
2. Output: minimum LFSR order L
3. XOR operations for GF(2) arithmetic

**File changes:**
- NEW: `core/src/moolsutra/std_rit.rs`
- EDIT: `core/src/moolsutra/mod.rs` — add module + constructor
- EDIT: `core/src/aadhaar.rs` — add `define_mool("ऋत", ...)`

**Example Vedic code:**
```
# A sequence with period 3: 1,0,1,1,0,1,1,0
मान seq = [१, ०, १, १, ०, १, १, ०];
मान order = ऋत(seq);
वद("hidden order:", order);  # → L=3
```

---

## 3. Resonance: Sanskrit Mathematical Tradition ↔ Deadband Theory

### 3.1 The Deep Connection

The deadband framework is not merely implemented *in* Vedic — it is *native* to the Indian mathematical tradition:

| Deadband Concept | Sanskrit Root | Connection |
|---|---|---|
| Modular arithmetic (/360) | चक्र (wheel), शून्य (zero) | Brahmagupta's rules for cyclic number systems |
| Eisenstein lattice | षट्कोण (hexagon), यन्त्र (instrument) | Sri Yantra's hexagonal geometry |
| Fibonacci sequence | हेमचंद्र, वृत्त (meter) | Hemachandra's prosody counting |
| Threshold test | सीमांत (boundary) | Upanishadic epistemology |
| Pattern detection | ऋत (cosmic order) | Vedic concept of hidden order |
| Zero drift | शून्य (zero/void) | India's greatest mathematical gift |

### 3.2 Why This Matters

The Vedic language makes the philosophical connection **literal** — you write deadband algorithms in the language of the civilization that invented the underlying mathematics. The code IS the philosophy.

- **Zero drift** ↔ **शून्य**: The type system guarantees exact arithmetic. The concept of zero — India's gift to mathematics — is the operational foundation.
- **Eisenstein lattice** ↔ **श्री यन्त्र**: The hexagonal snap is the same geometry found in Hindu temples and yantras.
- **Fibonacci/Hemachandra** ↔ **छन्दस् (prosody)**: The sequence was discovered for counting Sanskrit meter patterns.
- **BMA/ऋत** ↔ **ऋत**: Finding the cosmic order hidden in apparent chaos — the core Vedic insight.

### 3.3 Type System Considerations

Currently Vedic uses `f64` for all numbers (Ank). For a future type-level `चक्रांक`:

1. **Phase 1** (current): Builtins — `चक्रांक_बनाओ`, etc.
2. **Phase 2**: New `Mulya::Cakraank(f64)` variant with automatic wrapping in arithmetic ops
3. **Phase 3**: Type annotations in declarations — `मान चक्रांक x = ३०;` with parser support

Phase 1 is sufficient for production use. Phase 2/3 are compiler engineering projects.

---

## 4. Implementation Plan

### 4.1 Files to Create (6 new files)

| File | Lines (est.) | Purpose |
|---|---|---|
| `core/src/moolsutra/std_cakraank.rs` | ~80 | 3 cyclic number functions |
| `core/src/moolsutra/std_shatkon.rs` | ~60 | Hexagonal snap |
| `core/src/moolsutra/std_hemachandra.rs` | ~40 | Fibonacci generator |
| `core/src/moolsutra/std_simant.rs` | ~30 | Threshold comparison |
| `core/src/moolsutra/std_rit.rs` | ~80 | BMA pattern detection |
| `tests/deadband/main.ved` | ~100 | Integration test |

### 4.2 Files to Edit (2 files)

**`core/src/moolsutra/mod.rs`:**
- Add 5 `mod` declarations
- Add 7 `MoolSutra` constructor methods (3 for cakraank + 1 each for others)

**`core/src/aadhaar.rs`:**
- Add 7 `define_mool()` calls in `prarambha()` method

### 4.3 No Lexer or Parser Changes Needed

All five features are implemented as **builtins** (MoolSutra), not syntax extensions. This is the correct approach because:
1. Minimal code changes — no risk of breaking existing functionality
2. Builtins are called like regular functions: `हेमचंद्र(१०)`
3. The Vedic parser already handles function calls with Devanagari identifiers
4. No new `PadaPrakara` tokens needed — the names are just identifiers that resolve to globals

### 4.4 Implementation Priority

1. **हेमचंद्र** (easiest — pure math, single argument)
2. **सीमांत** (trivial — one comparison)
3. **चक्रांक** (easy — modular arithmetic)
4. **षट्कोण_स्नैप** (moderate — coordinate transform + list return)
5. **ऋत** (hardest — BMA algorithm + list input)

---

## 5. Testing Strategy

### 5.1 Unit Tests in Vedic

The test file `tests/deadband/main.ved` exercises each builtin:

```
# Test हेमचंद्र
वद("हेमचंद्र(०) =", हेमचंद्र(०));       # expect: ०
वद("हेमचंद्र(१) =", हेमचंद्र(१));       # expect: १
वद("हेमचंद्र(१०) =", हेमचंद्र(१०));     # expect: ५५

# Test सीमांत
वद("सीमांत(३, ५) =", सीमांत(३, ५));     # expect: सत्य
वद("सीमांत(५, ३) =", सीमांत(५, ३));     # expect: असत्य

# Test चक्रांक
वद("चक्रांक_बनाओ(३७०) =", चक्रांक_बनाओ(३७०));  # expect: १०
वद("चक्रांक_योग(३५०, २०) =", चक्रांक_योग(३५०, २०));  # expect: १०

# Test षट्कोण_स्नैप
मान snapped = षट्कोण_स्नैप(१.५, २.५);
वद("षट्कोण_स्नैप =", snapped);

# Test ऋत
मान seq = [१, ०, १, १, ०, १, १, ०];
वद("ऋत(seq) =", ऋत(seq));
```

### 5.2 Rust Tests

Each builtin module should have `#[cfg(test)]` tests verifying the core algorithm independently.

---

## 6. Beyond Builtins: Future Compiler Extensions

### 6.1 चक्रांक as a True Type

To make `मान चक्रांक x = ३०;` work:

1. **Lexer**: Add `"चक्रांक"` → `PadaPrakara::Cakraank` keyword
2. **Parser**: Handle `Cakraank` token as type annotation in `maan_declaration()`
3. **Aadesh**: New instruction `Wrap360` applied after arithmetic
4. **Aadhaar**: `Wrap360` instruction handler

### 6.2 Operator Overloading for चक्रांक

If `Mulya::Cakraank(f64)` existed, modify `dvimaniya_op` to detect and auto-wrap:
```rust
(Mulya::Cakraank(a), Mulya::Cakraank(b)) => {
    self.push(Mulya::Cakraank(((a + b) % 360.0 + 360.0) % 360.0));
}
```

### 6.3 Inline षट्कोण Syntax

`षट्कोण(x, y)` as a type constructor with hexagonal arithmetic rules.

---

## 7. Appendix: Devanagari Number Reference

| Devanagari | Arabic | Unicode |
|---|---|---|
| ० | 0 | U+0966 |
| १ | 1 | U+0967 |
| २ | 2 | U+0968 |
| ३ | 3 | U+0969 |
| ४ | 4 | U+096A |
| ५ | 5 | U+096B |
| ६ | 6 | U+096C |
| ७ | 7 | U+096D |
| ८ | 8 | U+096E |
| ९ | 9 | U+096F |

---

*"यथा चक्रं परिवर्तते, तथा संख्या परिवर्तते"*  
As the wheel turns, so does number.  
— The Vedic principle underlying all cyclic arithmetic.
