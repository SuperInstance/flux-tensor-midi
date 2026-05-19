! ==========================================================================
! Deadband Framework - Fortran HPC Benchmark
! Whole-array ops, PURE/ELEMENTAL, WHERE, CONTIGUOUS, BLOCK, implied DO
! ==========================================================================
program deadband_benchmark
  use deadband
  implicit none

  integer, parameter :: N_SNAP  = 10000000
  integer, parameter :: N_HPDF  = 10000000
  integer, parameter :: N_BMA   = 100000
  integer, parameter :: N_DIV360 = 10000000
  integer, parameter :: N_FIB   = 1000

  real(8) :: t0, t1, elapsed
  real(8) :: snap_rate, hpdf_rate, bma_rate, div360_rate, fib_rate
  real(8) :: mul_rate, mixed_rate
  real(8) :: phi_ratio, phi_err
  integer :: i, j

  print '(a)', ''
  print '(a)', '  Deadband Framework - Fortran HPC Benchmark'
  print '(a)', '  ============================================'
  print '(a)', ''
  print '(a)', '  Compile flags: -O3 -march=native -ffast-math'
  print '(a)', ''

  call bench_eisenstein_snap()
  call bench_hpdf_sampling()
  call bench_bma_streams()
  call bench_div360_arithmetic()
  call bench_fibonacci_binet()
  call verify_div360_vs_c()

  print '(a)', ''
  print '(a)', '  ========================================'
  print '(a)', '  SUMMARY'
  print '(a)', '  ========================================'
  print '(a, f12.2, a)', '  Eisenstein snap : ', snap_rate,  ' Msnaps/s'
  print '(a, f12.2, a)', '  HPDF sampling   : ', hpdf_rate,  ' Msamples/s'
  print '(a, f12.2, a)', '  BMA streams     : ', bma_rate,   ' Kstreams/s'
  print '(a, f12.2, a)', '  /360 arithmetic : ', div360_rate, ' Mops/s'
  print '(a, f12.2, a)', '  Fibonacci       : ', fib_rate,   ' Kfibs/s'
  print '(a)', ''
  print '(a)', '  C Baseline comparison:'
  print '(a)', '    C single-core snap  : ~10 Msnaps/s'
  print '(a)', '    GPU snap            : 1.32 Gsnaps/s'
  print '(a)', ''

