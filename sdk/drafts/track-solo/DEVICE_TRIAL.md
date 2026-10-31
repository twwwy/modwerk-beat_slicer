# Track Solo 0.2.0 — proposed MKII engineering trial

Offline preparation document for Track Solo 0.2.0-experimental. The focused
emulator gate passed on package SHA-256
`c26a5a6f43ef4fec809d87c50f5a7a95bea7aadbffa1300cdff611108386d17c` and corrected
private base MAIN SHA-256
`124548dc353b2f9cd41ba0a27113ae441e82b68a16d10a1b9509920c61839587`. The
private capsule is `~/.cache/modwerk-track-solo/device-trial-0.2.0/`; its
manifest binds reports and source hashes. No hardware trial has occurred, and
this is not release qualification.

## Review before starting

- Use the user's MKII, OS 1.40C, a backed-up spare CF card and a disposable
  eight-tone project. Parameter edits and recordings are ordinary real changes.
- Confirm no other session owns USB or the emulator. Read device identity,
  inventory, recovery state and current project before staging anything.
- Inventory existing modules and retain the exact packages needed to restore
  them. Review the whole proposed temporary set and any removals with the user.
- Proposed first trial: RAM-only, 900 seconds, then an explicit exact-build Undo
  and identity/inventory verification. Review this timeout with the user before
  beginning; its host timer can roll back even with a healthy USB link. Do not
  Keep, flash, replace the flashed base or save an owner project. A trial on a
  temporary base does not inherit the flashed kept set.
- The tested private base includes a separate ATA ordering fix which remains
  hardware-unqualified and owner-unreviewed. Do not silently substitute a public
  beta or a different base; inspect compatibility and obtain agreement on any
  RAM boot. No physical device action is performed by preparing these files.
- Run standalone first, then the same package with unchanged Mute Modes. Leave
  other companions for a separate trial after the small set is understood.

## First pass: controls and sound, without card saves

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Install the reviewed temporary package, inspect inventory; run SELF TEST if agreed | Correct identity and module set, healthy frames/DSPs; no assumed hardware pass from install alone. |
| 2 | Leave TRACK SOLO OFF; try short and long TRACK presses | Stock selection, shortcuts and lamps. |
| 3 | Enable HOLD; release before two seconds, then hold T2 beyond two seconds | Short hold does not isolate. Long hold isolates T2 and makes excluded TRACK buttons dim but visible. Check actual brightness by eye. |
| 4 | Add/remove T3, then add all tracks; try repeats and release a joined track | One toggle per press, no toggle on release or repeat. No editing-track selection or anchor transfer. |
| 5 | Release original T2 with another track still held | Whole audition ends; native indications and latest underlying state return. |
| 6 | While soloing, use PLAY/STOP and REC | Normal sequencer transport and recording-mode controls; the held anchor never becomes a TRACK shortcut. |
| 7 | Visit SRC/AMP/LFO/FX pages, SETUP and editing popups; turn encoders and LEVEL | Audition continues; edits work and remain after release. |
| 8 | Open MIXER and change its levels | Audition continues. MIXER shows underlying mute/solo; TRACK brightness shows the temporary group. |
| 9 | Use mixer mute/solo, quick mute and deliberate cue/other TRACK combinations | Underlying commands execute once; group stays active. The anchor is excluded from combinations. |
| 10 | Send MIDI mutes/solos and play an arrangement with mute changes | They update underneath and become effective when the anchor releases. Scheduled changes retain native timing; no replay on release. Record actual arranger behavior separately. |
| 11 | Change pattern, Part and bank within the disposable project | Group follows the same track numbers; release reveals destination state. |
| 12 | Open PROJECT; separately try MIDI mode | Audition cancels. Continuing to hold the old anchor neither rearms nor invokes a shortcut; release and rehold starts fresh. |
| 13 | Disable/remove while active, then inspect identity, inventory and lamps | No temporary audio state, stale patch, stuck lamp or orphan key. Confirm Undo restoration explicitly. |

For the hold threshold, repeat a comfortably short hold (~1.5 s) and a comfortably
long hold (~2.5 s), then bracket the boundary. The firmware threshold is 120 UI
ticks; human stopwatch observations do not establish exact interrupt timing.
Test all eight anchors after the initial T2 case passes.

## Companion, routing and capture pass

With unchanged Mute Modes, try OT, OTFX, OTFX-T and DT-T using a long delay/reverb
on an excluded track. Tails and already sounding loops follow native mode
semantics; DT-T does not guarantee a hard cut. Changing the mode through PROJECT
cancels at PROJECT entry. Verify cue routing and CUE MUTES TRACK, Neighbor chains
and T8 master using matched stock controls.

Record MAIN and a direct recorder source in the disposable project, then test
Pickup behavior. Temporary solo does not secretly substitute the underlying mix
for recording. Actual recordings and edits are not undone by anchor release.
These require dedicated capture comparisons; a normal REC-button test alone does
not establish recording-route correctness.

## Load and timing observations

Compare matched OFF, enabled-idle and held-group runs on the same project and
module set. Collect repeated CPU/DSP readings, frame gaps and short MAIN/CUE audio
captures while moving parameters and toggling membership. Listen for clicks,
dropouts, stuck notes and delayed releases. Cached CPU meters are observations,
not a worst-case execution bound.

The revised audio-frame shim is unchanged; input queries, LED filtering and the
UI transition do add work. Hardware CPU, cache and key latency are unmeasured.
The private storage helper's manual SR mask is not covered by every existing
profiling counter. Formal masked-duration measurement would need a separately
reviewed profiling build and emulator check.

## Separate persistence pass, only after the first pass succeeds

If the user separately agrees, save only the disposable project on the spare
card. Compare no-edit saves with no modules, Track Solo alone and the companion
set, including entering SAVE while physically holding the anchor. PROJECT entry
must already have canceled the audition. Audit project files, bank checksums and
FAT state, then reload under original stock firmware. A physical power cycle is
performed only by the user after agreement. Preserve test inputs and record the
exact base, package hashes and observations.

## Stop and restore

Stop at unexpected audio, frame loss, a crash, recovery/identity uncertainty or a
save-integrity mismatch. Do not issue another install to an uncertain recovery
state. Use the reviewed Undo when possible, then verify active identity and
inventory. If restoration fails, ask the user for a power cycle; do not Keep or
flash as a recovery shortcut. Release the USB session after verification.

Record only observed hardware results in TESTING.md. The module remains private
until the user says testing is settled and separately authorizes publication.
