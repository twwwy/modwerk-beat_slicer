#!/usr/bin/env python3
"""Host gesture regressions; separate ColdFire emulator evidence is required."""
import ctypes as ct
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    shared = Path(tmp) / 'solo.so'
    subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-shared', '-fPIC', '-DTS_HOST', str(HERE/'track_solo.c'),
                    '-o', str(shared)], check=True)
    lib = ct.CDLL(str(shared))
    lib.ts_effective_word.argtypes = [ct.c_uint32]
    lib.ts_effective_word.restype = ct.c_uint32
    overlay = ct.c_uint32.in_dll(lib, 'ts_overlay')
    context = ct.c_uint32.in_dll(lib, 'ts_host_context')
    api = ct.c_uint32()
    def key(t, down=True): return lib.ts_key(0x10+t, int(down))
    def tick(n=1):
        for _ in range(n): lib.ts_tick(ct.byref(api))
    def fresh(enabled=True):
        lib.ts_test_reset()
        if enabled: lib.ts_set(1, 0)
        tick()
    def arm(t):
        assert key(t) == 0
        tick(120)
        assert overlay.value == 1 << t
    fresh(False)
    key(1); tick(300)
    assert overlay.value == 0, 'OFF must leave long presses inert'
    fresh(); key(1); tick(119)
    assert overlay.value == 0, 'must not activate before two seconds'
    tick(); assert overlay.value == 2
    assert key(2) == 1 and overlay.value == 6
    assert key(2) == 1 and overlay.value == 6, 'repeat must not toggle'
    assert key(2,False) == 1 and overlay.value == 6
    assert key(2) == 1 and overlay.value == 2
    assert key(1,False) == 0 and overlay.value == 0
    assert key(2,False) == 1, 'paired release after anchor ended'
    for anchor in range(8):
        for selection in range(256):
            if not selection & (1 << anchor): continue
            fresh(); arm(anchor)
            for t in range(8):
                if t != anchor and selection & (1 << t):
                    assert key(t) == 1 and key(t,False) == 1
            assert overlay.value == selection
            for mutes in (0, 1, 0x55, 0xaa, 0xff):
                for solos in (0, 0x81, 0xff):
                    canonical = 0x5aa50000 | mutes << 8 | solos
                    assert lib.ts_effective_word(canonical) == 0x5aa50000 | selection
            key(anchor, False)
            assert overlay.value == 0
            assert lib.ts_effective_word(0x5aa58142) == 0x5aa58142
    for code in list(range(0x10)) + list(range(0x18,64)):
        fresh(); lib.ts_key(code,1); key(0); tick(150)
        assert overlay.value == 0
        fresh(); key(0); tick(60); lib.ts_key(code,1); tick(150)
        assert overlay.value == 0
        fresh(); arm(0); assert lib.ts_key(code,1) == 0
        assert overlay.value == 0
    fresh(); key(0); tick(100); key(1); tick(150)
    assert overlay.value == 0, 'ambiguous chord must not arm'
    fresh(); arm(3); lib.ts_enc(0,1)
    assert overlay.value == 0
    fresh(); arm(4); lib.ts_set(-1,0)
    assert overlay.value == 0
    fresh(); arm(5); context.value = 0; tick()
    assert overlay.value == 0
    fresh(); key(6); tick(60); context.value = 2; tick(80)
    assert overlay.value == 0
    print('PASS: threshold, 8 anchors / 1024 groups, mute/solo preservation, paired edges, shortcuts, disable and context')
