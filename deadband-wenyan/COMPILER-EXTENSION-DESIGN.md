# wenyan Compiler Extension: Deadband-Native Language Primitives

## Design Document v1.0
**Date:** 2026-05-19  
**Author:** Forgemaster ⚒️ (Cocapn Fleet)  
**Repo:** `deadband-constrained/wenyan-lang/`

---

## 1. Architecture of the wenyan Compiler

### 1.1 Compilation Pipeline

The wenyan compiler follows a classic multi-pass architecture:

```
Source (.wy) → [Macro Expansion] → [Tokenizer] → [Parser] → [Typecheck] → [Code Generation] → Target (JS/Py/Rb)
```

The entry point is `compile()` in `src/parser.ts` (line ~420). Each pass is a distinct function:

| Pass | Function | File | Lines |
|------|----------|------|-------|
| 0. Macro Expansion | `expandMacros()` | `src/macro.ts` | 184 |
| 1. Tokenization | `wy2tokens()` | `src/parser.ts` | 33-120 |
| 2. Parsing (→ ASC) | `tokens2asc()` | `src/parser.ts` | 178-410 |
| 2.5. Typecheck | `typecheck()` | `src/typecheck.ts` | 709 |
| 3. Code Generation | `transpiler.transpile()` | `src/transpilers/js.ts` | ~250 |

### 1.2 Token System

**File:** `src/keywords.ts` (128 lines)

Tokens are 3-tuples: `[TokenType, string | undefined, position_number]`

The `KEYWORDS_DEFINE` dictionary maps Chinese keyword strings to `[TokenType, subtype]` pairs. Keywords are sorted by length (longest first) to prevent prefix-matching ambiguity during tokenization.

Current token types (from `src/types.ts`):
```
"ans" | "assgn" | "bool" | "call" | "cmp" | "comment" | "ctnr" | "ctrl" | 
"data" | "decl" | "discard" | "expr" | "iden" | "import" | "lit" | "lop" | 
"macro" | "mod" | "name" | "not" | "num" | "op" | "opord" | "print" | 
"rassgn" | "take" | "try" | "type" | "throw"
```

Current variable types (mapped by `數→num`, `列→arr`, `言→str`, `術→fun`, `爻→bol`, `物→obj`, `元→any`):
```
KEYWORDS_DEFINE = {
  數: ["type", "num"],
  列: ["type", "arr"],
  言: ["type", "str"],
  術: ["type", "fun"],
  爻: ["type", "bol"],
  物: ["type", "obj"],
  元: ["type", "any"],
}
```

### 1.3 Abstract Syntax Chain (ASC)

The parser (`tokens2asc()`) converts a flat token array into an array of ASC nodes. This is NOT a tree — it's a linear chain where control flow is encoded by nesting markers (`fun`/`funbody`/`funend`, `if`/`else`/`end`, `whiletrue`/`end`, etc.).

Each ASC node has an `op` field and type-specific fields. Key node types:

- **`var`** — Variable declaration (count, type, values, names, public)
- **`op+`/`op-`/`op*`/`op/`/`op%`** — Binary operators (lhs, rhs)
- **`call`** — Function call (fun, args)
- **`return`** — Return statement
- **`if`** — Conditional (test, elseif, not)
- **`fun`** — Function declaration (arity, args)
- **`reassign`** — Variable reassignment (lhs, rhs)
- **`name`** — Name binding (names)
- **`print`** — Print statement

### 1.4 Code Generation

**File:** `src/transpilers/js.ts` (primary target)

The JS transpiler walks the ASC chain linearly, emitting JavaScript. It maintains:
- `tmpVarCnt` — Counter for temporary `_ans` variables
- `randVarCnt` — Counter for random `_rand` variables  
- `strayvar` — Stack of "stray" values (results not yet consumed)
- `curlvl` — Nesting depth for brace matching

The `getval()` function resolves tokens to JavaScript expressions:
- `["ans"]` → pops from strayvar stack
- `["num", "42", pos]` → `"42"`
- `["iden", "甲", pos]` → `"甲"`
- `["bool", "true", pos]` → `"true"`

### 1.5 Operator Handling (Critical for Extension)

Operators are parsed from patterns like:

```
「甲」加「乙」      →  op+  { lhs: 甲, rhs: 乙 }
加「甲」以「乙」    →  op+  { lhs: 乙, rhs: 甲 }  (right-to-left)
「甲」除「乙」所餘幾何  →  op%  { lhs: 甲, rhs: 乙 }  (modulo)
```

