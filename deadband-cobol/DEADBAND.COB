       IDENTIFICATION DIVISION.
       PROGRAM-ID. DEADBAND-FRAMEWORK.
       AUTHOR. FORGEMASTER-FLEET.
      * ============================================================
      * DEADBAND FRAMEWORK — COBOL 85 / GnuCOBOL Implementation
      * ============================================================
      * Six mathematical primitives for constraint-theory analysis:
      *   1. Eisenstein snap — round to Z[omega] lattice
      *   2. HPDF sampling  — uniform random in hexagonal cell
      *   3. /360 arithmetic — exact integer mod-360 operations
      *   4. BMA complexity  — Berlekamp-Massey over GF(2)
      *   5. Shell decomposition — 2x2 eigendecomposition
      *   6. Deadband check  — perceivability test
      *
      * COBOL is THE language for /360 arithmetic.
      * PIC 9(3) COMP is literally base-360 accounting.
      * ============================================================

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SPECIAL-NAMES.
           DECIMAL-POINT IS COMMA.

       DATA DIVISION.
       WORKING-STORAGE SECTION.

      * ============================================================
      * CONSTANTS
      * ============================================================
       01  WS-CONSTANTS.
           05  WS-SQRT3         PIC S9(7)V9(10) COMP VALUE 1.7320508076.
           05  WS-SQRT3-HALF    PIC S9(7)V9(10) COMP VALUE 0.8660254038.
           05  WS-PHI           PIC S9(7)V9(10) COMP VALUE 1.6180339887.
           05  WS-PHI-NEG-INV   PIC S9(7)V9(10) COMP VALUE -0.6180339887.
           05  WS-EPSILON       PIC S9(7)V9(10) COMP VALUE 0.01.
           05  WS-MOD-BASE      PIC 9(3) COMP VALUE 360.
           05  WS-PI            PIC S9(7)V9(10) COMP VALUE 3.1415926536.

      * ============================================================
      * EISENSTEIN SNAP WORKING STORAGE
      * ============================================================
       01  WS-EISENSTEIN.
           05  WS-E-IN-X        PIC S9(7)V9(10) COMP.
           05  WS-E-IN-Y        PIC S9(7)V9(10) COMP.
           05  WS-E-A-COORD     PIC S9(7)V9(10) COMP.
           05  WS-E-B-COORD     PIC S9(7)V9(10) COMP.
           05  WS-E-OUT-X       PIC S9(7)V9(10) COMP.
           05  WS-E-OUT-Y       PIC S9(7)V9(10) COMP.
           05  WS-E-TEMP        PIC S9(7)V9(10) COMP.

      * ============================================================
      * HPDF SAMPLING WORKING STORAGE
      * ============================================================
       01  WS-HPDF.
           05  WS-H-SEED        PIC 9(9) COMP VALUE 42.
           05  WS-H-U1          PIC S9(7)V9(10) COMP.
           05  WS-H-U2          PIC S9(7)V9(10) COMP.
           05  WS-H-R1          PIC S9(7)V9(10) COMP.
           05  WS-H-R2          PIC S9(7)V9(10) COMP.
           05  WS-H-S           PIC S9(7)V9(10) COMP.
           05  WS-H-T           PIC S9(7)V9(10) COMP.
           05  WS-H-OUT-X       PIC S9(7)V9(10) COMP.
           05  WS-H-OUT-Y       PIC S9(7)V9(10) COMP.
           05  WS-H-TABLE-SIZE  PIC 9(4) COMP VALUE 1000.

      * ============================================================
      * /360 ARITHMETIC — EXACT INTEGER MOD 360
      * ============================================================
       01  WS-MOD360.
           05  WS-M-A           PIC S9(4) COMP.
           05  WS-M-B           PIC S9(4) COMP.
           05  WS-M-RESULT      PIC S9(4) COMP.
           05  WS-M-TEMP        PIC S9(7) COMP.

      * ============================================================
      * BMA (BERLEKAMP-MASSEY) OVER GF(2)
      * ============================================================
       01  WS-BMA.
           05  WS-B-N           PIC 9(4) COMP.
           05  WS-B-L           PIC 9(4) COMP.
           05  WS-B-M           PIC 9(4) COMP.
           05  WS-B-D           PIC 9(1) COMP.
           05  WS-B-OLD-D       PIC 9(1) COMP.
           05  WS-B-I           PIC 9(4) COMP.
           05  WS-B-J           PIC 9(4) COMP.
           05  WS-B-DELTA       PIC 9(1) COMP.
           05  WS-B-SEQ-SIZE    PIC 9(4) COMP VALUE 64.
           05  WS-B-MAX-LFSR    PIC 9(4) COMP VALUE 32.
      * Input sequence — bits indexed 1..N
       01  WS-B-SEQ.
           05  WS-B-INPUT       PIC 9(1) COMP OCCURS 64 TIMES.
      * Current connection polynomial C
       01  WS-B-C-POLY.
           05  WS-B-C           PIC 9(1) COMP OCCURS 32 TIMES.
      * Previous connection polynomial B
       01  WS-B-B-POLY.
           05  WS-B-B           PIC 9(1) COMP OCCURS 32 TIMES.
      * Temporary polynomial for swap
       01  WS-B-TEMP-POLY.
           05  WS-B-TEMP-C      PIC 9(1) COMP OCCURS 32 TIMES.

      * ============================================================
      * SHELL DECOMPOSITION — 2x2 EIGENDECOMPOSITION
      * ============================================================
       01  WS-SHELL.
           05  WS-S-A11         PIC S9(7)V9(10) COMP.
           05  WS-S-A12         PIC S9(7)V9(10) COMP.
           05  WS-S-A21         PIC S9(7)V9(10) COMP.
           05  WS-S-A22         PIC S9(7)V9(10) COMP.
           05  WS-S-TRACE       PIC S9(7)V9(10) COMP.
           05  WS-S-DET         PIC S9(7)V9(10) COMP.
           05  WS-S-DISC        PIC S9(7)V9(10) COMP.
           05  WS-S-EIG1        PIC S9(7)V9(10) COMP.
           05  WS-S-EIG2        PIC S9(7)V9(10) COMP.
           05  WS-S-SQRT-DISC   PIC S9(7)V9(10) COMP.
      * Shell classification
       01  WS-SHELL-CLASS.
           05  WS-SC-TYPE       PIC X(20).
           05  WS-SC-PHI-DIST   PIC S9(7)V9(10) COMP.
           05  WS-SC-PNI-DIST   PIC S9(7)V9(10) COMP.
           05  WS-SC-IS-GOLDEN  PIC X(3).
             88  GOLDEN-SHELL          VALUE "YES".
             88  NOT-GOLDEN-SHELL      VALUE "NO ".
           05  WS-SC-IS-ANTI    PIC X(3).
             88  ANTI-GOLDEN           VALUE "YES".
             88  NOT-ANTI-GOLDEN       VALUE "NO ".

      * ============================================================
      * DEADBAND CHECK
      * ============================================================
       01  WS-DEADBAND.
           05  WS-DB-L          PIC 9(4) COMP.
           05  WS-DB-K          PIC 9(4) COMP.
           05  WS-DB-PERCEIVABLE PIC X(3).
             88  PERCEIVABLE           VALUE "YES".
             88  NOT-PERCEIVABLE       VALUE "NO ".

      * ============================================================
      * UTILITY
      * ============================================================
       01  WS-UTIL.
           05  WS-U-RAND        PIC 9(9) COMP.
           05  WS-U-QUOTIENT    PIC S9(7) COMP.
           05  WS-U-REMAINDER   PIC S9(7) COMP.

       PROCEDURE DIVISION.

      * ============================================================
      * MAIN ENTRY — DEMO ALL PRIMITIVES
      * ============================================================
       MAIN-DEMO.
           DISPLAY "========================================".
           DISPLAY " DEADBAND FRAMEWORK — COBOL 85 EDITION".
           DISPLAY "========================================.
           DISPLAY SPACE.
           STOP RUN.

      * ============================================================
      * 1. EISENSTEIN SNAP
      *    Round (x, y) to nearest Eisenstein lattice point.
      *    Basis: e1 = (1, 0), e2 = (-0.5, sqrt(3)/2)
      *    Convert to (a, b) coords, round, convert back.
      * ============================================================
       EISENSTEIN-SNAP.
      * Convert from Cartesian to lattice coordinates
      * a = x - y/sqrt(3)
      * b = 2*y/sqrt(3)
           COMPUTE WS-E-A-COORD ROUNDED =
               WS-E-IN-X - WS-E-IN-Y / WS-SQRT3.
           COMPUTE WS-E-B-COORD ROUNDED =
               2.0 * WS-E-IN-Y / WS-SQRT3.

      * Round to nearest integer lattice point
           COMPUTE WS-E-A-COORD ROUNDED =
               FUNCTION ANNUITY(0, 0) * WS-E-A-COORD
               ON SIZE ERROR DISPLAY "SNAP OVERFLOW".
           ADD 0.5 TO WS-E-A-COORD.
           COMPUTE WS-E-A-COORD ROUNDED =
               FUNCTION INTEGER(WS-E-A-COORD - 0.5).

           ADD 0.5 TO WS-E-B-COORD.
           COMPUTE WS-E-B-COORD ROUNDED =
               FUNCTION INTEGER(WS-E-B-COORD - 0.5).

      * Convert back to Cartesian
      * x = a - b/2
      * y = b * sqrt(3)/2
           COMPUTE WS-E-OUT-X =
               WS-E-A-COORD - WS-E-B-COORD / 2.0.
           COMPUTE WS-E-OUT-Y =
               WS-E-B-COORD * WS-SQRT3 / 2.0.
           .

      * ============================================================
      * EISENSTEIN-SNAP-V2 — Cleaner implementation
      * Uses integer rounding via FUNCTION INTEGER-PART
      * ============================================================
       EISENSTEIN-SNAP-V2.
      * a = x + y/sqrt(3)  (for the OTHER convention)
      * b = 2*y/sqrt(3)
           COMPUTE WS-E-TEMP =
               WS-E-IN-X - WS-E-IN-Y / WS-SQRT3.
           PERFORM ROUND-TO-NEAREST-INT
               VARYING WS-E-A-COORD FROM WS-E-TEMP
               BY 0 UNTIL 1 = 1.

           COMPUTE WS-E-TEMP =
               2.0 * WS-E-IN-Y / WS-SQRT3.
           MOVE WS-E-TEMP TO WS-E-B-COORD.
           ADD 0.5 TO WS-E-B-COORD.
           COMPUTE WS-E-B-COORD =
               FUNCTION INTEGER-PART(WS-E-B-COORD).
           SUBTRACT 0.5 FROM WS-E-B-COORD.

      * Convert back
           COMPUTE WS-E-OUT-X =
               WS-E-A-COORD - WS-E-B-COORD * 0.5.
           COMPUTE WS-E-OUT-Y =
               WS-E-B-COORD * WS-SQRT3-HALF.
           .

       ROUND-TO-NEAREST-INT.
           STOP RUN.

      * ============================================================
      * 3. /360 ARITHMETIC — EXACT MOD 360
      *    This is COBOL's natural domain.
      *    PIC 9(3) COMP with ON SIZE ERROR catches overflow.
      * ============================================================
       MOD360-ADD.
           ADD WS-M-A TO WS-M-B GIVING WS-M-TEMP
               ON SIZE ERROR
                   DISPLAY "/360 ADD OVERFLOW"
           END-ADD.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

       MOD360-SUB.
           SUBTRACT WS-M-B FROM WS-M-A GIVING WS-M-TEMP
               ON SIZE ERROR
                   DISPLAY "/360 SUB OVERFLOW"
           END-SUBTRACT.
      * Handle negative results by adding 360
           IF WS-M-TEMP < 0
               ADD WS-MOD-BASE TO WS-M-TEMP
           END-IF.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

       MOD360-MUL.
           MULTIPLY WS-M-A BY WS-M-B GIVING WS-M-TEMP
               ON SIZE ERROR
                   DISPLAY "/360 MUL OVERFLOW"
           END-MULTIPLY.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

      * ============================================================
      * 4. BMA — BERLEKAMP-MASSEY OVER GF(2)
      *    Classic algorithm using OCCURS tables.
      *    Returns LFSR order L in WS-B-L.
      * ============================================================
       BMA-INITIALIZE.
           MOVE 0 TO WS-B-L.
           MOVE 0 TO WS-B-M.
           MOVE 1 TO WS-B-C(1).
           MOVE 1 TO WS-B-B(1).
           PERFORM VARYING WS-B-I FROM 2 BY 1
               UNTIL WS-B-I > WS-B-MAX-LFSR
               MOVE 0 TO WS-B-C(WS-B-I)
               MOVE 0 TO WS-B-B(WS-B-I)
           END-PERFORM.
           .

       BMA-COMPUTE.
      * WS-B-N has sequence length, WS-B-INPUT has bits 1..N
           PERFORM BMA-INITIALIZE.

           PERFORM VARYING WS-B-I FROM 1 BY 1
               UNTIL WS-B-I > WS-B-N

      * Compute discrepancy d = s[i] XOR sum(C[j] * s[i-j])
               MOVE WS-B-INPUT(WS-B-I) TO WS-B-D.

               PERFORM VARYING WS-B-J FROM 1 BY 1
                   UNTIL WS-B-J > WS-B-L
      * XOR is addition mod 2
                   COMPUTE WS-B-DELTA =
                       WS-B-C(WS-B-J + 1) *
                       WS-B-INPUT(WS-B-I - WS-B-J).
      * GF(2) addition
                   ADD WS-B-DELTA TO WS-B-D.
                   IF WS-B-D > 1
                       SUBTRACT 2 FROM WS-B-D
                   END-IF
               END-PERFORM.

               IF WS-B-D = 0
      * No update needed
                   CONTINUE
               ELSE
      * Need to update C polynomial
      * Save C to temp
                   PERFORM VARYING WS-B-J FROM 1 BY 1
                       UNTIL WS-B-J > WS-B-MAX-LFSR
                       MOVE WS-B-C(WS-B-J)
                           TO WS-B-TEMP-C(WS-B-J)
                   END-PERFORM.

      * C = C XOR B shifted by (i - m) positions
                   COMPUTE WS-B-DELTA = WS-B-I - WS-B-M.
                   PERFORM VARYING WS-B-J FROM 1 BY 1
                       UNTIL WS-B-J + WS-B-DELTA
                           > WS-B-MAX-LFSR
                       COMPUTE WS-B-C(WS-B-J + WS-B-DELTA) =
                           WS-B-C(WS-B-J + WS-B-DELTA)
                           + WS-B-B(WS-B-J).
      * GF(2) normalize
                       IF WS-B-C(WS-B-J + WS-B-DELTA) > 1
                           SUBTRACT 2 FROM
                             WS-B-C(WS-B-J + WS-B-DELTA)
                       END-IF
                   END-PERFORM.

      * If 2*L <= i-1, update L and B
                   IF 2 * WS-B-L <= WS-B-I - 1
                       COMPUTE WS-B-L =
                           WS-B-I - WS-B-L
      * Copy temp to B
                       PERFORM VARYING WS-B-J FROM 1 BY 1
                           UNTIL WS-B-J > WS-B-MAX-LFSR
                           MOVE WS-B-TEMP-C(WS-B-J)
                               TO WS-B-B(WS-B-J)
                       END-PERFORM
                       MOVE WS-B-I TO WS-B-M
                   END-IF
               END-IF
           END-PERFORM.
           .

      * ============================================================
      * 5. SHELL DECOMPOSITION — 2x2 EIGENVALUES
      *    Eigenvalues of [[a11, a12], [a21, a22]]
      *    Classify by proximity to phi and -1/phi.
      * ============================================================
       SHELL-DECOMPOSE.
      * Eigenvalues from characteristic equation:
      * lambda^2 - trace*lambda + det = 0
           COMPUTE WS-S-TRACE = WS-S-A11 + WS-S-A22.
           COMPUTE WS-S-DET =
               WS-S-A11 * WS-S-A22 - WS-S-A12 * WS-S-A21.
           COMPUTE WS-S-DISC =
               WS-S-TRACE * WS-S-TRACE - 4.0 * WS-S-DET.

           IF WS-S-DISC >= 0
               COMPUTE WS-S-SQRT-DISC =
                   FUNCTION SQRT(WS-S-DISC)
               COMPUTE WS-S-EIG1 =
                   (WS-S-TRACE + WS-S-SQRT-DISC) / 2.0.
               COMPUTE WS-S-EIG2 =
                   (WS-S-TRACE - WS-S-SQRT-DISC) / 2.0.
           ELSE
      * Complex eigenvalues — store real part, flag imaginary
               MOVE 0 TO WS-S-EIG1.
               MOVE 0 TO WS-S-EIG2.
               MOVE "COMPLEX" TO WS-SC-TYPE.
           END-IF.

      * Classify: distance to golden ratio phi = 1.618
           COMPUTE WS-SC-PHI-DIST =
               FUNCTION ABS(WS-S-EIG1 - WS-PHI).
           COMPUTE WS-SC-PNI-DIST =
               FUNCTION ABS(WS-S-EIG1 - WS-PHI-NEG-INV).

           IF WS-SC-PHI-DIST < WS-EPSILON
               SET GOLDEN-SHELL TO TRUE
               MOVE "GOLDEN-PROXIMAL" TO WS-SC-TYPE
           ELSE
               IF WS-SC-PNI-DIST < WS-EPSILON
                   SET ANTI-GOLDEN TO TRUE
                   MOVE "ANTI-GOLDEN" TO WS-SC-TYPE
               ELSE
                   MOVE "GENERIC" TO WS-SC-TYPE
               END-IF
           END-IF.

      * Also check eig2
           IF NOT GOLDEN-SHELL
               COMPUTE WS-SC-PHI-DIST =
                   FUNCTION ABS(WS-S-EIG2 - WS-PHI)
               IF WS-SC-PHI-DIST < WS-EPSILON
                   SET GOLDEN-SHELL TO TRUE
                   MOVE "GOLDEN-PROXIMAL-EIG2" TO WS-SC-TYPE
               END-IF
           END-IF.
           .

      * ============================================================
      * 6. DEADBAND CHECK
      *    Is pattern order L perceivable by receiver with k bits?
      *    Criterion: L <= k (pattern fits within receiver bandwidth)
      * ============================================================
       DEADBAND-CHECK.
           IF WS-DB-L <= WS-DB-K
               SET PERCEIVABLE TO TRUE
           ELSE
               SET NOT-PERCEIVABLE TO TRUE
           END-IF.
           .

      * ============================================================
      * 2. HPDF SAMPLING — UNIFORM RANDOM IN HEXAGONAL CELL
      *    Uses parallelogram decomposition method.
      *    Hexagon = union of 3 rhombi, pick one at random.
      * ============================================================
       HPDF-SAMPLE.
      * Generate two uniform random numbers in [-1, 1]
           ACCEPT WS-U-RAND FROM TIME.
           COMPUTE WS-H-U1 =
               (FUNCTION MOD(WS-U-RAND, 10000) - 5000)
               / 5000.0.
           COMPUTE WS-H-U2 =
               (FUNCTION MOD(WS-U-RAND * 7 + 3, 10000) - 5000)
               / 5000.0.

      * Method: sample in parallelogram, fold into hexagon
      * Using the standard approach:
      *   Let r1 = 2*rand() - 1, r2 = 2*rand() - 1
      *   s = r1, t = r2
      *   if s + t > 1: s = 1-r2, t = 1-r1
      *   if s + t < -1: s = -1-r2, t = -1-r1
      *   Then hex coords: x = s - t/2, y = t*sqrt(3)/2
           MOVE WS-H-U1 TO WS-H-S.
           MOVE WS-H-U2 TO WS-H-T.

           IF WS-H-S + WS-H-T > 1.0
               COMPUTE WS-H-S = 1.0 - WS-H-U2.
               COMPUTE WS-H-T = 1.0 - WS-H-U1.
           END-IF.

           IF WS-H-S + WS-H-T < -1.0
               COMPUTE WS-H-S = -1.0 - WS-H-U2.
               COMPUTE WS-H-T = -1.0 - WS-H-U1.
           END-IF.

      * Convert parallelogram coords to hexagonal
           COMPUTE WS-H-OUT-X = WS-H-S - WS-H-T * 0.5.
           COMPUTE WS-H-OUT-Y = WS-H-T * WS-SQRT3-HALF.
           .

      * ============================================================
      * HPDF-SAMPLE-TABLE — Batch sampling using OCCURS
      * ============================================================
       01  WS-HPDF-TABLE.
           05  WS-HT-POINT.
               10  WS-HT-X     PIC S9(7)V9(10) COMP
                               OCCURS 1000 TIMES.
               10  WS-HT-Y     PIC S9(7)V9(10) COMP
                               OCCURS 1000 TIMES.

       HPDF-SAMPLE-BATCH.
           PERFORM VARYING WS-B-I FROM 1 BY 1
               UNTIL WS-B-I > WS-H-TABLE-SIZE
               PERFORM HPDF-SAMPLE
               MOVE WS-H-OUT-X TO WS-HT-X(WS-B-I)
               MOVE WS-H-OUT-Y TO WS-HT-Y(WS-B-I)
           END-PERFORM.
           .

       END PROGRAM DEADBAND-FRAMEWORK.
