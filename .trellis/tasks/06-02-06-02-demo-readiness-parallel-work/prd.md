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
4. Adopt the execution order agreed in planning:
   - Windows closes first as a small docs + CI commit.
   - Profile templates are the primary engineering track because they answer
     how Hardwise scales beyond one-off MPN profiles.
   - Interview materials may draft early, but final wording lands last after
     Windows and profile-template facts are known.
5. Preserve Hardwise scope boundaries: public inputs only, schematic-review
   node only, no PCB/layout, no supplier/PLM/lifecycle/price claims, and no
   unverified refdes.
6. Keep commits separated by track unless a parent-only integration update is
   required.
7. Before parent closeout, confirm that the finished artifacts are visible in
   the public repository and branch that the interview/resume links point to.
   If this workspace is not that public branch, record the merge/cherry-pick
   step instead of assuming the work is externally visible.

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
- [ ] The final integration check confirms whether these commits are on the
      interview-facing public `main`, or records the remaining publish step.
- [ ] Parent task records the final task map and remaining follow-ups.

## Notes

- Windows audit is already mostly complete; do not reopen a broad audit unless
  Windows CI reveals a concrete blocker.
- The profile archetype track is the main scalability story: family validators
  generalize rules, while source-backed profiles carry part-specific facts.
