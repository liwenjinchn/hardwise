# Reporting Guidelines

> Contracts for deterministic report renderers and static validator UI output.

---

## Scenario: Deterministic Component Validation Reports

### 1. Scope / Trigger

Applies when changing:

- `src/hardwise/report/component_validation_markdown.py`
- `src/hardwise/report/validator_multi_ui.py`
- `src/hardwise/report/validator_multi_ui_sections.py`
- `src/hardwise/report/validator_project_ui.py`
- `src/hardwise/report/validator_ui.py`
- report-only helpers under `src/hardwise/report/`

Trigger: any change that renders `ValidationReport`, carries `DatasheetProfile`
into a report, derives schematic connection paths, or changes markdown download
content.

### 2. Signatures

Multi-component UI detail payload:

```python
@dataclass(frozen=True)
class ValidatorUiResult:
    validation: ValidationReport
    profile_path: Path
    profile: DatasheetProfile | None = None
```

Markdown renderer:

```python
def render(
    report: ValidationReport,
    *,
    profile_path: Path | None = None,
    profile: DatasheetProfile | None = None,
    component: Component | None = None,
    design: Design | None = None,
) -> str: ...
```

Connection-path helper:

```python
def schematic_connection_path(
    component: Component,
    design: Design,
    pin_number: str,
    net_name: str | None,
    *,
    neighbor_limit: int = 4,
) -> str: ...
```

Evidence/trust display helpers:

```python
TrustTier = Literal["l1", "l2", "l3"]

def trust_label_html(tier: TrustTier) -> str: ...
def trust_label_text(tier: TrustTier) -> str: ...
def evidence_chips_html(tokens: list[str]) -> str: ...
```

### 3. Contracts

- `ValidationReport` is still the verdict source of truth. Report renderers may
  read it, but must not mutate it or change validator status rollups.
- `DatasheetProfile` is optional presentation context. It may surface existing
  `abs_max`, `recommended`, pin `limits`, `recommended_topology`, and
  `profile.evidence` tokens.
- Report renderers must not invent datasheet facts. If profile evidence lacks a
  thermal/package token, render the gap explicitly.
- Schematic connection paths are display hints from `Design.nets`; they do not
  imply current direction, PCB placement, routing, or board geometry.
- No-profile/project gap rows remain coverage artifacts. Rendering must not turn
  them into electrical judgements.
- Project workbench group rows may point to an already validated refdes detail
  panel for navigation, but only when that refdes already has a
  `ValidationReport`. A group id itself is not a component id and must not
  create a new electrical detail panel.
- Markdown downloads and HTML detail panels should stay in parity for major
  report sections, especially evidence and pin-consistency sections.
- Trust labels are presentation provenance, not validator states:
  `L1 deterministic` maps to existing `ValidationReport` rows/checks,
  `L3 manual` maps to no-profile/manual coverage rows, and `L2 grounded` is
  reserved until a grounded-LLM claim schema exists.
- HTML evidence chips must keep the raw source token as visible text so browser
  search/copy and tests can still see tokens such as `datasheet:xl1509.pdf#p9`.
  CSS classes alone are not evidence.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Profile detail provided | Render profile facts and source tokens already present in profile JSON |
| Profile detail missing | Render a profile-detail unavailable note; do not fabricate facts |
| Thermal/package evidence missing | State that no source token is present; do not infer thermal/package specs |
| Net missing from `Design.nets` | Render `NET -> REFDES-pin` as a bounded schematic display path |
| Net has many neighbors | Cap neighbor display and show `+N more` |
| Pin consistency mismatch | Render report-only WARN; do not change `ValidationReport.status` |
| No-profile project row | Keep coverage/no-profile messaging; do not emit electrical PASS/WARN/ERROR |
| Group row has a validated refdes sample | It may navigate to that existing refdes panel |
| Group row has no validated refdes | Keep group coverage behavior; do not synthesize a refdes detail |
| Deterministic validation row/check | Render `L1 deterministic` without changing PASS/WARN/ERROR |
| Manual/no-profile coverage row | Render `L3 manual` and keep coverage wording |
| Evidence token present | Render a copyable/searchable chip whose text is the token |
| Evidence token missing | Render a muted `-`; do not create placeholder page facts |

