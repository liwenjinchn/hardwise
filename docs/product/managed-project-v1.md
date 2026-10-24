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
2. Journal v2 adds a managed project UUID, snapshot reference and typed reopen arguments. Explicit save adopts the existing review namespace as the durable key, preserving its history verbatim; the new managed UUID selects its saved sources. No association is guessed from names. Both remain stable after sidecar relocation. Loading reconstructs declared reader inputs and profile files in a private temporary tree, preserving relative source layout; external document links remain subject to the existing missing-source checks.
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

## Implemented API and migration — 2026-10-24

- `GET /api/workbench/projects` lists saved IDs and snapshot references in the configured journal.
- `POST /api/workbench/projects/save?expected_run_id=<current>` captures sources and commits the catalog reference. It explicitly adopts the current legacy namespace without moving/relabeling old events.
- `POST /api/workbench/projects/<id>/open?expected_run_id=<current>` validates the saved source group, reconstructs a candidate context, begins a reviewed run and publishes it. Stale requests return409; unknown IDs404; missing/corrupt sources or descriptors422. Failure before activation retains the active context. Without --review-db, these functions return400 with configuration guidance.
- Rerun retains managed identity. Saving a reopened project updates its source revision while keeping its ID. No arbitrary filesystem path is accepted through these API endpoints.
- SQLite user_version1→2 is an additive, explicitly transactional schema migration. Existing state/events/runs/heads remain intact; managed_projects is added. Old binaries which only understand v1 reject a v2 journal on initialization: preserve a pre-upgrade backup for rollback; do not call the original format unchanged. This is not downgrade support.

Observed: public L78 source copies removed, journal plus sidecar moved and renamed, new independent process rebuilt the context and recovered a real API waiver with the exact Chinese reason and history count1. This verifies that local pin finding only; full topology dependency precision remains open. Basenames/relative layout are retained during reconstruction, but absent external PDFs are not invented. Invalid descriptor/snapshot validation is before context activation.

Remaining: further crash/power-loss proof spanning input publication and SQLite, cleanup of unreferenced snapshots. Complete CLI backup/restore is described below. Do not mark A09/M2 complete from these API and source tests.

## Direct saved-project startup

```bash
uv run hardwise serve-workbench --review-db /path/to/review.sqlite --open-project <saved-id> --no-auto-datasheet-candidates
```

No source positional argument is required with --open-project. The journal must already exist, and the ID is obtained from the saved-project catalog. Do not combine it with netlist/BOM, --profiles or optional source files: mixed sources are rejected rather than silently overriding the saved version. Existing source-based invocation remains supported; its profile directory default is unchanged. Use --dry-run to validate reconstruction without starting HTTP or adding a reviewed run. A normal startup opens a new reviewed run, applying existing fact/rule re-review logic.

The reconstructed source tree lives for the server lifetime, including reruns, and is cleaned on dry-run, initialization failure or server return/exception. Owned immutable snapshots stay in the sidecar. SIGKILL/OS crash temporary-tree cleanup remains unproven and is not claimed. Current CLI assumes an explicitly selected saved ID; a blank-start graphical project picker is not yet provided.

Observed in a real CLI/HTTP process with dotenv disabled and model credentials absent: a moved journal/sidecar copy from the deleted-source experiment started without positional source args. HTTP root/state returned200, selected local-pin waiver and exact Chinese reason/history1 remained. Service shutdown log completed and its port no longer listened. This is macOS local startup evidence, not Windows/Cadence acceptance.

## White frontend save/open controls

The existing Import page now includes Save and reopen. A file-backed live service lists saved names/managed IDs/source revisions, saves the current parsed source set, and opens a selection into the Review page. Opening resets stale component detail, query and filter state. Catalog read can be retried; stale-run open/save errors are displayed rather than converted into success. Initial catalog requests cannot overwrite a later refresh/save result. Old descriptors without a stored name use the explicit saved-project fallback label.

The catalog and save response have generated Pydantic/TypeScript contracts. Offline HTML makes no project API requests and explains that its report cannot save/open local projects. Memory-mode servers explain --review-db. Saved originals and linked external originals remain different scopes; the panel does not call this a complete backup.

Browser proof: save current public mixed design with a review reason, import L78, open the saved mixed project and recover project identity/reason; catalog outage retry and stale-open rejection. White narrow screenshot at760px inspected with no horizontal overflow. This is an existing live service UI, not an empty-start graphical picker or a complete backup/restore workflow.

## Complete saved-project backup and fresh restore — CLI

