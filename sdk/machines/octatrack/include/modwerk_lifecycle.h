/* SPDX-License-Identifier: MIT
 * Local proposed lifecycle table, not a released base capability.
 * Descriptor and entry must be in the contributing initialized image.
 * Callback: engine task, stable loader lock, bounded nonblocking writes to
 * the owner's state only. No firmware calls, allocation, loader reentry or
 * retained callback/API pointer. An absence must retire uncertain ownership.
 */
#ifndef MODWERK_LIFECYCLE_H
#define MODWERK_LIFECYCLE_H
#include <stdint.h>
enum modwerk_lifecycle_reason {
    MODWERK_LIFECYCLE_DETACH=1, MODWERK_LIFECYCLE_ATTACH,
    MODWERK_LIFECYCLE_BOOT, MODWERK_LIFECYCLE_RESTORE
};
/* A read-only value valid only for the callback. BOOT may preserve an edit
 * ledger only when its last witnessed boot is exactly the preceding one.
 * A skipped/failed restore therefore loses trust, even without a callback.
 * This is continuity within the Modwerk base, not evidence about other OSes. */
struct modwerk_lifecycle_context { uint32_t reason,boot_nonce,boot; };
struct modwerk_lifecycle { void (*notify)(const struct modwerk_lifecycle_context *); };
#endif
