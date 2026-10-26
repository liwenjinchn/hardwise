# Windows validation capsule v1

This is a pinned public source package for T08 target-machine validation. It is not a release approval, portable project backup, dependency installer, or proof of actual Cadence compatibility.

## Build and run

```bash
uv run python scripts/build_validation_bundle.py --output /absolute/path/Hardwise-Windows-check.zip
```

The supported source commit is `dab2e9149fe4dcca02c61cbcd4f0f9396ac6368b`. Other refs are rejected until the recorded public software baseline is updated deliberately. The package uses that Git tree, plus explicitly named verifier, public workflow helper, baseline and instructions. Its manifest hashes 958 source/supplement files; the manifest itself is the 959th file. Hashes detect accidental changes against this manifest; they are not a signature or an independent engineering correctness check. Local ignored environment, uploads, databases and generated reports are excluded by Git archive.

Extract to a normal directory. In native Windows PowerShell, from the extracted root:

```powershell
uv --version
uv sync --locked --extra dev
uv run python VALIDATE.py --require-windows
```

The first dependency installation requires network. No execution-policy change or model key is required. The verifier disables dotenv and clears model credentials only in its process and child. It verifies hashes, imports backend code from the extracted source, compares the entire recorded public-fixture summary and emitted-check coverage, generates the existing white React offline report, and runs real-mode no-key CLI dry-run. It also exercises canonical review states, rejects new legacy-state writes, captures offline history, saves managed inputs, downloads a project backup, makes original paths unavailable and verifies restored decisions/reasons in a fresh process. These are synthetic operations, never human engineering approvals. Results are saved under reports with unique names. `--hash-only` skips software probes. `--require-windows` fails on non-Windows.

Read START-HERE.md for the live workbench command and blank manual record. Follow import, explain UNKNOWN, handle one item, save, restart by saved managed-project ID, download a backup and restore an independent copy, export, stop server and read the offline report. Record the actual Windows/EDA version, installation result and public/synthetic Cadence export route. These observations must come from the target machine; the script never fills actual Cadence acceptance, human profile approval or product release approval.

## Previous 5dc437d evidence — retained history

On macOS/Python 3.12.10 with existing repository dependencies, an extraction directory containing spaces and Chinese characters passed all 897 hashes, public baseline comparison, white HTML generation and real/no-key startup. The public L78 workflow preserved both canonical statuses and reasons, exact machine assessments and two history events through offline capture and fresh-process restore without the original paths. The baseline is 25 components, 21 report-bearing, four profile gaps; 146 emitted records = 98 PASS + 4 FAIL + 44 UNKNOWN, full candidate denominator unknown. This is recorded software behavior, not an independently labelled gold set.

Native-Windows requirement on this host failed as expected. Adding a byte to the extracted public BOM failed before software probes; restoring it passed. Windows acceptance remained false in every report. The user confirmed only macOS is currently available. No fresh dependency installation, actual Windows run, actual Cadence export, live model or peer trial was performed. T08 and M0–M3 remain open.

The builder refuses an existing output path and any ref outside the supported baseline; an existing ZIP is never overwritten. Negative controls confirmed these failures, native-Windows rejection and tamper-before-probe rejection, with original bytes restored afterward. The previous frozen artifact is `Hardwise-5dc437d-Windows-check-final.zip`, 14,112,931 bytes, SHA-256 `91fb5971da2a19d631650e90596633b33b03fd1b067391f9d61362cd179c42fe`. Earlier non-final artifacts are intermediate. This capsule fixes runtime source to the named commit; supplemental verifier files come from the builder checkout and are separately listed and hashed. Their integrity is not an authenticated signature.


## Previous 2cfd152 delivery — 2026-10-25

The builder now deliberately accepts only the recorded 2cfd152 source baseline. The full summary and emitted coverage remain identical to the previous baseline; numeric rule producer versions changed, including the false-zero and nonfinite fixes. Canonical human states, source-audit OS-error fallback and local font assets are included. This is a packaging rebaseline, not new product behavior. Historical ZIPs are retained.

`Hardwise-2cfd152-Windows-check.zip`: 910 files / 909 hashes, 14,157,526 bytes; SHA-256 `37df5ede7e3d9a42a554f8305b185ce1b90c7415e57edcdbb4922569e36bfe28`. The Git source is fixed at 2cfd152; explicitly named supplement files come from the builder checkout and are hashed separately. A copied source tree may contain older documentation and builder defaults; the top-level START-HERE.md and BUNDLE-MANIFEST.json specify the actual archive version. This is not a current project backup.

Extraction under a directory with spaces and Chinese characters passed all 909 hashes, the exact public baseline, current white HTML generation, real/no-key CLI dry-run, canonical decision/history workflow, managed save and fresh-process restore after original input paths became unavailable. The extracted numeric tests passed 34/34, including real CSV/TSV/XLSX intake and numeric rule migration. Existing repository dependencies were used; a fresh dependency install was not tested.

