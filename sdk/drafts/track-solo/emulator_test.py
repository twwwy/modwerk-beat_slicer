#!/usr/bin/env python3
"""Compiled ColdFire + real stock-level-routine regression, without hardware.

Supply a private unpacked OS 1.40C MAIN, the generated runtime package, the
standard link_units symbol map, and ot_emu. No stock bytes enter this folder.
This is an isolated routine test: direct calls, synthetic gain inputs, no DSP
audio and no project persistence claim. Logs stay in the private output dir.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

BASE, API, LEVELS = 0x47400000, 0x47020000, 0x47021000
MUTE, SOLO_FLAG, SITE = 0x80000008, 0x80000037, 0x40004dcc

def packet_image(data):
    assert data[:4] == b'MWRM' and int.from_bytes(data[4:6], 'big') == 8
    image_len, bss, reloc_count, hooks, sites = struct.unpack_from('>IIIII', data, 8)
    assert bss == 0 and sites == 1
    start = 76 + hooks * 4
    image = bytearray(data[start:start+image_len])
    offsets = struct.unpack_from('>%dI' % reloc_count, data, start+image_len)
    for at in offsets:
        struct.pack_into('>I', image, at, struct.unpack_from('>I', image, at)[0] + BASE)
    return image

class Emulator:
    def __init__(self, binary, image, out, extra=()):
        self.log = (out/'emulator.private.log').open('w')
        self.err = (out/'emulator-stderr.private.log').open('w')
        self.p = subprocess.Popen([str(binary), '--image', str(image), '--mkii',
            '--periph', '--interactive', '--ms', '1000', '--max', '500000000', *map(str,extra)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err,
            text=True, bufsize=1)
        self.project_loaded = False
        while True:
            line = self.p.stdout.readline()
            if not line: raise RuntimeError('Emulator exited during boot')
            self.log.write(line)
            self.log.flush()
            if 'load run ended: LOAD PROJECT handled' in line:
                self.project_loaded = True
            if line.startswith('ready '): break
    def command(self, command):
        self.p.stdin.write(command+'\n'); self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line: raise RuntimeError('Emulator exited during '+command.split()[0])
            self.log.write(line); self.log.flush()
            if line.startswith(('ok', 'peek ', 'audio ', 'tx ', 'card ', 'writes ', 'err ')):
                if line.startswith('err '): raise RuntimeError(line.strip())
                return line.strip()
    def read(self, at, size): return bytes.fromhex(self.command(f'peek {at:#x} {size}').split()[1])
    def write(self, at, data): self.command(f'poke {at:#x} {data.hex()}')
    def u32(self, at, value): self.write(at, struct.pack('>I',value))
    def call(self, at, *args):
        text = self.command('call '+hex(at)+''.join(' '+hex(n & 0xffffffff) for n in args))
        return int(text.split('d0=')[1],0)
    def close(self):
        self.p.stdin.write('quit\n'); self.p.stdin.flush()
        self.p.communicate(timeout=20)
        self.log.close(); self.err.close()

def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sym=json.loads(args.symbols.read_text())
    data=args.package.read_bytes();image=packet_image(data)
    emu=Emulator(args.emulator,args.stock_main,out)
    checks=0
    try:
        emu.write(BASE,image)
        def call(name,*values): return emu.call(BASE+sym[name],*values)
        def overlay(): return int.from_bytes(emu.read(BASE+sym['ts_overlay'],4),'big')
        def tick(n=1):
            for _ in range(n): call('ts_tick',API)
        held=0
        def key(t,down=1):
            nonlocal held
            held = held | (1<<t) if down else held & ~(1<<t)
            emu.write(0x46100b1a,bytes([held]))
            return call('ts_key',0x10+t,down)
        emu.u32(0x80000012,0);emu.u32(0x460d175c,0)
        key(1);tick(150);assert overlay()==0;key(1,0);tick()
        call('ts_set',1,0);tick()
        for anchor in range(8):
            assert key(anchor)==0;tick(119);assert overlay()==0
            tick();assert overlay()==1<<anchor
            other=(anchor+1)%8
            assert key(other)==1 and overlay()==(1<<anchor|1<<other)
            assert key(other)==1 and key(other,0)==1
            assert key(other)==1 and overlay()==1<<anchor
            assert key(anchor,0)==0 and overlay()==0
            assert key(other,0)==1;tick()
            checks+=1
        # The real getter adapter must return d0 pointing to the correct label.
        label=call('ts_get');assert emu.read(label,5)==b'HOLD\0'
        call('ts_set',-1,0)
        label=call('ts_get');assert emu.read(label,4)==b'OFF\0'
        checks+=1
        call('ts_set',1,0);tick();key(0);tick(120);assert overlay()==1
        emu.write(0x46100b1a,b'\0')  # lost release: no ts_key callback
        tick();assert overlay()==0
        held=0;tick(2)
        key(0);tick(120);assert overlay()==1  # re-arm without the lost callback
        key(0,0);tick()
        checks+=1

        # Compare the real stock routine against itself with stock solo inputs.
        # Only the candidate run detours the level-builder flag test. Its
        # canonical word is deliberately different and must survive unchanged.
        original=emu.read(SITE,6)
        assert hashlib.sha256(original).hexdigest()=='4197a307430139cfae7f265ffae67e6207ae511917df0001c0a6382975fde3a7'
        patch=b'\x4e\xf9'+struct.pack('>I',BASE+sym['ts_frame_gate'])
        def levels(word,flag,mask,patched):
            emu.write(SITE,patch if patched else original)
            emu.u32(BASE+sym['ts_overlay'],mask)
            emu.u32(MUTE,word);emu.write(SOLO_FLAG,bytes([flag]))
            emu.u32(0x80003c10,LEVELS)
            emu.write(0x80000c60,struct.pack('>16H',*[0x1100+257*t for t in range(16)]))
            emu.write(0x80000c80,struct.pack('>8H',*[0x3000+t for t in range(8)]))
            emu.write(0x8000485a,bytes(64))
            emu.u32(0x8000009c,0)  # stock CUE MUTES TRACK off
            emu.call(0x40004db8)
            assert int.from_bytes(emu.read(MUTE,4),'big')==word
            assert emu.read(SOLO_FLAG,1)==bytes([flag])
            return emu.read(LEVELS,64)
        for flag in (0,1):
            for mask in range(1,256):
                expected=levels(0x550000|mask,flag,0,False)
                # Pre-existing mutes and solos are intentionally unrelated.
                word=0x55a581
                actual=levels(word,flag,mask,True)
                assert actual==expected,(flag,mask)
                checks+=1
            for word in (0,0x5500,0xff00,0x0042,0xff81):
                assert levels(word,flag,0,True)==levels(word,flag,0,False)
                checks+=1
        # Removing the overlay while active returns the exact original output.
        baseline=levels(0x5500,0,0,False)
        levels(0x5500,0,2,True)
        assert levels(0x5500,0,2,False)==baseline
        checks+=1
        emu.write(SITE,original)
    finally:
        emu.close()
    report={'result':'passed','checks':checks,'model':'MKII emulator',
        'scope':'Compiled gesture/getter code and stock level routine; synthetic inputs; no audio, project or hardware qualification',
        'packageSha256':hashlib.sha256(data).hexdigest(),
        'stockMainSha256':hashlib.sha256(args.stock_main.read_bytes()).hexdigest(),
        'emulatorSha256':hashlib.sha256(args.emulator.read_bytes()).hexdigest()}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('emulator','stock-main','package','symbols','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
