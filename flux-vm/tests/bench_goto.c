/*
 * bench_goto.c — FLUX VM Dispatch Benchmark
 * Compares computed-GOTO (&&label) dispatch vs standard switch dispatch
 * for a 30-opcode FLUX constraint VM subset.
 *
 * Compile:
 *   gcc -O2 -std=c11 -o bench_goto bench_goto.c
 *   ./bench_goto
 */

#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>
#include <assert.h>

/* ============================================================
 * FLUX 30-opcode constraint VM definition
 * ============================================================ */

typedef enum {
    OP_NOP      = 0,
    OP_PUSH     = 1,
    OP_DUP      = 2,
    OP_DROP     = 3,
    OP_SWAP     = 4,
    OP_EQ       = 5,
    OP_NE       = 6,
    OP_LT       = 7,
    OP_GT       = 8,
    OP_LE       = 9,
    OP_GE       = 10,
    OP_ADD      = 11,
    OP_SUB      = 12,
    OP_AND      = 13,
    OP_OR       = 14,
    OP_XOR      = 15,
    OP_NOT      = 16,
    OP_INRANGE  = 17,
    OP_ASSERT   = 18,
    OP_JMP      = 19,
    OP_JZ       = 20,
    OP_JNZ      = 21,
    OP_CALL     = 22,
    OP_RET      = 23,
    OP_HALT     = 24,
    OP_LAND     = 25,
    OP_LOR      = 26,
    OP_LNOT     = 27,
    OP_NEG      = 28,
    OP_LOAD     = 29,
    OP_STORE    = 30,
} Opcode;

#define MAX_STACK 256
#define STACK_CAPACITY 256

typedef struct {
    int64_t stack[MAX_STACK];
    int sp;             /* stack pointer */
    int ip;             /* instruction pointer */
    int64_t ret_stack[MAX_STACK];
    int rsp;            /* return stack pointer for CALL/RET */
} VMState;

/* Forward decls */
static void vm_switch(const uint8_t *bytecode, int bc_len, VMState *state);
static void vm_goto(const uint8_t *bytecode, int bc_len, VMState *state);

/* ============================================================
 * Helper: push/pop
 * ============================================================ */

static inline void vpush(VMState *s, int64_t v) {
    if (s->sp >= MAX_STACK) { fprintf(stderr, "Stack overflow\n"); exit(1); }
    s->stack[s->sp++] = v;
}

static inline int64_t vpop(VMState *s) {
    if (s->sp <= 0) { fprintf(stderr, "Stack underflow\n"); exit(1); }
    return s->stack[--s->sp];
}

static inline int64_t vpeek(VMState *s, int depth) {
    if (s->sp - depth - 1 < 0) { fprintf(stderr, "Stack underflow (peek)\n"); exit(1); }
    return s->stack[s->sp - depth - 1];
}

/* ============================================================
 * Bytecode builder for the constraint program
 * ============================================================ */

typedef struct {
    uint8_t *code;
    int len;
    int cap;
} BytecodeBuilder;

static void bc_init(BytecodeBuilder *b) {
    b->cap = 256;
    b->len = 0;
    b->code = malloc(b->cap);
}

static void bc_emit(BytecodeBuilder *b, uint8_t byte) {
    if (b->len >= b->cap) {
        b->cap *= 2;
        b->code = realloc(b->code, b->cap);
    }
    b->code[b->len++] = byte;
}

static void bc_emit64(BytecodeBuilder *b, int64_t v) {
    /* Little-endian encoding */
    for (int i = 0; i < 8; i++) {
        bc_emit(b, (uint8_t)(v >> (i * 8)));
    }
}

/* ============================================================
 * Build the constraint program bytecode
 * ============================================================ */

