# What Old Languages Teach Us About Constraint Engine Architecture

## The Thesis

Modern languages let you build anything. Fortran and COBOL only let you build *one thing* — batch processing on fixed-size records. That constraint IS the optimal shape for a constraint engine.

Python's `list.append()` and Rust's `Vec::push()` hide the truth. COBOL makes you say `OCCURS 8 TIMES` and now you know: **the constraint table is fixed at compile time.**

Fortran makes you say `INTEGER, PARAMETER :: MAX_CONSTRAINTS = 256` and now you know: **the hot path never allocates.**

## 1. Records, Not Objects

COBOL's data division:

```cobol
01 CONSTRAINT-RECORD.
   05 CONSTRAINT-TABLE OCCURS 8 TIMES.
      10 C-LO     PIC S9(9)V99 COMP.
      10 C-HI     PIC S9(9)V99 COMP.
      10 C-SEV    PIC 9(1) COMP.
      10 C-NAME   PIC X(16).
      10 C-ACTIVE PIC 9(1) COMP VALUE 1.
      10 C-VIOLATED PIC 9(1) COMP VALUE 0.
```

This is the truth. A constraint is six flat fields. No methods, no inheritance, no vtable. The `C-VIOLATED` flag IS the error mask bit — stored inline with the constraint, not in a separate data structure.

**Python obscures this with `@dataclass` and dynamic attributes. Rust obscures it with `struct` methods. COBOL makes it undeniable: data is flat, fixed, in columns.**

## 2. The Error Mask Is a Packed Byte

```cobol
01 RESULT-RECORD.
   05 ERROR-MASK    PIC 9(1) COMP VALUE 0.
   05 VIOLATED-CNT  PIC 9(1) COMP VALUE 0.
   05 SEVERITY      PIC 9(1) COMP VALUE 0.
   05 PASSED-FLAG   PIC 9(1) COMP VALUE 1.
```

8 constraints, 1 byte error mask. Not a `Set[int]`. Not a `Vec<bool>`. One byte. COBOL's `PIC 9(1) COMP` is a binary byte — exactly what the CPU sees.

The 88-level condition names are bit flags:

```cobol
05 ERROR-MASK PIC 9(1) COMP.
   88 ALL-PASSED VALUE 0.
   88 ANY-FAILED VALUE 1 THRU 255.
```

This is the same as `error_mask == 0` vs `error_mask != 0` but expressed as *named conditions on the data*. The data and the query are unified.

## 3. Sections = Pipeline Stages

COBOL's PROCEDURE DIVISION organizes code into sections. Not methods, not functions — *sections*. A section is a labeled block of imperative code. The natural pipeline:

```cobol
PROCEDURE DIVISION.
    PERFORM VALIDATE-INPUT
    PERFORM CHECK-CONSTRAINTS
    PERFORM APPLY-SEDIMENT
    PERFORM COMPUTE-SEVERITY
    STOP RUN.

VALIDATE-INPUT SECTION.
    ...

CHECK-CONSTRAINTS SECTION.
    PERFORM VARYING I FROM 1 BY 1 UNTIL I > N-CONSTRAINTS
        IF INPUT-VALUE(I) < C-LO(I) OR INPUT-VALUE(I) > C-HI(I)
           MOVE 1 TO C-VIOLATED(I)
        END-IF
    END-PERFORM.

APPLY-SEDIMENT SECTION.
    ...

COMPUTE-SEVERITY SECTION.
    ...
```

This IS the constraint engine. Not an object with methods. A linear pipeline of sections. Each section transforms the data in-place. No return values. No chaining. Just mutable state transformation in sequence.

**The Fortran equivalent:**

```fortran
call validate_input(constraints, values, n)
call check_constraints(constraints, values, n, error_mask)
call apply_sediment(sediment_stack, values, error_mask, n)
call compute_severity(error_mask, n, result)
```

Same shape. Subroutines that mutate their arguments. The pipeline is the architecture.