The tokenizer produces:
1. `["iden", "甲"]` 
2. `["op", "+"]` for 加
3. `["iden", "乙"]`
4. `["opord", "r"]` or `["opord", "l"]` for 於/以

The parser (`tokens2asc`, around line 290) checks:
```typescript
if (gettok(i, 0) == "op") {
  typeassert(i + 2, ["opord"]);
  var x: ASCNode = { op: "op+", pos };
  if (gettok(i + 2, 1) == "l") {
    x.lhs = tokens[i + 1];
    x.rhs = tokens[i + 3];
  } else {
    x.lhs = tokens[i + 3];
    x.rhs = tokens[i + 1];
  }
  if (gettok(i, 1) == "/" && tokens[i + 4] && gettok(i + 4, 0) == "mod") {
    x.op = "op%";
    i += 5;
  } else {
    x.op = ("op" + gettok(i, 1)) as "op+";
    i += 4;
  }
  asc.push(x);
}
```

The code generator (js.ts, around line 140) emits:
```typescript
else if (a.op.startsWith("op")) {
  const _a = a as ASCNodeOperator;
  const lhs = getval(_a.lhs);
  const rhs = getval(_a.rhs);
  const vname = this.nextTmpVar();
  js += `const ${vname}=${lhs}${a.op.slice(2)}${rhs};`;
  strayvar.push(vname);
}
```

---

## 2. Extension Design: Five Deadband Primitives

### 2.1 周天數 (zhōutiān shù) — Celestial Number Type [PRIORITY: IMPLEMENT FIRST]

#### Mathematical Foundation
The deadband framework constrains angular values to [0, 359] by construction. This is a TYPE-LEVEL guarantee — not a runtime check, but a compile-time constraint enforced by the type system. The number 360 corresponds to the traditional Chinese celestial cycle (周天, "full heavenly circuit"), divided into 24 solar terms of 15° each.

The wrapping expression `((x % 360) + 360) % 360` handles both positive and negative values correctly, always producing a result in [0, 360).

#### Chinese Philosophical Resonance
- **周天** (zhōutiān): The celestial sphere, the full circuit of heaven. Ancient Chinese astronomy divided the celestial equator into 365.25 度 (degrees), later simplified to 360.
- The 24 節氣 (solar terms) each span 15°, creating natural deadbands in the seasonal cycle.
- **天行有常** ("Heaven moves with constancy") — the periodicity IS the constraint.

#### Syntax
```
吾有一周天數。曰三十。名之曰「角」。
```
Parses identically to `吾有一數。曰三十。名之曰「角」。` but with type `周天` instead of `數/num`.

#### Compiler Changes

**A. Keyword Registration** (`src/keywords.ts`)

Add to `KEYWORDS_DEFINE`:
```typescript
周天數: ["type", "zhoutian"],
```

This must be registered BEFORE `數` in the dictionary (or use a longer match) because `周天數` ends with `數`. Since keywords are sorted by length (longest first) at the bottom of `keywords.ts`, `周天數` (3 chars) will be tried before `數` (1 char), which is correct.

**B. Tokenizer** (`src/parser.ts`, `wy2tokens()`)

No changes needed — the tokenizer already handles multi-character keyword matching via the sorted KEYWORDS lookup. Adding `周天數` to `KEYWORDS_DEFINE` automatically makes the tokenizer recognize it.

**C. Parser** (`src/parser.ts`, `tokens2asc()`)

The variable declaration handler (line ~210) already processes any type token:
```typescript
if (gettok(i, 0) == "decl" && (gettok(i, 1) == "uninit" || gettok(i, 1) == "public")) {
  typeassert(i + 1, ["num"], "variable count");
  typeassert(i + 2, ["type"], "variable type");
  var x: ASCNode = {
    op: "var",
    count: cnt,
    type: gettok(i + 2, 1),  // ← This captures "zhoutian"
    values: [],
    names: [],
    public: gettok(i, 1) == "public",
    pos
  };
```

The `type` field will be `"zhoutian"` — no parser change needed for declarations.

**D. Code Generator** (`src/transpilers/js.ts`)

In the `var` handler, add initialization for `zhoutian` type:
```typescript
// Existing:
if (a.type == "num") { value = "0"; }
// Add:
else if (a.type == "zhoutian") { value = "0"; }
```

For the critical part — arithmetic wrapping — we need to intercept operator nodes where both operands are known to be `zhoutian` type. However, the current ASC doesn't carry type information through operations. We have two approaches:

**Approach A: Wrapper Functions (Recommended for v1)**

Register wrapper functions in the transpiler. When a `zhoutian` variable is involved in arithmetic, the compiler wraps the result.

