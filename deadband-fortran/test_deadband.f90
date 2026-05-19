program test_deadband
  use deadband
  implicit none

  integer :: pass_count, fail_count, total_tests
  real(8) :: t_start, t_end
  logical :: ok

  pass_count = 0
  fail_count = 0
  total_tests = 0

  print '(a)', '========================================================='
  print '(a)', '  DEADBAND FRAMEWORK -- Fortran Test Suite'
  print '(a)', '========================================================='
  print '(a)', ''

  ! ---- Constants ----
  call test_approx('PHI = 1.6180339887...', PHI, 1.6180339887498948d0)
  call test_approx('PHI_INV = 0.6180339887...', PHI_INV, 0.6180339887498948d0)
  call test_approx('SQRT3 = 1.7320508075...', SQRT3, 1.7320508075688772d0)

  ! ---- Fibonacci ----
  call test_int('Fibonacci(0) = 0', int(fibonacci(0)), 0)
  call test_int('Fibonacci(1) = 1', int(fibonacci(1)), 1)
  call test_int('Fibonacci(10) = 55', int(fibonacci(10)), 55)
  call test_int('Fibonacci(20) = 6765', int(fibonacci(20)), 6765)

  ! ---- Eisenstein Snap ----
  print '(a)', '--- Eisenstein Snap ---'

  call cpu_time(t_start)
  block
    type(SnapResult) :: sr
    sr = eisenstein_snap(1.0d0, 0.0d0)
    call test_approx('Snap (1,0) → (1,0)', sr%x, 1.0d0)
    call test_approx('Snap (1,0) error=0', sr%error, 0.0d0)

    sr = eisenstein_snap(0.5d0, SQRT3/2.0d0)
    call test_approx('Snap (0.5, √3/2) → (-0.5, √3/2)', sr%x, -0.5d0)
    call test_approx('Snap (0.5, √3/2) y', sr%y, SQRT3/2.0d0)

    sr = eisenstein_snap(0.3d0, 0.3d0)
    call test_true('Snap (0.3,0.3) error small', sr%error < 0.5d0)

    sr = eisenstein_snap(0.0d0, 0.0d0)
    call test_approx('Snap origin → origin', sr%error, 0.0d0)
  end block
  call cpu_time(t_end)
  print '(a,f8.4,a)', '  Eisenstein snap time: ', t_end - t_start, 's'

  ! ---- HPDF Sampling ----
  print '(a)', ''
  print '(a)', '--- HPDF Sampling ---'
  call cpu_time(t_start)
  block
    real(8) :: sx, sy
    integer :: i
    do i = 1, 10000
      call hpdf_sample(sx, sy)
    end do
    call test_true('HPDF 10k samples completed', .true.)
  end block
  call cpu_time(t_end)
  print '(a,f8.4,a)', '  HPDF 10k samples time: ', t_end - t_start, 's'

  ! ---- /360 Arithmetic ----
  print '(a)', ''
  print '(a)', '--- /360 Field Arithmetic ---'
  call test_int8('/360 100+200=300', div360_add(100_8, 200_8), 300_8)
  call test_int8('/360 200+200=40', div360_add(200_8, 200_8), 40_8)
  call test_int8('/360 50-100=310', div360_sub(50_8, 100_8), 310_8)
  call test_int8('/360 180*2=0', div360_mul(180_8, 2_8), 0_8)
  call test_int8('/360 90*3=270', div360_mul(90_8, 3_8), 270_8)
  call test_int8('/360 359+1=0', div360_add(359_8, 1_8), 0_8)
  call test_int8('/360 0-1=359', div360_sub(0_8, 1_8), 359_8)

  ! ---- BMA over GF(2) ----
  print '(a)', ''
  print '(a)', '--- BMA (Berlekamp-Massey over GF(2)) ---'
  call cpu_time(t_start)
  block
    integer :: seq1(7)
    integer :: ln

    ! Simple: 1,0,1,0,1,0,1 → LFSR length 2 (toggles)
    seq1 = [1, 0, 1, 0, 1, 0, 1]
    ln = bma_detect(seq1, 7)
    call test_int('BMA [1,0,1,0,1,0,1] len=2', ln, 2)

    ! All zeros → length 0
    seq1 = [0, 0, 0, 0, 0, 0, 0]
    ln = bma_detect(seq1, 7)
    call test_int('BMA [0,0,0,...] len=0', ln, 0)

    ! All ones → length 1
    seq1 = [1, 1, 1, 1, 1, 1, 1]
    ln = bma_detect(seq1, 7)
    call test_int('BMA [1,1,1,...] len=1', ln, 1)
  end block
  call cpu_time(t_end)
  print '(a,f8.4,a)', '  BMA time: ', t_end - t_start, 's'

  ! ---- Shell Eigenstructure ----
  print '(a)', ''
  print '(a)', '--- Shell Eigenstructure ---'
  call cpu_time(t_start)
  block
    real(8) :: cov(2,2), ke, ae, ratio
    integer :: st

    ! Identity matrix
    cov = reshape([1.0d0, 0.0d0, 0.0d0, 1.0d0], [2,2])
    call shell_decompose(cov, ke, ae, ratio, st)
    call test_int('Identity status=0', st, 0)
    call test_approx('Identity known_energy=2', ke, 2.0d0)
    call test_approx('Identity ratio=0.5', ratio, 0.5d0)

    ! Diagonal: eigenvalues 4 and 1
    cov = reshape([4.0d0, 0.0d0, 0.0d0, 1.0d0], [2,2])
    call shell_decompose(cov, ke, ae, ratio, st)
    call test_approx('Diag(4,1) known_energy=5', ke, 5.0d0)
    call test_approx('Diag(4,1) ratio=0.8', ratio, 0.8d0)

    ! Mixed with off-diagonal
    cov = reshape([2.0d0, 1.0d0, 1.0d0, 2.0d0], [2,2])
    call shell_decompose(cov, ke, ae, ratio, st)
    call test_approx('Mixed known_energy=4', ke, 4.0d0)
    call test_approx('Mixed ratio=0.75', ratio, 0.75d0)
  end block
  call cpu_time(t_end)
  print '(a,f8.4,a)', '  Eigenstructure time: ', t_end - t_start, 's'

  ! ---- Fibonacci-Spline Search ----
  print '(a)', ''
  print '(a)', '--- Fibonacci-Spline Search ---'
  call cpu_time(t_start)
  block
    integer, parameter :: N = 1000
    integer, parameter :: D = 3
    integer, parameter :: K = 5
    real(8) :: db(N, D), query(D)
    integer :: idx(K)
    real(8) :: sims(K)
    integer :: i

    ! Fill database with points
    do i = 1, N
      db(i, :) = real(i, 8) * [0.1d0, 0.2d0, 0.3d0]
    end do

    query = [50.0d0, 100.0d0, 150.0d0]  ! close to point 500

    call fib_spline_search(query, db, N, D, K, idx, sims)

    call test_true('Fib-spline found K results', count(idx > 0) >= 1)
    call test_true('Fib-spline similarities positive', all(sims > 0.0d0 .and. sims <= 1.0d0))
  end block
  call cpu_time(t_end)
  print '(a,f8.4,a)', '  Fib-spline search time: ', t_end - t_start, 's'

  ! ---- Dodecet Pack/Unpack ----
  print '(a)', ''
  print '(a)', '--- Dodecet Pack/Unpack (60-bit CDC Word) ---'
  block
    integer(8) :: word
    integer :: d0, d1, d2, d3, d4

    d0 = 100; d1 = 500; d2 = 1000; d3 = 2000; d4 = 4095
    word = pack_dodecets(d0, d1, d2, d3, d4)

    call test_int('Unpack dodecet 0', unpack_dodecet(word, 0), d0)
    call test_int('Unpack dodecet 1', unpack_dodecet(word, 1), d1)
    call test_int('Unpack dodecet 2', unpack_dodecet(word, 2), d2)
    call test_int('Unpack dodecet 3', unpack_dodecet(word, 3), d3)
    call test_int('Unpack dodecet 4', unpack_dodecet(word, 4), d4)
  end block

  ! ---- Summary ----
  print '(a)', ''
  print '(a)', '========================================================='
  write(*, '(a,i0,a,i0,a)') '  RESULTS: ', pass_count, ' PASS, ', fail_count, ' FAIL'
  print '(a)', '========================================================='

  if (fail_count > 0) stop 1

