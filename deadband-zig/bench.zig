//! Deadband Framework — Zig Benchmarks
const std = @import("std");
const deadband = @import("deadband.zig");
const time = std.time;

fn bench_ns(comptime label: [:0]const u8, iterations: usize, comptime func: *const fn () u64) void {
    var sink: u64 = 0;
    const start = time.nanoTimestamp();
    for (0..iterations) |_| {
        sink |= func();
    }
    const elapsed = time.nanoTimestamp() - start;
    const ns_per_iter = @divTrunc(elapsed, @as(i128, @intCast(iterations)));
    const stdout = std.io.getStdOut().writer();
    // Prevent dead-code elimination of sink
    if (sink == 0xFFFFFFFFFFFFFFFF) std.debug.print("", .{});
    stdout.print("  {s:<40} {:>8} ns/op  ({d} iterations)\n", .{ label, ns_per_iter, iterations }) catch {};
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("\n⚒️  Deadband Framework — Zig Benchmarks\n", .{});
    try stdout.print("{s}\n\n", .{"=" ** 50});

    const N = 1_000_000;

    try stdout.print("Eisenstein Snap (f64):\n", .{});
    bench_ns("snap(1.0, 0.0)", N, struct {
        pub fn run() u64 {
            const r = deadband.eisenstein_snap(f64, 1.0, 0.0);
            return @as(u64, @intFromFloat(r[0])) | @as(u64, @intFromFloat(r[1]));
        }
    }.run);
    bench_ns("snap(2.7, 1.5)", N, struct {
        pub fn run() u64 {
            const r = deadband.eisenstein_snap(f64, 2.7, 1.5);
            return @as(u64, @intFromFloat(r[0])) | @as(u64, @intFromFloat(r[1]));
        }
    }.run);
    bench_ns("snap_coords(3.14, 2.71)", N, struct {
        pub fn run() u64 {
            const r = deadband.eisenstein_snap_coords(f64, 3.14, 2.71);
            return @as(u64, @intFromFloat(r.x)) | @as(u64, @intFromFloat(r.y));
        }
    }.run);

    try stdout.print("\nEisenstein Norm:\n", .{});
    bench_ns("norm(5, 3)", N, struct {
        pub fn run() u64 {
            const r = deadband.eisenstein_norm(f64, 5, 3);
            return @as(u64, @intFromFloat(r));
        }
    }.run);

    try stdout.print("\nModular360 (f64):\n", .{});
    bench_ns("init(45.0)", N, struct {
        pub fn run() u64 {
            const r = deadband.Modular360(f64).init(45.0);
            return @as(u64, @intFromFloat(r.value));
        }
    }.run);
    bench_ns("add", N, struct {
        pub fn run() u64 {
            const M = deadband.Modular360(f64);
            const a = M.init(30.0);
            const b = M.init(350.0);
            const r = a.add(b);
            return @as(u64, @intFromFloat(r.value));
        }
    }.run);
    bench_ns("distance", N, struct {
        pub fn run() u64 {
            const M = deadband.Modular360(f64);
            const a = M.init(30.0);
            const b = M.init(350.0);
            const r = a.distance(b);
            return @as(u64, @intFromFloat(r));
        }
    }.run);

    try stdout.print("\nBMA Binary:\n", .{});
    const seq = [_]u1{ 1, 0, 0, 1, 0, 0, 1, 0, 0, 1 };
    bench_ns("bma_binary(len=10)", 100_000, struct {
        pub fn run() u64 {
            return deadband.bma_binary(&seq);
        }
    }.run);

    try stdout.print("\nFibonacci-Spline Search:\n", .{});
    bench_ns("1D golden-section (tol=1e-10)", 100_000, struct {
        pub fn run() u64 {
            const objective = struct {
                pub fn f(x: f64) f64 {
                    const d = x - 2.5;
                    return d * d;
                }
            }.f;
            const r = deadband.fibonacci_spline_search(f64, std.heap.page_allocator, objective, 0.0, 10.0, 1.0e-10);
            return @as(u64, @intFromFloat(r));
        }
    }.run);

    try stdout.print("\nBatch Eisenstein Snap (4 points):\n", .{});
    bench_ns("snap_batch(4)", N, struct {
        pub fn run() u64 {
            const xs = [_]f64{ 1.0, 0.5, 2.3, 0.1 };
            const ys = [_]f64{ 0.0, deadband.SQRT3 / 2.0, 1.1, 0.1 };
            var sx: [4]f64 = undefined;
            var sy: [4]f64 = undefined;
            deadband.eisenstein_snap_batch(4, &xs, &ys, &sx, &sy);
            return @as(u64, @intFromFloat(sx[0]));
        }
    }.run);

    try stdout.print("\nShell Decomposer (size=6):\n", .{});
    bench_ns("init + decompose", 100_000, struct {
        pub fn run() u64 {
            const points = [_][2]f64{
                .{ 0.0, 0.0 },
                .{ 1.0, 0.0 },
                .{ 0.5, deadband.SQRT3 / 2.0 },
                .{ 2.0, 0.0 },
                .{ 1.0, deadband.SQRT3 },
                .{ 0.1, 0.1 },
            };
            const SD = deadband.ShellDecomposer(6);
            const r = SD.init(points);
            return r.shell_count;
        }
    }.run);

    try stdout.print("\n{s}\n", .{"=" ** 50});
    try stdout.print("Done. All primitives benchmarked.\n\n", .{});
}
