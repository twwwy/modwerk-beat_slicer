# Track Solo interaction cases

Agreed design, 1 November 2026. Author: `twwwy`. Target: Octatrack MKI / MKII,
OS 1.40C. Category: **system**, because this is an input and workflow feature
using native track processing. Development and validation start in the MKII
emulator; hardware trials come afterward, by separate agreement.

This is a documentation-only specification. It does not claim that the existing
prototype implements these rules or that they have passed tests. No firmware
version or release qualification is established by this document.

## Purpose and state ownership

Track Solo is a temporary compositional audition: isolate tracks, adjust their
sound and return to the mix. Keep the original gesture. Do not add latching,
anchor transfer or a long-press gesture to select another editing track.

- **Underlying state** is the current ordinary stock mute/solo state, including
  changes from the panel, MIDI and arranger during the audition.
- **Temporary group** is the set of audio tracks auditioned while the original
  TRACK button, the **anchor**, remains physically held.
- Temporary solo overrides the mute/solo selection used for native processing.
  It does not replace cue routing or bypass the selected Mute Modes policy.
- Stock mute/solo commands continue updating underlying state normally. Their
  effect on the mute/solo selection used for audition is hidden until the
  temporary override ends. Do not queue commands for replay on release.
- Release reveals the latest underlying state, never a stale snapshot from the
  beginning of the hold. Ordinary parameter edits remain real edits.

The final rules supersede earlier proposals to inherit the temporary group into
stock solos, cancel on native mute/solo input, or show the temporary group as
mixer mute/solo state. None of those proposals is part of this design.

## Gesture, activation and release

| ID | Case | Expected result |
| --- | --- | --- |
| G01 | Track Solo is OFF | All controls retain stock behavior. |
| G02 | Hold one audio TRACK alone for approximately two seconds | Activate temporary solo with that track as anchor and initial member. Use the instrument's UI timing. |
| G03 | Release before the threshold | No temporary solo. Preserve ordinary stock short-press behavior. |
| G04 | Press another key or turn an encoder before activation | Cancel pending activation; let the stock action proceed. Activation requires the initial hold alone. |
| G05 | Tap another unmodified TRACK during active solo | Toggle that track's membership once on its press. Its release does not toggle again. |
| G06 | Tap an existing joined member again | Remove that member. The original anchor remains the anchor and a member until release. |
| G07 | Add all seven other tracks | All eight tracks can belong to the group. |
| G08 | Hold another TRACK for two seconds during active solo | No editing-track selection or new anchor. Treat its initial unmodified press as a membership toggle only. |
| G09 | Release a joined TRACK while keeping the anchor held | Keep the resulting group unchanged. |
| G10 | Release the anchor while another TRACK is still held | End the entire audition. Do not transfer ownership to the other held TRACK. |
| G11 | A release belongs to a membership press consumed by Track Solo | Consume the matching release, including when it arrives after the anchor ended. Avoid an orphan stock release. |
| G12 | Solo ends while the anchor is still physically held | Remain inactive. Do not automatically rearm or expose the held anchor as a stock modifier. Require its release and a fresh hold. |
| G13 | Disable or unload Track Solo | Remove the temporary override and return to underlying stock behavior; leave no stuck key or indication. |

## Anchor visibility and stock shortcuts

After activation, hide the held anchor from stock combination handling. Track
Solo still monitors its physical release. Before activation, ordinary stock
behavior applies. Do not synthesize an extra stock action when hiding or
releasing the anchor.

| ID | Case during active solo | Expected result |
| --- | --- | --- |
| K01 | Anchor T2 held; press PLAY or STOP | Perform ordinary sequencer transport, without interpreting TRACK+PLAY/STOP for T2. Keep solo active. |
| K02 | Anchor held; press REC | Perform the normal REC action for the current context. Do not invoke the anchor's TRACK+REC shortcut. |
| K03 | Anchor held; press BANK | Perform the normal BANK action. Do not invoke the anchor's TRACK+BANK sample-editor shortcut. |
| K04 | Anchor held; press YES or NO | Perform the normal contextual action. Do not arm/disarm the anchor's recorder merely because the anchor is held. |
| K05 | Anchor held; press LEFT or RIGHT | Perform normal navigation, without the anchor's sample-nudging shortcut. |
| K06 | Press FUNC or CUE alone | Keep solo active. Do not interpret either as a combination with the anchor. |
| K07 | Deliberately use FUNC+another TRACK | Execute that TRACK's stock quick mute underneath the audition. Do not toggle temporary membership or cancel solo. |
| K08 | Deliberately use CUE+another TRACK | Execute the stock cue operation. Do not toggle temporary membership or cancel solo. |
| K09 | Deliberately use another recognized stock combination with a non-anchor TRACK | Give the recognized stock combination precedence over membership handling. Execute it once. The anchor remains excluded. Verify stock input ordering during implementation. |
| K10 | Want to switch the selected editing track | Release the anchor, then select the track normally. Joining a track does not select it. No additional selection gesture is planned. |