Native-Windows requirement, source tampering, overwrite of an existing ZIP and unregistered source ref all failed as expected; restored original bytes passed hashes and the frozen ZIP remained unchanged. Current full repository Python: 1548 passed / 7 deselected, 39.73s; Ruff/diff pass. No new runtime/frontend code changed in this packaging step, so the previous 105 unit / 23 E2E passes remain the 2cfd152 code evidence; they were not rerun or relabelled.

Evidence: task output Hardwise-统一交付56 (bundle-metadata.json, bundle-probe.txt, negative-controls.json, extracted-numeric-tests.txt). Both current main white HTML aliases were regenerated with the same inputs; exact stable-key assessments match after removing only rule_version. The live L78 demo retained all 4 previous events, old runs, managed catalog and input hashes; numeric version migration added one needs-review event, then actual UI rerun stayed at 5. The captured offline report exposes these 5 events and matching run provenance / project Markdown downloads with the browser forced offline (one HTML request; no API or external request). The live server remains running for the user; this browser check does not claim that server was stopped or file:// double-click was tested.

Windows software probe remains false; actual Cadence export, human profile approval and product release acceptance remain unverified/false. Current browser entry is documented in the task's current-entry note; old numbered reports and frozen ZIPs never update automatically.


## Previous 132bd57 delivery — 2026-10-25

Includes the additional inductance numeric fix under the same accepted local-UNKNOWN policy; generic inductor parse v2 and Buck inductor v3, with broad dependency fallback retained. Exact normal public-fixture report records remain equal excluding only rule_version. The current builder pin is 132bd572f2896b0b62584b2453b582365411e896; previous ZIPs are frozen history.

`Hardwise-132bd57-Windows-check.zip`: 912 files / 911 hashes, 14,166,026 bytes; SHA-256 `3fe88c07ec2c35375fc86eafd5fe1455cd6eec376539452bda26cf28d70345b6`. Chinese/space extraction passed hashes, recorded baseline, white report, real no-key CLI dry-run and canonical review / managed save / independent backup restore without original paths. All 53 resistor/capacitor/inductance numeric tests passed in the extraction. Existing dependencies were reused, no fresh install or native Windows was tested. Native-Windows, tamper, overwrite and unregistered-ref controls rejected, restored hashes passed, archive unchanged.

Current full Python 1567 passed / 7 deselected, 46.62s (delivery run). Final E2E 23 passed, 44.1s; the first run's one identity-import parse-page timeout is retained without an asserted root cause. Both mutable white aliases and owned live18772 now use this source. The live L78 scene contains no inductors, so all original 5 history rows, old runs/catalog and ten managed-input hashes remain unchanged after reload. Evidence: task output Hardwise-电感数值57; no product release, physical engineering approval or Windows/Cadence claim.


## Previous 8938cf7 delivery — 2026-10-25

Includes the user-selected quarantine of every competing reference candidate, same-name columns and Cadence continuation handling. Existing explicit-identity producer v4 invalidates prior decisions according to the established journal contract; ordinary valid public reports remain exactly equal. Current builder pin is 8938cf7108672f68147d9fe92ccdc59e05098a41; previous ZIPs remain frozen history.

`Hardwise-8938cf7-Windows-check.zip`: 916 files / 915 hashes, 14,176,603 bytes; SHA-256 `7bf6cfe42b66f7f66f109b2a5ee09b0de57fe60d15257637c5131b50908647d9`. Extraction under a Chinese/space path passed hashes, exact public baseline, white rendering, no-key CLI dry-run and managed save / independent restore without original paths. All 78 extracted numeric/reference tests passed in 10.10s. Native Windows, tamper, overwrite and unregistered ref were rejected as expected; restored bytes passed hashes and the ZIP remained unchanged. Existing dependencies were reused; no fresh install or actual Windows/Cadence acceptance was performed.

Current repository Python: 1592 passed / 7 deselected, 46.53s (delivery run); frontend contracts/type check, Ruff/diff and 24 E2E pass (46.4s), including actual white import/quarantine/correction with inspected desktop/narrow screenshots. Both main static white aliases and owned live18772 use this source; all original 5 event rows, 26 old runs, catalog and ten managed-input hashes survived reload without additional events. Evidence: task output Hardwise-位号隔离58. No release approval or independent engineering label is implied.


## Previous aeb45f9 delivery — 2026-10-26

