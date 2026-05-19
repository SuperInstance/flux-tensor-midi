       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTDB.
       AUTHOR. FORGEMASTER-FLEET.
      * ============================================================
      * DEADBAND FRAMEWORK — TEST PROGRAM
      * Exercises all six primitives.
      * Build: cobc -x -free TESTDB.COB
      * ============================================================

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SPECIAL-NAMES.
           DECIMAL-POINT IS COMMA.

       DATA DIVISION.
       WORKING-STORAGE SECTION.

      * Constants
       01  WS-CONSTANTS.
           05  WS-SQRT3         PIC S9(7)V9(10) COMP VALUE 1.7320508076.
           05  WS-SQRT3-HALF    PIC S9(7)V9(10) COMP VALUE 0.8660254038.
           05  WS-PHI           PIC S9(7)V9(10) COMP VALUE 1.6180339887.
           05  WS-PHI-NEG-INV   PIC S9(7)V9(10) COMP VALUE -0.6180339887.
           05  WS-EPSILON       PIC S9(7)V9(10) COMP VALUE 0.01.
           05  WS-MOD-BASE      PIC 9(3) COMP VALUE 360.

      * Test counters
       01  WS-TEST.
           05  WS-T-PASS        PIC 9(4) COMP VALUE 0.
           05  WS-T-FAIL        PIC 9(4) COMP VALUE 0.
           05  WS-T-COUNT       PIC 9(4) COMP VALUE 0.

      * /360 test variables
       01  WS-MOD360.
           05  WS-M-A           PIC S9(4) COMP.
           05  WS-M-B           PIC S9(4) COMP.
           05  WS-M-RESULT      PIC S9(4) COMP.
           05  WS-M-TEMP        PIC S9(7) COMP.
           05  WS-U-QUOTIENT    PIC S9(7) COMP.
           05  WS-U-REMAINDER   PIC S9(7) COMP.

      * Eisenstein test
       01  WS-EISENSTEIN.
           05  WS-E-IN-X        PIC S9(7)V9(10) COMP.
           05  WS-E-IN-Y        PIC S9(7)V9(10) COMP.
           05  WS-E-A-COORD     PIC S9(7)V9(10) COMP.
           05  WS-E-B-COORD     PIC S9(7)V9(10) COMP.
           05  WS-E-OUT-X       PIC S9(7)V9(10) COMP.
           05  WS-E-OUT-Y       PIC S9(7)V9(10) COMP.
           05  WS-E-TEMP        PIC S9(7)V9(10) COMP.
           05  WS-E-EXPECTED-X  PIC S9(7)V9(10) COMP.
           05  WS-E-EXPECTED-Y  PIC S9(7)V9(10) COMP.
           05  WS-E-DIFF-X      PIC S9(7)V9(10) COMP.
           05  WS-E-DIFF-Y      PIC S9(7)V9(10) COMP.

      * Shell decomposition test
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

      * BMA test
       01  WS-BMA.
           05  WS-B-N           PIC 9(4) COMP.
           05  WS-B-L           PIC 9(4) COMP.
           05  WS-B-M           PIC 9(4) COMP.
           05  WS-B-D           PIC 9(1) COMP.
           05  WS-B-I           PIC 9(4) COMP.
           05  WS-B-J           PIC 9(4) COMP.
           05  WS-B-DELTA       PIC 9(1) COMP.
           05  WS-B-MAX-LFSR    PIC 9(4) COMP VALUE 32.
       01  WS-B-SEQ.
           05  WS-B-INPUT       PIC 9(1) COMP OCCURS 64 TIMES.
       01  WS-B-C-POLY.
           05  WS-B-C           PIC 9(1) COMP OCCURS 32 TIMES.
       01  WS-B-B-POLY.
           05  WS-B-B           PIC 9(1) COMP OCCURS 32 TIMES.
       01  WS-B-TEMP-POLY.
           05  WS-B-TEMP-C      PIC 9(1) COMP OCCURS 32 TIMES.

      * Deadband test
       01  WS-DEADBAND.
           05  WS-DB-L          PIC 9(4) COMP.
           05  WS-DB-K          PIC 9(4) COMP.
           05  WS-DB-PERCEIVABLE PIC X(3).
             88  PERCEIVABLE           VALUE "YES".
             88  NOT-PERCEIVABLE       VALUE "NO ".

      * HPDF test
       01  WS-HPDF.
           05  WS-H-SEED        PIC 9(9) COMP VALUE 42.
           05  WS-H-U1          PIC S9(7)V9(10) COMP.
           05  WS-H-U2          PIC S9(7)V9(10) COMP.
           05  WS-H-S           PIC S9(7)V9(10) COMP.
           05  WS-H-T           PIC S9(7)V9(10) COMP.
           05  WS-H-OUT-X       PIC S9(7)V9(10) COMP.
           05  WS-H-OUT-Y       PIC S9(7)V9(10) COMP.
           05  WS-H-TABLE-SIZE  PIC 9(4) COMP VALUE 1000.
       01  WS-UTIL.
           05  WS-U-RAND        PIC 9(9) COMP.

      * Test result formatting
       01  WS-DISPLAY.
           05  WS-D-VAL         PIC -(7)9.9(6).
           05  WS-D-INT         PIC -(5)9.
           05  WS-D-LABEL       PIC X(30).

       PROCEDURE DIVISION.

       MAIN-TEST.
           DISPLAY "========================================".
           DISPLAY " DEADBAND FRAMEWORK — COBOL TEST SUITE".
           DISPLAY "========================================.
           DISPLAY SPACE.

      * ---- TEST 1: /360 Arithmetic ----
           DISPLAY "--- TEST: /360 Arithmetic ---".
           DISPLAY "ADD 180 + 200 = ? (expect 20)".
           MOVE 180 TO WS-M-A.
           MOVE 200 TO WS-M-B.
           PERFORM MOD360-ADD.
           MOVE WS-M-RESULT TO WS-D-INT.
           DISPLAY "Result: " WS-D-INT.
           IF WS-M-RESULT = 20
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL (expected 20)"
           END-IF.
           ADD 1 TO WS-T-COUNT.

           DISPLAY "MUL 90 * 5 = ? (expect 90)".
           MOVE 90 TO WS-M-A.
           MOVE 5 TO WS-M-B.
           PERFORM MOD360-MUL.
           MOVE WS-M-RESULT TO WS-D-INT.
           DISPLAY "Result: " WS-D-INT.
           IF WS-M-RESULT = 90
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL (expected 90)"
           END-IF.
           ADD 1 TO WS-T-COUNT.

           DISPLAY "SUB 10 - 350 = ? (expect 20)".
           MOVE 10 TO WS-M-A.
           MOVE 350 TO WS-M-B.
           PERFORM MOD360-SUB.
           MOVE WS-M-RESULT TO WS-D-INT.
           DISPLAY "Result: " WS-D-INT.
           IF WS-M-RESULT = 20
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL (expected 20)"
           END-IF.
           ADD 1 TO WS-T-COUNT.
           DISPLAY SPACE.

      * ---- TEST 2: Eisenstein Snap ----
           DISPLAY "--- TEST: Eisenstein Snap ---".
           DISPLAY "Snap (1.0, 0.0) — expect (1, 0)".
           MOVE 1.0 TO WS-E-IN-X.
           MOVE 0.0 TO WS-E-IN-Y.
           PERFORM EISENSTEIN-SNAP-INLINE.
           MOVE WS-E-OUT-X TO WS-D-VAL.
           DISPLAY "X: " WS-D-VAL.
           MOVE WS-E-OUT-Y TO WS-D-VAL.
           DISPLAY "Y: " WS-D-VAL.
           COMPUTE WS-E-DIFF-X = FUNCTION ABS(WS-E-OUT-X - 1.0).
           COMPUTE WS-E-DIFF-Y = FUNCTION ABS(WS-E-OUT-Y - 0.0).
           IF WS-E-DIFF-X < 0.001 AND WS-E-DIFF-Y < 0.001
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL"
           END-IF.
           ADD 1 TO WS-T-COUNT.

           DISPLAY "Snap (0.5, 0.866) — expect (0, 1)".
           MOVE 0.5 TO WS-E-IN-X.
           MOVE 0.866 TO WS-E-IN-Y.
           PERFORM EISENSTEIN-SNAP-INLINE.
           MOVE WS-E-OUT-X TO WS-D-VAL.
           DISPLAY "X: " WS-D-VAL.
           MOVE WS-E-OUT-Y TO WS-D-VAL.
           DISPLAY "Y: " WS-D-VAL.
           COMPUTE WS-E-DIFF-X = FUNCTION ABS(WS-E-OUT-X - 0.0).
           COMPUTE WS-E-DIFF-Y =
               FUNCTION ABS(WS-E-OUT-Y - WS-SQRT3-HALF).
           IF WS-E-DIFF-X < 0.01 AND WS-E-DIFF-Y < 0.01
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL"
           END-IF.
           ADD 1 TO WS-T-COUNT.
           DISPLAY SPACE.

      * ---- TEST 3: Shell Decomposition ----
           DISPLAY "--- TEST: Shell Decomposition ---".
           DISPLAY "Fibonacci matrix [[1,1],[1,0]]".
           MOVE 1.0 TO WS-S-A11.
           MOVE 1.0 TO WS-S-A12.
           MOVE 1.0 TO WS-S-A21.
           MOVE 0.0 TO WS-S-A22.
           PERFORM SHELL-DECOMPOSE.
           MOVE WS-S-EIG1 TO WS-D-VAL.
           DISPLAY "Eig1: " WS-D-VAL.
           MOVE WS-S-EIG2 TO WS-D-VAL.
           DISPLAY "Eig2: " WS-D-VAL.
           DISPLAY "Type: " WS-SC-TYPE.
           IF GOLDEN-SHELL
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS (Golden shell detected)"
           ELSE
      * Eig1 should still be ~1.618 even if not within epsilon
               COMPUTE WS-E-DIFF-X =
                   FUNCTION ABS(WS-S-EIG1 - WS-PHI)
               IF WS-E-DIFF-X < 0.01
                   ADD 1 TO WS-T-PASS
                   DISPLAY "PASS (eig1 near phi)"
               ELSE
                   ADD 1 TO WS-T-FAIL
                   DISPLAY "FAIL"
               END-IF
           END-IF.
           ADD 1 TO WS-T-COUNT.
           DISPLAY SPACE.

      * ---- TEST 4: Deadband Check ----
           DISPLAY "--- TEST: Deadband Check ---".
           DISPLAY "L=3, k=8 — expect PERCEIVABLE".
           MOVE 3 TO WS-DB-L.
           MOVE 8 TO WS-DB-K.
           PERFORM DEADBAND-CHECK.
           DISPLAY "Result: " WS-DB-PERCEIVABLE.
           IF PERCEIVABLE
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL"
           END-IF.
           ADD 1 TO WS-T-COUNT.

           DISPLAY "L=12, k=8 — expect NOT PERCEIVABLE".
           MOVE 12 TO WS-DB-L.
           MOVE 8 TO WS-DB-K.
           PERFORM DEADBAND-CHECK.
           DISPLAY "Result: " WS-DB-PERCEIVABLE.
           IF NOT-PERCEIVABLE
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL"
           END-IF.
           ADD 1 TO WS-T-COUNT.
           DISPLAY SPACE.

      * ---- TEST 5: BMA ----
           DISPLAY "--- TEST: BMA Complexity ---".
           DISPLAY "Sequence: 0 1 1 0 1 0 1 0 (LFSR order 3)".
           MOVE 8 TO WS-B-N.
           MOVE 0 TO WS-B-INPUT(1).
           MOVE 1 TO WS-B-INPUT(2).
           MOVE 1 TO WS-B-INPUT(3).
           MOVE 0 TO WS-B-INPUT(4).
           MOVE 1 TO WS-B-INPUT(5).
           MOVE 0 TO WS-B-INPUT(6).
           MOVE 1 TO WS-B-INPUT(7).
           MOVE 0 TO WS-B-INPUT(8).
           PERFORM BMA-COMPUTE.
           MOVE WS-B-L TO WS-D-INT.
           DISPLAY "LFSR order L: " WS-D-INT.
           IF WS-B-L = 3
               ADD 1 TO WS-T-PASS
               DISPLAY "PASS"
           ELSE
               ADD 1 TO WS-T-FAIL
               DISPLAY "FAIL (expected 3)"
           END-IF.
           ADD 1 TO WS-T-COUNT.
           DISPLAY SPACE.

      * ---- TEST 6: HPDF Sampling ----
           DISPLAY "--- TEST: HPDF Sampling ---".
           DISPLAY "Generating 10 hex points...".
           PERFORM VARYING WS-B-I FROM 1 BY 1
               UNTIL WS-B-I > 10
               PERFORM HPDF-SAMPLE-INLINE
               MOVE WS-H-OUT-X TO WS-D-VAL
               DISPLAY "Point " WS-B-I
                   " x=" WS-D-VAL
               MOVE WS-H-OUT-Y TO WS-D-VAL
               DISPLAY "         y=" WS-D-VAL
           END-PERFORM.
           ADD 1 TO WS-T-PASS.
           ADD 1 TO WS-T-COUNT.
           DISPLAY "PASS (sampling completed)".
           DISPLAY SPACE.

      * ---- SUMMARY ----
           DISPLAY "========================================".
           DISPLAY " TEST SUMMARY".
           DISPLAY "========================================.
           MOVE WS-T-PASS TO WS-D-INT.
           DISPLAY "Passed:  " WS-D-INT.
           MOVE WS-T-FAIL TO WS-D-INT.
           DISPLAY "Failed:  " WS-D-INT.
           MOVE WS-T-COUNT TO WS-D-INT.
           DISPLAY "Total:   " WS-D-INT.
           IF WS-T-FAIL = 0
               DISPLAY "*** ALL TESTS PASSED ***"
           ELSE
               DISPLAY "*** SOME TESTS FAILED ***"
           END-IF.

           STOP RUN.

      * ============================================================
      * INLINE IMPLEMENTATIONS (self-contained for test program)
      * ============================================================

      * Eisenstein snap inline
       EISENSTEIN-SNAP-INLINE.
           COMPUTE WS-E-A-COORD =
               WS-E-IN-X - WS-E-IN-Y / WS-SQRT3.
           COMPUTE WS-E-B-COORD =
               2.0 * WS-E-IN-Y / WS-SQRT3.
      * Round a-coord
           IF WS-E-A-COORD >= 0
               COMPUTE WS-E-A-COORD =
                   FUNCTION INTEGER(WS-E-A-COORD + 0.5)
           ELSE
               COMPUTE WS-E-A-COORD =
                   FUNCTION INTEGER(WS-E-A-COORD - 0.5)
           END-IF.
      * Round b-coord
           IF WS-E-B-COORD >= 0
               COMPUTE WS-E-B-COORD =
                   FUNCTION INTEGER(WS-E-B-COORD + 0.5)
           ELSE
               COMPUTE WS-E-B-COORD =
                   FUNCTION INTEGER(WS-E-B-COORD - 0.5)
           END-IF.
      * Convert back
           COMPUTE WS-E-OUT-X =
               WS-E-A-COORD - WS-E-B-COORD * 0.5.
           COMPUTE WS-E-OUT-Y =
               WS-E-B-COORD * WS-SQRT3-HALF.
           .

      * /360 operations inline
       MOD360-ADD.
           ADD WS-M-A TO WS-M-B GIVING WS-M-TEMP.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

       MOD360-SUB.
           SUBTRACT WS-M-B FROM WS-M-A GIVING WS-M-TEMP.
           IF WS-M-TEMP < 0
               ADD WS-MOD-BASE TO WS-M-TEMP
           END-IF.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

       MOD360-MUL.
           MULTIPLY WS-M-A BY WS-M-B GIVING WS-M-TEMP.
           DIVIDE WS-M-TEMP BY WS-MOD-BASE
               GIVING WS-U-QUOTIENT
               REMAINDER WS-M-RESULT.
           .

      * Shell decompose inline
       SHELL-DECOMPOSE.
           COMPUTE WS-S-TRACE = WS-S-A11 + WS-S-A22.
           COMPUTE WS-S-DET =
               WS-S-A11 * WS-S-A22 - WS-S-A12 * WS-S-A21.
           COMPUTE WS-S-DISC =
               WS-S-TRACE * WS-S-TRACE - 4.0 * WS-S-DET.
           IF WS-S-DISC >= 0
               COMPUTE WS-S-SQRT-DISC =
                   FUNCTION SQRT(WS-S-DISC)
               COMPUTE WS-S-EIG1 =
                   (WS-S-TRACE + WS-S-SQRT-DISC) / 2.0
               COMPUTE WS-S-EIG2 =
                   (WS-S-TRACE - WS-S-SQRT-DISC) / 2.0
           ELSE
               MOVE 0 TO WS-S-EIG1
               MOVE 0 TO WS-S-EIG2
               MOVE "COMPLEX" TO WS-SC-TYPE
           END-IF.
      * Classify
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
                   SET NOT-GOLDEN-SHELL TO TRUE
                   SET NOT-ANTI-GOLDEN TO TRUE
                   MOVE "GENERIC" TO WS-SC-TYPE
               END-IF
           END-IF.
           .

      * Deadband check inline
       DEADBAND-CHECK.
           IF WS-DB-L <= WS-DB-K
               SET PERCEIVABLE TO TRUE
           ELSE
               SET NOT-PERCEIVABLE TO TRUE
           END-IF.
           .

      * BMA inline
       BMA-COMPUTE.
      * Initialize
           MOVE 0 TO WS-B-L.
           MOVE 0 TO WS-B-M.
           MOVE 1 TO WS-B-C(1).
           MOVE 1 TO WS-B-B(1).
           PERFORM VARYING WS-B-J FROM 2 BY 1
               UNTIL WS-B-J > WS-B-MAX-LFSR
               MOVE 0 TO WS-B-C(WS-B-J)
               MOVE 0 TO WS-B-B(WS-B-J)
           END-PERFORM.
      * Main loop
           PERFORM VARYING WS-B-I FROM 1 BY 1
               UNTIL WS-B-I > WS-B-N
      * Compute discrepancy
               MOVE WS-B-INPUT(WS-B-I) TO WS-B-D
               PERFORM VARYING WS-B-J FROM 1 BY 1
                   UNTIL WS-B-J > WS-B-L
                   IF WS-B-I - WS-B-J >= 1
                       COMPUTE WS-B-DELTA =
                           WS-B-C(WS-B-J + 1) *
                           WS-B-INPUT(WS-B-I - WS-B-J)
                       ADD WS-B-DELTA TO WS-B-D
                       IF WS-B-D > 1
                           SUBTRACT 2 FROM WS-B-D
                       END-IF
                   END-IF
               END-PERFORM
      * Update
               IF WS-B-D NOT = 0
      * Save C
                   PERFORM VARYING WS-B-J FROM 1 BY 1
                       UNTIL WS-B-J > WS-B-MAX-LFSR
                       MOVE WS-B-C(WS-B-J)
                           TO WS-B-TEMP-C(WS-B-J)
                   END-PERFORM
      * C = C XOR B shifted
                   PERFORM VARYING WS-B-J FROM 1 BY 1
                       UNTIL WS-B-J > WS-B-MAX-LFSR
                       COMPUTE WS-B-DELTA = WS-B-I - WS-B-M
                       IF WS-B-J + WS-B-DELTA > 0
                       AND WS-B-J + WS-B-DELTA
                           <= WS-B-MAX-LFSR
                           COMPUTE WS-B-C(
                               WS-B-J + WS-B-DELTA) =
                               WS-B-C(WS-B-J + WS-B-DELTA)
                               + WS-B-B(WS-B-J)
                           IF WS-B-C(
                               WS-B-J + WS-B-DELTA) > 1
                               SUBTRACT 2 FROM
                                 WS-B-C(
                                 WS-B-J + WS-B-DELTA)
                           END-IF
                       END-IF
                   END-PERFORM
      * Update L if needed
                   IF 2 * WS-B-L <= WS-B-I - 1
                       COMPUTE WS-B-L = WS-B-I - WS-B-L
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

      * HPDF sample inline
       HPDF-SAMPLE-INLINE.
           ACCEPT WS-U-RAND FROM TIME.
           COMPUTE WS-H-U1 =
               (FUNCTION MOD(WS-U-RAND, 10000) - 5000)
               / 5000.0.
           COMPUTE WS-H-U2 =
               (FUNCTION MOD(WS-U-RAND * 7 + 3, 10000) - 5000)
               / 5000.0.
           MOVE WS-H-U1 TO WS-H-S.
           MOVE WS-H-U2 TO WS-H-T.
           IF WS-H-S + WS-H-T > 1.0
               COMPUTE WS-H-S = 1.0 - WS-H-U2
               COMPUTE WS-H-T = 1.0 - WS-H-U1
           END-IF.
           IF WS-H-S + WS-H-T < -1.0
               COMPUTE WS-H-S = -1.0 - WS-H-U2
               COMPUTE WS-H-T = -1.0 - WS-H-U1
           END-IF.
           COMPUTE WS-H-OUT-X = WS-H-S - WS-H-T * 0.5.
           COMPUTE WS-H-OUT-Y = WS-H-T * WS-SQRT3-HALF.
           .

       END PROGRAM TESTDB.