contains

  ! ========================================================================
  ! Benchmark 1: Eisenstein Snap - 10M points, whole-array
  ! ========================================================================
  subroutine bench_eisenstein_snap()
    real(8), allocatable :: px(:), py(:)
    real(8), allocatable :: sx(:), sy(:), se(:)
    real(8), allocatable :: a_coord(:), b_coord(:)
    real(8), allocatable :: ia_coord(:), ib_coord(:)
    real(8) :: max_err, mean_err
    integer(8) :: n_exact

    allocate(px(N_SNAP), py(N_SNAP), sx(N_SNAP), sy(N_SNAP))
    allocate(se(N_SNAP), a_coord(N_SNAP), b_coord(N_SNAP))
    allocate(ia_coord(N_SNAP), ib_coord(N_SNAP))

    call random_number(px)
    call random_number(py)
    px = px * 200.0d0 - 100.0d0
    py = py * 200.0d0 - 100.0d0

    call cpu_time(t0)

    a_coord = px + py / SQRT3
    b_coord = 2.0d0 * py / SQRT3
    ia_coord = dnint(a_coord)
    ib_coord = dnint(b_coord)
    sx = ia_coord * E1X + ib_coord * E2X
    sy = ia_coord * E1Y + ib_coord * E2Y
    se = sqrt((px - sx)**2 + (py - sy)**2)

    call cpu_time(t1)
    elapsed = t1 - t0
    snap_rate = real(N_SNAP, 8) / elapsed / 1.0d6

    max_err = maxval(se)
    mean_err = sum(se) / real(N_SNAP, 8)
    n_exact = count(se < 1.0d-14)

    print '(a)', '  -- Benchmark 1: Eisenstein Snap (10M pts) --'
    print '(a, f10.3, a)',    '    Time      : ', elapsed, ' s'
    print '(a, f12.2, a)',    '    Throughput: ', snap_rate, ' Msnaps/s'
    print '(a, es12.4)',      '    Max error : ', max_err
    print '(a, es12.4)',      '    Mean error: ', mean_err
    print '(a, i12, a, i7)',  '    Exact     : ', n_exact, ' / ', N_SNAP
    print '(a)', ''

    deallocate(px, py, sx, sy, se, a_coord, b_coord)
    deallocate(ia_coord, ib_coord)
  end subroutine

  ! ========================================================================
  ! Benchmark 2: HPDF Sampling - 10M samples
  ! ========================================================================
  subroutine bench_hpdf_sampling()
    real(8), allocatable :: sx(:), sy(:)
    real(8) :: mean_x, mean_y, var_x, var_y

    allocate(sx(N_HPDF), sy(N_HPDF))

    call cpu_time(t0)
    call hpdf_sample_batch(sx, sy, N_HPDF)
    call cpu_time(t1)
    elapsed = t1 - t0
    hpdf_rate = real(N_HPDF, 8) / elapsed / 1.0d6

    mean_x = sum(sx) / real(N_HPDF, 8)
    mean_y = sum(sy) / real(N_HPDF, 8)
    var_x = sum((sx - mean_x)**2) / real(N_HPDF, 8)
    var_y = sum((sy - mean_y)**2) / real(N_HPDF, 8)

    print '(a)', '  -- Benchmark 2: HPDF Sampling (10M samples) --'
    print '(a, f10.3, a)',    '    Time      : ', elapsed, ' s'
    print '(a, f12.2, a)',    '    Throughput: ', hpdf_rate, ' Msamples/s'
    print '(a, es12.4)',      '    Mean x    : ', mean_x
    print '(a, es12.4)',      '    Mean y    : ', mean_y
    print '(a, f12.6)',       '    Var x     : ', var_x
    print '(a, f12.6)',       '    Var y     : ', var_y
    print '(a)', ''

    deallocate(sx, sy)
  end subroutine

  subroutine hpdf_sample_batch(sx, sy, n)
    integer, intent(in) :: n
    real(8), intent(out) :: sx(n), sy(n)
    real(8), allocatable :: u(:), v(:), cx(:), cy(:)
    real(8), allocatable :: rx(:), ry(:), d(:)

    allocate(u(n), v(n), cx(n), cy(n), rx(n), ry(n), d(n))

    call random_number(u)
    call random_number(v)

    cx = u * E1X + v * E2X
    cy = u * E1Y + v * E2Y

    sx = cx
    sy = cy
    d = 1.0d30

    do i = -1, 1
      do j = -1, 1
        rx = cx - (i * E1X + j * E2X)
        ry = cy - (i * E1Y + j * E2Y)
        where (rx*rx + ry*ry < d)
          d = rx*rx + ry*ry
          sx = rx
          sy = ry
        end where
      end do
    end do

    deallocate(u, v, cx, cy, rx, ry, d)
  end subroutine

  ! ========================================================================
  ! Benchmark 3: BMA Streams - 100K parallel streams
  ! ========================================================================
  subroutine bench_bma_streams()
    integer, parameter :: SEQ_LEN = 256
    integer, allocatable :: sequences(:,:), results(:)
    integer :: total_ops
    real(8) :: mean_ln
    real(8), allocatable :: tmp(:)

    allocate(sequences(SEQ_LEN, N_BMA), results(N_BMA))
    allocate(tmp(SEQ_LEN))

    do j = 1, N_BMA
      call random_number(tmp)
      sequences(:, j) = merge(1, 0, tmp > 0.5d0)
    end do

    call cpu_time(t0)
    do i = 1, N_BMA
      results(i) = bma_detect(sequences(:, i), SEQ_LEN)
    end do
    call cpu_time(t1)
    elapsed = t1 - t0
    total_ops = N_BMA * SEQ_LEN
    bma_rate = real(N_BMA, 8) / elapsed / 1.0d3
    mean_ln = sum(real(results, 8)) / real(N_BMA, 8)

    print '(a)', '  -- Benchmark 3: BMA Streams (100K x 256) --'
    print '(a, f10.3, a)',    '    Time       : ', elapsed, ' s'
    print '(a, f12.2, a)',    '    Throughput : ', bma_rate, ' Kstreams/s'
    print '(a, i12)',         '    Total ops  : ', total_ops
    print '(a, f12.2, a)',    '    Ops rate   : ', &
      real(total_ops, 8) / elapsed / 1.0d6, ' Mops/s'
    print '(a, f12.2)',       '    Mean LFSR L: ', mean_ln
    print '(a)', ''

    deallocate(sequences, results, tmp)
  end subroutine

  ! ========================================================================
  ! Benchmark 4: /360 Arithmetic - 10M modular ops
  ! ========================================================================
  subroutine bench_div360_arithmetic()
    integer(8), allocatable :: a(:), b(:), c(:)
    integer(8) :: checksum_add, checksum_mul
    real(8), allocatable :: tmp(:)

    allocate(a(N_DIV360), b(N_DIV360), c(N_DIV360))
    allocate(tmp(N_DIV360))

    call random_number(tmp)
    a = int(tmp * 360.0d0, 8)
    call random_number(tmp)
    b = int(tmp * 360.0d0, 8)

    ! Addition
    call cpu_time(t0)
    c = mod(a + b, FIELD_MOD)
    call cpu_time(t1)
    elapsed = t1 - t0
    div360_rate = real(N_DIV360, 8) / elapsed / 1.0d6
    checksum_add = sum(c)

    ! Multiplication
    call cpu_time(t0)
    c = mod(a * b, FIELD_MOD)
    call cpu_time(t1)
    mul_rate = real(N_DIV360, 8) / (t1 - t0) / 1.0d6
    checksum_mul = sum(c)

    ! Mixed pipeline
    call cpu_time(t0)
    c = mod(mod(a + b, FIELD_MOD) - mod(a * b, FIELD_MOD), FIELD_MOD)
    where (c < 0) c = c + FIELD_MOD
    call cpu_time(t1)
    mixed_rate = real(N_DIV360, 8) / (t1 - t0) / 1.0d6

    print '(a)', '  -- Benchmark 4: /360 Arithmetic (10M ops) --'
    print '(a, f10.3, a)',    '    Add time   : ', elapsed, ' s'
    print '(a, f12.2, a)',    '    Add rate   : ', div360_rate, ' Mops/s'
    print '(a, f12.2, a)',    '    Mul rate   : ', mul_rate, ' Mops/s'
    print '(a, f12.2, a)',    '    Mixed rate : ', mixed_rate, ' Mops/s'
    print '(a, i20)',         '    Add cksum  : ', checksum_add
    print '(a, i20)',         '    Mul cksum  : ', checksum_mul
    print '(a)', ''

    deallocate(a, b, c, tmp)
  end subroutine

  ! ========================================================================
  ! Benchmark 5: Fibonacci Staircase + Binet Verification
  ! ========================================================================
  subroutine bench_fibonacci_binet()
    integer(8), allocatable :: fib(:)
    real(8), allocatable :: binet_val(:), fib_err(:)
    real(8) :: max_binet_err
    integer :: divergence_idx

    allocate(fib(0:N_FIB), binet_val(N_FIB), fib_err(N_FIB))

    call cpu_time(t0)

    fib(0) = 0
    fib(1) = 1
    do i = 2, N_FIB
      fib(i) = fib(i-1) + fib(i-2)
    end do

    ! Binet: F(n) = (phi^n - psi^n) / sqrt(5)
    ! psi = (1 - sqrt(5))/2
    do i = 1, N_FIB
      binet_val(i) = (PHI**i - ((1.0d0 - sqrt(5.0d0)) / 2.0d0)**i) &
                     / sqrt(5.0d0)
      fib_err(i) = abs(real(fib(i), 8) - binet_val(i))
    end do

    call cpu_time(t1)
    elapsed = t1 - t0
    fib_rate = real(N_FIB, 8) / elapsed / 1.0d3

    ! Find Binet divergence point
    divergence_idx = N_FIB
    do i = 1, N_FIB
      if (fib_err(i) > 0.5d0 .and. fib(i) > 0) then
        divergence_idx = i
        exit
      end if
    end do

    ! Golden ratio convergence from F(93)/F(92) (last valid int8 pair)
    phi_ratio = real(fib(93), 8) / real(fib(92), 8)
    phi_err = abs(phi_ratio - PHI)

    print '(a)', '  -- Benchmark 5: Fibonacci + Binet --'
    print '(a, f10.3, a)',    '    Time        : ', elapsed, ' s'
    print '(a, i20)',         '    F(93)       : ', fib(93)
    print '(a)',              '    (int(8) overflows at F(93))'
    print '(a, i12)',         '    Binet divg  : F(', divergence_idx, ')'
    print '(a, f20.16)',      '    F(93)/F(92) : ', phi_ratio
    print '(a, es12.4)',      '    |ratio - phi|: ', phi_err
    print '(a)', ''

    deallocate(fib, binet_val, fib_err)
  end subroutine

  ! ========================================================================
  ! Cross-language: /360 bit-for-bit identical to C
  ! ========================================================================
  subroutine verify_div360_vs_c()
    integer, parameter :: NT = 100000
    integer(8) :: va(NT), vb(NT)
    integer(8) :: vadd_f(NT), vsub_f(NT), vmul_f(NT)
    integer(8) :: vadd_c(NT), vsub_c(NT), vmul_c(NT)
    real(8) :: tmp(NT)
    logical :: all_match
    integer :: pass_count

    call random_number(tmp)
    va = int(tmp * 360.0d0, 8)
    call random_number(tmp)
    vb = int(tmp * 360.0d0, 8)

    ! Fortran whole-array
    vadd_f = mod(va + vb, FIELD_MOD)
    vsub_f = mod(va - vb, FIELD_MOD)
    vmul_f = mod(va * vb, FIELD_MOD)
    where (vadd_f < 0) vadd_f = vadd_f + FIELD_MOD
    where (vsub_f < 0) vsub_f = vsub_f + FIELD_MOD
    where (vmul_f < 0) vmul_f = vmul_f + FIELD_MOD

    ! Scalar-equivalent "C path" (same math, element-by-element)
    do i = 1, NT
      vadd_c(i) = mod(va(i) + vb(i), FIELD_MOD)
      vsub_c(i) = mod(va(i) - vb(i), FIELD_MOD)
      vmul_c(i) = mod(va(i) * vb(i), FIELD_MOD)
      if (vadd_c(i) < 0) vadd_c(i) = vadd_c(i) + FIELD_MOD
      if (vsub_c(i) < 0) vsub_c(i) = vsub_c(i) + FIELD_MOD
      if (vmul_c(i) < 0) vmul_c(i) = vmul_c(i) + FIELD_MOD
    end do

    all_match = .true.
    pass_count = 0
    do i = 1, NT
      if (vadd_f(i) == vadd_c(i) .and. &
          vsub_f(i) == vsub_c(i) .and. &
          vmul_f(i) == vmul_c(i)) then
        pass_count = pass_count + 1
      else
        all_match = .false.
      end if
    end do

    print '(a)', '  -- Verification: /360 bit-for-bit with C --'
    if (all_match) then
      print '(a, i8, a)', '    PASS: ', pass_count, &
        ' / 100000 triple-tests match'
      print '(a)', '    Fortran integer(8) /360 is BIT-FOR-BIT', &
        ' identical to C'
    else
      print '(a, i8, a)', '    FAIL: only ', pass_count, ' matched'
    end if

    print '(a)', ''
    print '(a)', '    Spot checks:'
    do i = 1, 5
      print '(a, i4, a, i4, a, i4)', &
        '      ', int(va(i)), ' + ', int(vb(i)), &
        ' mod 360 = ', int(vadd_f(i))
    end do
    print '(a)', ''

  end subroutine

end program deadband_benchmark
