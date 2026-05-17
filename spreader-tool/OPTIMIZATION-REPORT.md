# Optimization Report — spreader-tool

**Date:** 2026-05-17
**Baseline:** 201 tests passing, 2006 lines across 10 source modules
**After:** 201 tests passing, all changes verified

## Changes Made

### 1. Docstrings added to 16 public/internal methods

**Files:** `types.py`, `deadband.py`, `store.py`, `frozen_context.py`, `seed_lock.py`

Every public method on `DeadbandDetector`, `SpreaderStore`, `FCWManager`, and `SeedLockManager` now has a docstring. Factory helpers `make_fcw()` and `make_seed()` also documented. Transition methods on `FrozenContextWindow` and `Seed` now explain copy-on-write behavior.

**Justification:** Documentation debt — these are public APIs used by `spreader_room.py`, `cli.py`, and tests. IDE hover and `help()` now return useful text.

### 2. Extracted magic number to constant in `redaction.py`

```python
# Before:
proximity_threshold = 0.25  # inline magic number in coverage()

# After:
_PROXIMITY_THRESHOLD: float = 0.25  # module-level constant
```

**Justification:** The proximity threshold is the only tuning knob in the coverage model. Making it a named constant makes it findable and adjustable.

### 3. Deduplicated `list_fcws()` / `list_seeds()` in `store.py`

Both methods had identical filter logic (index lookup → hash iteration → deserialize → status filter). Extracted shared `_list_items()` helper that both call with their specific kind/filter attributes.

**Before:** 28 lines duplicated across two methods
**After:** 1 shared helper (20 lines) + 2 thin wrappers (8 lines each)

**Justification:** DRY — any future changes to the listing/filtering logic (e.g., pagination, sorting) only need to touch one place.

## Changes NOT Made

| Opportunity | Reason |
|---|---|
| Decompose `deadband.py` `update()` (75 lines) | Complex stateful logic with temporal coupling — refactoring risks subtle bugs in severity/hysteresis |
| Decompose `spreader_room.py` `tick()` (72 lines) | 8-step loop is explicitly documented architecture — splitting would obscure the algorithm |
| Decompose `spreader_room.py` `_update_seed()` (45 lines) | State machine with exception suppression — fragile to refactor |
| Add type annotations to `cli.py` helper functions | `_fmt_status`, `_fmt_seed_state` are trivial formatters, not worth the churn |
| Extract `transition_to` duplication in `types.py` | Frozen dataclasses require explicit field-by-field reconstruction — a shared helper would need reflection and risk breaking the frozen contract |
| Refactor `seed_lock.py` `deprecate()` manual Seed reconstruction | Same reason as above — frozen dataclass reconstruction is verbose but safe |

## Module Health Summary

| Module | Lines | Branches | Test Lines | Ratio | Status |
|---|---|---|---|---|---|
| `types.py` | 244 | 3 | 197 | 0.82x | ✅ Good |
| `cost.py` | 93 | 2 | 164 | 1.76x | ✅ Excellent |
| `deadband.py` | 206 | 10 | 319 | 1.59x | ✅ Excellent |
| `frozen_context.py` | 170 | 8 | 329 | 1.97x | ✅ Excellent |
| `redaction.py` | 194 | 17 | 262 | 1.37x | ✅ Good |
| `seed_lock.py` | 217 | 12 | 177 | 0.81x | ⚠️ Could use more tests |
| `spreader_room.py` | 293 | 19 | 302 | 1.03x | ✅ Adequate |
| `store.py` | 220 | 26 | 195 | 0.98x | ✅ Adequate |
| `cli.py` | 379 | 28 | 287 | 0.75x | ⚠️ CLI integration test gap |
| `development_patterns.py` | 338 | — | 0 | — | 🔴 **NO TESTS** |
| `self_optimize.py` | 635 | — | 0 | — | 🔴 **NO TESTS** |

## Remaining Optimization Opportunities

### High Priority
1. **Test `development_patterns.py` and `self_optimize.py`** — 973 lines with zero test coverage. These are the newest modules and carry significant complexity (subprocess calls, pattern matching, self-referential optimization).
2. **`seed_lock.py` test coverage** — ratio is below 1.0x. Add tests for edge cases in `deprecate()` with replacement seeds, and `_InMemorySeedStore.query()` with combined filters.

### Medium Priority
3. **`cli.py` integration tests** — Only 0.75x test ratio. Commands like `redact`, `stats`, and `deadband-status` need end-to-end tests against a temp store.
4. **Type annotations in `cli.py`** — `_SpreaderStoreAdapter.get()` and `.query()` lack return type annotations.

### Low Priority (Design Discussion Needed)
5. **Decompose `deadband.update()`** — 75-line method could be split into `_check_all_metrics()` + `_apply_hysteresis()` + `_update_state()`, but requires careful temporal ordering analysis.
6. **Frozen dataclass reconstruction pattern** — Both `FCW.transition_to()` and `Seed.transition_to()` manually copy every field. A `dataclasses.replace()` call would be cleaner but changes the reconstruction semantics subtly.

## Recommended Next Steps

1. Write tests for `development_patterns.py` and `self_optimize.py` (critical gap)
2. Add seed_lock edge case tests
3. Add CLI integration tests for `redact` and `stats` commands
4. Consider `dataclasses.replace()` for transition methods (after test coverage is solid)