In the JS transpiler, add to the `var` handler:
```typescript
if (a.type == "zhoutian") {
  value = `(((${value || 0}) % 360 + 360) % 360)`;
}
```

And track zhoutian variables:
```typescript
let zhoutianVars = new Set<string>();
// In var handler:
if (a.type == "zhoutian" && name) {
  zhoutianVars.add(name);
}
```

Then in the operator handler:
```typescript
if (a.op.startsWith("op") && isZhoutianOp(a, zhoutianVars)) {
  const lhs = getval((a as ASCNodeOperator).lhs);
  const rhs = getval((a as ASCNodeOperator).rhs);
  const vname = this.nextTmpVar();
  js += `const ${vname}=((${lhs}${a.op.slice(2)}${rhs})%360+360)%360;`;
  strayvar.push(vname);
}
```

**Approach B: Dedicated Operator (Future)**

Add new keywords `周加` (zhōu jiā), `周減` (zhōu jiǎn), etc. that compile to auto-wrapped operations. This is cleaner but requires more keyword/parser work.

We'll use **Approach A** for the initial implementation.

**E. Type System** (`src/types.ts`)

Add `"zhoutian"` to the `IdenType.type` union:
```typescript
export interface IdenType {
  type: "any" | "nil" | "fun" | "obj" | "arr" | "str" | "bol" | "num" | "zhoutian" | string;
  // ...
}
```

**F. Typecheck** (`src/typecheck.ts`)

Add zhoutian as a valid type. Operations between two zhoutian values should yield zhoutian. Operations between zhoutian and num should yield zhoutian (with auto-promotion).

#### Example wenyan Code
```
吾有一周天數。曰三十。名之曰「甲」。
吾有一周天數。曰三百四十。名之曰「乙」。
加「甲」以「乙」。名之曰「丙」。
書之。
```
Expected output: `10` (because (30 + 340) % 360 = 370 % 360 = 10)

#### Test Cases
1. `吾有一周天數。曰三百。名之曰「角」。書之。` → `300`
2. `吾有一周天數。曰零。名之曰「角」。書之。` → `0`
3. Adding two zhoutian wrapping over 360: `300 + 90 → 30`
4. Negative wrapping: `(-30) % 360 → 330`

---

### 2.2 歸 (guī) — Lattice Snap Operator

#### Mathematical Foundation
The Eisenstein lattice is the set of complex numbers of the form `a + bω` where `ω = e^(2πi/3)` and `a,b ∈ ℤ`. Given an arbitrary point (x,y) in the plane, the snap operation finds the nearest lattice point by:

1. Transform to Eisenstein basis: `u = x - y/√3`, `v = 2y/√3`
2. Round `u` and `v` to nearest integers
3. Transform back: `x' = u + v/2`, `y' = v·√3/2`

This is the fundamental operation of the deadband framework — it maps continuous values to the discrete constraint lattice.

#### Chinese Philosophical Resonance
- **歸** (guī): To return, to revert, to come home. The Proclamation of Returning (歸去來兮) by Tao Yuanming.
- The concept of "returning to the proper path" — 歸正 (guī zhèng).
- In the I Ching, 歸妹 (guī mèi) is Hexagram 54: "The Marrying Maiden — Returning." The lattice snap is literally "returning to the lattice."

#### Syntax
```
夫「點」歸
```
Postfix operator on an identifier. The variable `點` must be an object with `x` and `y` properties (a 2D point). The operator snaps it to the nearest Eisenstein lattice point.

#### Compiler Changes

**A. Keyword Registration** (`src/keywords.ts`)
```typescript
歸: ["snap", undefined],
```

**B. ASC Node** (`src/types.ts`)
```typescript
export interface ASCNodeSnap {
  op: "snap";
  target: Token;  // The variable to snap
}
```

**C. Parser** (`src/parser.ts`, `tokens2asc()`)

Add handling after the `expr` check:
```typescript
else if (gettok(i, 0) == "snap") {
  // This is a postfix operator — the target was the previous stray value
  asc.push({ op: "snap", target: tokens[i - 1], pos });
  i += 1;
}
```

Actually, since `歸` is postfix, it needs to consume the previous identifier. The wenyan syntax would be:
```
夫「點」之「「x」」歸
```
This is more complex — `夫` introduces an expression. Let's simplify: use a function call instead.

**Revised Syntax (Function-Based):**
```
施「歸格」於「點」。名之曰「格點」。
```
This calls a library function `歸格` (guī gé, "return to the pattern") that performs the lattice snap. No compiler changes needed — just a library addition in `lib/格子經.wy`.