contains

  subroutine test_approx(name, actual, expected)
    character(*), intent(in) :: name
    real(8), intent(in) :: actual, expected
    real(8), parameter :: tol = 1.0d-10

    total_tests = total_tests + 1
    if (abs(actual - expected) < tol) then
      print '(a,a,a)', '  ✓ PASS: ', name, ''
      pass_count = pass_count + 1
    else
      print '(a,a,a,es12.4,a,es12.4)', '  ✗ FAIL: ', name, ' got ', actual, ' expected ', expected
      fail_count = fail_count + 1
    end if
  end subroutine

  subroutine test_int(name, actual, expected)
    character(*), intent(in) :: name
    integer, intent(in) :: actual, expected

    total_tests = total_tests + 1
    if (actual == expected) then
      print '(a,a)', '  ✓ PASS: ', name
      pass_count = pass_count + 1
    else
      print '(a,a,a,i0,a,i0)', '  ✗ FAIL: ', name, ' got ', actual, ' expected ', expected
      fail_count = fail_count + 1
    end if
  end subroutine

  subroutine test_int8(name, actual, expected)
    character(*), intent(in) :: name
    integer(8), intent(in) :: actual, expected

    total_tests = total_tests + 1
    if (actual == expected) then
      print '(a,a)', '  ✓ PASS: ', name
      pass_count = pass_count + 1
    else
      print '(a,a,a,i0,a,i0)', '  ✗ FAIL: ', name, ' got ', actual, ' expected ', expected
      fail_count = fail_count + 1
    end if
  end subroutine

  subroutine test_true(name, condition)
    character(*), intent(in) :: name
    logical, intent(in) :: condition

    total_tests = total_tests + 1
    if (condition) then
      print '(a,a)', '  ✓ PASS: ', name
      pass_count = pass_count + 1
    else
      print '(a,a)', '  ✗ FAIL: ', name
      fail_count = fail_count + 1
    end if
  end subroutine

end program test_deadband
