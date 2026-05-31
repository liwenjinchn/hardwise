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
- Base: A report rendered without `profile` still shows pin/check evidence from
  `ValidationReport` and an explicit profile-detail unavailable note.
- Bad: A no-profile LED row gets an LLM-like polarity judgement in the static
  project workbench.
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
