# Hardwise Learning Log

> Every issue debugged is a unit of internalized knowledge. This file is not a complaint board — it's the journal of "what surprised me when reality didn't match my mental model."
>
> Format per entry: **Symptom** / **Root cause** / **Fix** / **Takeaway**. Add a HW analogy in root cause when it actually clarifies; don't force one.
>
> Interview hook: "what surprised you while building this?" → entries here are the honest answer.

---

## 2026-05-10 · Slice 1 · pic_programmer 跑出 0 finding 不是 bug，是 demo 设计的诚实结果

**Symptom**

R001（"新建器件候选识别 — footprint 字段为空"）在公开样例 `pic_programmer` 上跑出 0 finding。第一反应是"是不是 R001 写错了"。

**Root cause**

实测：`parse_schematic(pic_programmer)` 返回 124 个 record，其中 58 个 footprint 为空——但**这 58 个全部以 `#` 开头**（`#PWR05` / `#FLG01` 这类 KiCad 虚拟电源 flag / no-connect 标记）。R001 故意过滤虚拟器件后，**真实器件 0 个 footprint 为空**。

`pic_programmer` 是 KiCad 官方完整 demo，PCB layout 早就完成，所有真实器件 footprint 都已回填。这是"已完成项目"的预期状态——评审时本来就不该有"footprint 待 layout 团队回填"的器件。

**HW analogy**：拿一份已经投产 N 年的成熟 BOM 跑 ECN 检查器，输出"无 ECN 触发"是合理的；不能因为输出空就说工具坏。

**Fix**

不改 R001。改的是 demo 解释：

1. CLI 输出明确显示"0 candidate findings, 121 components reviewed"作为结果
2. R001 单测用手搓 fixture 覆盖正反例（真实 refdes 空 / 真实 refdes 填 / 虚拟 refdes 空），而**不依赖** demo 项目上 finding 命中
3. 面试 Q1 v0.5 答案直接写明这是诚实输出，并解释 R001 的真实价值在带新建器件的项目上才会显现
4. PLAN.md DR-006 / docs/review_node.md 都把这个事实写进去，避免下次自己也疑惑

**Takeaway**

**单元测试 ≠ demo 项目命中。两者要分开 acceptance。** 单元测试覆盖规则的"正反例正确性"，demo 项目证明"端到端能跑"——前者用 fixture，后者用真实数据。如果 demo 数据恰好不命中规则，那也是一种合法的"reviewed → no flag"输出。

更广义的教训：**vertical slice 的 acceptance 不能是"必须看见 finding"**，而应该是"管道跑通 + 输出结构对齐 + guards 生效 + 单测覆盖"。否则会因为数据偶然性反向调整规则逻辑，污染设计。

---

## 2026-05-10 · Slice 1 · BoardRegistry 必须区分 raw schematic vs merged

**Symptom**

写 R001 时发现：如果用 `parse_project(pic_programmer).components` 的 footprint 字段判定，会把 PCB-completed 项目里所有器件都判为"footprint 已填，无新建候选"——即使 sch 端原本是空的。R001 的判定信号被破坏。

**Root cause**

`adapters/kicad.py:30-31` 的 merge 逻辑：

```python
if not existing.footprint:
    merged[refdes] = existing.model_copy(update={"footprint": pcb_component.footprint})
```

这是 v0.1 时为了让 Refdes Guard 拿到完整封装信息而写的——对 Refdes Guard 是好事，但 R001 想看的是"sch 阶段原始字段是不是空"，merge 后字段已经被 PCB 端覆盖。

**HW analogy**：你想检查"原料状态"，但拿到的是"加工后状态"。两者不是一份数据。

**Fix**

`BoardRegistry` 加两个 raw 字段：

```python
schematic_records: list[ComponentRecord] = Field(default_factory=list)
pcb_records: list[ComponentRecord] = Field(default_factory=list)
```

`parse_project()` 同时填 raw + merged。`components` 字段语义不变（merged view，给 Refdes Guard 用）；`schematic_records` 是 sch-only raw view（给 R001 等"需要看 sch 阶段原始状态"的规则用）。沉淀为 PLAN.md **DR-008**。

**Takeaway**

**数据 merge 是有损的，原始视图必须并存。** 早期定数据模型时，只要后续可能有"我要看上游某一阶段的原始状态"的需求，就保留 raw 视图——不要假设 merge 后的视图能回溯。

广义教训：**Pydantic model 不是单一 truth 的容器，是多个 truth view 的集合。** 该字段一份，view 字段多份。Slice 1 这次是低成本扩字段；如果 Slice 3 才发现要这样改，下游所有规则代码都得改。

---

## 2026-05-09 · Day 2 · Coaching correction — shipped code without module I/O explanation

**Symptom**