static uint8_t *build_constraint_program(int *out_len) {
    BytecodeBuilder b;
    bc_init(&b);

    /* PUSH 4      // expected services */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 4);

    /* PUSH 4      // actual services */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 4);

    /* EQ          // check if equal */
    bc_emit(&b, OP_EQ);

    /* ASSERT      // must be equal */
    bc_emit(&b, OP_ASSERT);

    /* PUSH 308    // chain size */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 308);

    /* PUSH 256    // min expected */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 256);

    /* GT          // check chain > min */
    bc_emit(&b, OP_GT);

    /* ASSERT      // must be true */
    bc_emit(&b, OP_ASSERT);

    /* PUSH 54     // constraint count */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 54);

    /* PUSH 50     // min */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 50);

    /* PUSH 100    // max */
    bc_emit(&b, OP_PUSH);
    bc_emit64(&b, 100);

    /* INRANGE     // check 50 <= 54 <= 100 */
    bc_emit(&b, OP_INRANGE);

    /* ASSERT      // must be true */
    bc_emit(&b, OP_ASSERT);

    /* HALT */
    bc_emit(&b, OP_HALT);

    *out_len = b.len;
    return b.code;
}

/* ============================================================
 * VM: switch dispatch
 * ============================================================ */

static void vm_switch(const uint8_t *bc, int bc_len, VMState *s) {
    s->sp = 0;
    s->ip = 0;
    s->rsp = 0;
    int64_t a, b, lo, hi;
    int64_t addr;

    while (s->ip < bc_len) {
        uint8_t op = bc[s->ip++];
        switch (op) {
        case OP_NOP:
            break;

        case OP_PUSH:
            a = 0;
            for (int i = 0; i < 8; i++)
                a |= ((int64_t)bc[s->ip++]) << (i * 8);
            vpush(s, a);
            break;

        case OP_DUP:
            a = vpeek(s, 0);
            vpush(s, a);
            break;

        case OP_DROP:
            vpop(s);
            break;

        case OP_SWAP:
            a = vpop(s);
            b = vpop(s);
            vpush(s, a);
            vpush(s, b);
            break;

        case OP_EQ:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a == b ? 1 : 0);
            break;

        case OP_NE:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a != b ? 1 : 0);
            break;

        case OP_LT:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a < b ? 1 : 0);
            break;

        case OP_GT:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a > b ? 1 : 0);
            break;

        case OP_LE:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a <= b ? 1 : 0);
            break;

        case OP_GE:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a >= b ? 1 : 0);
            break;

        case OP_ADD:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a + b);
            break;

        case OP_SUB:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a - b);
            break;

        case OP_AND:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a & b);
            break;

        case OP_OR:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a | b);
            break;

        case OP_XOR:
            b = vpop(s);
            a = vpop(s);
            vpush(s, a ^ b);
            break;

        case OP_NOT:
            a = vpop(s);
            vpush(s, ~a);
            break;

        case OP_INRANGE: {
            hi = vpop(s);
            lo = vpop(s);
            a = vpop(s);
            vpush(s, (a >= lo && a <= hi) ? 1 : 0);
            break;
        }

        case OP_ASSERT: {
            a = vpop(s);
            if (!a) {
                fprintf(stderr, "ASSERTION FAILED at ip=%d\n", s->ip - 2);
                exit(1);
            }
            break;
        }

        case OP_JMP: {
            addr = 0;
            for (int i = 0; i < 8; i++)
                addr |= ((int64_t)bc[s->ip++]) << (i * 8);
            s->ip = (int)addr;
            break;
        }

        case OP_JZ: {
            addr = 0;
            for (int i = 0; i < 8; i++)
                addr |= ((int64_t)bc[s->ip++]) << (i * 8);
            a = vpop(s);
            if (a == 0)
                s->ip = (int)addr;
            break;
        }

        case OP_JNZ: {
            addr = 0;
            for (int i = 0; i < 8; i++)
                addr |= ((int64_t)bc[s->ip++]) << (i * 8);
            a = vpop(s);
            if (a != 0)
                s->ip = (int)addr;
            break;
        }

        case OP_CALL: {
            addr = 0;
            for (int i = 0; i < 8; i++)
                addr |= ((int64_t)bc[s->ip++]) << (i * 8);
            if (s->rsp >= MAX_STACK) { fprintf(stderr, "Return stack overflow\n"); exit(1); }
            s->ret_stack[s->rsp++] = s->ip;
            s->ip = (int)addr;
            break;
        }

        case OP_RET:
            if (s->rsp <= 0) { fprintf(stderr, "Return stack underflow\n"); exit(1); }
            s->ip = (int)s->ret_stack[--s->rsp];
            break;

        case OP_HALT:
            return;

        case OP_LAND: {
            b = vpop(s);
            a = vpop(s);
            vpush(s, a && b ? 1 : 0);
            break;
        }

        case OP_LOR: {
            b = vpop(s);
            a = vpop(s);
            vpush(s, a || b ? 1 : 0);
            break;
        }

        case OP_LNOT:
            a = vpop(s);
            vpush(s, !a ? 1 : 0);
            break;

        case OP_NEG:
            a = vpop(s);
            vpush(s, -a);
            break;

        case OP_LOAD: {
            a = 0;
            for (int i = 0; i < 8; i++)
                a |= ((int64_t)bc[s->ip++]) << (i * 8);
            /* Simple variable store: just push the value from a variable table
             * For simplicity, we just push a dummy value */
            vpush(s, 0);
            break;
        }

        case OP_STORE: {
            a = 0;
            for (int i = 0; i < 8; i++)
                a |= ((int64_t)bc[s->ip++]) << (i * 8);
            /* Discard top of stack (the value to store) */
            vpop(s);
            break;
        }

        default:
            fprintf(stderr, "Unknown opcode: %d at ip=%d\n", op, s->ip - 1);
            exit(1);
        }
    }
}