The source now includes full SQL profile contracts and the user-selected DRAFT migration across validators, candidates, evidence, reports, Agent and the white workbench. The public software baseline deliberately changes to 25 components / 22 reports / 3 unmatched gaps, component 0 PASS / 0 WARN / 0 ERROR / 22 UNKNOWN, and 167 emitted records = 52 PASS / 0 FAIL / 115 UNKNOWN. Effective READY is zero. These counts reflect unapproved premises, not repaired electrical defects; the full candidate denominator remains unknown. Prior baseline counts must not be accepted for this version.

`Hardwise-aeb45f9-Windows-check.zip`: 935 files / 934 hashes, 14,235,722 bytes; SHA-256 `1a508f4e8f35731ab4462ce22280278e593b184ed6ebbe5bbe58497fab8b63dc`. The Git source is fixed at aeb45f9; the four named supplements come from the builder checkout and are separately hashed. Nested source documentation/build defaults may describe earlier deliveries: the top-level START-HERE.md, PUBLIC-BASELINE.json and BUNDLE-MANIFEST.json define this capsule. The previous 3cda993 ZIP is preserved unchanged.

Chinese/space-path extraction passed all hashes, exact public baseline, white offline rendering, real no-key CLI dry-run, canonical review states, managed save and fresh-process backup restore after original paths became unavailable. Extracted profile/storage/lifecycle/migration/dependency/locator tests: 138 passed, 21.34s. Native-Windows enforcement, source tampering, deliberately mismatched baseline with otherwise valid hashes, archive overwrite and an unregistered source ref were rejected with the expected diagnostic; restored original bytes passed hashes and the frozen ZIP hash remained unchanged. Existing dependencies were reused; no fresh Windows install or actual Cadence acceptance was performed.

Current delivery-check Python: 1668 passed / 7 deselected / 7 deliberate malformed-fixture serialization warnings, 264.77s; Ruff/diff pass. Runtime/frontend source is unchanged from aeb45f9's 105 unit / 24 E2E passes; those frontend results were not rerun or relabelled as this packaging check. Original live 18772 and both mutable white aliases now use aeb45f9. The original journal's 5 events, 28 old runs, catalog, existing generic decision, four logical input hashes and ten managed input hashes survived upgrade; startup and an actual white-UI rerun added two runs (30 total), with no manufactured profile-review decision. Controlled profile-dependent decision invalidation is separately proven by stage63's old/new/restart 1→2→2 history exercise.

Windows software probe remains false; actual Cadence export and human profile approval remain unverified; product release acceptance remains false. Evidence: task output Hardwise-交付对齐64.

Actual white-UI rerun retained five history events. Its newly captured offline report was loaded once over localhost, then checked with the browser offline and all other requests blocked: five original reasons remained visible; current and historical provenance JSON downloads matched their respective embedded run IDs. Only the HTML request occurred, no API or external request. The user live server remains running; this does not claim a stopped-server file double-click or native Windows check.


## Previous e2e88f5 delivery — 2026-10-26

The precision comparison fix is now in the frozen capsule, both mutable white report aliases and the owned original live workbench on port18772. The recorded public summary/coverage stays exactly 167 records = 52 PASS + 0 FAIL + 115 UNKNOWN; producer versions change to v4 for capacitor voltage margin and resistor power. This is a software baseline, not independent engineering labels.

`Hardwise-e2e88f5-Windows-check.zip`: 937 files / 936 hashes, 14,247,628 bytes; SHA-256 `d6248de1c52b204338436210a86a6f53298f4d3d08a612ca38073960942e9dc6`. Source is exactly e2e88f5. Four supplements are separately hashed. Nested builder/docs can describe previous pins; top-level START-HERE.md, PUBLIC-BASELINE.json and BUNDLE-MANIFEST.json define this archive. Old aeb45f9 and3cda993 ZIP bytes remain unchanged.

Chinese/space-path extraction passes hashes, exact baseline, white offline report, real/no-key CLI dry-run, canonical review state/history, managed save and fresh-process independent restore without original paths. Extracted precision/intake/dependency tests:171 passed,15.29s. Existing dependencies reused. Native-Windows requirement, source tamper, semantic baseline tamper with updated manifest hash, overwrite and unregistered old ref reject with expected diagnostics; restored source passes hashes.

Delivery-check Python:1694 passed /7 deselected /7 deliberate malformed-profile serialization warnings,196.35s. Stage65's same runtime source passed24 E2E in1.4m; frontend tests were not rerun as stage66. No runtime/frontend change in this packaging step.

Original journal was backed up with SQLite backup and trialled on a copy before owned-process replacement. All5 old events,30 old runs, catalog, original reason/decision history and10 managed plus4 logical input hashes survive. Producer change adds one review event even though the old decision already needs_review: history5→6→6, runs30→31→32 after startup and actual white-UI rerun. Trial/live fingerprint agrees; repeat does not add another event.

