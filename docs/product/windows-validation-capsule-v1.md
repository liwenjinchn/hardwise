# Windows validation capsule v1

This is a pinned public source package for T08 target-machine validation. It is not a release approval, portable project backup, dependency installer, or proof of actual Cadence compatibility.

## Build and run

```bash
uv run python scripts/build_validation_bundle.py --output /absolute/path/Hardwise-Windows-check.zip
```

The supported source commit is `4a9fabfb58e4e5bdf719f8b2cf81b879bf0aec9d`. Other refs are rejected until the recorded public software baseline is updated deliberately. The package uses that Git tree, plus explicitly named verifier, baseline and instructions. Its manifest hashes 849 source/supplement files; the manifest itself is the 850th file. Hashes detect accidental changes against this manifest; they are not a signature or an independent engineering correctness check. Local ignored environment, uploads, databases and generated reports are excluded by Git archive.

Extract to a normal directory. In native Windows PowerShell, from the extracted root:

```powershell
uv --version
uv sync --locked --extra dev
uv run python VALIDATE.py --require-windows
```

The first dependency installation requires network. No execution-policy change or model key is required. The verifier disables dotenv and clears model credentials only in its process and child. It verifies hashes, imports backend code from the extracted source, compares the entire recorded public-fixture summary and emitted-check coverage, generates the existing white React offline report, and runs real-mode no-key CLI dry-run. Results are saved under reports with unique names. `--hash-only` skips software probes. `--require-windows` fails on non-Windows.

Read START-HERE.md for the live workbench command and blank manual record. Follow import, explain UNKNOWN, handle one item, save, restart the same fixed-source project, export, stop server and read the offline report. Record the actual Windows/EDA version, installation result and public/synthetic Cadence export route. These observations must come from the target machine; the script never fills actual Cadence acceptance, human profile approval or product release approval.

## Local evidence and limits — 2026-10-24

On macOS/Python 3.12.10 with existing repository dependencies, an extraction directory containing spaces and Chinese characters passed all 849 hashes, public baseline comparison, white HTML generation and real/no-key startup. The baseline is 25 components, 21 report-bearing, four profile gaps; 146 emitted records = 98 PASS + 4 FAIL + 44 UNKNOWN, full candidate denominator unknown. This is recorded software behavior, not an independently labelled gold set.

Native-Windows requirement on this host failed as expected. Adding a byte to the extracted public BOM failed before software probes; restoring it passed. Windows acceptance remained false in every report. No fresh dependency installation, actual Windows run, actual Cadence export, live model or peer trial was performed. T08 and M0–M3 remain open.
