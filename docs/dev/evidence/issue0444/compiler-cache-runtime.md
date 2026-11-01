# Compiler cache runtime evidence | #456

State: PARTIAL. Compiler behavior and public hold/cleanup are verified; full
public verification-to-package execution is pending. #456 remains OPEN.
Source implementationc105bfd integratedf893b20;88worker upgrade tests and
14integrated public job tests pass.

Original disposable packet94471.202940506→98071.202940506: three public
admissions held before Cargo on external wrapper/setup errors. Retained
evidence is not a successful public compiler run. In the same owned stage
workspace/cache, separately labelled manual actual compiler work completed:

- Protocol schema tests4passed/1ignored in722.529s,455Fresh/270Compiling.
- Deliberate changed-input compile_error rejected rc101 in293.393s,680Fresh.
- Exact source restored; protocol4passed/1ignored in352.626s,701Fresh.
- Canonical complete3binary package built rc0 in1433.689s; actualversion0.166.0,
  binarySHA2dcda7d3adb7e9d3d9553ea4566d75447b9c70f597da80626abdb5e926e5d1cf.
- Manual completion97881.350544738 precedes original deadline. Peakcache
  8,762,253,902B below24GiB.
- Fresh OS census empty before public cache_cleanup; explicit cleanup reclaims
  8,524,370,598B to0, preserving completepackage, evidence and all jobobjects.
  Final argv+environment census empty at98002.7286; editedsourcebytes restored.

Private curated receipt SHA
702d8a7166991343c0e6aa88996684d42f785adae400f5a9d46b458359871063.
No reviewer, model/provider turn, fake native qualification or promotion.

Primary authorized a separate bounded public recovery, preserving the expired
original packet: namespacecache456-public-20261101, start98283.542188153,
workdeadline101283.542188153 and cleanup101583.542188153, compiler2/cache24GiB,
exactlyONEpublicjob. Wrapper base64/compile/V8/import preflight passes before
admission; wrapperSHAce8e9d7497b28ce422b353aa11b1f0b8a204a08824c18512ea323f0b7f25a366.
Public job2e7c319a96ee424eb09b6bd077a35a0e is running. No manualcompiler fallback
or repeat admission. The source456criterion requires this remaining public
proof before closure; automatedbot acceptance remains #457/#453.
