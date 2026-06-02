# Interview materials closeout

## Goal

Package the real Allegro coverage story into concise interview/demo materials,
then update the final wording after Windows compatibility and profile-template
findings land.

The story should be easy to say out loud:

> Hardwise aligns a full public Allegro BOM to the schematic, performs light
> deterministic checks across the passive majority, and runs deeper
> source-backed topology validators on selected repeated active devices.

## Requirements

1. Produce interview-facing language for the current measured result:
   - 4010 parsed components;
   - 4010 BOM matches;
   - 3738 validated or generic-covered rows;
   - 272 manual rows;
   - PASS/WARN/ERROR = 3653/79/6.
2. Explain the two-layer coverage honestly:
   - `GENERIC_CAPACITOR` and `GENERIC_RESISTOR` are light deterministic
     coverage from BOM value/package and inferred rail voltage;
   - `LN2312LT1G`, `74LV165`, `PCA9617A`, `PCA9548A`, `MPQ8626`, and diode
     profiles are deeper source-backed checks.
3. Include the key demo point: `74LV165` proves Hardwise can inspect signal
   chain topology such as load/clock fanout and Q7-to-DS cascade, not only
   voltage limits.
4. Include the architecture point: family validators plus source-backed
   profiles, with profile archetypes/templates as the next scale mechanism.
5. Include the conservative safety point: ambiguous LED polarity stayed manual
   instead of being forced into PASS for coverage optics.
6. Update final materials after:
   - Windows compatibility audit determines the Windows wording; and
   - profile archetype/template work determines the exact scalability wording.
7. Keep claims inside the schematic-review node. Do not claim PCB/layout,
   supplier/PLM, lifecycle, price, simulation, or automated expert judgement.

## Acceptance Criteria

- [ ] `docs/interview_qa.md` contains a concise, current answer for the real
      Allegro demo and architecture story.
- [ ] README or a demo-facing doc contains the command and result summary for
      the public Allegro workbench, without overclaiming generic passive depth.
- [ ] At least one screenshot or artifact path is documented for the workbench
      result.
- [ ] The wording includes Windows support status accurately after the Windows
      audit: likely-compatible, WSL-recommended, or CI-verified depending on the
      actual result.
- [ ] The wording includes the profile-template scalability story after that
      task lands.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass if code or rendered doc
      generation changes are made.

## Notes

- This can start immediately as a draft, but should finish last among the three
  child tasks so it can absorb Windows/profile-template conclusions.
