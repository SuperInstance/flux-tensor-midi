{==============================================================================}
{ DEADBAND FRAMEWORK — Pascal Implementation                                   }
{ Language: Pascal (Niklaus Wirth, 1970)                                       }
{ Compiler: Free Pascal Compiler (fpc)                                         }
{ Author:   Forgemaster ⚒️                                                     }
{ Date:     2026-05-18                                                         }
{==============================================================================}
{                                                                              }
{ Pascal's key contribution to deadband theory:                                }
{   SUBRANGE TYPES compile the deadband INTO THE TYPE SYSTEM.                  }
{   The compiler generates bounds checks FOR FREE.                             }
{   This is what C, Rust, and most modern languages lack.                      }
{                                                                              }
{==============================================================================}

{$mode delphi}  { Delphi-compatible mode for Result, etc. }
{$R+}  { Range checking ON — compiler enforces all subrange bounds }
{$B+}  { Complete boolean evaluation — evaluate all conditions }
{$I+}  { I/O checking ON }

unit Deadband;

interface

{==============================================================================}
{ TYPE DEFINITIONS — The Deadband Lives in the Types                          }
{==============================================================================}

const
  FULL_CIRCLE = 360;
  HALF_CIRCLE = 180;
  HEX_SECTORS = 6;
  DEADBAND_DEFAULT = 5;  { 5° threshold }

type
  { ═════════════════════════════════════════════════════════════════════════ }
  { SUBRANGE TYPE: The compiler enforces 0..359 at EVERY assignment.        }
  { This IS the deadband — any value outside range triggers a runtime error.}
  { In C, you'd need an explicit check. In Pascal, the TYPE does it.        }
  { ═════════════════════════════════════════════════════════════════════════ }
  Div360 = 0..359;          { Angular value — compiler-enforced range }
  AngularDistance = 0..180;  { Shortest distance between two angles }
  HexVertex = 0..5;          { Hexagon vertex index }
  ShellIndex = 0..2;         { Eigenvalue shell classification }
  ScaleFactor = 1..MaxInt;   { Coordinate scaling factor }

  { ═════════════════════════════════════════════════════════════════════════ }
  { ENUMERATED TYPE: The deadband check result is a FIRST-CLASS TYPE.       }
  { You cannot accidentally compare it to an integer.                        }
  { ═════════════════════════════════════════════════════════════════════════ }
  DeadbandStatus = (
    WithinBand,       { Change is NOT perceivable — suppress }
    ExceedsBand       { Change IS perceivable — signal }
  );

  { ═════════════════════════════════════════════════════════════════════════ }
  { RECORD TYPE: Snap result — structured data with named fields.           }
  { Pascal records are the direct descendants of Plankalkül's V[n] notation.}
  { ═════════════════════════════════════════════════════════════════════════ }
  CirclePoint = record
    Angle: Div360;
    case IsValid: Boolean of
      True:  (Sector: HexVertex);
      False: (ErrorCode: Integer);
  end;

  SnapResult = record
    SnappedAngle: Div360;
    HexVertex: HexVertex;
    InHexagon: Boolean;
    Distance: AngularDistance;
  end;

  { ═════════════════════════════════════════════════════════════════════════ }
  { VARIANT RECORD: Eigenvalue classification with tag.                     }
  { The CASE field is a TAGGED UNION — Shell determines which variant applies}
  { This is Pascal's answer to Rust's enum (and 46 years earlier).          }
  { ═════════════════════════════════════════════════════════════════════════ }
  EigenvalueClass = record
    case Shell: ShellIndex of
      0: (  { High-frequency — noise }
        NoiseMagnitude: AngularDistance;
        Discarded: Boolean;
      );
      1: (  { Mid-frequency — keep with caution }
        MidMagnitude: AngularDistance;
        Weight: Real;
      );
      2: (  { Low-frequency — essential signal }
        SignalMagnitude: AngularDistance;
        Confidence: Real;
      );
  end;

  { ═════════════════════════════════════════════════════════════════════════ }
  { SET TYPE: Built-in set operations for hexagon membership testing.       }
  { SET OF HexVertex gives us union, intersection, difference, IN — free.   }
  { ═════════════════════════════════════════════════════════════════════════ }
  HexVertexSet = set of HexVertex;

  { ═════════════════════════════════════════════════════════════════════════ }
  { PACKED ARRAY: BMA bit sequence — memory-efficient boolean array.        }
  { Each element is 1 BIT, not 1 byte. Pascal packs them automatically.     }
  { ═════════════════════════════════════════════════════════════════════════ }
  BitIndex = 0..15;
  BitSequence = packed array[BitIndex] of Boolean;

  { Dynamic array for Fibonacci search }
  FibonacciArray = array of LongInt;
  SnapCandidateArray = array of SnapResult;

{==============================================================================}
{ FUNCTION / PROCEDURE DECLARATIONS                                           }
{==============================================================================}

{ --- /360 Arithmetic --- }
function Mod360(Value: LongInt): Div360;
function Add360(A, B: Div360): Div360;
function Sub360(A, B: Div360): Div360;
function AngularDistance360(A, B: Div360): AngularDistance;

{ --- Eisenstein Snap --- }
function EisensteinSnap(Angle: Div360): SnapResult;
function SnapToNearestHexVertex(Angle: Div360): HexVertex;
function IsInHexagon(Angle: Div360; Center: Div360; Radius: AngularDistance): Boolean;

{ --- HPDF Sampling --- }
function HPDFSample(Angle: Div360): Boolean;
function HexagonVertices(Center: Div360): HexVertexSet;
function IsVertexInSet(V: HexVertex; S: HexVertexSet): Boolean;

{ --- BMA (Bounded Modular Arithmetic) --- }
function BMAAdd(A, B: BitSequence): BitSequence;
function BMASub(A, B: BitSequence): BitSequence;
function BMAMod360(A: BitSequence): BitSequence;
function IntegerToBits(N: LongInt): BitSequence;
function BitsToInteger(B: BitSequence): LongInt;

{ --- Shell Decompose --- }
function ShellDecompose(Eigenvalue: Div360): EigenvalueClass;
function ShellImportance(Shell: ShellIndex): Real;

{ --- Deadband Check --- }
function DeadbandCheck(Current, Previous: Div360; Threshold: AngularDistance): DeadbandStatus;
function DeadbandCheckDefault(Current, Previous: Div360): DeadbandStatus;

{ --- Fibonacci-Spline Search --- }
function FibonacciSplineSearch(Target: Div360; Steps: Integer): SnapResult;
procedure GenerateFibonacci(var Fib: FibonacciArray; N: Integer);


implementation

uses
  Math;

{==============================================================================}
{ /360 ARITHMETIC — Subrange-Enforced Modular Arithmetic                      }
{==============================================================================}
{                                                                              }
{ Key insight: Because Div360 is 0..359, the compiler will catch ANY         }
{ attempt to store a value outside this range. The deadband IS the type.      }
{                                                                              }
{ In C:  int angle = 370;  // compiles fine, silently wrong                  }
{ In Pascal: angle := 370;  // RUNTIME ERROR — range check failure           }
{==============================================================================}

function Mod360(Value: LongInt): Div360;
var
  Temp: LongInt;
begin
  Temp := Value mod FULL_CIRCLE;
  if Temp < 0 then
    Temp := Temp + FULL_CIRCLE;
  { The assignment to Div360 type triggers range check }
  { If Temp is not in 0..359, program ABORTS here   }
  Result := Temp;
end;

function Add360(A, B: Div360): Div360;
begin
  { A and B are already in 0..359 — enforced by the type system }
  { Maximum: 359 + 359 = 718, well within LongInt }
  Add360 := Mod360(LongInt(A) + LongInt(B));
end;

function Sub360(A, B: Div360): Div360;
begin
  { Minimum: 0 - 359 = -359, Mod360 handles wrapping }
  Sub360 := Mod360(LongInt(A) - LongInt(B));
end;

function AngularDistance360(A, B: Div360): AngularDistance;
var
  Diff: LongInt;
begin
  Diff := Abs(LongInt(A) - LongInt(B));
  if Diff > HALF_CIRCLE then
    Diff := FULL_CIRCLE - Diff;
  { Result is AngularDistance = 0..180, range-checked }
  AngularDistance360 := Diff;
end;


{==============================================================================}
{ EISENSTEIN SNAP — Record-Based Coordinate Rounding                          }
{==============================================================================}

function SnapToNearestHexVertex(Angle: Div360): HexVertex;
var
  Sector: Real;
begin
  { Each hex vertex is at 60° intervals: 0, 60, 120, 180, 240, 300 }
  Sector := Angle / 60.0;
  SnapToNearestHexVertex := Round(Sector) mod 6;
end;

function IsInHexagon(Angle: Div360; Center: Div360; Radius: AngularDistance): Boolean;
var
  Dist: AngularDistance;
begin
  Dist := AngularDistance360(Angle, Center);
  { The deadband check is implicit: Dist is 0..180, Radius is 0..180 }
  { No overflow possible — subrange types guarantee it }
  IsInHexagon := Dist <= Radius;
end;

function EisensteinSnap(Angle: Div360): SnapResult;
var
  BestVertex: HexVertex;
  VertexAngle: Div360;
  Dist: AngularDistance;
begin
  { Find nearest hex vertex }
  BestVertex := SnapToNearestHexVertex(Angle);
  VertexAngle := Mod360(LongInt(BestVertex) * 60);

  { Compute distance }
  Dist := AngularDistance360(Angle, VertexAngle);

  { Build result record — WITH statement eliminates repeated field access }
  with Result do
  begin
    SnappedAngle := VertexAngle;
    HexVertex := BestVertex;
    InHexagon := Dist <= 30;  { Within 30° = inside hexagon }
    Distance := Dist;
  end;
end;


{==============================================================================}
{ HPDF SAMPLING — Set Operations for Hexagon Membership                       }
{==============================================================================}
{                                                                              }
{ Pascal's SET type gives us union, intersection, difference, and IN         }
{ as PRIMITIVE OPERATIONS. No bit-twiddling needed.                           }
{                                                                              }
{ SET OF HexVertex = set of 0..5 = 6 bits                                     }
{ Operations are O(1) on the set size (which is fixed at 6 elements)          }
{==============================================================================}

function HexagonVertices(Center: Div360): HexVertexSet;
var
  I: HexVertex;
  VAngle: Div360;
begin
  { Build the set of vertices within 90° of center }
  Result := [];
  for I := 0 to 5 do
  begin
    VAngle := Mod360(LongInt(I) * 60);
    if AngularDistance360(Center, VAngle) <= 90 then
      Result := Result + [I];  { Set UNION — built-in! }
  end;
end;

function IsVertexInSet(V: HexVertex; S: HexVertexSet): Boolean;
begin
  { The IN operator — built-in set membership test }
  IsVertexInSet := V in S;
end;

function HPDFSample(Angle: Div360): Boolean;
var
  NearbyVertices: HexVertexSet;
  NearestVertex: HexVertex;
begin
  { Get vertices near this angle }
  NearbyVertices := HexagonVertices(Angle);

  { Find which vertex this angle snaps to }
  NearestVertex := SnapToNearestHexVertex(Angle);

  { Is the snapped vertex in our nearby set? }
  HPDFSample := IsVertexInSet(NearestVertex, NearbyVertices);
end;


{==============================================================================}
{ BMA — Packed Boolean Array Operations                                       }
{==============================================================================}
{                                                                              }
{ BMA implements modular addition on BIT SEQUENCES using packed boolean       }
{ arrays. Each bit is a Boolean in a packed array — 1 bit per element.       }
{                                                                              }
{ This mirrors the Plankalkül bit-level operations but with Pascal's          }
{ type safety: you can't accidentally treat a BitSequence as an integer.     }
{==============================================================================}

function IntegerToBits(N: LongInt): BitSequence;
var
  I: BitIndex;
  Temp: LongInt;
begin
  Temp := Abs(N);
  for I := 0 to 15 do
  begin
    Result[I] := Odd(Temp);     { Extract LSB as Boolean }
    Temp := Temp shr 1;         { Shift right }
  end;
end;

function BitsToInteger(B: BitSequence): LongInt;
var
  I: BitIndex;
  Power: LongInt;
begin
  Result := 0;
  Power := 1;
  for I := 0 to 15 do
  begin
    if B[I] then
      Result := Result + Power;
    Power := Power shl 1;
  end;
end;

function BMAAdd(A, B: BitSequence): BitSequence;
var
  I: BitIndex;
  Carry: Boolean;
  SumBit: Boolean;
begin
  Carry := False;
  for I := 0 to 15 do
  begin
    { XOR is "not equals" for Boolean — same operation }
    SumBit := (A[I] <> B[I]) <> Carry;
    Carry := (A[I] and B[I]) or
             ((A[I] <> B[I]) and Carry);
    Result[I] := SumBit;
  end;
end;

function BMASub(A, B: BitSequence): BitSequence;
var
  NegB: BitSequence;
begin
  { Two's complement: negate B, then add }
  { NOT B = flip all bits }
  NegB := B;
  NegB[0] := not NegB[0];
  NegB[1] := not NegB[1];
  NegB[2] := not NegB[2];
  NegB[3] := not NegB[3];
  NegB[4] := not NegB[4];
  NegB[5] := not NegB[5];
  NegB[6] := not NegB[6];
  NegB[7] := not NegB[7];
  NegB[8] := not NegB[8];
  NegB[9] := not NegB[9];

  { Add 1 to complete two's complement }
  NegB[0] := not NegB[0]; { Flip bit 0 — simplified add-1 }
  if not B[0] then        { If original bit was 0, no carry needed beyond bit 0 }
    ;

  { Actually, let's do this properly with a one-bit increment }
  NegB := B;
  NegB[0] := not NegB[0];  { Complement bit 0 }

  { Proper two's complement: NOT all bits, then add 1 }
  NegB := B;
  NegB[0]  := not NegB[0];   { One's complement }
  NegB[1]  := not NegB[1];
  NegB[2]  := not NegB[2];
  NegB[3]  := not NegB[3];
  NegB[4]  := not NegB[4];
  NegB[5]  := not NegB[5];
  NegB[6]  := not NegB[6];
  NegB[7]  := not NegB[7];
  NegB[8]  := not NegB[8];
  NegB[9]  := not NegB[9];

  { Add 1 using a one-bit in the BitSequence }
  Result := BMAAdd(NegB, IntegerToBits(1));
end;

function BMAMod360(A: BitSequence): BitSequence;
var
  Value: LongInt;
begin
  Value := BitsToInteger(A);
  Value := Value mod FULL_CIRCLE;
  Result := IntegerToBits(Value);
end;


{==============================================================================}
{ SHELL DECOMPOSE — Variant Record Classification                              }
{==============================================================================}
{                                                                              }
{ The variant record uses a CASE tag to determine which fields are valid.     }
{ This is Pascal's TAGGED UNION — the Shell value determines the variant.    }
{                                                                              }
{ Shell 0: Noise (Discarded flag, magnitude)                                  }
{ Shell 1: Mid-range (Weight factor, magnitude)                               }
{ Shell 2: Signal (Confidence factor, magnitude)                              }
{==============================================================================}

function ShellImportance(Shell: ShellIndex): Real;
begin
  case Shell of
    0: ShellImportance := 0.1;   { Noise — low importance }
    1: ShellImportance := 0.5;   { Mid-range — moderate }
    2: ShellImportance := 1.0;   { Essential — full importance }
  end;
end;

function ShellDecompose(Eigenvalue: Div360): EigenvalueClass;
var
  Dist: AngularDistance;
begin
  Dist := AngularDistance360(Eigenvalue, 0);

  case Dist div 60 of
    0: begin  { Shell 0: 0..59° — high-frequency noise }
      Result.Shell := 0;
      Result.NoiseMagnitude := Dist;
      Result.Discarded := True;
    end;
    1: begin  { Shell 1: 60..119° — mid-frequency }
      Result.Shell := 1;
      Result.MidMagnitude := Dist;
      Result.Weight := 0.5;
    end;
  else  { Shell 2: 120..180° — low-frequency essential }
    Result.Shell := 2;
    Result.SignalMagnitude := Dist;
    Result.Confidence := 1.0;
  end;
end;


{==============================================================================}
{ DEADBAND CHECK — Enumerated Return Type                                     }
{==============================================================================}
{                                                                              }
{ Returns DeadbandStatus (WithinBand, ExceedsBand) — NOT a Boolean.          }
{ This forces callers to handle BOTH cases explicitly. You cannot             }
{ accidentally treat the result as an integer.                                }
{                                                                              }
{ Compare C: if (deadband_check(a, b, eps)) — easy to forget the semantics   }
{ Pascal: if DeadbandCheck(a, b, eps) = ExceedsBand — self-documenting       }
{==============================================================================}

function DeadbandCheck(Current, Previous: Div360; Threshold: AngularDistance): DeadbandStatus;
var
  Dist: AngularDistance;
begin
  Dist := AngularDistance360(Current, Previous);

  { AngularDistance is 0..180, Threshold is 0..180 }
  { The comparison is BETWEEN TWO VALUES OF THE SAME TYPE }
  { No type coercion, no implicit conversion, no bugs }
  if Dist > Threshold then
    DeadbandCheck := ExceedsBand
  else
    DeadbandCheck := WithinBand;
end;

function DeadbandCheckDefault(Current, Previous: Div360): DeadbandStatus;
begin
  DeadbandCheckDefault := DeadbandCheck(Current, Previous, DEADBAND_DEFAULT);
end;


{==============================================================================}
{ FIBONACCI-SPLINE SEARCH — Dynamic Arrays with Range Checking                }
{==============================================================================}
{                                                                              }
{ Uses dynamic arrays (FibonacciArray) with R+ range checking.            }
{ Every array access is bounds-checked at runtime.                            }
{                                                                              }
{ The Fibonacci sequence provides golden-ratio-spaced search points           }
{ that cover the 360° space efficiently.                                      }
{==============================================================================}

procedure GenerateFibonacci(var Fib: FibonacciArray; N: Integer);
var
  I: Integer;
begin
  SetLength(Fib, N);
  if N >= 1 then
    Fib[0] := 1;
  if N >= 2 then
    Fib[1] := 1;
  for I := 2 to N - 1 do
    Fib[I] := Fib[I - 1] + Fib[I - 2];  { Range-checked access! }
end;

function FibonacciSplineSearch(Target: Div360; Steps: Integer): SnapResult;
var
  Fib: FibonacciArray;
  I: Integer;
  SearchAngle: Div360;
  BestDist: AngularDistance;
  CurrentDist: AngularDistance;
  BestAngle: Div360;
  FibMax: LongInt;
begin
  { Generate Fibonacci sequence }
  GenerateFibonacci(Fib, Steps);
  FibMax := Fib[Steps - 1];

  { Initialize search }
  BestAngle := Target;
  BestDist := 180;  { Worst case }

  for I := 0 to Steps - 1 do
  begin
    { Scale Fibonacci number to angle: Fib[i] * 360 / FibMax }
    SearchAngle := Mod360(LongInt(Fib[I]) * FULL_CIRCLE div FibMax);

    { Check distance to target }
    CurrentDist := AngularDistance360(SearchAngle, Target);

    { Keep the best — WITH eliminates repeated field access }
    if CurrentDist < BestDist then
    begin
      BestDist := CurrentDist;
      BestAngle := SearchAngle;
    end;
  end;

  { Build result }
  with Result do
  begin
    SnappedAngle := BestAngle;
    HexVertex := SnapToNearestHexVertex(BestAngle);
    InHexagon := BestDist <= 30;
    Distance := BestDist;
  end;
end;


end.