## Underlying mute/solo changes

These commands never inherit the temporary group, cancel the audition, or
replace its membership. Quantized/scheduled stock operations retain their normal
timing underneath; releasing the anchor does not restart their timing.

| ID | Case during active solo | Expected result |
| --- | --- | --- |
| M01 | Use a MIXER mute control | Update underlying mute state normally. Keep the temporary group active. |
| M02 | Use a MIXER solo control | Update underlying solo state normally. Keep the temporary group active. |
| M03 | Use FUNC+TRACK quick mute | Toggle that track's underlying mute normally. Keep the temporary group active. |
| M04 | Receive MIDI mute or solo | Process it normally into underlying state. Keep the temporary group active. |
| M05 | Arranger changes track mutes | Follow those changes underneath. Keep the temporary group active. |
| M06 | Issue repeated, conflicting or scheduled mute/solo changes | Preserve the normal stock result and timing, including multiple toggles. Do not replay historical commands on release. |
| M07 | Release anchor after any of M01-M06 | Reveal the latest underlying state, subject to ordinary stock solo/mute precedence. |
| M08 | Audition a previously muted track | Allow it into the temporary group without clearing its underlying mute. On release its latest underlying state applies. |
| M09 | Underlying stock solos exist before activation | Audition the temporary group, then reveal the current underlying solos on release. Do not merge the groups. |

Example: audition T2+T3, quick-mute T3, then receive a MIDI mute for T5. The
temporary group remains T2+T3. On release, the underlying mix applies with those
mute changes, subject to any underlying stock solos. No temporary membership is
converted into a mute or stock solo.

## TRACK LEDs and MIXER display

| ID | Case | Expected result |
| --- | --- | --- |
| V01 | View MIXER during the audition | Show underlying stock mute/solo state. Do not project the temporary group into MIXER mute/solo indicators. Viewing does not commit or cancel anything. |
| V02 | Change underlying state while viewing MIXER | Show the ordinary resulting underlying state, even though the temporary audition remains effective. |
| V03 | TRACK belongs to the temporary group | Show normal brightness on its TRACK button. This includes auditioned tracks whose underlying state is muted. |
| V04 | TRACK is outside the temporary group | Dim its TRACK button, but never make it completely unlit. |
| V05 | Toggle membership | Update the affected TRACK indication promptly. |
| V06 | Temporary solo ends for any reason | Restore current stock TRACK indications. |
| V07 | FX tails, cue audio or existing loops remain audible outside the group | Continue indicating group membership; LEDs do not measure audible output. |

Verify the available hardware brightness controls and preserve stock color and
selected-track cues where supported. Brightness feasibility is not established
by this specification; propose any necessary compromise before implementing it.

## Editing, navigation and playback

| ID | Case during active solo | Expected result |
| --- | --- | --- |
| E01 | Open SRC, AMP, LFO, FX1 or FX2, including their SETUP pages | Keep solo active. |
| E02 | Turn parameter encoders or adjust track level | Keep solo active. Retain actual edits after release. |
| E03 | Open/close MIXER; adjust output levels, headphone mix or input levels | Keep solo active. Apply ordinary parameter/routing edits normally. |
| E04 | Change scenes or move the crossfader | Keep solo active. Apply normal scene behavior. |
| E05 | Edit trigs, parameter locks or sequencer settings | Keep solo active. Retain ordinary edits. |
| E06 | Open, close or cancel an ordinary editing popup or sample editor | Keep solo active. Canceling a dialog alone does not cancel the audition. Project operations follow P01-P03 below. |
| E07 | Start, stop or restart playback | Keep solo active. Interpret the input without the hidden anchor. |
| E08 | Change pattern, Part or bank within the same project, manually or automatically | Keep the same numbered-track group. On release, use the destination's latest underlying state. Do not carry an old mute snapshot into the destination. |
| E09 | Switch into MIDI editing mode | Cancel temporary audio-track solo. Do not reinterpret the held anchor as a MIDI-track gesture. |

## Cue, recording and companion behavior

