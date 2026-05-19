module deadband
  implicit none
  public

  ! Golden ratio and derived constants
  real(8), parameter :: PHI = (1.0d0 + sqrt(5.0d0)) / 2.0d0
  real(8), parameter :: PHI_INV = 1.0d0 / PHI
  real(8), parameter :: SQRT3 = sqrt(3.0d0)

  ! Eisenstein lattice basis vectors
  real(8), parameter :: E1X = 1.0d0,          E1Y = 0.0d0
  real(8), parameter :: E2X = -0.5d0,          E2Y = SQRT3 / 2.0d0

  ! Dodecet: 12-bit nibble precision, 5 dodecets = 60 bits = 1 CDC word
  integer, parameter :: DODECET_BITS = 12
  integer, parameter :: DODECETS_PER_WORD = 5
  integer, parameter :: CDC_WORD_BITS = 60

  ! /360 field modulus
  integer(8), parameter :: FIELD_MOD = 360

  ! ---- Types ----
  type :: SnapResult
    real(8) :: x, y, error
  end type

  type :: EigenResult
    real(8) :: lambda1, lambda2   ! eigenvalues (sorted descending)
    real(8) :: v1x, v1y          ! eigenvector 1
    real(8) :: v2x, v2y          ! eigenvector 2
    integer :: status            ! 0=ok, 1=degenerate, 2=negative
  end type

