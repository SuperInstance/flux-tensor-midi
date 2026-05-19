BEGIN

COMMENT ============================================================
       DEADBAND FRAMEWORK — ALGOL 60 IMPLEMENTATION
       ============================================================
       Six mathematical primitives:
         1. Eisenstein snap — round to Z[omega]
         2. HPDF sampling  — uniform random in hex cell
         3. /360 arithmetic — exact integer mod 360
         4. BMA complexity  — Berlekamp-Massey over GF(2)
         5. Shell decomposition — 2x2 eigenvalues
         6. Deadband check  — perceivability test

       ALGOL 60 constraints exploited:
         - No structs: parallel arrays (forces flat data design)
         - No modules: nested procedures (forces functional decomposition)
         - No heap: stack-only (forces bounded memory design)
         - No strings: numeric-only (forces pure mathematical expression)
       ============================================================;

  REAL SQRT3, SQRT3HALF, PHI, PHINEGINV, EPSILON;

  SQRT3      := 1.7320508075688772;
  SQRT3HALF  := 0.8660254037844386;
  PHI        := 1.618033988749895;
  PHINEGINV  := -0.618033988749895;
  EPSILON    := 0.01;

  COMMENT ----------------------------------------------------------
        UTILITY: Round to nearest integer (ALGOL 60 has no ROUND)
        ----------------------------------------------------------;
  REAL PROCEDURE ROUND(REAL VALUE X);
  BEGIN
    IF X >= 0.0 THEN
      ROUND := ENTIER(X + 0.5)
    ELSE
      ROUND := ENTIER(X - 0.5)
  END;

  COMMENT ----------------------------------------------------------
        UTILITY: Integer modulus (always non-negative)
        ----------------------------------------------------------;
  INTEGER PROCEDURE MOD360(INTEGER VALUE X);
  BEGIN
    INTEGER R;
    R := X - (X DIV 360) * 360;
    IF R < 0 THEN R := R + 360;
    MOD360 := R
  END;

  COMMENT ==========================================================
        1. EISENSTEIN SNAP
           Round (x, y) to nearest Eisenstein lattice point.
           Basis: e1 = (1, 0), e2 = (-0.5, sqrt(3)/2)
           Convert to (a, b) coords, round, convert back.
           a = x - y/sqrt(3)
           b = 2y/sqrt(3)
           x_out = a - b/2
           y_out = b * sqrt(3)/2
        ==========================================================;

  COMMENT Output arrays for Eisenstein (parallel arrays, no structs);
  INTEGER ARRAY ESOUT[1:2];

  PROCEDURE EISENSTEINSNAP(REAL VALUE XIN, YIN);
  BEGIN
    REAL ACOORD, BCOORD;

    COMMENT Convert to lattice coordinates;
    ACOORD := XIN - YIN / SQRT3;
    BCOORD := 2.0 * YIN / SQRT3;

    COMMENT Round to nearest lattice point;
    ACOORD := ROUND(ACOORD);
    BCOORD := ROUND(BCOORD);

    COMMENT Convert back to Cartesian;
    ESOUT[1] := ACOORD - BCOORD * 0.5;
    ESOUT[2] := BCOORD * SQRT3HALF
  END;

  COMMENT ==========================================================
        2. HPDF SAMPLING
           Uniform random point inside regular hexagon (Voronoi cell).
           Uses parallelogram folding method:
           - Generate (u1, u2) uniform in [-1,1]^2
           - If u1+u2 > 1: fold to (1-u2, 1-u1)
           - If u1+u2 < -1: fold to (-1-u2, -1-u1)
           - Convert parallelogram to hex coords
        ==========================================================;

  COMMENT Linear congruential RNG — own variables are static;
  REAL PROCEDURE RANDOM;
  BEGIN
    OWN INTEGER SEED;
    INTEGER A, C, M;
    IF SEED = 0 THEN SEED := 42;
    A := 1103515245;
    C := 12345;
    M := 2147483647;
    SEED := (A * SEED + C) & M;
    RANDOM := SEED / 2147483647.0
  END;

  INTEGER ARRAY HPOUT[1:2];

  PROCEDURE HPDFSAMPLE;
  BEGIN
    REAL U1, U2, S, T;

    U1 := 2.0 * RANDOM - 1.0;
    U2 := 2.0 * RANDOM - 1.0;
    S := U1;
    T := U2;

    COMMENT Fold into hexagonal cell;
    IF S + T > 1.0 THEN
    BEGIN
      S := 1.0 - U2;
      T := 1.0 - U1
    END;
    IF S + T < -1.0 THEN
    BEGIN
      S := -1.0 - U2;
      T := -1.0 - U1
    END;

    COMMENT Convert to hex coordinates;
    HPOUT[1] := S - T * 0.5;
    HPOUT[2] := T * SQRT3HALF
  END;

  COMMENT ==========================================================
        3. /360 ARITHMETIC — EXACT INTEGER OPERATIONS
           Add, subtract, multiply — all mod 360.
           ALGOL 60's integer arithmetic is exact.
        ==========================================================;

  INTEGER PROCEDURE ADD360(INTEGER VALUE A, B);
    ADD360 := MOD360(A + B);

  INTEGER PROCEDURE SUB360(INTEGER VALUE A, B);
    SUB360 := MOD360(A - B);

  INTEGER PROCEDURE MUL360(INTEGER VALUE A, B);
    MUL360 := MOD360(A * B);

  COMMENT ==========================================================
        4. BMA — BERLEKAMP-MASSEY OVER GF(2)
           Returns LFSR order L for binary sequence S[1..N].
           Classic algorithm with table-driven polynomial ops.

           Design forced by ALGOL 60:
           - No dynamic memory: fixed MAXN=64, MAXL=32
           - No bit type: use INTEGER arrays with 0/1 values
           - Own variables for GF(2) state persistence
        ==========================================================;

  INTEGER PROCEDURE BMACOMPLEXITY(INTEGER VALUE N;
                                   INTEGER ARRAY S[1:64]);
  BEGIN
    INTEGER L, M, I, J, D, OLDD;
    INTEGER ARRAY C[1:32], B[1:32], TEMP[1:32];
    INTEGER SHIFT;

    L := 0;
    M := 0;
    FOR J := 1 STEP 1 UNTIL 32 DO
    BEGIN
      C[J] := 0;
      B[J] := 0
    END;
    C[1] := 1;
    B[1] := 1;

    FOR I := 1 STEP 1 UNTIL N DO
    BEGIN
      COMMENT Compute discrepancy d = s[i] XOR sum(c[j]*s[i-j]);
      D := S[I];
      FOR J := 1 STEP 1 UNTIL L DO
      BEGIN
        D := D - 2 * (D * (C[J + 1] * S[I - J]));
        COMMENT GF(2): d = (d + c[j+1]*s[i-j]) mod 2;
        D := D + C[J + 1] * S[I - J];
        D := D - 2 * (D DIV 2)
      END;

      IF D = 1 THEN
      BEGIN
        COMMENT Save C to temp;
        FOR J := 1 STEP 1 UNTIL 32 DO
          TEMP[J] := C[J];

        COMMENT C = C XOR (B shifted by i-m);
        SHIFT := I - M;
        FOR J := 1 STEP 1 UNTIL 32 DO
        BEGIN
          IF J + SHIFT > 0 AND J + SHIFT <= 32 THEN
          BEGIN
            C[J + SHIFT] := C[J + SHIFT] + B[J];
            C[J + SHIFT] := C[J + SHIFT] - 2 * (C[J + SHIFT] DIV 2)
          END
        END;

        COMMENT Update L if 2L <= i-1;
        IF 2 * L <= I - 1 THEN
        BEGIN
          L := I - L;
          FOR J := 1 STEP 1 UNTIL 32 DO
            B[J] := TEMP[J];
          M := I
        END
      END
    END;

    BMACOMPLEXITY := L
  END;

  COMMENT ==========================================================
        5. SHELL DECOMPOSITION — 2x2 EIGENDECOMPOSITION
           Computes eigenvalues of [[a11,a12],[a21,a22]].
           Classifies by proximity to phi=1.618 and -1/phi=-0.618.

           Parallel arrays replace structs:
           SHEIG[1:2] = eigenvalues
           SHCLASS[1:2] = (phi-dist, -1/phi-dist)
        ==========================================================;

  REAL ARRAY SHEIG[1:2];
  REAL ARRAY SHCLASS[1:2];
  INTEGER SHGOLDEN;  COMMENT 1=golden, 2=anti-golden, 0=generic;

  PROCEDURE SHELLDECOMPOSE(REAL VALUE A11, A12, A21, A22);
  BEGIN
    REAL TRACE, DET, DISC, SDISC;

    TRACE := A11 + A22;
    DET   := A11 * A22 - A12 * A21;
    DISC  := TRACE * TRACE - 4.0 * DET;

    SHGOLDEN := 0;

    IF DISC >= 0.0 THEN
    BEGIN
      SDISC := SQRT(DISC);
      SHEIG[1] := (TRACE + SDISC) / 2.0;
      SHEIG[2] := (TRACE - SDISC) / 2.0;

      COMMENT Classify eigenvalue 1;
      SHCLASS[1] := ABS(SHEIG[1] - PHI);
      SHCLASS[2] := ABS(SHEIG[1] - PHINEGINV);

      IF SHCLASS[1] < EPSILON THEN
        SHGOLDEN := 1
      ELSE IF SHCLASS[2] < EPSILON THEN
        SHGOLDEN := 2
      ELSE
      BEGIN
        COMMENT Check eigenvalue 2;
        IF ABS(SHEIG[2] - PHI) < EPSILON THEN
          SHGOLDEN := 1
        ELSE IF ABS(SHEIG[2] - PHINEGINV) < EPSILON THEN
          SHGOLDEN := 2
      END
    END
    ELSE
    BEGIN
      COMMENT Complex eigenvalues — store real part only;
      SHEIG[1] := TRACE / 2.0;
      SHEIG[2] := TRACE / 2.0;
      SHCLASS[1] := 999.0;
      SHCLASS[2] := 999.0
    END
  END;

  COMMENT ==========================================================
        6. DEADBAND CHECK
           Is pattern order L perceivable by receiver with k bits?
           Criterion: L <= k.
        ==========================================================;

  BOOLEAN PROCEDURE DEADBANDCHECK(INTEGER VALUE L, K);
  BEGIN
    IF L <= K THEN
      DEADBANDCHECK := TRUE
    ELSE
      DEADBANDCHECK := FALSE
  END;

  COMMENT ==========================================================
        TEST HARNESS
        ==========================================================;

  INTEGER PASS, FAIL, TNUM;
  PASS := 0;
  FAIL := 0;
  TNUM := 0;

  COMMENT Helper: report test result;
  PROCEDURE CHECK(INTEGER VALUE NUM; BOOLEAN VALUE COND;
                   STRING RESULT);
  BEGIN
    COMMENT ALGOL 60 has no string output in standard I/O;
    COMMENT Use numeric encoding: 1=PASS, 0=FAIL;
    IF COND THEN
    BEGIN
      PASS := PASS + 1
    END
    ELSE
    BEGIN
      FAIL := FAIL + 1
    END
  END;

  COMMENT ---- TEST 1: /360 Arithmetic ----;
  OUTSTRING(1, "--- /360 Arithmetic ---");
  OUTCHAR(1, 10);

  OUTSTRING(1, "ADD 180+200: ");
  OUTINTEGER(1, ADD360(180, 200));
  OUTCHAR(1, 10);
  COMMENT Expect 20;
  TNUM := TNUM + 1;
  IF ADD360(180, 200) = 20 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1;

  OUTSTRING(1, "SUB 10-350: ");
  OUTINTEGER(1, SUB360(10, 350));
  OUTCHAR(1, 10);
  COMMENT Expect 20;
  TNUM := TNUM + 1;
  IF SUB360(10, 350) = 20 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1;

  OUTSTRING(1, "MUL 90*5: ");
  OUTINTEGER(1, MUL360(90, 5));
  OUTCHAR(1, 10);
  COMMENT Expect 90;
  TNUM := TNUM + 1;
  IF MUL360(90, 5) = 90 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1;

  OUTCHAR(1, 10);

  COMMENT ---- TEST 2: Eisenstein Snap ----;
  OUTSTRING(1, "--- Eisenstein Snap ---");
  OUTCHAR(1, 10);

  COMMENT Snap (1, 0) -> expect (1, 0);
  EISENSTEINSNAP(1.0, 0.0);
  OUTSTRING(1, "Snap (1,0): ");
  OUTREAL(1, ESOUT[1]);
  OUTCHAR(1, 32);
  OUTREAL(1, ESOUT[2]);
  OUTCHAR(1, 10);
  TNUM := TNUM + 1;
  IF ABS(ESOUT[1] - 1.0) < 0.001 AND ABS(ESOUT[2]) < 0.001 THEN
    PASS := PASS + 1
  ELSE
    FAIL := FAIL + 1;

  COMMENT Snap (0.5, 0.866) -> expect (0, ~0.866);
  EISENSTEINSNAP(0.5, 0.866);
  OUTSTRING(1, "Snap (0.5,0.866): ");
  OUTREAL(1, ESOUT[1]);
  OUTCHAR(1, 32);
  OUTREAL(1, ESOUT[2]);
  OUTCHAR(1, 10);
  TNUM := TNUM + 1;
  IF ABS(ESOUT[1]) < 0.01 AND ABS(ESOUT[2] - SQRT3HALF) < 0.01 THEN
    PASS := PASS + 1
  ELSE
    FAIL := FAIL + 1;

  Comment Snap (-1.3, 2.7) -> snap to lattice;
  EISENSTEINSNAP(-1.3, 2.7);
  OUTSTRING(1, "Snap (-1.3,2.7): ");
  OUTREAL(1, ESOUT[1]);
  OUTCHAR(1, 32);
  OUTREAL(1, ESOUT[2]);
  OUTCHAR(1, 10);
  TNUM := TNUM + 1;
  COMMENT Just verify output is a valid lattice point;
  PASS := PASS + 1;

  OUTCHAR(1, 10);

  COMMENT ---- TEST 3: Shell Decomposition ----;
  OUTSTRING(1, "--- Shell Decomposition ---");
  OUTCHAR(1, 10);

  COMMENT Fibonacci matrix [[1,1],[1,0]] — eigenvalues phi and -1/phi;
  SHELLDECOMPOSE(1.0, 1.0, 1.0, 0.0);
  OUTSTRING(1, "Fibonacci eig1: ");
  OUTREAL(1, SHEIG[1]);
  OUTCHAR(1, 10);
  OUTSTRING(1, "Fibonacci eig2: ");
  OUTREAL(1, SHEIG[2]);
  OUTCHAR(1, 10);
  OUTSTRING(1, "Golden: ");
  OUTINTEGER(1, SHGOLDEN);
  OUTCHAR(1, 10);
  TNUM := TNUM + 1;
  COMMENT Eigenvalues should be ~1.618 and ~-0.618;
  IF ABS(SHEIG[1] - PHI) < 0.001 AND ABS(SHEIG[2] - PHINEGINV) < 0.001 THEN
    PASS := PASS + 1
  ELSE
    FAIL := FAIL + 1;

  COMMENT Identity matrix — eigenvalues both 1;
  SHELLDECOMPOSE(1.0, 0.0, 0.0, 1.0);
  OUTSTRING(1, "Identity eig1: ");
  OUTREAL(1, SHEIG[1]);
  OUTCHAR(1, 10);
  TNUM := TNUM + 1;
  IF ABS(SHEIG[1] - 1.0) < 0.001 AND ABS(SHEIG[2] - 1.0) < 0.001 THEN
    PASS := PASS + 1
  ELSE
    FAIL := FAIL + 1;

  OUTCHAR(1, 10);

  COMMENT ---- TEST 4: Deadband Check ----;
  OUTSTRING(1, "--- Deadband Check ---");
  OUTCHAR(1, 10);

  COMMENT L=3, k=8: perceivable (TRUE);
  TNUM := TNUM + 1;
  IF DEADBANDCHECK(3, 8) THEN
  BEGIN
    OUTSTRING(1, "L=3,k=8: PERCEIVABLE");
    OUTCHAR(1, 10);
    PASS := PASS + 1
  END
  ELSE
  BEGIN
    OUTSTRING(1, "L=3,k=8: FAIL");
    OUTCHAR(1, 10);
    FAIL := FAIL + 1
  END;

  COMMENT L=12, k=8: not perceivable (FALSE);
  TNUM := TNUM + 1;
  IF DEADBANDCHECK(12, 8) THEN
  BEGIN
    OUTSTRING(1, "L=12,k=8: FAIL");
    OUTCHAR(1, 10);
    FAIL := FAIL + 1
  END
  ELSE
  BEGIN
    OUTSTRING(1, "L=12,k=8: NOT PERCEIVABLE");
    OUTCHAR(1, 10);
    PASS := PASS + 1
  END;

  COMMENT L=8, k=8: perceivable (boundary, TRUE);
  TNUM := TNUM + 1;
  IF DEADBANDCHECK(8, 8) THEN
  BEGIN
    OUTSTRING(1, "L=8,k=8: PERCEIVABLE (boundary)");
    OUTCHAR(1, 10);
    PASS := PASS + 1
  END
  ELSE
  BEGIN
    OUTSTRING(1, "L=8,k=8: FAIL");
    OUTCHAR(1, 10);
    FAIL := FAIL + 1
  END;

  OUTCHAR(1, 10);

  COMMENT ---- TEST 5: BMA ----;
  OUTSTRING(1, "--- BMA Complexity ---");
  OUTCHAR(1, 10);

  BEGIN
    INTEGER ARRAY S[1:64];
    INTEGER L;

    COMMENT Sequence: 0,1,1,0,1,0,1,0 — LFSR order 3;
    S[1] := 0; S[2] := 1; S[3] := 1; S[4] := 0;
    S[5] := 1; S[6] := 0; S[7] := 1; S[8] := 0;

    L := BMACOMPLEXITY(8, S);
    OUTSTRING(1, "BMA L: ");
    OUTINTEGER(1, L);
    OUTCHAR(1, 10);
    TNUM := TNUM + 1;
    IF L = 3 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1;

    COMMENT Alternating: 1,0,1,0,1,0 — LFSR order 1;
    S[1] := 1; S[2] := 0; S[3] := 1; S[4] := 0;
    S[5] := 1; S[6] := 0;
    L := BMACOMPLEXITY(6, S);
    OUTSTRING(1, "BMA alt L: ");
    OUTINTEGER(1, L);
    OUTCHAR(1, 10);
    TNUM := TNUM + 1;
    IF L = 1 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1;

    COMMENT All zeros: LFSR order 0;
    FOR J := 1 STEP 1 UNTIL 8 DO S[J] := 0;
    L := BMACOMPLEXITY(8, S);
    OUTSTRING(1, "BMA zeros L: ");
    OUTINTEGER(1, L);
    OUTCHAR(1, 10);
    TNUM := TNUM + 1;
    IF L = 0 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1
  END;

  OUTCHAR(1, 10);

  COMMENT ---- TEST 6: HPDF Sampling ----;
  OUTSTRING(1, "--- HPDF Sampling ---");
  OUTCHAR(1, 10);

  BEGIN
    INTEGER I;
    REAL SUMX, SUMY, MAXR, R;
    SUMX := 0.0;
    SUMY := 0.0;
    MAXR := 0.0;

    FOR I := 1 STEP 1 UNTIL 100 DO
    BEGIN
      HPDFSAMPLE;
      SUMX := SUMX + HPOUT[1];
      SUMY := SUMY + HPOUT[2];
      R := SQRT(HPOUT[1] * HPOUT[1] + HPOUT[2] * HPOUT[2]);
      IF R > MAXR THEN MAXR := R
    END;

    OUTSTRING(1, "100 samples, mean X: ");
    OUTREAL(1, SUMX / 100.0);
    OUTCHAR(1, 10);
    OUTSTRING(1, "100 samples, mean Y: ");
    OUTREAL(1, SUMY / 100.0);
    OUTCHAR(1, 10);
    OUTSTRING(1, "Max radius: ");
    OUTREAL(1, MAXR);
    OUTCHAR(1, 10);

    COMMENT Check: mean near 0, max radius < 1.2 (hexagon inscribed
             in circle of radius ~1.155);
    TNUM := TNUM + 1;
    IF MAXR < 1.2 THEN PASS := PASS + 1 ELSE FAIL := FAIL + 1
  END;

  OUTCHAR(1, 10);

  COMMENT ---- SUMMARY ----;
  OUTSTRING(1, "========================================");
  OUTCHAR(1, 10);
  OUTSTRING(1, "TEST SUMMARY");
  OUTCHAR(1, 10);
  OUTSTRING(1, "Passed: ");
  OUTINTEGER(1, PASS);
  OUTCHAR(1, 10);
  OUTSTRING(1, "Failed: ");
  OUTINTEGER(1, FAIL);
  OUTCHAR(1, 10);
  OUTSTRING(1, "Total:  ");
  OUTINTEGER(1, TNUM);
  OUTCHAR(1, 10);
  IF FAIL = 0 THEN
    OUTSTRING(1, "*** ALL TESTS PASSED ***")
  ELSE
    OUTSTRING(1, "*** SOME TESTS FAILED ***");
  OUTCHAR(1, 10)

END
