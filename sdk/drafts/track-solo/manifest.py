"""TRACK SOLO: a register-only temporary audio-track solo overlay.

No canonical mute/solo, project or battery-backed byte is written. USB settings
use ot_sequencer_rows. Native card settings and non-stock Mute Modes behavior
remain qualification gaps: see TESTING.md.
"""
from pathlib import Path
import os
from remix.schema import Category, Proof, Gate, Detour, Kind, Linked, Module
from remix.stock_guard import stock_guard

HERE = Path(os.path.relpath(Path(__file__).resolve().parent))
MODULE = Module(
    name="track-solo", key="TRACK SOLO", kind=Kind.CF_PATCH,
    category=Category.FIXES, author="twwwy", author_url="https://github.com/twwwy",
    doc="Hold a track for two seconds, tap other tracks to join, release to restore.",
    proof=Proof.UNTESTED, proof_note="Local prototype; no hardware qualification.",
    linked=(Linked("ts_core", str(HERE / "core.s"), dram=True),
            Linked("ts_gate", str(HERE / "gate.s"), dram=True)),
    detours=(Detour(0x40004dcc,
        stock_guard(0x40004dcc, 6, "4197a307430139cfae7f265ffae67e6207ae511917df0001c0a6382975fde3a7"),
        "ts_gate", "ts_frame_gate", "temporary solo in the level builder's register only"),),
    gates=(Gate("modules/track-solo/verify.py", remix_arg=False),),
)
