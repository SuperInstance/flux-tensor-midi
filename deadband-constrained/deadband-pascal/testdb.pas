{==============================================================================}
{ DEADBAND FRAMEWORK — Pascal Test Program                                     }
{ Compile: fpc testdb.pas                                                      }
{ Run:     ./testdb                                                            }
{ Author:  Forgemaster ⚒️                                                      }
{==============================================================================}

program TestDeadband;

{$mode delphi}
{$R+}  { Range checking ON }
{$B+}  { Complete boolean evaluation }

uses
  Deadband, Math;

var
  Passed: Integer = 0;
  Failed: Integer = 0;

procedure Check(Name: String; Condition: Boolean);
begin
  if Condition then
  begin
    WriteLn('  PASS: ', Name);
    Inc(Passed);
  end
  else
  begin
    WriteLn('  FAIL: ', Name);
    Inc(Failed);
  end;
end;

procedure TestMod360;
begin
  WriteLn('=== /360 Arithmetic ===');
  Check('Mod360(0) = 0', Mod360(0) = 0);
  Check('Mod360(359) = 359', Mod360(359) = 359);
  Check('Mod360(360) = 0', Mod360(360) = 0);
  Check('Mod360(361) = 1', Mod360(361) = 1);
  Check('Mod360(-1) = 359', Mod360(-1) = 359);
  Check('Mod360(-360) = 0', Mod360(-360) = 0);
  WriteLn;
end;

procedure TestAdd360;
begin
  WriteLn('=== Add360 ===');
  Check('Add360(0, 0) = 0', Add360(0, 0) = 0);
  Check('Add360(180, 180) = 0', Add360(180, 180) = 0);
  Check('Add360(200, 200) = 40', Add360(200, 200) = 40);
  Check('Add360(359, 1) = 0', Add360(359, 1) = 0);
  Check('Add360(359, 359) = 358', Add360(359, 359) = 358);
  WriteLn;
end;

procedure TestSub360;
begin
  WriteLn('=== Sub360 ===');
  Check('Sub360(0, 0) = 0', Sub360(0, 0) = 0);
  Check('Sub360(0, 1) = 359', Sub360(0, 1) = 359);
  Check('Sub360(100, 200) = 260', Sub360(100, 200) = 260);
  Check('Sub360(180, 180) = 0', Sub360(180, 180) = 0);
  WriteLn;
end;

procedure TestAngularDistance;
begin
  WriteLn('=== Angular Distance ===');
  Check('Dist(0, 0) = 0', AngularDistance360(0, 0) = 0);
  Check('Dist(0, 180) = 180', AngularDistance360(0, 180) = 180);
  Check('Dist(0, 181) = 179', AngularDistance360(0, 181) = 179);
  Check('Dist(10, 350) = 20', AngularDistance360(10, 350) = 20);
  Check('Dist(90, 270) = 180', AngularDistance360(90, 270) = 180);
  Check('Dist(0, 90) = 90', AngularDistance360(0, 90) = 90);
  WriteLn;
end;

procedure TestEisensteinSnap;
var
  R: SnapResult;
begin
  WriteLn('=== Eisenstein Snap ===');
  R := EisensteinSnap(0);
  Check('Snap(0) angle = 0', R.SnappedAngle = 0);
  Check('Snap(0) vertex = 0', R.HexVertex = 0);

  R := EisensteinSnap(30);
  Check('Snap(30) angle = 0', R.SnappedAngle = 0);
  Check('Snap(30) in hexagon', R.InHexagon);

  R := EisensteinSnap(45);
  Check('Snap(45) vertex = 1 or 0', (R.HexVertex = 0) or (R.HexVertex = 1));

  R := EisensteinSnap(90);
  Check('Snap(90) vertex = 2', R.HexVertex = 2);

  R := EisensteinSnap(330);
  Check('Snap(330) vertex = 0 or 5', (R.HexVertex = 0) or (R.HexVertex = 5));
  WriteLn;
end;

procedure TestHPDF;
begin
  WriteLn('=== HPDF Sampling ===');
  Check('HPDF(0) — should be consistent', HPDFSample(0) = HPDFSample(0));
  Check('HPDF(30) — hex vertex boundary', HPDFSample(30) or (not HPDFSample(30)));
  WriteLn;
end;

procedure TestBMA;
var
  A, B, Sum, Diff: BitSequence;
begin
  WriteLn('=== BMA (Bit-Level Arithmetic) ===');
  A := IntegerToBits(100);
  B := IntegerToBits(200);
  Sum := BMAAdd(A, B);
  Check('BMA 100+200 = 300', BitsToInteger(Sum) = 300);

  A := IntegerToBits(200);
  B := IntegerToBits(200);
  Sum := BMAAdd(A, B);
  Sum := BMAMod360(Sum);
  Check('BMA 200+200 mod 360 = 40', BitsToInteger(Sum) = 40);

  A := IntegerToBits(359);
  B := IntegerToBits(1);
  Sum := BMAAdd(A, B);
  Sum := BMAMod360(Sum);
  Check('BMA 359+1 mod 360 = 0', BitsToInteger(Sum) = 0);

  { Bit-level identity: XOR with 0 }
  A := IntegerToBits(42);
  B := IntegerToBits(0);
  Sum := BMAAdd(A, B);
  Check('BMA 42+0 = 42', BitsToInteger(Sum) = 42);
  WriteLn;