### 5. Good / Base / Bad Cases

- Good: `U12` XL1509 detail shows `Topology Path`, pin consistency, profile
  evidence ledger, and `datasheet:xl1509.pdf#p9` without changing its ERROR
  verdict.
- Good: The same row shows `L1 deterministic` plus
  `<span class="evidence-chip">datasheet:xl1509.pdf#p9</span>`.
- Good: A project group row containing validated `U12` selects the existing
  `U12` panel; an unvalidated group remains an `L3 manual` coverage row.
- Base: A report rendered without `profile` still shows pin/check evidence from
  `ValidationReport` and an explicit profile-detail unavailable note.
- Bad: A no-profile LED row gets an LLM-like polarity judgement in the static
  project workbench.
- Bad: A group row uses the BOM group id as if it were a refdes and creates an
  electrical detail panel for an unvalidated group.
- Bad: A renderer shows only an icon or CSS class for evidence and hides the raw
  token text from browser search/copy.
- Bad: A topology path is worded as current flow or PCB placement evidence.

### 6. Tests Required

- Renderer tests assert new sections in HTML and markdown.
- Renderer tests assert `L1 deterministic`, `L3 manual`, evidence chip classes,
  and the raw evidence token text.
- CLI component-validation tests assert evidence tokens remain visible in
  downloaded markdown.
- Project workbench tests assert PASS/WARN/ERROR counts are unchanged.
- Gap/no-profile tests assert wording still says no-profile rows are not
  converted into electrical judgements.
- Full gate remains `uv run pytest -q` and `uv run ruff check .`.

### 7. Wrong vs Correct

#### Wrong

```python
# Rendering layer changes the truth model.
validation.component_checks.append(
    ComponentValidation(check="thermal", status="WARN", summary="looks hot")
)
```

#### Correct

```python
# Rendering layer surfaces only existing profile evidence.
evidence_details(validation, profile)
```

#### Wrong

```html
<span class="evidence-chip" data-source="datasheet"></span>
```

#### Correct

```html
<span class="evidence-chip" data-source="datasheet">datasheet:xl1509.pdf#p9</span>
```

#### Wrong

```text
+24V -> C33 -> U12-1, so current flows through C33 first.
```

#### Correct

```text
+24V -> C33.1 / C34.1 -> U12-1
```

Label the row as schematic topology / display path, not current flow.

---

## Scenario: Coverage Analytics Reports

### 1. Scope / Trigger

Applies when changing:

- `src/hardwise/documents/candidates.py`
- `src/hardwise/validation/coverage_priority.py`
- CLI commands that render coverage/profile-loop artifacts

Trigger: ranking document-index candidates, recommending next profile/validator
families, or adding grouped-coverage Markdown/CSV fields.

### 2. Signatures

Candidate CSV command:

```bash
hardwise build-document-index-candidates <validation-index.json> \
  [--family <suggested-family>]... \
  --output <document-candidates.csv>
```

Next-family command:

```bash
hardwise recommend-next-family <validation-index.json> \
  --output <next-family.md>
```

Analytics entry points:

```python
def score_candidate(suggested_family: str, refdes_count: int) -> tuple[float, str]: ...
def build_family_coverage_report(index_path: Path) -> FamilyCoverageReport: ...
def render_family_coverage_markdown(report: FamilyCoverageReport) -> str: ...
```

### 3. Contracts

- Input is a `ProjectValidationIndex` generated by `design-validator-ui
  --index-json`.
- Candidate CSV appends `Priority` as the last column; existing prefix columns
  stay stable.
- Candidate CSV preserves document-index identity semantics. Rows whose
  `identity_kind` is `mpn` populate `MPN`; rows whose `identity_kind` is
  `part_like_value` populate `Value` and keep `MPN` empty until a reviewer adds
  a public part number. Never promote BOM item numbers, Chinese `编号`, source
  lines, or refdes into `MPN`.
