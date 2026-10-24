# Managed project storage v1 — implementation contract

Decision: on 2026-10-24 the user selected **SQLite journal + managed input directory**. This clears the project-format choice; it does not choose offline evidence readiness semantics or approve profiles. Existing white React frontend is retained.

Goal / Context / Constraints / Done when:

- Goal: save, reopen, move, back up and restore a local review with its owned original inputs, confirmed facts, profile versions, decisions and history.
- Context: current journal is transactional but source identity uses absolute paths and uploaded directories are temporary. Copying the journal alone cannot restore a complete project.
- Constraints: public/synthetic data only; no implicit vendor PDF redistribution, keys or machine configuration in archives. Existing legacy journal opens remain supported without rewriting original history. No claims of human approval from persisted files.
- Done when: browser save/reopen plus actual independent-process restart, moved-directory open and archive restore retain project identity, reasons and history; related premises still require re-review. Tampered/missing inputs and unknown formats fail before activation. Failure cannot replace the previous valid project.

## Publication and ownership

The sidecar is adjacent to the selected journal, under `<journal-name>.inputs/`. Every source snapshot is immutable and has a UUID. Capture the original bytes from the observed read manifest, verify their size/hash against the successful parse, and publish the complete snapshot by same-filesystem rename only after every file and manifest is written. A failure cleans staging; an unreferenced published snapshot is harmless, never an active project. SQLite must reference only successfully published snapshots; it remains the authority for active project/version selection. Source and SQLite are not one filesystem transaction; this ordering is intentional.

Raw snapshots preserve each logical source independently, including duplicate basenames. They record original paths as provenance but never use those absolute paths as destinations. A source manifest records role, source address, byte hash and stored relative member. These are actually consumed inputs, not a claim to contain every cited document. External original PDFs absent from the readset remain absent.

## Remaining implementation sequence

1. Immutable observed-input snapshots, validation and rejection of changed inputs. Implemented as a storage primitive first; not yet a user-facing save function.
2. Journal extension for managed project UUID, input revision and explicit reopen arguments. Preserve legacy absolute-path namespaces through an alias/migration record; do not guess associations by matching names. A managed UUID remains stable after sidecar relocation. Loading reconstructs only declared reader inputs and profile files; unresolved relative document links stay explicit gaps.
3. Save/open/rerun endpoints serialize under the existing review lock. Candidate context must parse and verify before publish. Context cleanup must never remove owned snapshots. Existing legacy import continues working until explicit save adoption.
4. Complete backup uses a consistent SQLite backup and only its referenced source snapshots; restore stages and validates before activation in a fresh destination, never overwrites a valid existing project. Reject traversal, symlinks, duplicate members, unknown versions, hash mismatch and missing members. Run IDs/history are retained; current code/rule changes still trigger normal re-review.
5. Add save/open/backup/restore to the existing white frontend, generated API contracts and offline scope explanations; exercise the actual browser and independent-process lifecycle. Record exactly which evidence originals are included. Offline readiness contract remains a separate pending choice.

## Acceptance checks

- Persist after uploaded temp sources disappear; reopen without the old paths.
- Move journal plus sidecar to another directory and retain the same project and reasons.
- Restore a complete backup into a fresh location, then change a related fact and observe NEEDS_REVIEW with the original reason retained.
- Interrupt before source publication, after source publication/before SQLite commit, and during journal transaction: retain the previous active version, no reference to partial sources.
- Concurrent/stale writers remain rejected using existing revision checks.
- A corrupt archive or source snapshot never clears/replaces the active context or original journal.
- Legacy source-bound journals remain readable; explicit adoption preserves original run provenance rather than rewriting past source paths.

The storage primitive alone does not close A09/M2 or the full goal. Every integration and acceptance item above remains required.
