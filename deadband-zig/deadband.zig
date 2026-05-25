//! Deadband Framework — Zig 0.13.0 Implementation
//! Eisenstein lattice, HPDF sampling, /360 arithmetic, BMA detection,
//! Shell decomposition, Fibonacci-spline search.

const std = @import("std");
const Random = std.Random;

// ─── Comptime Constants ──────────────────────────────────────────────

pub const PHI: f64 = 1.6180339887498948482;
pub const PHI_INV: f64 = -1.0 / PHI;
pub const SQRT3: f64 = 1.7320508075688772935;
pub const TAU: f64 = 2.0 * std.math.pi;
pub const EPS: f64 = 1.0e-12;

// ─── Eisenstein Snap ─────────────────────────────────────────────────

pub fn eisenstein_snap(comptime F: type, x: F, y: F) [2]F {
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);

    const l_exact = y / sqrt3;
    const k_exact = x - half * l_exact;
    const k = @round(k_exact);
    const l = @round(l_exact);
    return .{ k, l };
}

pub fn eisenstein_snap_coords(comptime F: type, x: F, y: F) struct { x: F, y: F } {
    const kl = eisenstein_snap(F, x, y);
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);
    return .{
        .x = kl[0] + half * kl[1],
        .y = sqrt3 * kl[1],
    };
}

pub fn eisenstein_norm(comptime F: type, k: i64, l: i64) F {
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);
    const kf: F = @floatFromInt(k);
    const lf: F = @floatFromInt(l);
    const rx = kf + half * lf;
    const ry = sqrt3 * lf;
    return @sqrt(rx * rx + ry * ry);
}

// ─── HPDF Sampling ───────────────────────────────────────────────────

pub fn hpdf_sample(rnd: Random, index: usize, total: usize) f64 {
    const golden_ratio_strat = PHI - 1.0;
    const jitter = rnd.float(f64);
    const strat = @as(f64, @floatFromInt(index)) * golden_ratio_strat;
    const base = @mod(strat, 1.0);
    return @mod(base + jitter / @as(f64, @floatFromInt(@max(total, 1))), 1.0);
}

pub fn hpdf_fill(allocator: std.mem.Allocator, count: usize, seed: u64) ![]f64 {
    const buf = try allocator.alloc(f64, count);
    var prng = std.Random.DefaultPrng.init(seed);
    const rnd = prng.random();
    for (buf, 0..) |*slot, i| {
        slot.* = hpdf_sample(rnd, i, count);
    }
    return buf;
}

// ─── Modular360 Arithmetic ──────────────────────────────────────────

pub fn Modular360(comptime T: type) type {
    return struct {
        value: T,

        const Self = @This();

        pub fn init(v: T) Self {
            return .{ .value = normalize(v) };
        }

        pub fn normalize(v: T) T {
            const vf: f64 = @floatCast(v);
            var norm = @mod(vf, 360.0);
            if (norm < 0) norm += 360.0;
            return @floatCast(norm);
        }

        pub fn add(a: Self, b: Self) Self {
            const s = @as(f64, @floatCast(a.value)) + @as(f64, @floatCast(b.value));
            var norm = @mod(s, 360.0);
            if (norm < 0) norm += 360.0;
            return .{ .value = @floatCast(norm) };
        }

        pub fn sub(a: Self, b: Self) Self {
            const d = @as(f64, @floatCast(a.value)) - @as(f64, @floatCast(b.value));
            var norm = @mod(d, 360.0);
            if (norm < 0) norm += 360.0;
            return .{ .value = @floatCast(norm) };
        }

        pub fn distance(a: Self, b: Self) T {
            const d = @abs(@as(f64, @floatCast(a.value)) - @as(f64, @floatCast(b.value)));
            return @floatCast(@min(d, 360.0 - d));
        }
    };
}

// ─── BMA Detector (Binary) ──────────────────────────────────────────

