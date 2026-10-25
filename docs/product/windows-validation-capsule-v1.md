# Windows validation capsule v1

This is a pinned public source package for T08 target-machine validation. It is not a release approval, portable project backup, dependency installer, or proof of actual Cadence compatibility.

## Build and run

```bash
uv run python scripts/build_validation_bundle.py --output /absolute/path/Hardwise-Windows-check.zip
```

The supported source commit is `2cfd152b80aa532bbcd2b235d305b595a6c48086`. Other refs are rejected until the recorded public software baseline is updated deliberately. The package uses that Git tree, plus explicitly named verifier, public workflow helper, baseline and instructions. Its manifest hashes 909 source/supplement files; the manifest itself is the 910th file. Hashes detect accidental changes against this manifest; they are not a signature or an independent engineering correctness check. Local ignored environment, uploads, databases and generated reports are excluded by Git archive.

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


## Current 2cfd152 delivery — 2026-10-25

The builder now deliberately accepts only the recorded 2cfd152 source baseline. The full summary and emitted coverage remain identical to the previous baseline; numeric rule producer versions changed, including the false-zero and nonfinite fixes. Canonical human states, source-audit OS-error fallback and local font assets are included. This is a packaging rebaseline, not new product behavior. Historical ZIPs are retained.

`Hardwise-2cfd152-Windows-check.zip`: 910 files / 909 hashes, 14,157,526 bytes; SHA-256 `37df5ede7e3d9a42a554f8305b185ce1b90c7415e57edcdbb4922569e36bfe28`. The Git source is fixed at 2cfd152; explicitly named supplement files come from the builder checkout and are hashed separately. A copied source tree may contain older documentation and builder defaults; the top-level START-HERE.md and BUNDLE-MANIFEST.json specify the actual archive version. This is not a current project backup.

Extraction under a directory with spaces and Chinese characters passed all 909 hashes, the exact public baseline, current white HTML generation, real/no-key CLI dry-run, canonical decision/history workflow, managed save and fresh-process restore after original input paths became unavailable. The extracted numeric tests passed 34/34, including real CSV/TSV/XLSX intake and numeric rule migration. Existing repository dependencies were used; a fresh dependency install was not tested.

Native-Windows requirement, source tampering, overwrite of an existing ZIP and unregistered source ref all failed as expected; restored original bytes passed hashes and the frozen ZIP remained unchanged. Current full repository Python: 1548 passed / 7 deselected, 39.73s; Ruff/diff pass. No new runtime/frontend code changed in this packaging step, so the previous 105 unit / 23 E2E passes remain the 2cfd152 code evidence; they were not rerun or relabelled.

Evidence: task output Hardwise-统一交付56 (bundle-metadata.json, bundle-probe.txt, negative-controls.json, extracted-numeric-tests.txt). Both current main white HTML aliases were regenerated with the same inputs; exact stable-key assessments match after removing only rule_version. The live L78 demo retained all 4 previous events, old runs, managed catalog and input hashes; numeric version migration added one needs-review event, then actual UI rerun stayed at 5. The captured offline report exposes these 5 events and matching run provenance / project Markdown downloads with the browser forced offline (one HTML request; no API or external request). The live server remains running for the user; this browser check does not claim that server was stopped or file:// double-click was tested.

Windows software probe remains false; actual Cadence export, human profile approval and product release acceptance remain unverified/false. Current browser entry is documented in the task's current-entry note; old numbered reports and frozen ZIPs never update automatically.