contains

  ! =========================================================================
  ! Eisenstein lattice snap
  ! The Eisenstein integers are Z[ω] where ω = exp(2πi/3) = (-1+i√3)/2
  ! Basis: e1 = (1,0), e2 = (-1/2, √3/2)
  ! =========================================================================
  function eisenstein_snap(x, y) result(res)
    real(8), intent(in) :: x, y
    type(SnapResult) :: res

    ! Project onto Eisenstein basis: solve [e1|e2] [a; b] = (x,y)
    ! e1=(1,0), e2=(-1/2, √3/2)
    ! det = √3/2
    ! a = (√3/2·x + 1/2·y) / (√3/2) = x + y/√3
    ! b = y / (√3/2) = 2y/√3

    real(8) :: a, b, ia, ib

    a = x + y / SQRT3
    b = 2.0d0 * y / SQRT3

    ! Round to nearest Eisenstein integer
    ia = dnint(a)
    ib = dnint(b)

    ! Reconstruct snapped point
    res%x = ia * E1X + ib * E2X
    res%y = ia * E1Y + ib * E2Y

    ! Compute snap error
    res%error = sqrt((x - res%x)**2 + (y - res%y)**2)
  end function

  ! =========================================================================
  ! HPDF (Hexagonal Probability Density Function) sampling
  ! Samples uniformly in the Voronoi cell of the Eisenstein lattice
  ! =========================================================================
  subroutine hpdf_sample(sx, sy)
    real(8), intent(out) :: sx, sy

    real(8) :: u, v, cx, cy, rx, ry, best_x, best_y, best_d, d
    integer :: i, j

    ! Random point in fundamental parallelogram [0,1) × [0,1)
    call random_number(u)
    call random_number(v)

    ! Map to Eisenstein coordinates
    cx = u * E1X + v * E2X
    cy = u * E1Y + v * E2Y

    ! Check neighbors: snap to nearest Eisenstein point
    ! The Voronoi cell boundary requires checking nearby lattice points
    best_d = 1.0d30
    best_x = cx
    best_y = cy

    do i = -1, 1
      do j = -1, 1
        rx = cx - (i * E1X + j * E2X)
        ry = cy - (i * E1Y + j * E2Y)
        d = rx*rx + ry*ry
        if (d < best_d) then
          best_d = d
          best_x = rx
          best_y = ry
        end if
      end do
    end do

    sx = best_x
    sy = best_y
  end subroutine

  ! =========================================================================
  ! /360 field arithmetic
  ! All operations mod 360 — angular field, SE(5) constraint space
  ! Maps to dodecets: 360/5 dodecets = 72 degrees per dodecet slot
  ! 72° = 12 bits of nibble precision in each slot
  ! =========================================================================
  function div360_add(a, b) result(c)
    integer(8), intent(in) :: a, b
    integer(8) :: c
    c = mod(a + b, FIELD_MOD)
    if (c < 0) c = c + FIELD_MOD
  end function

  function div360_sub(a, b) result(c)
    integer(8), intent(in) :: a, b
    integer(8) :: c
    c = mod(a - b, FIELD_MOD)
    if (c < 0) c = c + FIELD_MOD
  end function

  function div360_mul(a, b) result(c)
    integer(8), intent(in) :: a, b
    integer(8) :: c
    c = mod(a * b, FIELD_MOD)
    if (c < 0) c = c + FIELD_MOD
  end function

  ! =========================================================================
  ! Berlekamp-Massey Algorithm over GF(2)
  ! Finds the minimal LFSR that generates the binary sequence
  ! Returns the LFSR length (constraint complexity)
  ! =========================================================================
  function bma_detect(sequence, n) result(ln)
    integer, intent(in) :: n
    integer, intent(in) :: sequence(n)  ! binary: 0 or 1
    integer :: ln

    integer :: m, i, j
    integer :: delta
    integer, allocatable :: c(:), b(:), t(:)

    allocate(c(0:n), b(0:n), t(0:n))
    c = 0; b = 0; t = 0
    c(0) = 1; b(0) = 1
    ln = 0
    m = -1  ! shift of previous copy

    do i = 0, n-1
      ! Compute discrepancy
      delta = sequence(i+1)
      do j = 1, ln
        delta = ieor(delta, c(j) * sequence(i+1-j))
      end do

      if (delta == 0) then
        ! no change needed
      else
        ! T = C copy
        t(0:ln) = c(0:ln)
        ! C = C + x^(i-m) * B
        do j = 0, ln
          if (b(j) == 1) then
            c(i - m + j) = ieor(c(i - m + j), 1)
          end if
        end do
        if (2*ln <= i) then
          ln = i + 1 - ln
          b(0:n) = 0
          b(0:size(t)-1) = t(0:size(t)-1)
          ! Copy t into b, keeping track of current b-length
          b = t
          m = i
        end if
      end if
    end do

    deallocate(c, b, t)
  end function

  ! =========================================================================
  ! Shell eigenstructure: 2x2 analytic eigendecomposition
  ! For a 2x2 symmetric matrix [[a,b],[b,d]]
  ! Closed-form eigenvalues and eigenvectors
  ! =========================================================================
  subroutine shell_decompose(cov, known_energy, assumed_energy, ratio, status)
    real(8), intent(in) :: cov(2,2)    ! symmetric covariance matrix
    real(8), intent(out) :: known_energy, assumed_energy, ratio
    integer, intent(out) :: status

    real(8) :: a, b, d, trace, det, disc, sqdisc
    real(8) :: lambda1, lambda2

    a = cov(1,1)
    b = cov(1,2)
    d = cov(2,2)

    trace = a + d
    det = a*d - b*b

    ! Discriminant = trace² - 4·det
    disc = trace*trace - 4.0d0*det

    if (disc < 0.0d0) then
      status = 2   ! negative discriminant (shouldn't happen for symmetric)
      known_energy = 0.0d0
      assumed_energy = 0.0d0
      ratio = 0.0d0
      return
    end if

    sqdisc = sqrt(disc)
    lambda1 = (trace + sqdisc) / 2.0d0
    lambda2 = (trace - sqdisc) / 2.0d0

    if (lambda1 < 1.0d-15 .and. lambda2 < 1.0d-15) then
      status = 1   ! degenerate
      known_energy = 0.0d0
      assumed_energy = 0.0d0
      ratio = 0.0d0
      return
    end if

    status = 0

    ! Known energy = sum of eigenvalues (trace)
    known_energy = lambda1 + lambda2

    ! Assumed energy = max eigenvalue (dominant mode)
    assumed_energy = max(lambda1, lambda2)

    ! Ratio = energy captured by dominant mode
    if (known_energy > 1.0d-15) then
      ratio = assumed_energy / known_energy
    else
      ratio = 1.0d0
    end if

  end subroutine

  ! =========================================================================
  ! Fibonacci-spline search
  ! Uses Fibonacci-like shrinking to find k nearest neighbors in D-dim database
  ! Works by iteratively narrowing the search band using golden ratio splits
  ! =========================================================================
  subroutine fib_spline_search(query, database, n, d, k, indices, similarities)
    real(8), intent(in) :: query(d)           ! query vector
    real(8), intent(in) :: database(n, d)     ! database of vectors
    integer, intent(in) :: n, d, k
    integer, intent(out) :: indices(k)
    real(8), intent(out) :: similarities(k)

    real(8), allocatable :: dists(:)
    real(8) :: tmp_dist
    integer :: i, j, lo, hi, mid, band_size, step
    real(8) :: diff

    allocate(dists(n))

    ! Compute all distances (L2)
    do i = 1, n
      tmp_dist = 0.0d0
      do j = 1, d
        diff = query(j) - database(i, j)
        tmp_dist = tmp_dist + diff*diff
      end do
      dists(i) = sqrt(tmp_dist)
    end do

    ! Fibonacci-golden narrowing: find the band containing k nearest
    ! Sort by Fibonacci-spline shrinking windows
    lo = 1
    hi = n
    step = 0

    do while (hi - lo > k .and. step < 50)
      band_size = hi - lo + 1
      mid = lo + nint(band_size * PHI_INV)  ! golden split
      if (mid < lo + k) mid = lo + k
      if (mid > hi) mid = hi

      ! Check if the k-th nearest is in [lo, mid] or [mid+1, hi]
      ! Simple heuristic: compare mid-th distance to average
      if (dists(mid) < sum(dists(lo:hi)) / real(hi-lo+1, 8)) then
        hi = mid
      else
        lo = mid + 1
      end if
      step = step + 1
    end do

    ! Final selection: simple selection sort for k smallest in [lo, hi]
    ! (k is typically small, so O(k·n) is fine)
    do i = 1, min(k, n)
      indices(i) = lo
      do j = lo+1, hi
        if (j <= n .and. dists(j) < dists(indices(i))) then
          indices(i) = j
        end if
      end do
      if (indices(i) <= n) then
        similarities(i) = 1.0d0 / (1.0d0 + dists(indices(i)))
        dists(indices(i)) = 1.0d30  ! mark as used
      end if
    end do

    deallocate(dists)
  end subroutine

  ! =========================================================================
  ! Utility: Fibonacci number
  ! =========================================================================
  function fibonacci(n) result(f)
    integer, intent(in) :: n
    integer(8) :: f
    integer(8) :: a, b, i

    if (n <= 0) then; f = 0; return; end if
    if (n == 1) then; f = 1; return; end if

    a = 0; b = 1
    do i = 2, n
      f = a + b
      a = b
      b = f
    end do
  end function

  ! =========================================================================
  ! Utility: Pack 5 dodecets into 60-bit CDC word
  ! Each dodecet is 12 bits (0..4095)
  ! =========================================================================
  function pack_dodecets(d0, d1, d2, d3, d4) result(word)
    integer, intent(in) :: d0, d1, d2, d3, d4
    integer(8) :: word

    word = ior(ior(ior(ior( &
      int(d0, 8), &
      ishft(int(d1, 8), 12)), &
      ishft(int(d2, 8), 24)), &
      ishft(int(d3, 8), 36)), &
      ishft(int(d4, 8), 48))
  end function

  ! Unpack dodecet i from a 60-bit word
  function unpack_dodecet(word, i) result(d)
    integer(8), intent(in) :: word
    integer, intent(in) :: i   ! 0-4
    integer :: d

    d = int(iand(ishft(word, -12*i), int(z'FFF', 8)))
  end function

end module deadband
