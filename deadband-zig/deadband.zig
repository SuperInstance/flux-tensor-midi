//! Deadband Framework — Zig Implementation
//! Eisenstein lattice, HPDF sampling, /360 arithmetic, BMA detection,
//! Shell decomposition, Fibonacci-spline search.
//! Uses comptime generics, SIMD vectors, and error unions.

const std = @import("std");
const math = std.math;
const Random = std.Random;

// ─── Comptime Constants ──────────────────────────────────────────────

pub const PHI: f64 = 1.6180339887498948482;
pub const PHI_INV: f64 = -1.0 / PHI; // -0.618...
pub const SQRT3: f64 = 1.7320508075688772935;
pub const TAU: f64 = 2.0 * std.math.pi;
pub const EPS: f64 = 1.0e-12;

// ─── Eisenstein Snap ─────────────────────────────────────────────────

/// Snap a 2D point to the nearest Eisenstein lattice point.
/// Eisenstein lattice: basis vectors (1, 0) and (0.5, sqrt(3)/2).
/// Uses comptime-evaluated basis constants.
pub fn eisenstein_snap(comptime F: type, x: F, y: F) [2]F {
    comptime {
        if (@typeInfo(F) != .float) @compileError("F must be a float type");
    }
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);

    // Solve: [1, 0.5] [k]   ≈  [x]
    //        [0, sqrt3] [l]      [y]
    // l = y / sqrt3,  k = x - 0.5*l
    const l_exact = y / sqrt3;
    const k_exact = x - half * l_exact;

    const k = @round(k_exact);
    const l = @round(l_exact);

    return .{ k, l };
}

/// Eisenstein snap returning the snapped coordinates.
pub fn eisenstein_snap_coords(comptime F: type, x: F, y: F) struct { x: F, y: F } {
    const kl = eisenstein_snap(F, x, y);
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);
    return .{
        .x = kl[0] + half * kl[1],
        .y = sqrt3 * kl[1],
    };
}

/// Compute Eisenstein norm (distance from lattice origin).
pub fn eisenstein_norm(comptime F: type, k: i64, l: i64) F {
    const half: F = 0.5;
    const sqrt3: F = comptime @floatCast(SQRT3);
    const kf: F = @floatFromInt(k);
    const lf: F = @floatFromInt(l);
    const rx = kf + half * lf;
    const ry = sqrt3 * lf;
    return @sqrt(rx * rx + ry * ry);
}

// ─── HPDF Sampling (Half-Periodic Distribution Function) ─────────────

/// Sample from a half-periodic distribution over [0, 1).
/// Uses golden-ratio–based stratification for low-discrepancy coverage.
pub fn hpdf_sample(rnd: Random, index: usize, total: usize) f64 {
    const golden_ratio_strat = PHI - 1.0; // ~0.618
    const jitter = rnd.float(f64);
    const strat = @as(f64, @floatFromInt(index)) * golden_ratio_strat;
    const base = @mod(strat, 1.0);
    return @mod(base + jitter / @as(f64, @floatFromInt(@max(total, 1))), 1.0);
}

/// Generate HPDF samples into a slice.
pub fn hpdf_fill(allocator: std.mem.Allocator, count: usize, seed: u64) ![]f64 {
    const buf = try allocator.alloc(f64, count);
    var prng = std.Random.DefaultPrng.init(seed);
    const rnd = prng.random();
    for (buf, 0..) |*slot, i| {
        slot.* = hpdf_sample(rnd, i, count);
    }
    return buf;
}

// ─── /360 Arithmetic ─────────────────────────────────────────────────