Captured offline white report retains all6 reasons. Browser forced offline after its sole HTML request:0 API/external requests. Current receipt matches captured current run and v4; downloaded old receipt matches its original run and v3. User live server remains running; this is not stopped-server/file-double-click/native-Windows evidence. Windows software acceptance=false, actual Cadence and human profile approval unverified, release=false. Evidence: task output Hardwise-精度交付66. Full product acceptance remains NOT_COMPLETE.


## Current 26f74fc delivery — 2026-10-26

The exact signed terminal/pin comparison fix now reaches the original live18772, both mutable white aliases and a new source capsule. Public summary and coverage remain167=52PASS/0FAIL/115UNKNOWN;22 profile-related producers deliberately move2→3, while original passive stress producer4 remains. Profile approval is still required; source30JSON bytes are unchanged and actual human approvals remain0.

`Hardwise-26f74fc-Windows-check.zip`:940 files /939 hashes,14,260,560 bytes; SHA-256 `9e85b806133182f36aa6e93d7445f4b6f07ec0c3c3dc2dacb6afac9e18069f14`. Source exactly26f74fc, four supplements separately hashed. Top-level START-HERE.md/PUBLIC-BASELINE.json/BUNDLE-MANIFEST.json define the package; nested source docs/builder defaults can describe an earlier pin. Old e2e88f5/aeb45f9/3cda993 ZIP hashes remain unchanged; this is not a project backup or authenticated signature.

Chinese/space extraction passes all hashes, full public baseline, white report, real/no-key CLI dry-run, canonical state/history, managed save and fresh-process independent restore without original paths.340 extracted signed-difference/pin/family/control/dependency/import/offline tests pass18.72s. Negative controls reject nativeWindows-on-macOS, source tamper, semantic baseline mismatch despite updated manifest hash, ZIP overwrite and unregistered e2e88f5; restore passes hashes. Existing dependencies reused, no fresh target install.

Packaging-check Python:1712 passed /7 deselected /7 deliberate malformed-profile serialization warnings,91.33s; Ruff/diff pass. The same26f74fc runtime already passed24 E2E1.4m in stage68; not rerun as stage69. Runtime/frontend code and static assets are unchanged in this packaging step.

SQLite backup/all-row snapshot precedes copied-journal trial and owned-process replacement. Original6events/32runs/catalog/reason/decision and10managed+4logicalinputhashes survive. The existing decision depends on unchanged generic capacitor v4, so no artificial review event is added:6→6→6 events,32→33→34 runs after startup and actual UI rerun. Separate stage68 old/new/restart profile-dependent producer migration proves1→2→2 where dependencies do change.

Offline white original-reason report retains6 reasons; forced-offline browser makes1HTML and0API/external requests. Downloaded current pin producer3.profile-review1 and original historical pin2 each match their own recorded run IDs; old passive receipt3 is also preserved while current passive remains4. Old receipts are not backfilled. Live server remains running; no stopped-server/file-double-click/nativeWindows claim. Windows software=false, actual Cadence and human engineering approval unverified, release=false, full productNOT_COMPLETE. Evidence:Hardwise-端间交付69.


### 2026-10-26 — 第75统一交付

源码dab2e91已进入白色主入口与新冻结包（959文件/958哈希）。副本连续升级两次，原日志安全启动及浏览器重跑：6旧事件/34旧运行和原决定、理由均保留，最终6事件/36运行。旧v1未自动改成新人工批准。公开整份rows/summary/coverage不变；1790Python通过67.71s、解压108专项通过5.83s。离线断网仅1HTML/0API或外部请求，原6条理由及历史运行清单保留。真实Windows/Cadence/工程主审仍未完成，F01保持partial，产品NOT_COMPLETE。详见任务输出Hardwise-统一交付75。


## Current 0e77607 delivery — 2026-10-26

Includes scoped per-turn model claim verification in Runner/API, fake snapshots and typed white/legacy panels. Public deterministic baseline unchanged at167=52PASS/0FAIL/115UNKNOWN; no real profile approval. New archive969files/968hashes,14,365,479bytes, SHA256077e1e7e0268785dbc1b22754027b084398423a302d48545e3f2723db6c475c0. Chinese/space extraction passed full validator and156claim/chat/disclosure tests; native-Windows, source tamper, semantic baseline mismatch, archive overwrite and unregistered source controls rejected, restored hash verification passed. Existing dependencies reused, not a fresh install or Windows/Cadence acceptance.

Original main journal copied before update; trial twice and real browser rerun retain6events/36oldruns/reasons, final38runs. Input hashes and17oldZIPs unchanged. CSV differs only in the expected source observation timestamp. Main API now demonstrates bounded negative-query output. Stage82 evidence is in the continuation task outputs/Hardwise-交付82 and work/hardwise-82. Complete product NOT_COMPLETE; no push.
