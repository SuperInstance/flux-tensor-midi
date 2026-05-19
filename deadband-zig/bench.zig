//! Deadband Framework — Zig Benchmarks
const std = @import("std");
const deadband = @import("deadband.zig");
const time = std.time;

fn bench_ns(comptime label: [:0]const u8, iterations: usize, comptime func: *const fn () void) void {
    const start = time.nanoTimestamp();
    for (0..iterations) |_| {
        func();
    }
    const elapsed = time.nanoTimestamp() - start;
    const ns_per_iter = @divTrunc(elapsed, @as(i128, @intCast(iterations)));
    const stdout = std.io.getStdOut().writer();
    stdout.print("  {s:<40} {:>8} ns/op  ({d} iterations)\n", .{ label, ns_per_iter, iterations }) catch {};
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("\n⚒️  Deadband Framework — Zig Benchmarks\n", .{});
    try stdout.print("{s}\n\n", .{"=" ** 50});

    const N = 1_000_000;

    // Eisenstein snap
    try stdout.print("Eisenstein Snap (f64):\n", .{});
    bench_ns("snap(1.0, 0.0)", N, struct {
        pub fn run() void {
            const _ = deadband.eisenstein_snap(f64, 1.0, 0.0);
        }
    }.run);
    bench_ns("snap(2.7, 1.5)", N, struct {
        pub fn run() void {
            const _ = deadband.eisenstein_snap(f64, 2.7, 1.5);
        }
    }.run);
    bench_ns("snap_coords(3.14, 2.71)", N, struct {
        pub fn run() void {
            const _ = deadband.eisenstein_snap_coords(f64, 3.14, 2.71);
        }
    }.run);

    // Eisenstein norm
    try stdout.print("\nEisenstein Norm:\n", .{});
    bench_ns("norm(5, 3)", N, struct {
        pub fn run() void {
            const _ = deadband.eisenstein_norm(f64, 5, 3);
        }
    }.run);

    // Modular 360
    try stdout.print("\nModular360 (f64):\n", .{});
    bench_ns("init(45.0)", N, struct {
        pub fn run() void {
            const _ = deadband.Modular360(f64).init(45.0);
        }
    }.run);
    bench_ns("add", N, struct {
        pub fn run() void {
            const M = deadband.Modular360(f64);
            const a = M.init(30.0);
            const b = M.init(350.0);
            const _ = a.add(b);
        }
    }.run);
    bench_ns("distance", N, struct {
        pub fn run() void {
            const M = deadband.Modular360(f64);
            const a = M.init(30.0);
            const b = M.init(350.0);
            const _ = a.distance(b);
        }
    }.run);

    // BMA
    try stdout.print("\nBMA Binary:\n", .{});
    const seq = [_]u1{ 1, 0, 0, 1, 0, 0, 1, 0, 0, 1 };
    bench_ns("bma_binary(len=10)", 100_000, struct {
        pub fn run() void {
            const _ = deadband.bma_binary(&seq);
        }
    }.run);

    // Fibonacci spline
    try stdout.print("\nFibonacci-Spline Search:\n", .{});
    bench_ns("1D golden-section (tol=1e-10)", 100_000, struct {
        pub fn run() void {
            const objective = struct {
                pub fn f(x: f64) callconv(.c) f64 {
                    const d = x - 2.5;
                    return d * d;
                }
            }.f;
            const _ = deadband.fibonacci_spline_search(f64, std.heap.page_allocator, objective, 0.0, 10.0, 1.0e-10);
        }
    }.run);

    // SIMD
    try stdout.print("\nSIMD Eisenstein Snap (batch=4):\n", .{});
    const xs = [_]f64{ 1.0, 0.5, 2.3, 0.1 };
    const ys = [_]f64{ 0.0, deadband.SQRT3 / 2.0, 1.1, 0.1 };
    bench_ns("snap_simd(4 points)", N, struct {
        pub fn run() void {
            const _ = deadband.eisenstein_snap_simd(4, xs, ys);
        }
    }.run);

    // Shell decomposer
    try stdout.print("\nShell Decomposer (size=6):\n", .{});
    const points = [_][2]f64{
        .{ 0.0, 0.0 },
        .{ 1.0, 0.0 },
        .{ 0.5, deadband.SQRT3 / 2.0 },
        .{ 2.0, 0.0 },
        .{ 1.0, deadband.SQRT3 },
        .{ 0.1, 0.1 },
    };
    bench_ns("init + decompose", 100_000, struct {
        pub fn run() void {
            const SD = deadband.ShellDecomposer(6);
            const _ = SD.init(points);
        }
    }.run);

    try stdout.print("\n{s}\n", .{"=" ** 50});
    try stdout.print("Done. All primitives benchmarked.\n\n", .{});
}