pub fn bma_binary(seq: []const u1) usize {
    if (seq.len == 0) return 0;
    var l: usize = 0;
    var m: usize = 1;

    var c = std.ArrayList(usize).initCapacity(std.heap.page_allocator, seq.len + 1) catch return 0;
    defer c.deinit();
    c.appendAssumeCapacity(0);

    var b = std.ArrayList(usize).initCapacity(std.heap.page_allocator, seq.len + 1) catch return 0;
    defer b.deinit();
    b.appendAssumeCapacity(0);

    for (seq, 0..) |s, i| {
        var d: u1 = s;
        for (c.items) |j| {
            if (j > 0 and j <= i) {
                d ^= seq[i - j];
            }
        }

        if (d == 0) {
            m += 1;
        } else {
            var temp = std.ArrayList(usize).initCapacity(std.heap.page_allocator, seq.len + 1) catch return l;
            for (b.items) |item| temp.appendAssumeCapacity(item);

            for (b.items) |j| {
                const idx = j + m;
                if (idx <= i + 1) {
                    var found = false;
                    var found_idx: usize = 0;
                    for (c.items, 0..) |cj, ci| {
                        if (cj == idx) {
                            found = true;
                            found_idx = ci;
                            break;
                        }
                    }
                    if (found) {
                        _ = c.orderedRemove(found_idx);
                    } else {
                        c.append(idx) catch {};
                    }
                }
            }

            if (2 * l <= i) {
                l = i + 1 - l;
                b.clearAndFree();
                b = temp;
                m = 1;
            } else {
                m += 1;
                temp.deinit();
            }
        }
    }
    return l;
}

// ─── Shell Decomposer ────────────────────────────────────────────────

pub fn ShellDecomposer(comptime size: usize) type {
    return struct {
        const Self = @This();

        pub const ShellEntry = struct {
            k: i64,
            l: i64,
            norm: f64,
            shell_index: usize,
        };

        entries: [size]ShellEntry,
        shell_count: usize,

        pub fn init(points: [size][2]f64) Self {
            var self: Self = undefined;
            self.shell_count = 0;

            for (points, 0..) |pt, i| {
                const kl = eisenstein_snap(f64, pt[0], pt[1]);
                const k: i64 = @intFromFloat(kl[0]);
                const l: i64 = @intFromFloat(kl[1]);
                const norm = eisenstein_norm(f64, k, l);
                self.entries[i] = .{ .k = k, .l = l, .norm = norm, .shell_index = 0 };
            }

            // Sort by norm using insertion sort
            const SortCtx = struct {
                entries: *[size]ShellEntry,
                pub fn lessThan(ctx: *@This(), a: ShellEntry, b: ShellEntry) bool {
                    _ = ctx;
                    return a.norm < b.norm;
                }
            };
            var sort_ctx = SortCtx{ .entries = &self.entries };
            std.sort.insertion(ShellEntry, &self.entries, &sort_ctx, SortCtx.lessThan);

            // Assign shell indices
            var current_shell: usize = 0;
            var prev_norm: f64 = -1.0;
            const tolerance: f64 = 1.0e-9;

            for (&self.entries, 0..) |*entry, i| {
                if (i == 0 or @abs(entry.norm - prev_norm) > tolerance) {
                    current_shell += 1;
                    prev_norm = entry.norm;
                }
                entry.shell_index = current_shell;
            }
            self.shell_count = current_shell;
            return self;
        }

        pub fn get_shell(self: Self, shell_idx: usize) []const ShellEntry {
            var start: usize = 0;
            var len: usize = 0;
            var found_start = false;
            for (self.entries, 0..) |entry, i| {
                if (entry.shell_index == shell_idx) {
                    if (!found_start) {
                        start = i;
                        found_start = true;
                    }
                    len += 1;
                }
            }
            return self.entries[start .. start + len];
        }
    };
}

// ─── Fibonacci-Spline Search ─────────────────────────────────────────

pub fn fibonacci_spline_search(
    comptime F: type,
    allocator: std.mem.Allocator,
    objective: *const fn (F) F,
    lo: F,
    hi: F,
    tolerance: F,
) F {
    _ = allocator;
    var a = lo;
    var b = hi;
    const gr: F = comptime @floatCast(PHI);

    var c = b - (b - a) / gr;
    var d = a + (b - a) / gr;

    var fc = objective(c);
    var fd = objective(d);

    var iterations: usize = 0;
    const max_iter = 100;

    while (@abs(b - a) > tolerance and iterations < max_iter) : (iterations += 1) {
        if (fc < fd) {
            b = d;
            d = c;
            fd = fc;
            c = b - (b - a) / gr;
            fc = objective(c);
        } else {
            a = c;
            c = d;
            fc = fd;
            d = a + (b - a) / gr;
            fd = objective(d);
        }
    }

    return (a + b) / @as(F, 2.0);
}

// ─── SIMD Vector Operations ─────────────────────────────────────────

pub fn eisenstein_snap_batch(len: usize, xs: []const f64, ys: []const f64, sx: []f64, sy: []f64) void {
    const sqrt3: f64 = SQRT3;
    for (0..len) |i| {
        const l_exact = ys[i] / sqrt3;
        const k_exact = xs[i] - 0.5 * l_exact;
        const k = @round(k_exact);
        const l = @round(l_exact);
        sx[i] = k + 0.5 * l;
        sy[i] = sqrt3 * l;
    }
}

// ─── Tests ───────────────────────────────────────────────────────────

