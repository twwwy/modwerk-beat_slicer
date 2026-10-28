# Local owner lifecycle prototype

Unpublished base extension on `prototype/module-lifecycle-base`, separate from
any module release. A source backup to twwwy/modwerk-beat_slicer is authorized;
no upstream PR, release or physical testing is authorized.

`ot_module_lifecycle` is table index 37. A contributing module supplies one
four-byte descriptor pointing into its own initialized image. Admission checks
both descriptor and callback bounds against the exact initialized owner; BSS,
unknown owners, odd code addresses and foreign pointers are refused before a
stock-code or table switch.

After a successful per-owner switch, while the stable loader task lock holds
and both images remain allocated, the base notifies the outgoing owner with
DETACH, followed by the incoming owner with ATTACH. Undo restoration uses
RESTORE. Only the automatic saved-set restore loop uses BOOT. Failed admissions
and same-owner no-op switches make no notification. Whole-set rollback can
conservatively retire a provisionally attached owner's metadata.

Callbacks may do bounded writes to their own state. They may not block, call
firmware, allocate, reenter the loader or retain the context pointer. The base
retains no module callback after its owner leaves.

The copied context supplies the initialized diagnostic log's nonce and boot
counter. A module preserving a private ledger may trust BOOT only if its last
witness is the immediately preceding boot under that nonce. Missing/skipped
restoration therefore loses continuity. ATTACH/RESTORE/DETACH should forget
unobserved edit ownership. External non-Modwerk firmware history cannot be
proved by this witness. It is not a portable project metadata service.

## Actual checks, 28 October 2026

- Node 24.22.1, `npm ci`.
- Generated event files: `python3 -B sdk/machines/octatrack/events.py --check`.
- Host loader suite: 17 tests, 3 optional skips; owner notifications run locked
  and unmasked, while both owners are allocated. Added refusal/no-op assertions.
- Saved-set transaction and lifecycle bounds tests pass. Bounds tests compile
  the production admission function with a fake owner registry under ASan/UBSan.
- The diagnostic host test passes readiness, unchanged nonce and successive
  boot counters in addition to existing log checks.
- Pinned full-featured private base build and MCF54455 object guard passed.
  Base identity: `2e1a612832625e268492a06623c3cac5ebfb0ea324889d9e8f30509bbbffc248`.
  MAIN SHA-256: `da5a9d93eaed2270af824e6c4b524f122865d01a2d1d168303e962651cb3e029`.
- Intermediate sample-lock candidate installed, removed, and restored
  automatically in a fresh MKII emulator process using only saved card and
  battery material, with no USB re-upload. Created/manual distinction survived.
  This was an emulator metadata check, DSP disabled, not hardware evidence.
- A minimal base configuration failed the existing strict codegen guard on
  scale-eight indexing in `status.c`; the matching full-featured configuration
  passed. No compiler guard was changed. A later Docker engine stall prevented
  additional native timing and companion tests.

Hardware callbacks/timing, interrupted storage, all restore failure paths and
other contributors remain unqualified. No firmware, packages or snapshots are
committed here.

## Separate follow-up before submission

Offered as **Improvement: fingerprint lifecycle ABI headers in base builds**:
`build_core.py` copies the new lifecycle header but does not explicitly include
that header in its input fingerprint list. Add it before submitting this base
extension, then rebuild/requalify the resulting base identity. The current
private prototype receipts bind the actual MAIN/package hashes and the frozen
header used; they do not establish this future input-fingerprinting behavior.
No PR has been opened or authorized. Keep this shared build change outside the
sample-lock module's eventual PR.

## Fork backup after upstream merge

Current upstream main (`d2cb12d6`) was merged for the fork-only push. The one
conflict was generated `runtime_events.h`; it was regenerated from the merged
event registry. Recorded emulator/native-build evidence above remains bound to
the earlier exact base hash, not a new build of this merged SDK.