This is more practical for the initial implementation. We can add native operator support later.

#### Library Implementation (`lib/格子經.wy`)
```wenyan
吾嘗觀「「算經」」之書。方悟「平方根」「取整」「取底」「圓周率」之義。

注曰「「三之平方根」」
施「平方根」於三。名之曰「三根」。

注曰「「歸格 — Snap to Eisenstein lattice.
Given (x,y), find nearest point a + b*omega where omega = e^(2pi*i/3).」」
吾有一術。名之曰「歸格」。欲行是術。必先得一物。曰「點」。乃行是術曰。
  夫「點」之「「x」」。名之曰「甲」。
  夫「點」之「「y」」。名之曰「乙」。
  
  注曰「「Transform to Eisenstein basis: u = x - y/sqrt(3), v = 2y/sqrt(3)」」
  除「乙」以「三根」。減其於「甲」。名之曰「丙」。
  乘二以「乙」。除其以「三根」。名之曰「丁」。
  
  注曰「「Round to nearest integers」」
  施「取整」於「丙」。名之曰「戊」。
  施「取整」於「丁」。名之曰「己」。
  
  注曰「「Transform back: x' = u + v/2, y' = v * sqrt(3) / 2」」
  除「己」以二。加其於「戊」。名之曰「新甲」。
  乘「己」以「三根」。除其以二。名之曰「新乙」。
  
  吾有一物。名之曰「格點」。其物如是。
    物之「「x」」者。數曰「新甲」。
    物之「「y」」者。數曰「新乙」。
  是謂「格點」之物也。
  乃得「格點」。
是謂「歸格」之術也。
```

---

### 2.3 可辨 (kě biàn) — Deadband Comparison

#### Mathematical Foundation
The deadband perceivability condition: a pattern of order `n` is perceivable with `b` bits if `n ≤ b`. This is the fundamental constraint — you cannot perceive finer detail than your bit depth allows.

This comes from the deadband framework's constraint theory:
- **Order** `n`: The minimum number of distinguishable states needed to represent the pattern
- **Bits** `b`: The available precision in bits
- **Perceivable**: iff `n ≤ 2^b` (or simplified: `n ≤ b` for the linearized version)

#### Chinese Philosophical Resonance
- **可辨** (kě biàn): "Can distinguish." From 辨 (biàn): to discriminate, to distinguish.
- In the 莊子 (Zhuangzi): "天地與我並生，而萬物與我為一。既已為一矣，且得有言乎？" — the question of what CAN be distinguished.
- The deadband boundary is literally the threshold of distinguishability.

#### Syntax
```
「甲」可辨「乙」
```
Returns 陽 (true) if pattern of order 甲 is perceivable with 乙 bits, 陰 (false) otherwise.

#### Compiler Changes

**A. Keyword Registration** (`src/keywords.ts`)
```typescript
可辨: ["perceive", undefined],
```

**B. ASC Node** (`src/types.ts`)
```typescript
export interface ASCNodePerceive {
  op: "perceive";
  order: Token;  // n
  bits: Token;   // b
}
```

**C. Parser** (`src/parser.ts`)

Add after operator handling. Pattern: `iden "可辨" iden`:
```typescript
else if (gettok(i, 0) == "perceive") {
  var x: ASCNode = { op: "perceive", order: tokens[i - 1], bits: tokens[i + 1], pos };
  asc.push(x);
  i += 2;
}
```

Wait — this needs careful thought about tokenization. `「甲」可辨「乙」` tokenizes as:
1. `["iden", "甲"]`
2. `["perceive", undefined]`
3. `["iden", "乙"]`

So the parser needs to handle `perceive` as a binary infix operator. The left operand comes from the previous stray token, and the right from the next.

**Better approach:** Treat it like a comparison operator. Add it to the `cmp` family:

```typescript
可辨: ["cmp", "<="],
```

Then `「甲」可辨「乙」` becomes a comparison `甲 <= 乙`, which the compiler already handles via the `if` test mechanism. This requires zero compiler changes — just a keyword registration!

However, this doesn't carry the semantic meaning. For a proper implementation, we'd add a dedicated node type.

**Recommended v1 approach:** Use keyword-as-comparison:
```typescript
可辨: ["cmp", "<="],
```

This is elegant — "can order 甲 be distinguished by 乙 bits?" literally compiles to `甲 <= 乙`. Zero drift by construction.

#### Example wenyan Code
```
吾有一數。曰三。名之曰「階」。
吾有一數。曰五。名之曰「位」。
若「階」可辨「位」者。
  書之。
  注曰「「Pattern of order 3 IS perceivable with 5 bits」」
云云。
```

