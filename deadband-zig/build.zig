const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib = b.addStaticLibrary(.{
        .name = "deadband",
        .root_source_file = b.path("deadband.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    // Tests
    const unit_tests = b.addTest(.{
        .root_source_file = b.path("deadband.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);

    // Benchmark executable
    const bench = b.addExecutable(.{
        .name = "deadband-bench",
        .root_source_file = b.path("bench.zig"),
        .target = target,
        .optimize = .ReleaseFast,
    });
    b.installArtifact(bench);

    const run_bench = b.addRunArtifact(bench);
    const bench_step = b.step("bench", "Run benchmarks");
    bench_step.dependOn(&run_bench.step);
}