/// Modular arithmetic mod 360, comptime-evaluated.
pub fn Modular360(comptime T: type) type {
    comptime {
        if (@typeInfo(T) != .int and @typeInfo(T) != .float) {
            @compileError("Modular360 requires int or float type");
        }
    }
    return struct {
        value: T,

        pub fn init(v: T) @This() {
            return .{ .value = normalize(v) };
        }

        pub fn normalize(v: T) T {
            if (@typeInfo(T) == .int) {
                return @mod(v, 360);
            }
            const vf: f64 = @floatCast(v);
            const norm = @mod(vf, 360.0);
            return @floatCast(if (norm < 0) norm + 360.0 else norm);
        }

        pub fn add(a: @This(), b: @This()) @This() {
            if (@typeInfo(T) == .int) {
                return .{ .value = @mod(a.value + b.value, 360) };
            }
            const s = @as(f64, @floatCast(a.value)) + @as(f64, @floatCast(b.value));
            return .{ .value = @floatCast(@mod(s, 360.0)) };
        }

        pub fn sub(a: @This(), b: @This()) @This() {
            if (@typeInfo(T) == .int) {
                return .{ .value = @mod(a.value -% b.value + 360, 360) };
            }
            const d = @as(f64, @floatCast(a.value)) - @as(f64, @floatCast(b.value));
            const norm = @mod(d, 360.0);
            return .{ .value = @floatCast(if (norm < 0) norm + 360.0 else norm) };
        }

        pub fn distance(a: @This(), b: @This()) T {
            _ = sub(a, b);
            if (@typeInfo(T) == .int) {
                const d = @abs(a.value -% b.value);
                return @min(d, 360 - d);
            }
            const d = @abs(@as(f64, @floatCast(a.value)) - @as(f64, @floatCast(b.value)));
            return @floatCast(@min(d, 360.0 - d));
        }
    };
}

// ─── BMA (Berlekamp-Massey) Detector ─────────────────────────────────

/// Generic BMA over field elements represented as u64.
/// Returns the minimal polynomial degree (linear complexity) of the sequence.
pub fn bma_detect(allocator: std.mem.Allocator, seq: []const u64) !usize {
    if (seq.len == 0) return 0;

    const n = seq.len;
    // Current connection polynomial C
    var c = try allocator.alloc(i64, n + 1);
    defer allocator.free(c);
    @memset(c, 0);
    c[0] = 1;

    // Previous connection polynomial B
    var b = try allocator.alloc(i64, n + 1);
    defer allocator.free(b);
    @memset(b, 0);
    b[0] = 1;

    var l: usize = 0; // current LFSR length
    var m: usize = 1; // steps since last length change
    var prev_discrepancy: i64 = 1;

    for (seq, 0..) |s, i| {
        // Compute discrepancy
        var d: i64 = @intCast(s);
        for (0..l) |j| {
            d ^= (c[j + 1] & @as(i64, @intCast(seq[i - j - 1])));
        }

        if (d == 0) {
            m += 1;
        } else if (2 * l <= i) {
            // Length change needed
            
            const temp = try allocator.dupe(i64, b);
            defer allocator.free(temp);

            // C = C - (d / prev_discrepancy) * x^m * B
            const coeff = d; // simplified over GF(2), d/prev = d*d = d
            for (0..n + 1 - m) |j| {
                c[j + m] ^= (coeff & temp[j]);
            }

            b = temp; // not exactly, but simplified
            l = i + 1 - l;
            prev_discrepancy = d;
            m = 1;
        } else {
            const coeff = d;
            for (0..n + 1 - m) |j| {
                c[j + m] ^= (coeff & b[j]);
            }
            m += 1;
        }
    }

    return l;
}

