# Track Solo testing

Local prototype `0.1.0-experimental`. No device testing, flash, push or PR.

## Commands and exact revision

The branch is `track-solo`, based on upstream `f9450e48`. Native source hashes
below bind the tested code. The all-zero `tests.evidenceRevision` is a draft
placeholder, not a claim that this source has release qualification.

Host logic:

```sh
python3 -B sdk/drafts/track-solo/verify.py
```

Native generation uses the existing `modwerk-source-tools` image and its pinned
ColdFire compiler:

```sh
python3 -B sdk/drafts/track-solo/generate.py
python3 -B sdk/drafts/track-solo/generate.py --check
```

`generate.py` runs both shared code-generation guards. Native linking must have
no undefined symbols. The private runtime candidate is built by the unchanged
`sdk/runtime/loader/build.py --octabam track-solo` after temporarily staging this
draft in `sdk/octabam/modules/track-solo` under the machine-wide check lock.
The staging copy is removed in a finally block. Generated firmware and packages
remain outside Git.

## Host gesture regressions

Passed: OFF, threshold at 119/120 ticks, all eight anchors and 1,024 groups,
repeat suppression, toggle on press only, anchor release, a joined key released
after the anchor, every other panel key before/during arming and active solo,
encoder cancellation, disabling, and context changes. Every group is checked
against multiple original mute/solo words. This does not exercise a device.

## Compiled ColdFire and stock routine

`emulator_test.py` takes an emulator, private original MAIN, runtime package,
matching `link_units` symbol map and new private output folder. It boots MKII
mode, relocates the exact package, and executes the compiled gesture and getter
code. The level routine is compared against the actual unmodified stock solo
operation for all 255 nonempty groups in both routing branches. Canonical
mute/solo and routing state must remain unchanged. OFF and removal are compared
with stock. Inputs and direct calls are synthetic; this is not a panel, DSP
render, project save or hardware test.

Final-source run: **531 checks passed** on the exact package identified below.

## Panel and runtime backend

`panel_test.py` boots a private base and uses its matching symbol map. It
installs through the actual runtime backend, sends physical UART key-matrix
messages, and advances the real UI tick. It checks OFF, the hold threshold,
T2/T3 toggles, all-eight membership, unchanged selected track, FUNC cancellation,
and runtime removal while TRACK buttons remain held. It does not use a physical
USB device. Direct backend calls are not review/trial/Keep/Undo evidence.

A no-card startup opens a real INSERT COMPACT FLASH CARD dialog over SET
DATE/TIME: the context guard correctly refuses solo there. Tests use their own
formatted scratch card and dismiss startup dialogs. A nonzero popup pointer
alone is not an open-window check.

Final-source loaded-project panel/backend run passed. A separate actual menu run
passed OFF/HOLD rendering and the stock YES handler, followed by the complete
gesture/removal suite. The private reports are `state-debug/report.json` and
`menu-quiet/report.json` in the local cache.

## DSP audio

The final DSP run and persistence run both used the canonical stock-saved
text form of the generated fixture, with identical tones and banks.

`prepare_fixture.py` makes a private stock-only project/card from a local
project template using the shared SDK's tone, marker and bank tools. Eight
original generated tones identify T1-T8. No factory audio is used. Both FX slots
are NONE in every Part and bank.

With `panel_test.py --fixture PRIVATE_DIR --audio`, the DSP emulator captures
per-track stems before solo, during T2 solo, during T2+T3 and after release.
The test requires signal on the selected tracks and silence on all others.
This observes emulated DSP output, not physical audio or hardware timing.

Result: **passed** on the exact package below (`audio-final-canonical/report.json`).
All eight stems have signal initially; only T2 has signal during solo; only T2
and T3 have signal after joining; all eight return on anchor release. Selected
stems must exceed RMS 10 and excluded stems must be below RMS 1 (16-bit PCM).
The interpreter runs both DSP cores with the frame ISR enabled.

Additional real DSP stem checks passed with test-only synthetic underlying
mask inputs: a muted T2 becomes audible during its temporary solo; the earlier
T1 solo returns on release; an underlying change to T3 solo during the hold
survives release. Production never writes that canonical word. This is not
qualification of the physical or MIDI gestures used to edit mute/solo state.

Package removal during playback correctly hit the base's existing stopped-track
guard. The passing run uses two stock STOP presses, re-arms solo while stopped,
and removes the module while both anchor and joined keys remain physically held.
Synthetic backend calls pause frame delivery and wait for main's spin. Only
the emulator's explicit pre-call context rejection is retried, before the
target executes; a failed backend operation is never repeated.

## Stock flows and persistence