```bash
uv run hardwise backup-projects --review-db /path/review.sqlite --output /path/review-backup.zip
uv run hardwise restore-projects /path/review-backup.zip --destination /new/path/restored-project
uv run hardwise serve-workbench --review-db /new/path/restored-project/journal.sqlite --open-project <saved-id> --no-auto-datasheet-candidates
```

Scope is **saved projects and journal history**. Save the desired current input version first. SQLite's online backup API captures one consistent committed journal while the service may continue running; referenced source snapshots are then copied and revalidated. Successful saves now write descriptorv2 with retained prior source-snapshot references, so repeated saved versions remain in future backups. Descriptorv1 remains readable; previously unreferenced older snapshots cannot be retrospectively certified. SQLite schema staysv2. Older binaries lacking descriptorv2 support cannot open newly saved descriptors; no downgrade support is claimed.

The archive includes a fixed-name journal, its referenced current/retained immutable source snapshots and a versioned file size/SHA256 manifest. It omits orphan/staging snapshots, .env/keys, temporary materializations and external PDFs that were never owned inputs. Journal namespaces without saved sources are listed as source_unowned_project_ids: their history is included, but their original designs are not recoverable from this package. This field must not be presented as a complete source backup for those namespaces. At least one saved project is required.

Restore verifies ZIP member uniqueness (including case collisions), relative paths, supported types, exact manifest/member set, sizes/hashes, SQLite quick_check/schema/catalog and every referenced snapshot. It reconstructs each current saved project before publishing. Rejects encrypted members, symlinks, directories, traversal, unknown versions and extra/missing members. Limits:50,000 payload files,1GiB total expanded content,16MiB manifest. Checksums detect corruption against the manifest; they are not signatures or human engineering approval.

Destination must be new; backup output must be new. Neither operation may write into owned input directories. After validation, restore reserves the destination exclusively and publishes sources before the journal. A restore-incomplete marker blocks all DecisionJournal opens until publication finishes; ordinary failures remove only the newly created destination. A real subprocess _exit after source publication leaves the marker and blocks partial open; restore the original archive into another fresh destination. This is a tested process-interruption boundary, not filesystem/OS power-loss durability certification. Parent staging leftovers after forced exit are not automatically pruned.

Observed real CLI/HTTP experiment: backup from current public demo journal, restore to a fresh directory, then independently start --open-project without source paths/key/fake mode. The three prior history events and original NEEDS_REVIEW reason were retained. Original demo inputs/journal were preserved. Separate tests delete source and journal before restore, retain repeated saved versions, preserve local-pin waived reason, prove a concurrent later save cannot mix into the frozen catalog, reject damaged packages/existing targets and block interrupted restore.

Archive backup/restore is available through both these local commands and the white page described below; restored copies remain separate from the current service. Full A09/M2 requires remaining source-publication/SQLite crash boundaries, all relevant rule-dependency acceptance and target environment proof; do not close the full product goal from these tests.

## Browser archive operations

The white Import page now downloads a complete saved-project ZIP and uploads a ZIP for restore into a fresh server-owned sibling directory `<journal>.restored/<uuid>/`. The current journal and active context are never replaced or merged by restore. A typed receipt identifies the restored journal, source-unowned namespaces and explicit startup commands for macOS/Linux and PowerShell. It also persists as restore-info.json beside the recovered journal. This is not an automatic switch of the current tab or an empty-start graphical project picker.

- `POST /api/workbench/projects/backup?expected_run_id=<current>` returns application/zip with saved/unowned-project count headers. Temporary download staging is cleaned after the response; interrupted-process cleanup is not claimed.
- `POST /api/workbench/projects/restore?expected_run_id=<current>` accepts multipart `archive`, ignoring its filename as a destination. Payload size is bounded including ZIP overhead, then existing full archive validation runs. Returns a generated ProjectRestoreReceipt. Stale run409; corrupt backup422; oversized copied payload413. No arbitrary destination path is accepted from the browser. The framework may spool multipart data before route validation; this is not advertised as an ingress bandwidth limit.

The restore action means 'restore to new directory'. To open it, run the provided command as a new local service, retaining the original service/project as-is. If receipt writing fails, remove only that newly restored copy and return failure. User-visible errors never claim successful restoration. UI loading disables overlapping project actions; offline list/save/open/backup/restore make no API request.

Browser proof downloads the actual ZIP, uploads a corrupt file and observes an error, retries with the downloaded archive, displays the new copy/commands, compares original active state unchanged and runs real CLI dry-run from the restored journal. Narrow760px receipt/PowerShell command rendering is inspected without horizontal overflow. PowerShell quoting is checked as text; actual Windows execution remains an external gate.