- `--family` filters the review queue by
  `ProjectComponentGroup.suggested_family`. Family names are queue scope only;
  document matching remains identity-based by parsed MPN or reviewer-confirmed
  exact `Value` alias.
- A candidate CSV may become a reviewed document index after a reviewer fills
  `Title`, `URL` or `Path`, and `Description`. Blank `URL`/`Path` rows remain
  ignored by `parse_document_index()` and must not create coverage.
- Matched document rows rendered in project Markdown and workbench group UI must
  show title, URL, and the raw `doc:<file>#line<N>` source token.
- Candidate rows sort true profile gaps before matched-profile document
  backfill rows.
- Family recommendations count uncovered refdes per row, not whole groups, so a
  `mixed` group contributes only its unmatched refdes.
- Recommendations are L3 coverage artifacts. They may suggest
  `try_existing_validator_profile` or `triage_for_new_validator`, but must not
  claim an electrical verdict or promote a draft.
- `coverage_priority.py` is not re-exported through `validation/__init__.py`;
  CLI commands lazy-import the submodule to avoid validation/documents
  cross-import cycles.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Index JSON cannot load | Raise `CoveragePriorityError`; CLI exits 1 |
| Index has no `component_groups` | Raise `CoveragePriorityError`; CLI exits 1 |
| `--family transistor` is set | Include only `suggested_family == "transistor"` candidate rows and count other groups as family-filter skips |
| Candidate identity kind is `mpn` | Write the identity to `MPN`; do not duplicate it into `Value` |
| Candidate identity kind is `part_like_value` | Write the exact BOM value to `Value`; leave `MPN` blank unless reviewed later |
| Reviewed row has `MPN` and exact `Value` alias | Allow reuse by another BOM/project when either parsed MPN or reviewed value alias matches |
| Reviewed row is matched | Render title, URL, and raw `doc:<file>#line<N>` token in project Markdown/HTML |
| `profile_status == "matched"` candidate lacks docs | Keep row, but sort after true profile gaps |
| Group status is `mixed` | Count only rows whose `match_status != "matched"` |
| Passive/mechanical family | Exclude from next-family recommendations |
| No mapped validator family | Use `triage_for_new_validator` |
| Mapped validator family exists | Use `try_existing_validator_profile` |

### 5. Good / Base / Bad Cases

- Good: A 65-component public fixture ranks diode/transistor/IC coverage gaps
  while the project validation counts remain unchanged.
- Good: A family-scoped transistor review queue emits only transistor rows, and
  Chinese part-like values appear in `Value`, not `MPN`.
- Good: A reviewed `L2N7002KLT1G` row can be reused across projects by parsed
  MPN or by an exact reviewer-confirmed BOM `Value` alias.
- Base: A matched profile with missing document-index entry remains visible as a
  CSV backfill row.
- Bad: A recommendation Markdown table emits `PASS`, `WARN`, or `ERROR`.
- Bad: An advisory family-to-validator map is imported by deterministic
  dispatch.
- Bad: A document row matches a component only because both are `transistor`.
- Bad: Chinese BOM `编号` is copied into `MPN` and treated as a public part
  number.

### 6. Tests Required

- Unit tests for score ordering and priority band thresholds.
- Unit tests for mixed-group per-refdes counting.
- CSV tests asserting `Priority` is appended and gap rows sort before backfill
  rows.
- CSV tests asserting `MPN` vs `Value` semantics and family filtering.
- Matcher tests asserting a reviewed document row can be reused across BOMs by
  parsed MPN or exact reviewed value alias, without refdes or source item
  number.
- Project Markdown/HTML tests asserting raw `doc:<file>#line<N>` source tokens
  remain visible beside matched document title/URL.
- CLI test that runs `design-validator-ui --index-json`, then
  `recommend-next-family`, and asserts advisory action tokens plus absence of
  verdict tokens.

### 7. Wrong vs Correct

#### Wrong