After the KiCad parser shipped, the user pointed out: "我不是只是为了做出来，是为了边做边学，你要说一下你做的每个模块输入是什么，输出是什么等等." The code worked, but the learning loop was incomplete.

**Root cause**

I optimized for delivery proof (`inspect-kicad`, tests, lint) and under-served the coaching goal. For this project, a module is not done when it runs; it is done when the user can explain its purpose, input, output, design reason, and verification path.

**Fix**

Added a "Day 2 shipped module I/O" table to `docs/architecture.md` covering `ComponentRecord`, `BoardRegistry`, `parse_schematic`, `parse_pcb`, `parse_project`, and `inspect-kicad`. Also added a reusable "Module explanation template" so future modules follow the same format.

**Takeaway**

Hardwise has two deliverables: working code and transferable understanding. Every future module needs a short teaching pass before and after implementation: purpose, input, output, why, verification, interview sentence. If any part is missing, the module is not actually shipped for this user's goal.

---

## 2026-05-09 · Day 2 · KiCad parser verification — sandbox, dev deps, virtual refdes order

**Symptom**

Three small surprises appeared while validating the first KiCad registry parser:

```
error: failed to open file `/Users/liwenjin/.cache/uv/sdists-v9/.git`: Operation not permitted
error: Failed to spawn: `pytest`
error: Failed to spawn: `ruff`
```

After the parser did run, the first CLI screen was dominated by KiCad virtual symbols such as `#PWR01` and `#FLG06`, hiding real review targets like `C1`, `D11`, and `U3`.

**Root cause**

1. Codex sandbox allowed writes in the project but not reads under the user-level `uv` cache, so `uv run ...` needed an approved run.
2. The project had runtime dependencies installed, but dev dependencies were not installed yet; `pytest` and `ruff` were declared under `[project.optional-dependencies].dev` but missing from `.venv`.
3. KiCad stores power symbols and power flags as schematic symbols with refdes-like names. They are valid registry entries, but poor first-screen demo material.

**Fix**

1. Re-ran validation with approved `uv run`.
2. Ran `uv sync --extra dev` to install `pytest` and `ruff`.
3. Changed registry sort order so physical refdes print before virtual `#PWR` / `#FLG` entries.

**Takeaway**

Validation friction is still information. A demo command should print the objects a hardware engineer cares about first, even if the underlying registry keeps virtual symbols for correctness. Also, Day-1 setup should include `uv sync --extra dev` once tests exist, not only plain `uv sync`.

---

## 2026-05-08 · Day 1 · API verify — load_dotenv override + lowercase model id

**Symptom**

Two failures in sequence on the first `uv run hardwise verify-api`:

```
# 1. wrong base URL
calling MiMo-V2.5 via https://anyrouter.top
error: AuthenticationError: Error code: 401 - 无效的令牌

# 2. wrong model identifier (after fix #1)
calling MiMo-V2.5 via https://token-plan-sgp.xiaomimimo.com/anthropic
error: BadRequestError: Error code: 400 - Not supported model MiMo-V2.5
```

**Root cause**

Two unrelated bugs surfaced together:

1. **`python-dotenv`'s `load_dotenv()` does not override existing environment variables by default.** The user had `ANTHROPIC_BASE_URL=https://anyrouter.top` exported globally on the Mac (from another Anthropic-format proxy used by other projects). When Hardwise loaded its `.env`, the existing env var won; Hardwise's value was silently ignored.

2. **API model identifiers are not the same as marketing names.** The user wrote "MiMo-V2.5" (camel-case + dot), but the actual API id is `mimo-v2.5` (lowercase + hyphen). Discovered by curling `/v1/models` on the proxy, which exposes an OpenAI-style listing endpoint.

**HW analogy**: a connector pin labeled "VBAT" on a schematic is rarely "VBAT" in the BOM database — it's `vbat_main` or `V_BATT_3V3` or some normalized identifier. Marketing names ≠ engineering identifiers; always look up the registry.

**Fix**

1. `src/hardwise/cli.py` — changed `load_dotenv()` to `load_dotenv(override=True)`. Hardwise's `.env` now wins against any pre-existing shell env. Trade-off documented: if Hardwise is ever deployed to CI where env is the source of truth, this needs revisiting.

2. `.env`, `.env.example`, `CLAUDE.md` — model values changed from `MiMo-V2.5` to `mimo-v2.5`. CLAUDE.md Models section now also documents the model-list curl command so future identifier confusion is one command away from resolution.

**Takeaway**

Two generalizable rules:

1. **For local CLI tools, `load_dotenv(override=True)` is the correct default.** The principle of least surprise is "the .env in this project IS the source of truth here." Anyone deploying to CI can flip it back; users debugging locally will lose hours otherwise.