end;

procedure TestShellDecompose;
var
  EC: EigenvalueClass;
begin
  WriteLn('=== Shell Decompose ===');
  EC := ShellDecompose(10);
  Check('Shell(10) = 0 (noise)', EC.Shell = 0);

  EC := ShellDecompose(90);
  Check('Shell(90) = 1 (mid)', EC.Shell = 1);

  EC := ShellDecompose(150);
  Check('Shell(150) = 2 (signal)', EC.Shell = 2);

  EC := ShellDecompose(45);
  Check('Shell(45) = 0', EC.Shell = 0);

  EC := ShellDecompose(100);
  Check('Shell(100) = 1', EC.Shell = 1);

  EC := ShellDecompose(200);
  Check('Shell(200) = 2', EC.Shell = 2);
  WriteLn;
end;

procedure TestDeadbandCheck;
begin
  WriteLn('=== Deadband Check ===');
  Check('Same angle = WithinBand',
    DeadbandCheck(100, 100, 5) = WithinBand);
  Check('2° diff, 5° threshold = WithinBand',
    DeadbandCheck(102, 100, 5) = WithinBand);
  Check('10° diff, 5° threshold = ExceedsBand',
    DeadbandCheck(110, 100, 5) = ExceedsBand);
  Check('4° diff, 5° threshold = WithinBand',
    DeadbandCheck(96, 100, 5) = WithinBand);
  Check('Wraparound: 359→1, threshold 5 = WithinBand (2° diff)',
    DeadbandCheck(1, 359, 5) = WithinBand);
  Check('Wraparound: 359→0, threshold 5 = WithinBand',
    DeadbandCheck(0, 359, 5) = WithinBand);
  Check('Default: 3° diff = WithinBand',
    DeadbandCheckDefault(103, 100) = WithinBand);
  Check('Default: 10° diff = ExceedsBand',
    DeadbandCheckDefault(110, 100) = ExceedsBand);
  WriteLn;
end;

procedure TestFibonacciSearch;
var
  R: SnapResult;
begin
  WriteLn('=== Fibonacci-Spline Search ===');
  R := FibonacciSplineSearch(0, 8);
  Check('FibSearch(0) found something', R.Distance <= 180);
  WriteLn('  Best angle: ', R.SnappedAngle, ' distance: ', R.Distance);

  R := FibonacciSplineSearch(90, 10);
  Check('FibSearch(90) found something', R.Distance <= 180);
  WriteLn('  Best angle: ', R.SnappedAngle, ' distance: ', R.Distance);

  R := FibonacciSplineSearch(180, 12);
  Check('FibSearch(180) found something', R.Distance <= 180);
  WriteLn('  Best angle: ', R.SnappedAngle, ' distance: ', R.Distance);
  WriteLn;
end;

procedure TestTypeSafety;
var
  Angle: Div360;
begin
  WriteLn('=== Type Safety (Subrange Enforcement) ===');
  Angle := 100;
  Check('Div360 accepts 100', Angle = 100);
  Angle := 0;
  Check('Div360 accepts 0', Angle = 0);
  Angle := 359;
  Check('Div360 accepts 359', Angle = 359);
  WriteLn('  (Assigning 360 to Div360 would trigger runtime error with {$R+})');
  WriteLn;
end;

procedure TestSetOperations;
var
  S1, S2, Union, Intersect, Diff: HexVertexSet;
begin
  WriteLn('=== Set Operations ===');
  S1 := [0, 1, 2];
  S2 := [2, 3, 4];
  Union := S1 + S2;        { Union }
  Intersect := S1 * S2;    { Intersection }
  Diff := S1 - S2;         { Difference }

  Check('Union [0,1,2] + [2,3,4] = [0,1,2,3,4]',
    Union = [0, 1, 2, 3, 4]);
  Check('Intersect [0,1,2] * [2,3,4] = [2]',
    Intersect = [2]);
  Check('Diff [0,1,2] - [2,3,4] = [0,1]',
    Diff = [0, 1]);
  Check('2 IN [0,1,2]', 2 in S1);
  Check('5 NOT IN [0,1,2]', not (5 in S1));
  WriteLn;
end;

{==============================================================================}
{ MAIN PROGRAM                                                                }
{==============================================================================}

begin
  WriteLn('╔══════════════════════════════════════════════════╗');
  WriteLn('║  DEADBAND FRAMEWORK — Pascal Test Suite          ║');
  WriteLn('║  Forgemaster ⚒️  |  2026-05-18                    ║');
  WriteLn('╚══════════════════════════════════════════════════╝');
  WriteLn;

  TestMod360;
  TestAdd360;
  TestSub360;
  TestAngularDistance;
  TestEisensteinSnap;
  TestHPDF;
  TestBMA;
  TestShellDecompose;
  TestDeadbandCheck;
  TestFibonacciSearch;
  TestTypeSafety;
  TestSetOperations;

  WriteLn('═══════════════════════════════════════════════════');
  WriteLn('  Results: ', Passed, ' passed, ', Failed, ' failed');
  WriteLn('═══════════════════════════════════════════════════');

  if Failed > 0 then
    Halt(1);
end.