test "eisenstein snap basic" {
    const kl = eisenstein_snap(f64, 1.0, 0.0);
    try std.testing.expectEqual(@as(f64, 1.0), kl[0]);
    try std.testing.expectEqual(@as(f64, 0.0), kl[1]);

    const kl2 = eisenstein_snap(f64, 0.5, SQRT3 / 2.0);
    try std.testing.expectEqual(@as(f64, 0.0), kl2[0]);
    try std.testing.expectEqual(@as(f64, 1.0), kl2[1]);

    const kl3 = eisenstein_snap(f64, 0.1, 0.1);
    try std.testing.expectEqual(@as(f64, 0.0), kl3[0]);
    try std.testing.expectEqual(@as(f64, 0.0), kl3[1]);
}

test "eisenstein snap f32" {
    const kl = eisenstein_snap(f32, 2.7, 1.5);
    _ = kl;
}

test "eisenstein norm" {
    const n0 = eisenstein_norm(f64, 0, 0);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), n0, EPS);

    const n1 = eisenstein_norm(f64, 1, 0);
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), n1, EPS);
}

test "hpdf sample" {
    var prng = std.Random.DefaultPrng.init(42);
    const rnd = prng.random();
    const s = hpdf_sample(rnd, 0, 100);
    try std.testing.expect(s >= 0.0 and s < 1.0);
}

test "hpdf fill" {
    const samples = try hpdf_fill(std.testing.allocator, 50, 123);
    defer std.testing.allocator.free(samples);
    try std.testing.expect(samples.len == 50);
    for (samples) |s| {
        try std.testing.expect(s >= 0.0 and s < 1.0);
    }
}

test "modular360 basic" {
    const M360 = Modular360(f64);
    const a = M360.init(30.0);
    const b = M360.init(350.0);
    try std.testing.expectApproxEqAbs(@as(f64, 30.0), a.value, EPS);
    try std.testing.expectApproxEqAbs(@as(f64, 350.0), b.value, EPS);

    const sum = a.add(b);
    try std.testing.expectApproxEqAbs(@as(f64, 20.0), sum.value, EPS);

    const dist = a.distance(b);
    try std.testing.expectApproxEqAbs(@as(f64, 40.0), dist, EPS);
}

test "modular360 negative" {
    const M360 = Modular360(f64);
    const a = M360.init(-45.0);
    try std.testing.expectApproxEqAbs(@as(f64, 315.0), a.value, EPS);
}

test "bma binary simple" {
    const seq = [_]u1{ 1, 0, 0, 1, 0, 0, 1, 0, 0, 1 };
    const lc = bma_binary(&seq);
    try std.testing.expect(lc == 3);
}

test "bma binary all zero" {
    const seq = [_]u1{ 0, 0, 0, 0, 0 };
    const lc = bma_binary(&seq);
    try std.testing.expect(lc == 0);
}

test "shell decomposer" {
    const SD = ShellDecomposer(6);
    const points = [_][2]f64{
        .{ 0.0, 0.0 },
        .{ 1.0, 0.0 },
        .{ 0.5, SQRT3 / 2.0 },
        .{ 2.0, 0.0 },
        .{ 1.0, SQRT3 },
        .{ 0.1, 0.1 },
    };
    const sd = SD.init(points);
    try std.testing.expect(sd.shell_count >= 2);
    const shell1 = sd.get_shell(1);
    try std.testing.expect(shell1.len >= 1);
}

test "fibonacci spline search" {
    const objective = struct {
        pub fn f(x: f64) f64 {
            const d = x - 2.5;
            return d * d;
        }
    }.f;

    const result = fibonacci_spline_search(f64, std.testing.allocator, objective, 0.0, 10.0, 1.0e-10);
    try std.testing.expectApproxEqAbs(@as(f64, 2.5), result, 1.0e-8);
}

test "snap batch" {
    const xs = [_]f64{ 1.0, 0.5, 2.3, 0.1 };
    const ys = [_]f64{ 0.0, SQRT3 / 2.0, 1.1, 0.1 };
    var sx: [4]f64 = undefined;
    var sy: [4]f64 = undefined;
    eisenstein_snap_batch(4, &xs, &ys, &sx, &sy);
    // Verify first point snaps to (1, 0)
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), sx[0], EPS);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), sy[0], EPS);
}

test "comptime constants" {
    try std.testing.expect(PHI > 1.618);
    try std.testing.expect(PHI < 1.619);
    try std.testing.expect(PHI_INV < -0.617);
    try std.testing.expect(PHI_INV > -0.619);
    try std.testing.expect(SQRT3 > 1.732);
    try std.testing.expect(SQRT3 < 1.733);
}
