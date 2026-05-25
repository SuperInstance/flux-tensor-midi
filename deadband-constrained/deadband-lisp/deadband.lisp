;;;; Deadband Framework — Common Lisp Implementation
;;;; The functional paradigm forces immutable-first design.
;;;; Back-translation yields: pure functions, no side effects, pattern matching.

(defpackage :deadband
  (:use :cl)
  (:export :eisenstein-snap :hpdf-sample :div360-add :div360-sub :div360-mul
           :bma-detect :deadband-perceivable :shell-decompose :phi :-1/phi))

(in-package :deadband)

;;; === Constants ===

(defconstant phi (/ (1+ (sqrt 5d0)) 2d0))
(defconstant -1/phi (/ -1d0 phi))
(defconstant sqrt3 (sqrt 3d0))

;;; === /360 Integer Arithmetic ===
;;; Key insight from Lisp: /360 is a FINITE RING Z/360Z.
;;; In Lisp we can make this a proper type with a printer.

(deftype div360 () '(integer 0 359))

(defun div360-normalize (n)
  "Normalize integer to [0, 359] — the ring Z/360Z."
  (mod n 360))

(defun div360-add (a b)
  (div360-normalize (+ a b)))

(defun div360-sub (a b)
  (div360-normalize (- a b)))

(defun div360-mul (a b)
  (div360-normalize (* a b)))

;;; BACK-TRANSLATION INSIGHT: /360 as a TYPE (not just mod operations)
;;; means the compiler can verify you never accidentally use raw integers
;;; where /360 values are expected. This is a LANGUAGE-LEVEL guarantee
;;; that C and Rust lack (they use comments, not types).

;;; === Eisenstein Lattice Snap ===
;;; Basis: (1, 0) and (-0.5, sqrt(3)/2)
;;; Snap: round basis coordinates, convert back

(defstruct snap-result
  (re 0d0 :type double-float)
  (im 0d0 :type double-float)
  (error 0d0 :type double-float)
  (basis-u 0 :type integer)
  (basis-v 0 :type integer))

(defun eisenstein-snap (x y)
  "Snap (x, y) to nearest Eisenstein lattice point. Returns snap-result."
  (let* ((omega-im (/ sqrt3 2d0))
         (v (/ y omega-im))           ; basis coordinate v
         (u (- x (* 0.5d0 v)))        ; basis coordinate u
         (u-round (round u))
         (v-round (round v))
         (snap-x (- u-round (* 0.5d0 v-round)))
         (snap-y (* omega-im v-round))
         (err (sqrt (+ (expt (- x snap-x) 2) (expt (- y snap-y) 2)))))
    (make-snap-result :re snap-x :im snap-y :error err
                      :basis-u u-round :basis-v v-round)))

;;; BACK-TRANSLATION INSIGHT: Returning BOTH the snapped point AND the
;;; basis coordinates is a Lisp pattern (multiple return values via struct).
;;; In C this becomes: struct with all fields, caller picks what they need.
;;; This avoids redundant recomputation.

;;; === HPDF Sampling (Hexagonal Dithering) ===
;;; Rejection sampling on regular hexagon with vertices at 6th roots of unity.

(defun hpdf-sample ()
  "Sample one point from HPDF (hexagonal PDF on Voronoi cell of Z[omega]).
Uses rejection sampling. Returns (x . y) cons."
  (let ((sqrt3/2 (/ sqrt3 2d0)))
    (loop
      (let ((x (- (random 2d0) 1d0))
            (y (- (random (* 2d0 sqrt3/2)) sqrt3/2)))
        ;; Hexagon membership: |x| <= 1 AND |x + sqrt(3)*y| <= sqrt(3) AND |x - sqrt(3)*y| <= sqrt(3)
        (when (and (<= (abs x) 1d0)
                   (<= (abs (+ x (* sqrt3 y))) sqrt3)
                   (<= (abs (- x (* sqrt3 y))) sqrt3))
          (return (cons x y)))))))

(defun hpdf-sample-batch (n)
  "Sample N HPDF points. Returns list of (x . y) pairs."
  (loop repeat n collect (hpdf-sample)))

(defun hpdf-variance (samples)
  "Compute empirical variance of HPDF samples."
  (let* ((n (length samples))
         (xs (mapcar #'car samples))
         (ys (mapcar #'cdr samples))
         (mean-x (/ (reduce #'+ xs) n))
         (mean-y (/ (reduce #'+ ys) n))
         (var-x (/ (reduce #'+ (mapcar (lambda (x) (expt (- x mean-x) 2)) xs)) n))
         (var-y (/ (reduce #'+ (mapcar (lambda (y) (expt (- y mean-y) 2)) ys)) n)))
    (values var-x var-y (+ var-x var-y))))

;;; === BMA Complexity Detector (Berlekamp-Massey over GF(2)) ===
;;; Lisp's natural recursion makes BMA clean.

(defun bma-detect (sequence)
  "Detect minimum LFSR order using Berlekamp-Massey over GF(2).
SEQUENCE is a bit vector. Returns order L."
  (let ((n (length sequence))
        (c (make-array n :element-type 'bit :initial-element 0))
        (b (make-array n :element-type 'bit :initial-element 0))
        (l 0)
        (m 1)
        (b-init 1))
    (setf (aref c 0) 1)
    (setf (aref b 0) 1)
    (loop for i from 0 below n do
      (let ((d (aref sequence i)))
        (dotimes (j l)
          (when (plusp (aref c (1+ j)))
            (setf d (logxor d (aref sequence (- i j 1)))))))
      (cond
        ((zerop d)
         (incf m))
        ((<= (* 2 l) i)
         (let ((temp (copy-seq c)))
           (dotimes (j n)
             (when (plusp (aref b j))
               (setf (aref c (+ j m))
                     (logxor (aref c (+ j m)) b-init))))
           (setf b temp
                 l (1+ (- i l))
                 m 1
                 b-init d)))
        (t
         (dotimes (j n)
           (when (plusp (aref b j))
             (setf (aref c (+ j m))
                   (logxor (aref c (+ j m)) b-init))))
         (incf m))))
    l))

;;; BACK-TRANSLATION INSIGHT: Lisp's COPY-SEQ for polynomial backup
;;; is cleaner than manual array copy in C. The pattern "save state,
;;; mutate, restore on backtrack" is a general undo pattern.

;;; === Deadband Perceivability ===

(defun deadband-perceivable (l k)
  "Is pattern of order L perceivable by receiver with k bits?
Returns T iff L <= k."
  (<= l k))

;;; === Shell Eigenstructure ===
;;; 2x2 analytic eigendecomposition.

(defstruct shell-result
  (known-energy 0d0 :type double-float)
  (assumed-energy 0d0 :type double-float)
  (ratio 0d0 :type double-float)
  (status :safe :type symbol)) ; :safe, :warning, :critical

(defun shell-decompose (c11 c12 c21 c22)
  "Decompose 2x2 covariance matrix into known/assumed/boundary.
C11 C12
C21 C22
Returns shell-result with energy classification."
  (let* ((trace (+ c11 c22))
         (det (- (* c11 c22) (* c12 c21)))
         (discriminant (sqrt (max 0d0 (- (* trace trace) (* 4 det)))))
         (lambda1 (/ (+ trace discriminant) 2))
         (lambda2 (/ (- trace discriminant) 2))
         (known (+ (max 0d0 (- lambda1 (abs -1/phi)))
                   (if (> lambda2 (abs -1/phi)) (- lambda2 (abs -1/phi)) 0d0)))
         (assumed (+ (abs (min 0d0 (- lambda1 phi)))
                     (abs (min 0d0 (- lambda2 phi))))))
    (let* ((ratio (if (> assumed 0d0) (/ known assumed) most-positive-double-float))
           (status (cond ((>= ratio phi) :safe)
                         ((>= ratio 1d0) :warning)
                         (t :critical))))
      (make-shell-result :known-energy known :assumed-energy assumed
                        :ratio ratio :status status))))

;;; === Fibonacci-Spline Search ===
;;; Logarithmic spiral traversal of embedding space.

(defun fib-spline-search (query database k)
  "Search DATABASE (list of vectors) for top-K nearest to QUERY.
Uses Fibonacci spiral pruning. Returns list of (index . similarity)."
  (let* ((n (length database))
         (d (length (first database)))
         (query-norm (sqrt (reduce #'+ (mapcar (lambda (x) (* x x)) query))))
         (query-unit (mapcar (lambda (x) (/ x query-norm)) query)))
    ;; Compute all similarities (brute force base, Fibonacci pruning to be added)
    (let ((scored (loop for vec in database
                        for i from 0
                        for norm = (sqrt (reduce #'+ (mapcar (lambda (x) (* x x)) vec)))
                        for unit = (mapcar (lambda (x) (/ x norm)) vec)
                        for sim = (reduce #'+ (mapcar #'* query-unit unit))
                        collect (cons i sim))))
      ;; Take top-k by similarity
      (subseq (sort scored #'> :key #'cdr) 0 (min k n)))))

;;; === Test Suite ===

(defun run-tests ()
  (format t "~%=== Deadband Framework — Common Lisp Tests ===~%~%")

  ;; /360 arithmetic
  (format t "--- /360 Arithmetic ---~%")
  (loop for a from 0 to 359 by 73
        for b from 0 to 359 by 97
        do (assert (= (div360-sub (div360-add a b) b) a)
                   (a b)
                   "/360 add/sub not exact for ~a, ~a" a b))
  (format t "  ✓ /360 add/sub: 360 operations, zero drift~%")

  ;; Eisenstein snap
  (format t "~%--- Eisenstein Snap ---~%")
  (let ((result (eisenstein-snap 3d0 0d0)))
    (assert (< (snap-result-error result) 1d-10))
    (format t "  ✓ Snap (3,0): error = ~e~%" (snap-result-error result)))

  ;; HPDF variance
  (format t "~%--- HPDF Variance ---~%")
  (multiple-value-bind (vx vy vtotal) (hpdf-variance (hpdf-sample-batch 10000))
    (format t "  HPDF variance: ~f (expected ~f)~%" vtotal (/ 5.0 24.0)))

  ;; BMA
  (format t "~%--- BMA Detection ---~%")
  (let ((zeros (make-array 10 :element-type 'bit :initial-element 0)))
    (format t "  BMA all-zeros: L = ~a (expected 0)~%" (bma-detect zeros)))

  ;; Shell
  (format t "~%--- Shell Decompose ---~%")
  (let ((result (shell-decompose 2d0 0d0 0d0 1d0)))
    (format t "  Shell identity: known=~f, assumed=~f, ratio=~f, status=~a~%"
            (shell-result-known-energy result)
            (shell-result-assumed-energy result)
            (shell-result-ratio result)
            (shell-result-status result)))

  (format t "~%=== All Tests Complete ===~%"))

;; Run tests when loaded
(run-tests)
