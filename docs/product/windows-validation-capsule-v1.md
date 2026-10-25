# Windows validation capsule v1

This is a pinned public source package for T08 target-machine validation. It is not a release approval, portable project backup, dependency installer, or proof of actual Cadence compatibility.

## Build and run

```bash
uv run python scripts/build_validation_bundle.py --output /absolute/path/Hardwise-Windows-check.zip
```

The supported source commit is `5dc437dbfcca7ab5e6224171e369e2f82577364d`. Other refs are rejected until the recorded public software baseline is updated deliberately. The package uses that Git tree, plus explicitly named verifier, public workflow helper, baseline and instructions. Its manifest hashes 897 source/supplement files; the manifest itself is the 898th file. Hashes detect accidental changes against this manifest; they are not a signature or an independent engineering correctness check. Local ignored environment, uploads, databases and generated reports are excluded by Git archive.

Extract to a normal directory. In native Windows PowerShell, from the extracted root:

```powershell
uv --version
uv sync --locked --extra dev
uv run python VALIDATE.py --require-windows
```

The first dependency installation requires network. No execution-policy change or model key is required. The verifier disables dotenv and clears model credentials only in its process and child. It verifies hashes, imports backend code from the extracted source, compares the entire recorded public-fixture summary and emitted-check coverage, generates the existing white React offline report, and runs real-mode no-key CLI dry-run. It also exercises canonical review states, rejects new legacy-state writes, captures offline history, saves managed inputs, downloads a project backup, makes original paths unavailable and verifies restored decisions/reasons in a fresh process. These are synthetic operations, never human engineering approvals. Results are saved under reports with unique names. `--hash-only` skips software probes. `--require-windows` fails on non-Windows.

Read START-HERE.md for the live workbench command and blank manual record. Follow import, explain UNKNOWN, handle one item, save, restart by saved managed-project ID, download a backup and restore an independent copy, export, stop server and read the offline report. Record the actual Windows/EDA version, installation result and public/synthetic Cadence export route. These observations must come from the target machine; the script never fills actual Cadence acceptance, human profile approval or product release approval.

## Local evidence and limits — 2026-10-25

On macOS/Python 3.12.10 with existing repository dependencies, an extraction directory containing spaces and Chinese characters passed all 897 hashes, public baseline comparison, white HTML generation and real/no-key startup. The public L78 workflow preserved both canonical statuses and reasons, exact machine assessments and two history events through offline capture and fresh-process restore without the original paths. The baseline is 25 components, 21 report-bearing, four profile gaps; 146 emitted records = 98 PASS + 4 FAIL + 44 UNKNOWN, full candidate denominator unknown. This is recorded software behavior, not an independently labelled gold set.

Native-Windows requirement on this host failed as expected. Adding a byte to the extracted public BOM failed before software probes; restoring it passed. Windows acceptance remained false in every report. The user confirmed only macOS is currently available. No fresh dependency installation, actual Windows run, actual Cadence export, live model or peer trial was performed. T08 and M0–M3 remain open.

The builder refuses an existing output path and any ref outside the supported baseline; an existing ZIP is never overwritten. Negative controls confirmed these failures, native-Windows rejection and tamper-before-probe rejection, with original bytes restored afterward. The final artifact is `Hardwise-5dc437d-Windows-check-final.zip`, 14,112,931 bytes, SHA-256 `91fb5971da2a19d631650e90596633b33b03fd1b067391f9d61362cd179c42fe`. Earlier non-final artifacts are intermediate. This capsule fixes runtime source to the named commit; supplemental verifier files come from the builder checkout and are separately listed and hashed. Their integrity is not an authenticated signature.