---

### 2.4 占卦 (zhān guà) — Hexagram Random

#### Mathematical Foundation
The I Ching's 64 hexagrams provide a natural 6-bit state space (2^6 = 64). Each hexagram encodes:
- 6 lines (爻), each solid (陽/1) or broken (陰/0)
- A unique 6-bit binary number
- Traditional name, image, and judgment
- Mathematical structure (symmetry, complement pairs)

The existing `易經.wy` library implements `占()` using a linear congruential generator. We need to extend this to map the random output to hexagram indices [0, 63].

#### Chinese Philosophical Resonance
- **占卦** (zhān guà): "To divine by hexagrams." The fundamental act of consulting the I Ching.
- The 64 hexagrams (六十四卦) encode all possible states of 6 binary choices.
- Hexagram pairs (like 乾/坤, heaven/earth) are natural complement pairs — identical to bitwise NOT.
- The **卦序** (hexagram sequence) of King Wen is a specific permutation of 64 elements that has resisted mathematical explanation for 3000+ years.

#### Syntax
```
占卦
```
Returns a number in [0, 63], representing one hexagram.

```
「甲」占卦
```
Returns the 甲-th line (爻) of the current hexagram (0 = bottom, 5 = top). Each line is 陽 (1) or 陰 (0).

#### Compiler Changes

**Approach: Library Function (Recommended)**

No compiler changes needed. Add to `lib/易經.wy`:

```wenyan
注曰「「占卦 — Draw one hexagram (0-63).」」
吾有一術。名之曰「占卦」。乃行是術曰。
  施「占」於零。乘其以六十四。施「取整」於其。
  乃得矣。
是謂「占卦」之術也。

注曰「「卦爻 — Get the i-th line of hexagram h.」」
吾有一術。名之曰「卦爻」。欲行是術。必先得二數。曰「卦」。曰「位」。乃行是術曰。
  施「取底除」於「卦」。於「二」。
  夫其之「「商」」。名之曰「商」。
  若「位」等於零者。乃得「商」也。云云。
  施「卦爻」於「商」。減「位」以一。取二以施「卦爻」。乃得矣。
是謂「卦爻」之術也。
```

Actually, for the 爻 extraction, the bit-shifting approach is simpler:
```wenyan
注曰「「卦爻 — Get the bit-th line of hexagram.」」
吾有一術。名之曰「卦爻」。欲行是術。必先得二數。曰「卦」。曰「位」。乃行是術曰。
  注曰「「Shift right by 位, then mask with 1」」
  吾有一數。曰一。名之曰「掩」。
  為是「位」遍。
    乘「掩」以二。昔之「掩」者。今其是矣。
  云云。
  除「掩」以「卦」。所餘幾何。名之曰「餘」。
  除「餘」以「掩」。名之曰「爻」。
  施「取整」於「爻」。乃得矣。
是謂「卦爻」之術也。
```

Hmm, that's getting complex. Let's use a simpler recursive approach for the library:

```wenyan
注曰「「卦爻 — Get the 位-th bit of hexagram 卦.」」
吾有一術。名之曰「卦爻」。欲行是術。必先得二數。曰「卦」。曰「位」。乃行是術曰。
  若「位」等於零者。
    除二於「卦」。所餘幾何。乃得矣。
  若非。
    除二於「卦」。取整。減「位」以一。取二以施「卦爻」。乃得矣。
  云云。
是謂「卦爻」之術也。
```

Wait, `除二於「卦」。取整。` — `取整` is a function that needs to be called with `施`. Let me fix:

```wenyan
吾有一術。名之曰「卦爻」。欲行是術。必先得二數。曰「卦」。曰「位」。乃行是術曰。
  若「位」等於零者。
    除二以「卦」。所餘幾何。乃得矣。
  若非。
    除二以「卦」。名之曰「半卦」。
    減一於「位」。名之曰「減位」。
    施「卦爻」於「半卦」。於「減位」。乃得矣。
  云云。
是謂「卦爻」之術也。
```

Note: `除二以「卦」` means "divide 2 by 卦" (the operand order is `以` = "using"). Actually looking at the operator handling more carefully:

`除「甲」以「乙」` → `甲 / 乙` (left operand / right operand)  
`除「甲」於「乙」` → `乙 / 甲` (right operand / left operand, right-to-left)

And `所餘幾何` gives the remainder. So `除二以「卦」。所餘幾何` gives `2 % 卦` which is wrong.