## 4. The Dependency Matrix Is Column-Major

Fortran stores arrays column-major. The adjacency matrix `adj(constraint, dimension)` means:

- Column = dimension (fixed, iterate over constraints)
- Row = constraint (varies per check)

```fortran
integer :: adj(MAX_CONSTRAINTS, MAX_DIMS)

! Fortran naturally iterates column-major
do j = 1, n_dims           ! inner loop = contiguous memory
    do i = 1, n_constraints
        if (adj(i, j) == 1) then
            ! constraint i depends on dimension j
        end if
    end do
end do
```

This is cache-friendly. The adjacency matrix access pattern matches Fortran's memory layout. In C/Rust (row-major), you'd transpose for the same effect.

**The language tells you the layout. You don't choose — the language chooses, and you organize around it.**

## 5. BFS Without Recursion

COBOL doesn't do recursion. Period. BFS for fracture MUST be iterative:

```cobol
FIND-CONNECTED-COMPONENTS SECTION.
    MOVE 0 TO N-BLOCKS
    MOVE ZERO TO VISITED-TABLE

    PERFORM VARYING I FROM 1 BY 1 UNTIL I > N-CONSTRAINTS
        IF VISITED(I) = 0
           ADD 1 TO N-BLOCKS
           MOVE I TO BFS-QUEUE(1)
           MOVE 1 TO QUEUE-FRONT
           MOVE 1 TO QUEUE-BACK
           MOVE 1 TO VISITED(I)
           PERFORM BFS-EXPAND
              UNTIL QUEUE-FRONT > QUEUE-BACK
        END-IF
    END-PERFORM.
```

This forces you to manage the queue explicitly. `BFS-QUEUE` is a fixed-size WORKING-STORAGE array. No heap. No `VecDeque`. No dynamic allocation. The queue size is bounded by `MAX_CONSTRAINTS` — known at compile time.

**The constraint is the insight: if your BFS queue can exceed fixed size, your system is wrong.**

## 6. Sediment Layers Are OCCURS Tables

```cobol
01 SEDIMENT-STACK.
   05 SED-DEPTH PIC 9(3) COMP VALUE 0.
   05 SED-LAYER OCCURS 50 TIMES.
      10 SED-CONSTRAINT-IDX PIC 9(3) COMP.
      10 SED-LO PIC S9(9)V99 COMP.
      10 SED-HI PIC S9(9)V99 COMP.
      10 SED-SURPRISE PIC S9(9)V99 COMP.
      10 SED-TIMESTAMP PIC 9(8) COMP.
      10 SED-ACTIVE PIC 9(1) COMP VALUE 1.
```

50 layers. Fixed. When full, supersede the oldest. No garbage collection. No reference counting. The stack is a circular buffer managed by timestamp comparison.

This is the **frozen hot path + open edges** pattern made physical:
- **Frozen**: the constraint table (OCCURS 8 TIMES) never changes at runtime
- **Open**: sediment layers accumulate (OCCURS 50 TIMES), superseding old corrections

## 7. COMMON Blocks = Module State

Fortran COMMON blocks are the original shared mutable state:

```fortran
! constraint_engine.f90
integer, parameter :: MAX_C = 256
real(8) :: c_lo(MAX_C), c_hi(MAX_C)
integer :: c_sev(MAX_C), c_active(MAX_C)
integer :: n_constraints
common /ENGINE/ c_lo, c_hi, c_sev, c_active, n_constraints
```

Every subroutine that `USE`s this module sees the same arrays. No passing arguments through 5 layers of call stack. The state is global and shared.

**This is what the Rust `lazy_static` or `once_cell` pattern recreates — but Fortran had it in 1957.**

## 8. Copybooks = Headers

COBOL's COPY statement is `#include`:

```cobol
COPY "FLXCONST".
COPY "FLXRESULT".
COPY "FLXSEDIMNT".
```

Each copybook defines the record layout. Any program that COPYs the same book sees the same data layout. This is the C header pattern — data layout separated from procedure logic.

