| SPDX-License-Identifier: MIT
| Copyright (c) 2026 twwwy
        .text
        .balign 4
        .global ts_frame_gate, ts_get, ts_rows

| The level builder has loaded its mute/solo word into d5. Override only
| that working register. The stock word and solo-mode byte stay untouched.
| Restore d0 and reproduce the displaced flag test, including its CCR.
ts_frame_gate:
        move.l %d0,-(%sp)
        move.l ts_overlay,%d0
        tst.l %d0
        beq .Lts_stock
        andi.l #0xffff0000,%d5
        or.l %d0,%d5
.Lts_stock:
        move.l (%sp)+,%d0
        tst.b 0x80000037
        jmp 0x40004dd2

ts_get:
        jmp ts_label

        .balign 4
ts_rows:
        .long 1
        .long .Lts_row_label,ts_get,ts_set
.Lts_row_label:
        .asciz "TRACK SOLO"