2. **Always probe the upstream's model-list endpoint before committing to a model name.** Most LLM-as-a-service proxies (OpenAI-compatible or Anthropic-compatible) expose `/v1/models` or `/models` regardless of which protocol they speak. One curl beats five guesses.

Both were caught in the first verify call — which is itself the third generalizable rule: **build a `verify-api` CLI command on Day 1**, not in a panic on Day 7. The cost was 5 minutes; the value was catching both bugs before any real code touched the API.

---

## 2026-05-08 · Day 1 · CLAUDE.md scaffolding — abstract vs concrete

**Symptom**

The Day-1 CLAUDE.md was structurally correct (right sections, right intent) but **abstract**: "Refdes Guard verifies output against the EDA registry" without specifying the regex, the layer split, or the file path. User compared it to Wrench Board's CLAUDE.md, where the equivalent rule specifies `\b[A-Z]{1,3}\d{1,4}\b`, the two-layer mechanics (tool returns `{found:false, closest_matches:[...]}` + post-hoc sanitizer), and the exact file (`api/agent/sanitize.py`).

The gap was concentrated in three places:
- Hard rules said *what* but not *how*
- Stack section had no version pins
- No Models section linking env var → model → tier → use case
- No "tools return structured null" or "file size guard" rules
- No editorial meta-rule, so dated context ("started 2026-05-08") leaked in

**Root cause**

Two compounding mistakes:
1. **Wrong genre.** I wrote CLAUDE.md as a *narrative* document (explaining what the project is and why it exists). Narrative belongs in README. CLAUDE.md is a *spec* — operational reference with file paths, regexes, schemas, and command-level rules.
2. **Missing meta-rule.** Without an explicit "no temporal framing" rule, dated context drifts in. Wrench Board's editorial rule at the bottom of their CLAUDE.md is the immune system that prevents this; mine had no immune system.

**HW analogy**: a netlist with refdes but no values is structurally correct but unbuildable. CLAUDE.md without concrete specs is the same shape — present, well-organized, non-functional.

**Fix**

Refactored CLAUDE.md to mirror Wrench Board's spec-density:
- Hard rule on anti-hallucination now specifies the regex, the two layers, the wrapping format `⟨?U999⟩`, and the implementation file
- Stack pins major versions (`anthropic >= 0.40.0` etc.)
- New Models section: env var → model → tier → use case table
- Conventions added: structured-null return, ~300-line file size guard, verify-before-done
- New Commit hygiene section with conventional-commits + ask-before-push
- New "Two stores, one join key" rule preventing future schema mixing
- Editorial rule at bottom — strips any sentence that won't read accurate in six months

Items needing code progress before they can be specific (layout tree, tool manifest, on-disk schema, CLI surface, anti-rules from real review runs) deferred to `docs/rolling_log.md` with explicit code-milestone triggers, not date-based deadlines.

**Takeaway**

CLAUDE.md is **specs, not narrative**. Two tests for whether a sentence belongs:

1. Could a fresh session execute against it without grepping the codebase?
2. Will it still read as accurate six months from now (no dates, no "currently"-framed claims)?

If either answer is no, the sentence belongs in README, memory, learning_log, or rolling_log instead.

Generalizes beyond Hardwise: any time I scaffold a CLAUDE.md from scratch, default to spec mode (regex, file paths, schemas, command-level rules), not narrative mode. And always include the editorial meta-rule on Day 1 — it's free and it self-enforces every future edit.

---

## 2026-05-08 · Day 1 · CLI scaffold — Typer single-command collapse

**Symptom**

```
$ uv run hardwise hello
Usage: hardwise [OPTIONS]
Try 'hardwise --help' for help.
Got unexpected extra argument (hello)
```

**Root cause**

Typer collapses a `Typer()` app with only one `@app.command()` into a *single-command app* — the lone command becomes the implicit default, so the positional argument `hello` is parsed as an extra arg to that default command, not as a subcommand selector.

**HW analogy**: a multi-pin connector with only one wire soldered. The system auto-degrades to "single signal" mode and stops expecting channel selection. To keep multi-channel semantics, you have to explicitly declare the connector pinout — even with only one channel populated.

**Fix**

`src/hardwise/cli.py` — added `@app.callback()` with an empty body. The callback forces Typer into multi-command mode regardless of how many commands are registered.

```python
@app.callback()
def _root() -> None:
    """Force Typer to treat this as a multi-command app even when only one command is registered."""
```

**Takeaway**

When a framework auto-detects intent based on shape (here: number of commands), the scaffold needs to match the *eventual* shape, not the *current* shape. Adding the callback at Day 1 was free; discovering it after the user runs `hello` cost two round-trips. **Build for the shape you're heading toward, not the one you have today.** This generalizes to schemas, type hints, and DB models too.

---
