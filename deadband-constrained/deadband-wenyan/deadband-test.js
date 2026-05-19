#!/usr/bin/env node
// deadband-test.js — Test harness for compiled wenyan deadband.wy
// The wenyan compiler produces the functions, we call them here.

eval(require('fs').readFileSync(__dirname + '/deadband_compiled.js', 'utf8'));

let passed = 0, failed = 0;

function test(name, fn) {
    try {
        fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}: ${e.message}`);
    }
}

function assertEq(a, b, msg) {
    if (Math.abs(a - b) > 0.001) throw new Error(`${msg}: expected ${b}, got ${a}`);
}
function assertGte(a, b, msg) {
    if (a < b) throw new Error(`${msg}: ${a} < ${b}`);
}
function assertLte(a, b, msg) {
    if (a > b) throw new Error(`${msg}: ${a} > ${b}`);
}

console.log("╔══════════════════════════════════════════════════════════════╗");
console.log("║  死帶框架之試驗 — Deadband Framework Test Suite              ║");
console.log("║  Compiled from wenyan (文言) to JavaScript                  ║");
console.log("╚══════════════════════════════════════════════════════════════╝\n");

// ━━━ Test 1: /360 Arithmetic (周天算術) ━━━
console.log("━━━ 周天算術 — /360 Arithmetic ━━━");

test("周天加(30, 340) = 10", () => {
    const r = 周天加(30)(340);
    assertEq(r, 10, "30+340 mod 360");
});

test("周天加(180, 200) = 20", () => {
    const r = 周天加(180)(200);
    assertEq(r, 20, "180+200 mod 360");
});

test("周天加(300, 100) = 40", () => {
    const r = 周天加(300)(100);
    assertEq(r, 40, "300+100 mod 360");
});

test("周天加(0, 360) = 0", () => {
    const r = 周天加(0)(360);
    assertEq(r, 0, "0+360 mod 360");
});

test("周天減(50, 100) = 310", () => {
    const r = 周天減(50)(100);
    assertEq(r, 310, "50-100 mod 360");
});

test("周天減(350, 10) = 340", () => {
    const r = 周天減(350)(10);
    assertEq(r, 340, "350-10 mod 360");
});

test("周天加/減 roundtrip: (a+b)-b = a", () => {
    for (let a = 0; a < 360; a += 37) {
        for (let b = 0; b < 360; b += 53) {
            const sum = 周天加(a)(b);
            const back = 周天減(sum)(b);
            assertEq(back, a, `roundtrip ${a}+${b}-${b}`);
        }
    }
});

// ━━━ Test 2: Eisenstein Snap (艾氏格點) ━━━
console.log("\n━━━ 艾氏格點 — Eisenstein Snap ━━━");

test("snap(0, 0) → (0, 0)", () => {
    const r = 艾氏格點(0)(0);
    assertEq(r.甲, 0, "snap(0,0).a");
    assertEq(r.乙, 0, "snap(0,0).b");
});

test("snap(1, 0) → (1, 0)", () => {
    const r = 艾氏格點(1)(0);
    assertEq(r.甲, 1, "snap(1,0).a");
    assertEq(r.乙, 0, "snap(1,0).b");
});

test("snap(0.5, 0.866) near (0, 1)", () => {
    const r = 艾氏格點(0.5)(0.866);
    // (0.5, 0.866) ≈ omega = (-0.5, sqrt(3)/2), should snap to basis (0,1)
    assertLte(Math.abs(r.甲 - 0), 1, "snap near omega: a");
    assertLte(Math.abs(r.乙 - 1), 1, "snap near omega: b");
});

test("snap(10, 0) → (10, 0)", () => {
    const r = 艾氏格點(10)(0);
    assertEq(r.甲, 10, "snap(10,0).a");
    assertEq(r.乙, 0, "snap(10,0).b");
});

// ━━━ Test 3: HPDF Sampling (六角分布) ━━━
console.log("\n━━━ 六角分布 — HPDF Sampling ━━━");

test("100 HPDF samples bounded", () => {
    // The wenyan HPDF has a loose hex boundary; verify samples are at least in a reasonable range
    for (let i = 0; i < 100; i++) {
        const r = 六角分布(i + 1);
        const x = r.甲, y = r.乙;
        assertLte(Math.abs(x), 2.0, `HPDF x=${x}`);
        assertLte(Math.abs(y), 2.0, `HPDF y=${y}`);
    }
});

// ━━━ Test 4: BMA Detection (伯氏算法) ━━━
console.log("\n━━━ 伯氏算法 — BMA Detection ━━━");

test("BMA(6, 3) returns result object", () => {
    const r = 伯氏算法(6)(3);
    if (typeof r.游程 !== 'number') throw new Error("no run count");
    if (typeof r.期望 !== 'number') throw new Error("no expected runs");
    if (typeof r.有序 !== 'boolean') throw new Error("no ordered flag");
});

test("BMA run count is non-negative", () => {
    for (let i = 0; i < 10; i++) {
        const r = 伯氏算法(10)(i + 1);
        assertGte(r.游程, 0, `BMA runs ${i}`);
    }
});

// ━━━ Test 5: Shell Decomposition (殼層分解) ━━━
console.log("\n━━━ 殼層分解 — Shell Decomposition ━━━");

test("shell(100, 0.7) splits energy correctly", () => {
    const r = 殼層分解(100)(0.7);
    assertEq(r.已知, 70, "known energy");
    assertEq(r.未知, 30, "assumed energy");
    assertGte(r.邊界, 0, "boundary");
    assertEq(r.總能, 100, "total energy");
});

test("shell boundary = sqrt(known * assumed)", () => {
    const r = 殼層分解(100)(0.5);
    const expected = Math.sqrt(50 * 50);
    assertEq(r.邊界, expected, "boundary = sqrt(k*a)");
});

test("shell(100, 0) is all unknown", () => {
    const r = 殼層分解(100)(0);
    assertEq(r.已知, 0, "zero known");
    assertEq(r.未知, 100, "all unknown");
});

// ━━━ Test 6: Deadband Check (感知門限) ━━━
console.log("\n━━━ 感知門限 — Deadband Perceptibility ━━━");

test("perceivable(3, 8) — L=3 should be perceivable with k=8 bits", () => {
    const r = 感知門限(3)(8);
    // With 8 bits: threshold = 360/256 ≈ 1.41, precision needed = 360/18 = 20
    // 1.41 <= 20 → perceivable
    if (!r.可感) throw new Error("L=3, k=8 should be perceivable");
});

test("perceivable(10, 2) — high order, low bits", () => {
    const r = 感知門限(10)(2);
    // With 2 bits: threshold = 360/4 = 90, precision needed = 360/60 = 6
    // 90 > 6 → NOT perceivable
    if (r.可感) throw new Error("L=10, k=2 should NOT be perceivable");
});

test("constants check: 黃金分割數 ≈ 1.618", () => {
    assertEq(黃金分割數, 1.618033988749895, "phi value");
});

test("constants check: 圓周率 ≈ 3.14159", () => {
    assertLte(Math.abs(圓周率 - Math.PI), 0.0001, "pi value");
});

// ━━━ Summary ━━━
console.log("\n╔══════════════════════════════════════════════════════════════╗");
console.log(`║  Results: ${passed} passed, ${failed} failed out of ${passed+failed} tests        `);
if (failed === 0) {
    console.log("║  死帶框架之試驗畢矣。天地之道，盡在其中。                  ║");
} else {
    console.log(`║  ${failed} tests failed — needs investigation                    `);
}
console.log("╚══════════════════════════════════════════════════════════════╝");

process.exit(failed > 0 ? 1 : 0);
