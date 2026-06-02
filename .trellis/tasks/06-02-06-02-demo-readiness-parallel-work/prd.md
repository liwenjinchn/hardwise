# Demo readiness parallel work

## Goal

Coordinate three parallel readiness tracks after the real Allegro coverage
slice:

- Windows compatibility audit, so the demo can be reproduced outside the macOS
  development machine;
- profile archetype/template workflow, so Hardwise scales by reusable validator
  families rather than one-off MPN work; and
- interview/demo materials closeout, so the public-board story is packaged in a
  way that is easy to show and defend.

The parent task owns sequencing and final integration. Each child task should
remain independently reviewable and committable.

## Requirements

1. Reuse the existing `06-01-windows-compatibility-audit` task as the Windows
   child track.
2. Create a profile archetype/template child track for `needs_review` profile
   generation and promotion rules.
3. Create an interview materials child track for README/interview/screenshot
   packaging.
4. Keep the three tracks parallel where possible:
   - Windows audit can proceed immediately.
   - Profile templates can proceed immediately.
   - Interview materials can draft immediately, then receive final facts from
     Windows and profile-template results.
5. Preserve Hardwise scope boundaries: public inputs only, schematic-review
   node only, no PCB/layout, no supplier/PLM/lifecycle/price claims, and no
   unverified refdes.
6. Keep commits separated by track unless a parent-only integration update is
   required.

## Acceptance Criteria

- [ ] Windows child task documents and/or implements the minimum Windows usage
      and CI story.
- [ ] Profile archetype child task demonstrates a reusable template path for at
      least one high-value family without bypassing `review_status` safety.
- [ ] Interview child task packages the real Allegro story using measured
      facts: 4010 BOM-matched components, 3738 validated/generic-covered rows,
      and the generic-passive plus deep-topology narrative.
- [ ] Final materials do not overclaim: generic passives are light coverage,
      profile-backed families are deeper deterministic checks, and Windows
      support is only called verified after an actual Windows/CI run.
- [ ] Parent task records the final task map and remaining follow-ups.

## Notes

- Suggested order: start Windows audit first, start profile archetypes in
  parallel, and let interview materials trail slightly so it can absorb both
  outcomes.