**The constraint table definition exists in ONE place (the copybook) and is included everywhere.** Single source of truth, enforced by the language.

## 9. No Generics, No Templates — Just Arrays

Fortran and COBOL have no generics. Everything is concrete. You don't write `check<T>(value: T, bounds: Bounds<T>)`. You write:

```fortran
subroutine check_constraints(c_lo, c_hi, values, n, error_mask)
    real(8), intent(in) :: c_lo(n), c_hi(n), values(n)
    integer, intent(in) :: n
    integer, intent(out) :: error_mask(n)
```

Real numbers. Concrete. No abstraction tax. The compiler knows exactly what it's dealing with and generates optimal code.

**The constraint engine operates on `real(8)` and `integer`. Always. No polymorphism needed. The domain is finite and known.**

## 10. The Makefile IS the Build System

```makefile
flux_test: src/flux_fracture.f90 src/flux_sediment.f90 src/flux_test.f90
	gfortran -O2 -o $@ $^
```

No Cargo. No npm. No pip. Just compile the files in order. The dependency graph is the list of `.f90` files on the command line. The build system is a single Makefile rule.

**Complexity budget: zero.**

## What Modern Languages Get Wrong

1. **Dynamic sizing** — `Vec::with_capacity(8)` is pretending you don't know the size. You know the size. It's 8. Say 8.

2. **Heap allocation** — `Box::new(Constraint)` goes to the heap. COBOL puts it in WORKING-STORAGE. Stack-allocated, cache-local, zero indirection.

3. **Error types** — `Result<ConstraintResult, ConstraintError>` is two words per check. The COBOL answer is one byte: the error mask. Pass/fail in bit 0, severity in bits 1-3.

4. **Iteration** — `.iter().map().filter().collect()` allocates intermediate collections. COBOL's `PERFORM VARYING` mutates in place. Zero allocations.

5. **Abstraction layers** — traits, interfaces, protocols. The constraint engine has ONE implementation. You don't need to abstract over it.

## The Architecture Old Languages Reveal

```
┌─────────────────────────────────────────┐
│ FIXED-SIZE RECORDS (compile-time known) │
│                                         │
│  Constraint Table: 8 records × 6 fields │
│  Error Mask: 1 byte                     │
│  Sediment Stack: 50 layers × 5 fields   │
│  Dependency Matrix: 8×8 binary          │
│  BFS Queue: 8 entries                   │
│                                         │
│  TOTAL WORKING STORAGE: ~2KB            │
│  HEAP ALLOCATIONS: ZERO                 │
│  CACHE MISSES: MINIMAL (contiguous)     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ LINEAR PIPELINE (no branching on type)  │
│                                         │
│  VALIDATE → CHECK → FRACTURE →          │
│  COALESCE → SEDIMENT → SEVERITY         │
│                                         │
│  Each section: O(N) flat loop           │
│  No virtual dispatch                    │
│  No polymorphism                        │
│  No recursion                           │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ MUTATE IN PLACE (no copies)             │
│                                         │
│  Error mask: set bit, don't allocate    │
│  Sediment: update layer, don't clone    │
│  Result: write to OUTPUT record         │
│                                         │
│  RETURN VALUES: NONE                    │
│  Everything is WORKING-STORAGE mutation │
└─────────────────────────────────────────┘
```

## The Forgemaster's Verdict

COBOL and Fortran don't constrain the engineer. They *reveal* the engineer's constraints.

The constraint engine IS a batch processor on fixed records. It IS a linear pipeline of sections. It IS in-place mutation on preallocated storage. It IS column-major array access. It IS iterative BFS on a bounded queue.

Every modern language feature that obscures these facts — dynamic sizing, heap allocation, iterator chains, trait objects, Result types — makes the code *easier to write* and *harder to understand*.

The old languages made it *hard to write anything else*. That hardness was the architecture.

**The shape was always there. Fortran and COBOL just refused to let you pretend otherwise.**
