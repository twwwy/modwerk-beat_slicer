/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 twwwy
 * UI-task gesture state. Only ts_overlay is read by the audio interrupt.
 * No stock mute/solo, Part, pattern, project or battery-backed byte is written.
 */
#include <stdint.h>

#define TRACK_FIRST 0x10
#define TRACK_COUNT 8
#define HOLD_TICKS 120u
#define NO_ANCHOR 8u

struct ts_api { volatile uint32_t value; };
struct ts_state {
    uint32_t initialized, other[2], context;
    uint16_t elapsed;
    uint8_t enabled, held, swallowed, anchor, blocked;
};
/* Fully initialized data, also on card builds which do not clear .bss. */
static struct ts_state ts = { .initialized = 1, .anchor = NO_ANCHOR };
static struct ts_state *volatile ts_at = &ts;
volatile uint32_t ts_overlay __attribute__((aligned(4))) = 0;

#ifdef TS_HOST
uint32_t ts_host_context = 1;
static uint32_t context(void) { return ts_host_context; }
void ts_test_reset(void) {
    struct ts_state fresh = { .initialized = 1, .anchor = NO_ANCHOR };
    ts = fresh;
    ts_overlay = 0;
    ts_host_context = 1;
}
#else
static uint32_t context(void) {
    /* MIDI mode is a separate bank of tracks. Never solo audio from there.
     * An open stock popup owns its keys; a nonzero popup pointer alone is
     * insufficient (octabam trap-popup-redraw). No firmware calls here.
     */
    if (*(volatile uint32_t *)0x80000012u) return 0;
    uint32_t popup = *(volatile uint32_t *)0x460d175cu;
    if (popup >= 0x46000000u && popup < 0x47000000u && !(popup & 1u) &&
        (*(volatile uint32_t *)(uintptr_t)(popup + 32u) & 0x20u)) return 0;
    return 1;
}
#endif

static void cancel(struct ts_state *s) {
    ts_overlay = 0;
    s->anchor = NO_ANCHOR;
    s->elapsed = 0;
    s->blocked = 1;
}

static int others(const struct ts_state *s) { return s->other[0] || s->other[1]; }

static unsigned physical_tracks(const struct ts_state *s) {
#ifdef TS_HOST
    return s->held;
#else
    (void)s;
    return *(volatile const uint8_t *)0x46100b1au;
#endif
}

static uint32_t physical_other(const struct ts_state *s, unsigned bank) {
#ifdef TS_HOST
    return s->other[bank];
#else
    (void)s;
    volatile const uint8_t *rows = (volatile const uint8_t *)0x46100b18u;
    unsigned i = bank * 4u;
    return (uint32_t)rows[i] | (uint32_t)rows[i+1] << 8 |
        (bank ? (uint32_t)rows[i+2] << 16 : 0) | (uint32_t)rows[i+3] << 24;
#endif
}

static int physically_held(unsigned anchor) {
#ifdef TS_HOST
    (void)anchor;
    return 1; /* host tests drive edge delivery; native tests also set the matrix */
#else
    /* Panel parser's raw matrix, before event consumption by any module.
     * A lost/consumed release must not leave a session active. Other keys
     * also cancel even when an earlier subscriber consumed their event.
     */
    volatile const uint8_t *rows = (volatile const uint8_t *)0x46100b18u;
    return (rows[2] & (1u << anchor)) &&
        !(rows[0] | rows[1] | rows[3] | rows[4] | rows[5] | rows[6] | rows[7]);
#endif
}

void ts_set(int delta, int wrap) {
    struct ts_state *s = ts_at;
    if (wrap) s->enabled ^= 1u;
    else if (delta) s->enabled = delta > 0;
    cancel(s);
}

/* Both stock's getter and the pinned ColdFire compiler return this in d0. */
const char *ts_label(void) { return ts_at->enabled ? "HOLD" : "OFF"; }

int ts_key(int code, int pressed) {
    struct ts_state *s = ts_at;
    if (code < 0 || code > 63) return 0;
    if (code >= TRACK_FIRST && code < TRACK_FIRST + TRACK_COUNT) {
        unsigned track = (unsigned)(code - TRACK_FIRST), bit = 1u << track;
        unsigned swallowed = s->swallowed & bit;
        if (!pressed) {
            s->held &= (uint8_t)~bit;
            s->swallowed &= (uint8_t)~bit;
            if (s->anchor == track) cancel(s);
            return swallowed != 0;
        }
        if (s->held & bit) return swallowed != 0; /* never toggle on a repeat */
        /* A fresh down follows any queued release. Retire a swallowed edge
         * whose release an earlier module consumed, without swallowing the
         * release of this new (possibly stock-owned) press.
         */
        s->swallowed &= (uint8_t)~bit;
        s->held |= (uint8_t)bit;
        if (!s->enabled || !context() || others(s)) { cancel(s); return 0; }
        if (ts_overlay) {
            /* Anchor remains a member; another track toggles on its down edge. */
            ts_overlay ^= bit;
            s->swallowed |= (uint8_t)bit;
            return 1;
        }
        if (s->blocked || s->anchor != NO_ANCHOR) { cancel(s); return 0; }
        s->anchor = (uint8_t)track;
        s->context = context();
        s->elapsed = 0;
        return 0; /* let stock handle the original track press */
    }
    unsigned bank = (unsigned)code >> 5, bit = 1u << ((unsigned)code & 31u);
    if (pressed) {
        s->other[bank] |= bit;
        cancel(s); /* includes FUNC/CUE, recording, transport, menus and nudges */
    } else s->other[bank] &= ~bit;
    return 0;
}

int ts_enc(int encoder, int delta) {
    (void)encoder;
    if (delta) cancel(ts_at); /* a track + encoder shortcut belongs to stock */
    return 0;
}

void ts_tick(struct ts_api *api) {
    struct ts_state *s = ts_at;
    /* Recover from releases consumed earlier on the hook bus. Preserve the
     * swallowed-release bookkeeping until the edge arrives or a fresh down.
     */
    s->held &= (uint8_t)physical_tracks(s);
    s->other[0] &= physical_other(s,0);
    s->other[1] &= physical_other(s,1);
    if (!s->held && !others(s)) s->blocked = 0;
    if (s->anchor != NO_ANCHOR) {
        if (!s->enabled || !context() || context() != s->context || others(s) ||
            !physically_held(s->anchor)) cancel(s);
        else if (!ts_overlay && ++s->elapsed >= HOLD_TICKS)
            ts_overlay = 1u << s->anchor;
    }
    api->value = (uint32_t)s->enabled << 16 | (uint32_t)s->held << 8 | ts_overlay;
}

/* Independent oracle for the assembly's register-only transformation. */
uint32_t ts_effective_word(uint32_t original) {
    unsigned overlay = ts_overlay;
    return overlay ? (original & 0xffff0000u) | overlay : original;
}