/* ============================================================
 * VM: computed-GOTO dispatch (GCC extension)
 * ============================================================ */

static void vm_goto(const uint8_t *bc, int bc_len, VMState *s) {
    s->sp = 0;
    s->ip = 0;
    s->rsp = 0;
    int64_t a, b, lo, hi;
    int64_t addr;

    /* Build dispatch table — must have entries for all opcodes 0..30 */
    static const void *dispatch[31] = {
        [OP_NOP]     = &&L_NOP,
        [OP_PUSH]    = &&L_PUSH,
        [OP_DUP]     = &&L_DUP,
        [OP_DROP]    = &&L_DROP,
        [OP_SWAP]    = &&L_SWAP,
        [OP_EQ]      = &&L_EQ,
        [OP_NE]      = &&L_NE,
        [OP_LT]      = &&L_LT,
        [OP_GT]      = &&L_GT,
        [OP_LE]      = &&L_LE,
        [OP_GE]      = &&L_GE,
        [OP_ADD]     = &&L_ADD,
        [OP_SUB]     = &&L_SUB,
        [OP_AND]     = &&L_AND,
        [OP_OR]      = &&L_OR,
        [OP_XOR]     = &&L_XOR,
        [OP_NOT]     = &&L_NOT,
        [OP_INRANGE] = &&L_INRANGE,
        [OP_ASSERT]  = &&L_ASSERT,
        [OP_JMP]     = &&L_JMP,
        [OP_JZ]      = &&L_JZ,
        [OP_JNZ]     = &&L_JNZ,
        [OP_CALL]    = &&L_CALL,
        [OP_RET]     = &&L_RET,
        [OP_HALT]    = &&L_HALT,
        [OP_LAND]    = &&L_LAND,
        [OP_LOR]     = &&L_LOR,
        [OP_LNOT]    = &&L_LNOT,
        [OP_NEG]     = &&L_NEG,
        [OP_LOAD]    = &&L_LOAD,
        [OP_STORE]   = &&L_STORE,
    };

    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_NOP:
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_PUSH:
    a = 0;
    for (int i = 0; i < 8; i++)
        a |= ((int64_t)bc[s->ip++]) << (i * 8);
    vpush(s, a);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_DUP:
    a = vpeek(s, 0);
    vpush(s, a);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_DROP:
    vpop(s);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_SWAP:
    a = vpop(s);
    b = vpop(s);
    vpush(s, a);
    vpush(s, b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_EQ:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a == b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_NE:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a != b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_LT:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a < b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_GT:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a > b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_LE:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a <= b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_GE:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a >= b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_ADD:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a + b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_SUB:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a - b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_AND:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a & b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_OR:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a | b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_XOR:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a ^ b);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_NOT:
    a = vpop(s);
    vpush(s, ~a);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_INRANGE:
    hi = vpop(s);
    lo = vpop(s);
    a = vpop(s);
    vpush(s, (a >= lo && a <= hi) ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_ASSERT:
    a = vpop(s);
    if (!a) {
        fprintf(stderr, "ASSERTION FAILED at ip=%d\n", s->ip - 2);
        exit(1);
    }
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_JMP:
    addr = 0;
    for (int i = 0; i < 8; i++)
        addr |= ((int64_t)bc[s->ip++]) << (i * 8);
    s->ip = (int)addr;
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_JZ:
    addr = 0;
    for (int i = 0; i < 8; i++)
        addr |= ((int64_t)bc[s->ip++]) << (i * 8);
    a = vpop(s);
    if (a == 0) {
        s->ip = (int)addr;
        if (s->ip >= bc_len) return;
    }
    goto *dispatch[bc[s->ip++]];

L_JNZ:
    addr = 0;
    for (int i = 0; i < 8; i++)
        addr |= ((int64_t)bc[s->ip++]) << (i * 8);
    a = vpop(s);
    if (a != 0) {
        s->ip = (int)addr;
        if (s->ip >= bc_len) return;
    }
    goto *dispatch[bc[s->ip++]];

L_CALL:
    addr = 0;
    for (int i = 0; i < 8; i++)
        addr |= ((int64_t)bc[s->ip++]) << (i * 8);
    if (s->rsp >= MAX_STACK) { fprintf(stderr, "Return stack overflow\n"); exit(1); }
    s->ret_stack[s->rsp++] = s->ip;
    s->ip = (int)addr;
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_RET:
    if (s->rsp <= 0) { fprintf(stderr, "Return stack underflow\n"); exit(1); }
    s->ip = (int)s->ret_stack[--s->rsp];
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_HALT:
    return;

L_LAND:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a && b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_LOR:
    b = vpop(s);
    a = vpop(s);
    vpush(s, a || b ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_LNOT:
    a = vpop(s);
    vpush(s, !a ? 1 : 0);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_NEG:
    a = vpop(s);
    vpush(s, -a);
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_LOAD:
    a = 0;
    for (int i = 0; i < 8; i++)
        a |= ((int64_t)bc[s->ip++]) << (i * 8);
    vpush(s, 0);  /* dummy value */
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

L_STORE:
    a = 0;
    for (int i = 0; i < 8; i++)
        a |= ((int64_t)bc[s->ip++]) << (i * 8);
    vpop(s);  /* discard value */
    if (s->ip >= bc_len) return;
    goto *dispatch[bc[s->ip++]];

    /* Unreachable */
}

/* ============================================================
 * Timing helper
 * ============================================================ */

static double time_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static double run_benchmark(const uint8_t *bc, int bc_len,
                            void (*vm_func)(const uint8_t *, int, VMState *),
                            int iterations, const char *name) {
    double best = 1e18;
    VMState state;
    int runs = 10;

    for (int r = 0; r < runs; r++) {
        double t0 = time_seconds();
        for (int i = 0; i < iterations; i++) {
            vm_func(bc, bc_len, &state);
        }
        double t1 = time_seconds();
        double elapsed = t1 - t0;
        if (elapsed < best) best = elapsed;
    }

    double ns_per_op = (best / iterations) * 1e9;
    printf("%s: %.3fs for %d iterations (%.2f ns/op)\n",
           name, best, iterations, ns_per_op);
    return best;
}

/* ============================================================
 * Main
 * ============================================================ */

int main(void) {
    int bc_len;
    uint8_t *bc = build_constraint_program(&bc_len);

    printf("FLUX VM Dispatch Benchmark\n");
    printf("==========================\n");
    printf("Bytecode: %d instructions\n", bc_len);
    printf("Iterations per run: 10,000,000\n");
    printf("Best of 10 runs each\n\n");

    /* Validate correctness first */
    VMState state;
    vm_switch(bc, bc_len, &state);
    printf("Switch VM: correct (stack depth = %d)\n", state.sp);

    vm_goto(bc, bc_len, &state);
    printf("GOTO VM: correct (stack depth = %d)\n\n", state.sp);

    /* Benchmark */
    const int ITERATIONS = 10000000;

    double t_switch = run_benchmark(bc, bc_len, vm_switch, ITERATIONS, "Switch dispatch");
    double t_goto   = run_benchmark(bc, bc_len, vm_goto,   ITERATIONS, "GOTO dispatch");

    double ratio = t_switch / t_goto;
    printf("\nSpeedup: %.2fx\n", ratio);

    free(bc);
    return 0;
}