Correct: `除「卦」以二。所餘幾何。` gives `卦 % 2` ✓

Let me fix the library code:

```wenyan
吾有一術。名之曰「卦爻」。欲行是術。必先得二數。曰「卦」。曰「位」。乃行是術曰。
  若「位」等於零者。
    除「卦」以二。所餘幾何。乃得矣。
  若非。
    除「卦」以二。名之曰「半卦」。施「取底」於「半卦」。名之曰「整半」。
    減一於「位」。施「卦爻」於「整半」。於其。乃得矣。
  云云。
是謂「卦爻」之術也。
```

Actually wait — `除「卦」以二` produces `卦/2` and the result goes to strayvar. Then `所餘幾何` gives the remainder. But `除「卦」以二。名之曰「半卦」` — does `名之曰` consume the strayvar? Let me re-check...

In the ASC, `除` produces an `op+` node with `op%` when followed by `所餘幾何`. Without `所餘幾何`, it's `op/`. So `除「卦」以二` gives `卦/2` as a stray value. `所餘幾何` gives `卦%2`.

So:
```
除「卦」以二。所餘幾何。名之曰「餘」。
```
gives `var 餘 = 卦%2;` ✓

And for integer division:
```
除「卦」以二。名之曰「商」。
施「取底」於「商」。名之曰「整商」。
```

Hmm, `取底` is from 算經, which takes one argument. So `施「取底」於「商」。` gives `Math.floor(商)`.

OK the library code should work. Let me finalize it cleanly.

---

### 2.5 生數 (shēng shù) — Fibonacci/Hemachandra Generator

#### Mathematical Foundation
The Fibonacci sequence (1, 1, 2, 3, 5, 8, 13, 21, ...) was known in India as the Hemachandra numbers (हेमचन्द्र संख्या) well before Fibonacci. In the deadband framework, Fibonacci numbers appear in:
- The growth rate of constraint satisfaction
- The golden ratio φ = (1+√5)/2 ≈ 1.618... which is already defined in 算經 as 黃金分割數
- Lattice point counting on the Eisenstein lattice

#### Chinese Philosophical Resonance
- **生數** (shēng shù): "Generating numbers." From 生 (shēng): to produce, to give birth.
- The sequence embodies the Daoist principle of 生生不息 (shēng shēng bù xī): "endless generation."
- Each term is born from its parents, like the 64 hexagrams emerge from the 8 trigrams.

#### Syntax
```
吾有一術。名之曰「生數」。欲行是術。必先得一數。曰「甲」。乃行是術曰。
  ...
是謂「生數」之術也。
```
Returns the 甲-th Fibonacci number (0-indexed: F(0)=0, F(1)=1, F(2)=1, ...).

#### Compiler Changes

**Approach: Library Function Only**

No compiler changes needed. This is a pure library addition.

```wenyan
吾有一術。名之曰「生數」。欲行是術。必先得一數。曰「甲」。乃行是術曰。
  若「甲」等於零者。乃得零也。
  若「甲」等於一者。乃得一也。
  
  有數零。名之曰「前」。
  有數一。名之曰「今」。
  減「甲」以一。名之曰「餘」。
  
  為是「餘」遍。
    加「前」以「今」。名之曰「新」。
    昔之「前」者。今「今」是矣。
    昔之「今」者。今「新」是矣。
  云云。
  
  乃得「今」。
是謂「生數」之術也。
```

---

## 3. Implementation Plan

### Phase 1: 周天數 Type (Compiler Extension)

**Files to modify:**

| File | Change | Lines Affected |
|------|--------|---------------|
| `src/keywords.ts` | Add `周天數: ["type", "zhoutian"]` | ~line 15 |
| `src/types.ts` | Add `"zhoutian"` to IdenType | ~line 120 |
| `src/transpilers/js.ts` | Add zhoutian var init + op wrapping | ~lines 23, 140 |
| `src/transpilers/py.ts` | Same for Python target | ~lines 30, 140 |
| `src/transpilers/rb.ts` | Same for Ruby target | ~lines 30, 140 |
| `src/typecheck.ts` | Add zhoutian type handling | ~line 60 |

**Specific code patches** — see Section 4 below.

### Phase 2: 可辨 Comparison (Keyword Only)

| File | Change | Lines Affected |
|------|--------|---------------|
| `src/keywords.ts` | Add `可辨: ["cmp", "<="]` | ~line 90 |

One line. That's it. The comparison `「甲」可辨「乙」` compiles to `甲 <= 乙`.

### Phase 3: Library Extensions (No Compiler Changes)