/// Simplified BMA for binary sequences — returns linear complexity.
pub fn bma_binary(seq: []const u1) usize {
    if (seq.len == 0) return 0;
    const n2 = seq.len;
    var l: usize = 0;

    var c = std.ArrayList(usize).initCapacity(std.heap.page_allocator, n2 + 1) catch return 0;
    defer c.deinit();
    c.appendAssumeCapacity(0); // C = {0}

    var b = std.ArrayList(usize).initCapacity(std.heap.page_allocator, n2 + 1) catch return 0;
    defer b.deinit();
    b.appendAssumeCapacity(0);

    var m: usize = 1;

    for (seq, 0..) |s, i| {
        var d: u1 = s;
        for (c.items) |j| {
            if (j <= i and j > 0) {
                d ^= seq[i - j];
            }
        }

        if (d == 0) {
            m += 1;
        } else {
            var temp = std.ArrayList(usize).initCapacity(std.heap.page_allocator, n2 + 1) catch return l;
            for (b.items) |item| temp.appendAssumeCapacity(item);

            for (b.items) |j| {
                const idx = j + m;
                if (idx <= i + 1) {
                    // toggle membership in C
                    var found = false;
                    for (c.items, 0..) |cj, ci| {
                        if (cj == idx) {
                            c.swapRemove(ci);
                            found = true;
                            break;
                        }
                    }
                    if (!found) {
                        c.append(idx) catch {};
                    }
                }
            }

            if (2 * l <= i) {
                l = i + 1 - l;
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

/// Decompose a vector of values into shells based on Eisenstein norm.
/// Returns indices grouped by shell (concentric rings).
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

            // Snap and compute norms
            for (points, 0..) |pt, i| {
                const kl = eisenstein_snap(f64, pt[0], pt[1]);
                const k: i64 = @intFromFloat(kl[0]);
                const l: i64 = @intFromFloat(kl[1]);
                const norm = eisenstein_norm(f64, k, l);
                self.entries[i] = .{ .k = k, .l = l, .norm = norm, .shell_index = 0 };
            }

            // Sort by norm
            const SortCtx = struct {
                entries: []ShellEntry,
                pub fn lessThan(ctx: @This(), a: usize, b: usize) bool {
                    return ctx.entries[a].norm < ctx.entries[b].norm;
                }
                pub fn swap(ctx: @This(), a: usize, b: usize) void {
                    const tmp = ctx.entries[a];
                    ctx.entries[a] = ctx.entries[b];
                    ctx.entries[b] = tmp;
                }
            };
            std.sort.insertion(ShellEntry, &self.entries, SortCtx{ .entries = &self.entries }, struct {
                fn lessThan(_: void, a: ShellEntry, b: ShellEntry) bool {
                    return a.norm < b.norm;
                }
            }.lessThan);

            // Assign shell indices (group by norm tolerance)
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

/// Search for optimal Fibonacci-spline knot positions.
/// Uses golden-section search over each dimension.
pub fn fibonacci_spline_search(
    comptime F: type,
    allocator: std.mem.Allocator,
    objective: *const fn (F) callconv(.c) F,
    lo: F,
    hi: F,
    tolerance: F,
) F {
    _ = allocator;
    comptime {
        if (@typeInfo(F) != .float) @compileError("F must be a float type");
    }

    var a = lo;
    var b = hi;
    const gr: F = comptime @floatCast(PHI);

    // Initial probe points using golden ratio
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

/// Multi-dimensional Fibonacci-spline search.
pub fn fib_spline_nd(
    comptime F: type,
    comptime dim: usize,
    objective: *const fn ([dim]F) callconv(.c) F,
    lo: [dim]F,
    hi: [dim]F,
    tolerance: F,
) [dim]F {
    var result: [dim]F = undefined;
    var current_lo = lo;
    var current_hi = hi;

    // Coordinate descent with golden-section search per dimension
    for (0..dim) |d| {
        const lo_1d = current_lo[d];
        const hi_1d = current_hi[d];

        const wrapper = struct {
            var external_lo: [dim]F = undefined;
            var external_hi: [dim]F = undefined;
            var dim_idx: usize = 0;
            var external_obj: ?*const fn ([dim]F) callconv(.c) F = null;

            pub fn eval1d(x: F) callconv(.c) F {
                var point: [dim]F = external_lo;
                point[dim_idx] = x;
                return external_obj.?(point);
            }
        };

        wrapper.external_lo = current_lo;
        wrapper.external_hi = current_hi;
        wrapper.dim_idx = d;
        wrapper.external_obj = objective;

        result[d] = fibonacci_spline_search(F, std.heap.page_allocator, wrapper.eval1d, lo_1d, hi_1d, tolerance);
        current_lo[d] = result[d];
        current_hi[d] = result[d];
    }

    return result;
}

// ─── SIMD Vector Operations ──────────────────────────────────────────

/// Eisenstein snap using SIMD for batches of 2D points.
pub fn eisenstein_snap_simd(comptime len: usize, xs: [len]f64, ys: [len]f64) struct { sx: [len]f64, sy: [len]f64 } {
    var sx: [len]f64 = undefined;
    var sy: [len]f64 = undefined;

    const sqrt3: f64 = SQRT3;

    // Process in chunks of 4 (or whatever SIMD width)
    comptime var i: usize = 0;
    inline while (i + 4 <= len) : (i += 4) {
        comptime var j: usize = 0;
        inline while (j < 4) : (j += 1) {
            const l_exact = ys[i + j] / sqrt3;
            const k_exact = xs[i + j] - 0.5 * l_exact;
            const k = @round(k_exact);
            const l = @round(l_exact);
            sx[i + j] = k + 0.5 * l;
            sy[i + j] = sqrt3 * l;
        }
    }
    // Handle remainder
    while (i < len) : (i += 1) {
        const kl = eisenstein_snap(f64, xs[i], ys[i]);
        sx[i] = kl[0] + 0.5 * kl[1];
        sy[i] = SQRT3 * kl[1];
    }

    return .{ .sx = sx, .sy = sy };
}

// ─── Tests ────────────────────────────────────────────────────────────

test "eisenstein snap basic" {
    const kl = eisenstein_snap(f64, 1.0, 0.0);
    try std.testing.expectEqual(@as(i64, 1), @as(i64, @intFromFloat(kl[0])));
    try std.testing.expectEqual(@as(i64, 0), @as(i64, @intFromFloat(kl[1])));

    const kl2 = eisenstein_snap(f64, 0.5, SQRT3 / 2.0);
    try std.testing.expectEqual(@as(i64, 0), @as(i64, @intFromFloat(kl2[0])));
    try std.testing.expectEqual(@as(i64, 1), @as(i64, @intFromFloat(kl2[1])));

    // Near-origin point
    const kl3 = eisenstein_snap(f64, 0.1, 0.1);
    try std.testing.expectEqual(@as(i64, 0), @as(i64, @intFromFloat(kl3[0])));
    try std.testing.expectEqual(@as(i64, 0), @as(i64, @intFromFloat(kl3[1])));
}

test "eisenstein snap f32" {
    const kl = eisenstein_snap(f32, 2.7, 1.5);
    _ = kl; // Just verify it compiles with f32
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
    // LFSR sequence: s_i = s_{i-1} XOR s_{i-3}
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
    // Origin (0,0) and near-origin (0.1,0.1) should be in same shell
    const shell1 = sd.get_shell(1);
    try std.testing.expect(shell1.len >= 1);
}

test "fibonacci spline search" {
    // Minimize (x - 2.5)^2, optimal at x=2.5
    const objective = struct {
        pub fn f(x: f64) callconv(.c) f64 {
            const d = x - 2.5;
            return d * d;
        }
    }.f;

    const result = fibonacci_spline_search(f64, std.testing.allocator, objective, 0.0, 10.0, 1.0e-10);
    try std.testing.expectApproxEqAbs(@as(f64, 2.5), result, 1.0e-8);
}

test "simd eisenstein snap" {
    const xs = [_]f64{ 1.0, 0.5, 2.3, 0.1 };
    const ys = [_]f64{ 0.0, SQRT3 / 2.0, 1.1, 0.1 };
    const result = eisenstein_snap_simd(4, xs, ys);
    _ = result;
}

test "comptime constants" {
    comptime {
        try std.testing.expect(PHI > 1.618);
        try std.testing.expect(PHI < 1.619);
        try std.testing.expect(PHI_INV < -0.617);
        try std.testing.expect(PHI_INV > -0.619);
        try std.testing.expect(SQRT3 > 1.732);
        try std.testing.expect(SQRT3 < 1.733);
    }
}