| ID | Case during active solo | Expected result |
| --- | --- | --- |
| R01 | Change cue routing | Apply it immediately and keep solo active. Temporary solo does not impose a new cue-routing policy. |
| R02 | CUE MUTES TRACK causes an underlying mute change | Preserve that underlying change, but keep its mute-selection effect overridden until the audition ends. Cue routing itself still operates normally. |
| R03 | Record sequencer notes or parameter locks | Keep solo active; retain the recorded edits normally. |
| R04 | Perform audio or Pickup recording | Keep solo active. Preserve stock source/routing behavior. Do not secretly replace the audition with the underlying full mix for recording. |
| R05 | Record MAIN during the audition | Capture the result determined by stock MAIN routing, including the audition's influence. Recording can create lasting audio even though the solo group itself is temporary. |
| R06 | Use other recorder sources | Preserve stock source semantics; do not assume every source follows the audible MAIN mix. Verify the relevant routes. |
| R07 | Run Track Solo without Mute Modes | Work independently using native stock processing. No companion module is required. |
| R08 | Run beside Mute Modes | Let the selected mode govern excluded-track processing, FX tails and new-trig suppression. Membership alone does not promise immediate silence. |
| R09 | Change the selected Mute Modes policy while soloing | Prefer keeping the group active and applying the new policy immediately. The user accepts cancellation if existing framework behavior makes it the simpler consistent outcome. Verify and record the actual choice; avoid special cross-module coordination. |
| R10 | Use Neighbor chains or T8 as master | Retain native routing and processing semantics; do not introduce automatic chain expansion or custom master handling. Include these configurations in validation. |

## Project operations, persistence and cancellation

| ID | Case | Expected result |
| --- | --- | --- |
| P01 | Open PROJECT or enter the project-save workflow | Cancel temporary solo, even if the anchor remains physically held. |
| P02 | Save afterward | Save ordinary project state. Never serialize temporary membership or the Track Solo session enable setting. Do not change normal stock persistence rules for underlying mutes, solos or parameter edits. |
| P03 | Load, create or reload a project | Cancel the audition. Never carry its group into the new/reloaded project. |
| P04 | Boot, reinstall or replace the module package | No audition resumes. Track Solo defaults to OFF. |
| P05 | Release anchor following a project operation or other cancellation | No extra restoration, stock action or automatic reactivation. |
| P06 | Save with no deliberate ordinary edits | Project contents must remain unchanged. A temporary audition must not introduce saved mute changes or file corruption. |

Opening PROJECT cancels the audition, so a save reached through that UI while
the physical anchor remains held is not a save with the temporary override still
active. Keep that distinction explicit in test records.

## Implementation and validation boundaries

No new editing-track gesture is pending. Remaining questions concern whether the
framework can deliver the agreed behavior, rather than additional UX features.

Before changing firmware, inspect stock input paths and shared hooks, then
propose an implementation consistent with the existing module and base. In
particular, verify hidden-anchor handling across key events and raw held-key
readers; modifier ordering and exactly-once stock shortcuts; matching releases;
popup and context transitions; and dim TRACK LED support. Do not couple Track
Solo to another module's private code or state.

Treat every case above as **not yet validated for this revised design**. Earlier
prototype or storage-fix results do not establish these new UX behaviors. The
existing prototype's blanket key/encoder cancellation and underlying-only TRACK
indications differ from this target design.

Validation order:

1. Emulator gesture and state tests, all eight anchors and membership patterns,
   threshold boundaries, key repeats and release/cancellation ordering.
2. Editing and native-shortcut cases, mixer display separation and TRACK LED
   output. Preserve immediate membership toggling on unmodified TRACK press.
3. Underlying panel/MIDI/arranger mute and solo changes, repeated toggles,
   quantized changes, pattern/Part/bank transitions and release to latest state.
4. Standalone and all Mute Modes policies; cue configurations; machine/routing,
   recorder and Pickup cases. Check audio as well as state.
5. No-edit saves, saved-file integrity and reload comparisons with no modules,
   Track Solo alone and relevant companion combinations. Distinguish ordinary
   editing changes from forbidden persistence of temporary state.
6. Only after the emulator prototype passes, arrange a separate MKII device
   trial. No USB load, Keep, flash, hardware save, publication or upstream PR is
   authorized by this documentation task.

If implementation requires changing a meaningful agreed behavior, explain the
constraint and propose the change before coding it. No general guide deficiency
was identified by this design discussion; this document records this module's
specific interaction contract.