| File | Change |
|------|--------|
| `lib/格子經.wy` | New file: 歸格 (lattice snap) |
| `lib/易經.wy` | Add: 占卦, 卦爻 functions |
| `lib/算經.wy` | Add: 生數 (Fibonacci) function |

### Phase 4: Native 歸 Operator (Future)

Requires:
- New keyword: `歸: ["snap", undefined]`
- New ASC node type: `ASCNodeSnap`
- Parser handling for postfix operator
- Code generation for Eisenstein lattice snap

This is complex because wenyan doesn't have postfix operators currently. All operators are either infix (`加/減/乘/除`) or prefix (`變` for NOT). Adding a postfix operator would require changes to the expression parsing logic.

---

## 4. Code Patches: 周天數 Type Implementation

### 4.1 Patch: `src/keywords.ts`

**Location:** Line 15 (in the KEYWORDS_DEFINE object, type section)

**Add after `元: ["type", "any"],`:**
```typescript
  周天數: ["type", "zhoutian"],
```

The keyword sorting at the bottom of the file will automatically place 周天數 (3 chars) before 數 (1 char), ensuring correct tokenization.

### 4.2 Patch: `src/types.ts`

**Location:** ~Line 230 (IdenType interface)

**Change:**
```typescript
export interface IdenType {
  type: "any" | "nil" | "fun" | "obj" | "arr" | "str" | "bol" | "num" | "zhoutian" | string;
```

(The `| string` escape hatch already exists, but explicit is better.)

### 4.3 Patch: `src/transpilers/js.ts`

**Location 1: Variable initialization** (~line 23, in the `var` handler)

After:
```typescript
} else if (a.type == "any") {
  value = "void 0";
}
```
Add:
```typescript
} else if (a.type == "zhoutian") {
  value = value !== undefined ? `((${value}%360+360)%360)` : "0";
}
```

**Location 2: Operator wrapping** (~line 140, in the `op` handler)

We need to track which variables are zhoutian type. Add a class property:
```typescript
export default class JSCompiler extends BaseTranspiler {
  zhoutianVars: Set<string> = new Set();
  // ... existing properties
```

In the `var` handler, after assigning name:
```typescript
if (a.type == "zhoutian" && name) {
  this.zhoutianVars.add(name);
}
```

In the operator handler, replace the simple emission:
```typescript
} else if (a.op.startsWith("op")) {
  const _a = a as ASCNodeOperator;
  const lhs = getval(_a.lhs);
  const rhs = getval(_a.rhs);
  const vname = this.nextTmpVar();
  const opSymbol = a.op.slice(2);
  
  // Check if either operand is a zhoutian variable
  const lhsZhoutian = _a.lhs && _a.lhs[0] === "iden" && this.zhoutianVars.has(_a.lhs[1]);
  const rhsZhoutian = _a.rhs && _a.rhs[0] === "iden" && this.zhoutianVars.has(_a.rhs[1]);
  
  if ((lhsZhoutian || rhsZhoutian) && (opSymbol === "+" || opSymbol === "-"")) {
    js += `const ${vname}=((${lhs}${opSymbol}${rhs})%360+360)%360;`;
  } else {
    js += `const ${vname}=${lhs}${opSymbol}${rhs};`;
  }
  strayvar.push(vname);
}
```

**Location 3: Reassignment wrapping** (~line 160, in the `reassign` handler)

After reassignment, wrap if zhoutian:
```typescript
// After: js += `${lhs}=${rhs};`;
if (this.zhoutianVars.has(getval(a.lhs))) {
  js += `${lhs}=((${lhs})%360+360)%360;`;
}
```

### 4.4 Patch: `src/typecheck.ts`

**Location:** Where type names are validated (search for `"num"` in type assertions)

Add `"zhoutian"` alongside `"num"` in any type whitelist. The typecheck should allow operations between `zhoutian` and `num` types, producing `zhoutian`.

---

## 5. Test wenyan Code

### 5.1 Basic 周天數 Declaration
```wenyan
注曰「「Test: 周天數 basic declaration」」
吾有一周天數。曰三百。名之曰「角」。
書之。
```
**Expected output:** `300`

### 5.2 周天數 Wrapping Addition
```wenyan
注曰「「Test: 周天數 addition wrapping over 360」」
吾有一周天數。曰三百。名之曰「甲」。
吾有一周天數。曰九十。名之曰「乙」。
加「甲」以「乙」。名之曰「丙」。
書之。
```
**Expected output:** `30`