The source contains no writes to canonical mute/solo, Part, pattern or project
storage. Compiled routine and runtime-removal checks observed canonical-state
preservation. Actual stock SAVE PROJECT was tested before and after the solo
sequence, with the anchor physically held when the second save was opened.
All **52 work/stored project files (20,958,970 bytes)** were byte-identical.
Opening PROJECT cancelled the overlay while stock completed its save. The
private `save-engine-idle/persistence-comparison.json` records every file hash.

The save engine runs asynchronously: a zero popup pointer while its progress
bar runs does not mean saving finished. The first test correctly cancelled
arming when the delayed stock DONE toast opened. The corrected driver waits
for an empty engine queue with a blocked receiver and lets that toast expire.

The complete canonical-fixture save test passed (`save-canonical/report.json`).
A **fresh original-stock DSP emulator** completed loading the actual saved card,
without Track Solo or the Modwerk base; all sixteen FX assignments remained
NONE. Its MAIN hash is recorded below. This tests emulator project loading,
not a physical reboot, Keep or a hardware result.

The persistence fixture uses the exact text form observed after stock saves
its unstretched FLEX samples. The shared tone helper includes bar-count hints
which stock omits. In an earlier synthetic fixture, that first normal save
shortened `project.work` across a cluster boundary and left a dangling FAT16
allocation link, before any solo activity. Repacking identical file contents
loaded successfully. The final fixture avoids that unrelated first-save size
change; the harness now checks FAT mirrors and dangling links before extracting
files. Both final saved card images passed that additional check. General
FAT16 file-resizing behavior remains outside this module's qualification.

Actual Part save/reload, altered project settings and physical reboot
persistence remain unqualified.

MKI, Master track, Neighbor chains, Pickup, MIDI mute/solo changes, normal/studio
cue routing, recording, external clock, automatic pattern/Part changes and
common custom companions remain unqualified. Mute Modes' non-stock modes need
particular care: their earlier canonical-state evaluation is distinct from the
register-only output overlay.

## Performance and resources

No DSP engine or DSP memory is added. The module's audio hook is bounded and
contains no loops or firmware calls. ColdFire tick/key worst-case cycles,
measured CPU comparison, stack bounds and stress-run qualification are pending.
Do not turn linked bytes or executed instructions into hardware timing claims.

Linked initialized code/data: **980 bytes**, zero BSS, 16 relocations, four hooks
and one guarded site. Encoded private package: **1,288 bytes**. This excludes
base/loader bookkeeping, stack reservation and reused stock memory. No
performance numbers have been invented to pass a publication check.

Exact local artifacts (SHA-256):

| Artifact | SHA-256 |
| --- | --- |
| Runtime package | `7d1abf6e4e201c6834af514974fbcd935ed86b90bf5b1e77c20f35b8d5fdbe47` |
| Private base MAIN | `da5a9d93eaed2270af824e6c4b524f122865d01a2d1d168303e962651cb3e029` |
| Original stock MAIN | `164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e` |
| Emulator executable | `b087c97f3031f075551b3336afcd75a407ca4d3476e04a9d5cfaa059b1d40363` |
| `track_solo.c` | `e934db604a185772b2ff0c56c5902594be37e56fd165357f8fedf510413ed40d` |
| `core.s` | `6de1a9017404a69fe5802e0f2c04d9eecb3f1e6fe2d076204b77679fef596f16` |
| `gate.s` | `138d37e59e2d196c021f4b7a700f1cb1a6dd1b262307f8236aec70d1e2fd5bd7` |

Both unchanged private-stock-free scanners passed the exact runtime package.
`generate.py --check` passed both shared ColdFire code-generation guards; native
linking has no undefined symbols. Full emulator reports, packages, card images and
raw emulator logs remain private under `~/.cache/modwerk-track-solo/`.

## Hardware

Not tested. The developer has an MKII and requested emulator success before
moving to device tests. MKI support is an additional qualification gap.

## OT UI capture evidence

The two committed menu captures come from the real UART LCD stream in the
passing menu run. `media/capture.json` records the build, package and emulator
hashes, key sequence, palette and PNG hashes. They were visually inspected.
No active-group indicator exists yet; no reconstructed instrument UI is used.

## Publication gates

`module:doctor -- --draft track-solo` passes the declaration-level cross-compatibility
check beside the base and active modules, UI claims, category, thumbnail and
board claim. Its remaining failures are the deliberately missing public listing,
public packages/fingerprint, native card comparison/pair listing and release
qualification. This draft is not ready for publication. No gates were weakened
or hardware/performance records fabricated.

Latest `npm run check -- --base origin/main`: **passed** in 148.92 seconds
(339 frontend test files; 2,758 passed and one skipped; SDK checks passed).
