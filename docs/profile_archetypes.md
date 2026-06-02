# Profile Archetypes

Profile archetypes are reusable templates for drafting datasheet profiles for
repeated component families. They solve a narrow scaling problem:

```text
family validator generalizes the rule;
source-backed profile carries the part-specific facts.
```

An archetype does not make a part ready for automatic validation. It only fills
a `review_status="needs_review"` profile draft with common family shape so a
reviewer does not start from an empty JSON file.

## Current Command

```bash
uv run hardwise draft-datasheet-profile project-index.json \
  --identity 74LV165PW \
  --archetype 74x165_piso_16pin \
  --output drafts/74lv165pw.json
```

The project index comes from:

```bash
uv run hardwise design-validator-ui <netlist-or-pst> <bom> --index-json project-index.json
```

## Safety Contract

- Generated profiles always remain `review_status="needs_review"`.
- `suggest-validation-targets` and `design-validator-ui` ignore generated
  drafts until a human promotes them to `ready`.
- Archetypes may propose pin roles, topology family, and recommended metadata.
  A reviewer must still confirm public datasheet pinout, package mapping,
  voltage/current limits, aliases, polarity, and evidence tokens.
- Do not use private datasheets, internal BOM systems, supplier live data, PLM,
  price, lifecycle, PCB layout, or boardview data.

## Supported Archetypes

| Archetype | Family | Validator topology | Main use |
|---|---|---|---|
| `74x165_piso_16pin` | 16-pin 74x165-style PISO shift register | `shift_register_piso` | Drafts pin-role and cascade-check placeholders for 74LV165-like parts. |

## Promotion Checklist

Before changing a generated profile from `needs_review` to `ready`, verify:

- part number and aliases match the BOM identities you want to cover;
- package pinout matches the local symbol pin numbers;
- every pin `number`, `name`, `category`, and `function` matches the public
  datasheet;
- voltage/current limits are copied from public evidence, not guessed;
- diode/LED polarity is checked against public pin diagrams when relevant;
- `recommended.topology_family` matches an implemented family validator; and
- every source-backed fact has a searchable evidence token.