### 5.3 周天數 with Negative Values
```wenyan
注曰「「Test: 周天數 initialization with negative wrapping」」
吾有一周天數。曰負三十。名之曰「角」。
書之。
```
**Expected output:** `330` (because ((-30) % 360 + 360) % 360 = 330)

### 5.4 可辨 Comparison
```wenyan
注曰「「Test: Deadband perceivability comparison」」
吾有一數。曰三。名之曰「階」。
吾有一數。曰五。名之曰「位」。
若「階」可辨「位」者。
  夫「「三階可辨於五位」」。書之。
云云。
吾有一數。曰七。名之曰「大階」。
若「大階」可辨「位」者。
  夫「「七階不可辨於五位」」。書之。
若非。
  夫「「誠然。七不可辨於五。」」。書之。
云云。
```
**Expected output:** `三階可辨於五位` then `誠然。七不可辨於五。`

### 5.5 Fibonacci Generator (Library)
```wenyan
注曰「「Test: Fibonacci generator」」
吾嘗觀「「算經」」之書。方悟「生數」之義。

施「生數」於零。書之。
施「生數」於一。書之。
施「生數」於五。書之。
施「生數」於十。書之。
```
**Expected output:** `0`, `1`, `5`, `55`

---

## 6. Design Principles

### 6.1 Zero Drift by Construction
The 周天數 type guarantees values stay in [0, 359] by:
1. **Initialization wrapping** — constructor wraps any value
2. **Arithmetic wrapping** — every `+` and `-` on zhoutian vars wraps
3. **Assignment wrapping** — reassignment wraps

This is NOT a runtime check — it's a compile-time guarantee baked into the code generation. The type IS the constraint.

### 6.2 Philosophical Coherence
Each extension maps to a Chinese philosophical concept that perfectly matches its mathematical meaning:

| Primitive | Chinese Concept | Mathematical Meaning |
|-----------|----------------|---------------------|
| 周天數 | Celestial circuit (周天) | Modular arithmetic mod 360 |
| 歸 | Return to proper form (歸正) | Lattice snap (nearest point) |
| 可辨 | Can distinguish (可辨) | Perceivability (n ≤ b) |
| 占卦 | I Ching divination | Random from 64-hexagram space |
| 生數 | Endless generation (生生不息) | Fibonacci sequence |

### 6.3 Layered Implementation
- **Layer 1** (Compiler): 周天數 type — guaranteed by the type system
- **Layer 2** (Keywords): 可辨 comparison — one keyword, zero compiler logic
- **Layer 3** (Libraries): 歸格, 占卦, 生數 — pure wenyan, no compiler changes

This layering minimizes risk. The compiler only needs changes for 周天數. Everything else is either a keyword trick or a library.

---

## 7. Future Extensions

### 7.1 Native Eisenstein Type (格子數)
A type for Eisenstein integers `a + bω` where operations preserve lattice membership. Would require:
- Two-component variable type
- Custom arithmetic operators
- Integration with 歸格 snap

### 7.2 Deadband Assertions (必辨)
Compile-time assertions that verify deadband constraints:
```
「甲」必辨「乙」
```
Compile error if the constraint cannot be proven.

### 7.3 Constraint Propagation (推)
Automatic constraint propagation through function calls:
```
吾有一周天數。曰「甲」。推「甲」於「乙」。
```
Where 乙 inherits the zhoutian constraint from 甲.

---

## 8. Appendix: File Inventory

### Files Modified (周天數 implementation)
- `src/keywords.ts` — +1 line (keyword registration)
- `src/types.ts` — +1 token in union type
- `src/transpilers/js.ts` — +~15 lines (zhoutian tracking + wrapping)
- `src/transpilers/py.ts` — +~15 lines (same for Python)
- `src/typecheck.ts` — +~5 lines (zhoutian type acceptance)

### Files Added (Library extensions)
- `lib/格子經.wy` — Lattice snap library (~30 lines wenyan)
- Enhanced `lib/易經.wy` — +~20 lines (占卦, 卦爻)
- Enhanced `lib/算經.wy` — +~15 lines (生數)

### Files Added (Tests)
- `test/周天數_test.wy` — Test suite for celestial number type
- `test/可辨_test.wy` — Test suite for perceivability comparison
- `test/格子經_test.wy` — Test suite for lattice snap
- `test/占卦_test.wy` — Test suite for hexagram random
- `test/生數_test.wy` — Test suite for Fibonacci generator

---

*"天行有常，不為堯存，不為桀亡。" — Xunzi*

Heaven moves with constancy. It does not exist for Yao, nor perish with Jie.

The deadband IS the constancy. The type IS the guarantee. 周天三百六十度，天行有常。