```python
# Over-counts a mixed group by treating all refdes as uncovered.
if group.profile_status != "matched":
    uncovered += group.refdes_count
```

#### Correct

```python
# Count uncovered rows, then roll up by the group's suggested family.
if row.match_status != "matched":
    family_counts[refdes_family[row.refdes]] += 1
```

#### Wrong

```python
# Turns a source item number into a fake public part number.
row["MPN"] = bom_item.item_number
```

#### Correct

```python
if group.identity_kind == "mpn":
    row["MPN"] = group.identity
elif group.identity_kind == "part_like_value":
    row["Value"] = group.value
```

### Common Mistake: Synthetic Fixture Refdes Prefixes

The coverage family classifier is prefix based. In synthetic fixtures, use
standard component prefixes when the family matters: `C20` instead of `CS1`,
`R30` instead of `RBOOT`, `D10` for LEDs/TVS/Schottky, `Q10` for transistors,
and `FB1` for ferrites. Non-standard passive refdes can be classified as
`unknown` and pollute next-family recommendations.

---

## Scenario: Portable Text Artifact Paths

### 1. Scope / Trigger

Applies when changing:

- CLI status output that prints project input paths
- YAML manifests such as `suggest-validation-targets`
- JSON/Markdown sidecars such as `design-validator-ui --index-json`
- Tests that read generated Markdown/HTML/YAML/JSON artifacts

Trigger: any path value intended for humans or machine-readable review artifacts,
not paths used for actual filesystem I/O.

### 2. Signatures

Path display helper:

```python
def display_path(path: Path | str | None) -> str | None: ...
```

Generated artifact readers in tests:

```python
text = output.read_text(encoding="utf-8")
```

### 3. Contracts

- Text artifacts use POSIX separators (`data/datasheet_profiles/l78.json`) even
  when generated on Windows. This keeps manifests, JSON sidecars, and CLI echoes
  stable across CI hosts and easy to compare in tests.
- `display_path()` is presentation-only. It must not be used to open files,
  resolve paths, or mutate user-provided filesystem inputs before execution.
- Generated Hardwise reports and indexes are UTF-8. Tests must read generated
  text with `encoding="utf-8"` instead of relying on the host default encoding.
- Runtime file access should continue to use `Path` objects and platform-native
  semantics.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| `Path("data") / "profiles" / "x.json"` in a text artifact | Render `data/profiles/x.json` |
| Windows-style string `data\\profiles\\x.json` in display output | Render `data/profiles/x.json` |
| `None` optional path | Preserve `None`; do not render `"None"` |
| Test reads generated UTF-8 HTML/Markdown/YAML/JSON | Use `read_text(encoding="utf-8")` |
| Runtime opens a user path | Use the original `Path`; do not round-trip through `display_path()` |

### 5. Good / Base / Bad Cases

- Good: `design-validator-ui --index-json` emits
  `"profile_path": "data/datasheet_profiles/xl1509.json"` on macOS and Windows.
- Good: `suggest-validation-targets` writes
  `profile: data/datasheet_profiles/l78.json` on every host.
- Base: CLI echoes absolute Windows paths with forward slashes for readability;
  the command still used the original `Path` for execution.
- Bad: A test calls `report.read_text()` on generated Chinese HTML and passes on
  macOS but fails on Windows cp1252.
- Bad: Runtime code converts a filesystem path to POSIX text and then tries to
  open that converted string on Windows.

### 6. Tests Required

- Unit tests for `display_path()` covering `Path`, Windows-style strings, and
  `None`.
- CLI/report tests assert stable `/` separators in YAML manifests, index JSON,
  and status output.
- E2E tests that read generated Unicode artifacts use explicit UTF-8 decoding.
- Full gate remains `uv run pytest -q` and `uv run ruff check .`; Windows
  support requires a passing `windows-latest` CI job.

### 7. Wrong vs Correct

#### Wrong

```python
payload["profile_path"] = str(profile_path)
text = report.read_text()
```

#### Correct

```python
payload["profile_path"] = display_path(profile_path)
text = report.read_text(encoding="utf-8")
```
