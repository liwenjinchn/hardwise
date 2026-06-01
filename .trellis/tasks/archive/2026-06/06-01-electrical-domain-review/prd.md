# Review electrical domain algorithms

## Goal

Audit Hardwise's electrical-domain understanding and deterministic validation
algorithms against hardware-engineering expectations, using only public or
explicitly releasable reference material, so the project avoids professional
mistakes in reported electrical conclusions.

## Requirements

- Review code paths that encode electrical semantics or validation judgments,
  especially `src/hardwise/validation/`, `src/hardwise/ir/profile.py`,
  validation fixtures, and report wording that could overclaim capability.
- Compare implemented checks against the project's stated pre-layout schematic
  review boundary: parsed netlist topology, BOM identity, structured pin
  profiles, explicit evidence tokens, and deterministic family templates.
- Treat the three user-provided reference directories as publicly releasable
  material based on the user's clarification. Use them selectively as domain
  references for electrical correctness, while avoiding bulk transcription or
  embedding non-essential project/vendor context into code, tests, docs, or
  prompts.
- If a user preference conflicts with the repository's no-internal-hardware-data
  rule, the repository rule wins. The review may note that private material
  exists but must not read its body or derive project rules from it.
- Produce a findings-first review with file/line references, severity, risk,
  and recommended remediation. Separate true professional correctness risks
  from intentional MVP scope boundaries.
- Do not modify production code until planning is approved and a concrete
  remediation scope is selected.

## Acceptance Criteria

- [ ] The review identifies the exact code modules that perform electrical
      interpretation and validation.
- [ ] Findings are grounded in repository code/tests and, where applicable,
      public reference material only.
- [ ] Each finding states whether it is a correctness bug, overclaiming risk,
      missing electrical model, test gap, or acceptable MVP limitation.
- [ ] The review calls out any place where the code could imply unsupported
      judgments such as PCB layout, SI/PI, timing/deadtime, thermal, PLM, or
      full protocol compliance.
- [ ] If fixes are needed, follow-up implementation work is scoped separately
      with validation commands.

## Notes

- User-provided directories inspected so far:
  `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/652`,
  `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/接口文档`,
  and
  `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/S5000C`.
- The directories contain a large mixed corpus: about 317 PDFs, 19 PPTX files,
  12 XLSX files, 10 DOCX files, images, archives, and platform-specific
  material. Scope must stay selective.
- User clarified that the provided company materials are public. This task may
  consult them selectively as public/releasable references.
