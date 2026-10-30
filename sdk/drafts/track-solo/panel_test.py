#!/usr/bin/env python3
"""Emulator-only package install, real UART panel events, UI ticks and removal.

Uses the real runtime backend, directly invoked as an emulator fixture. This
does not claim USB transport, review/trial/Keep/Undo or physical unit evidence.
Supply a private base MAIN and its matching symbol map, never another build's.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import math
import shutil
from emulator_test import Emulator

def check_scratch_fat16(image):
    """Catch dangling allocation links hidden by file-size-limited extraction."""
    part=struct.unpack_from('<I',image,454)[0]*512
    assert image[part+54:part+62]==b'FAT16   ', 'expected SDK FAT16 scratch card'
    reserved=struct.unpack_from('<H',image,part+14)[0]
    size=struct.unpack_from('<H',image,part+22)[0]*512
    at=part+reserved*512
    assert image[at:at+size]==image[at+size:at+2*size], 'FAT mirrors differ'
    fat=struct.unpack_from('<%dH'%(size//2),image,at)
    for cluster,link in enumerate(fat[2:],2):
        if link and link<0xfff8:
            assert 2<=link<len(fat) and fat[link]!=0, ('dangling FAT chain',cluster,link)

def reload_project(args, card_path, out):
    """Boot the named module-free firmware, never silently substitute a build."""
    reload_dir=out/'module-free-reload';reload_dir.mkdir()
    extra=['--card',card_path,'--mount','--set','SOLO','--project','TEST',
           '--load-ms','90000','--rtc','1793318400']
    if args.reload_dsp: extra += ['--dsp']
    stock=Emulator(args.emulator,args.reload_main,reload_dir,extra=extra)
    try:
        assert stock.project_loaded, 'module-free firmware did not complete project load'
        assert stock.read(0x80000ec4,16)==bytes(16), 'stock FX assignments changed on load'
        result={'result':'passed','mainSha256':hashlib.sha256(args.reload_main.read_bytes()).hexdigest(),
                'checks':['fresh named module-free firmware completes saved-project load',
                          'all sixteen FX assignments remain NONE'],
                'dspEnabled':args.reload_dsp}
        (reload_dir/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally: stock.close()

def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    symbols=json.loads(args.base_symbols.read_text())
    own=json.loads(args.symbols.read_text());data=args.package.read_bytes()
    # A missing card deliberately opens a stock modal. Supply an empty scratch
    # card so that the test can reach the ordinary track screen.
    card_script=Path(__file__).resolve().parents[2]/'octabam/tools/emu/emu_card.py'
    spec=importlib.util.spec_from_file_location('solo_emu_card',card_script)
    card=importlib.util.module_from_spec(spec);spec.loader.exec_module(card)
    tree=out/'card-tree';tree.mkdir()
    card_path=out/'card.private.img'
    extra=['--card',card_path]
    if args.fixture:
        shutil.copy2(args.fixture/'card.private.img',card_path)
        extra += ['--mount','--set','SOLO','--project','TEST','--load-ms','30000']
    else: card_path.write_bytes(card.build_image(str(tree),32))
    if args.audio: extra += ['--dsp','--frame']
    if args.persistence: extra += ['--card-rw','--rtc','1793318400']
    emu=Emulator(args.emulator,args.base_main,out,extra=extra)
    if args.fixture and not emu.project_loaded:
        emu.close()
        raise RuntimeError('The fixture project did not complete its actual firmware load')
    installed=False
    checks=[]
    def invoke(at,*v):
        # callAsMain is synthetic and only valid at main's spin. Let any
        # pending frame ISR finish first. Production uses the engine task.
        if args.audio: emu.command('frame off');advance(10)
        try:
            for attempt in range(100):
                try: return emu.call(at,*v)
                except RuntimeError as error:
                    # Emulator rejects this precondition before changing PC,
                    # stack or calling the target. Retry ONLY that rejection;
                    # never repeat a backend operation that actually ran.
                    if "not main's spin" not in str(error) or attempt==99: raise
                    advance(1)
        finally:
            if args.audio: emu.command('frame on');advance(10)
    def call(name,*v): return invoke(symbols[name],*v)
    def read32(at): return int.from_bytes(emu.read(at,4),'big')
    packet=0x47010000
    def install(content):
        for at in range(0,len(content),4096): emu.write(packet+at,content[at:at+4096])
        assert call('modwerk_backend_prepare',0,packet,len(content))==1, 'prepare refused'
        assert call('modwerk_backend_publish',0)==1, 'publish refused'
        assert call('modwerk_backend_retire',0)==1, 'retire refused'
    def advance(ms): emu.command('run '+str(ms))
    rows=[0]*8
    def key(code,down=True):
        row,bit=code>>3,1<<(code&7)
        rows[row]=(rows[row]|bit) if down else rows[row]&~bit
        emu.command(f'key {0x20|row} {rows[row]}')
        advance(40)
    def audio_levels():
        emu.command('audio start tracks');advance(100)
        reply=emu.command('audio read')
        fields=reply.split();frames=int(fields[1])
        samples=struct.unpack('<%dh'%(len(fields[2])//4),bytes.fromhex(fields[2]))
        assert frames>2000 and len(samples)==frames*24
        # Last 2048 frames exclude mute transitions and the DSP's gain ramps.
        samples=samples[-2048*24:]
        return [math.sqrt(sum(v*v for i,v in enumerate(samples) if i%24 in (8+2*t,9+2*t))/4096) for t in range(8)]
    def project_files():
        emu.command('card flush')
        image=card_path.read_bytes();check_scratch_fat16(image)
        files=card.extract_image(image)
        return {name:content for name,content in files.items()
                if name.upper().startswith('SOLO/TEST/') and name.endswith(('.work','.strd'))}
    def save_project():
        # Documented stock MKII SAVE PROJECT path. Reset the right-pane
        # cursor so the second save does not inherit the first save's row.
        for code in (0x1c,0x21,*([0x33]*8),0x20,0x31,0x31):
            key(code);key(code,False);advance(100)
        # SAVE PROJECT is asynchronous. A zero popup while its progress bar
        # is running is not completion. Wait for the engine queue's blocked
        # receiver and no pending messages, then let its DONE toast expire.
        for _ in range(300):
            advance(100)
            if read32(0x460d17d2)==0 and read32(0x460d17da)!=0: break
        else: raise AssertionError('SAVE PROJECT engine did not return idle')
        advance(3000)
        for _ in range(2): tap(0x32)
        wait_clear_screen()
    def tap(code): key(code);key(code,False);advance(100)
    def wait_clear_screen():
        # NO on the track screen opens stock's DISARM ALL toast. Its popup
        # legitimately owns the screen briefly; don't test arming under it.
        # First drain queued UI events; a zero handle sampled before the
        # final NO release is dispatched is not yet a quiet track screen.
        advance(2000)
        for _ in range(30):
            if not read32(0x460d175c): return
            advance(100)
        raise AssertionError('A stock popup still owns the screen')
    panel=None
    def screenshot(name):
        nonlocal panel
        if not args.panel_decoder: return
        if panel is None:
            spec=importlib.util.spec_from_file_location('solo_panel',args.panel_decoder)
            decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
            panel=decoder.PanelLink()
        panel.feed(bytes.fromhex(emu.command('tx').split()[1]))
        (out/(name+'.png')).write_bytes(panel.render_png(scale=4,dark=24,light=240))
    try:
        before=emu.read(0x40004dcc,6)
        install(data);installed=True
        for _ in range(3): key(0x32);key(0x32,False)
        # The live module record's first hook is ts_tick. Derive its actual
        # installed address instead of assuming an arena placement.
        record=call('modwerk_runtime_module',0)
        assert record
        base=read32(record+8)-own['ts_tick']
        assert 0x40000000<=base<0x50000000
        def overlay(): return read32(base+own['ts_overlay'])
        def gesture_state():
            state=emu.read(base+own['ts'],24)
            return {'enabled':state[18],'held':state[19],'anchor':state[21],'blocked':state[22],
                    'elapsed':int.from_bytes(state[16:18],'big'),
                    'other':list(struct.unpack('>II',state[4:12])),
                    'physicalRows':list(emu.read(0x46100b18,8)),
                    'popup':hex(read32(0x460d175c)),
                    'midiModeWord':read32(0x80000012)}
        def enabled(on): invoke(base+own['ts_set'],int(on)*2-1,0);advance(50)
        assert overlay()==0
        key(0x11);advance(2200);assert overlay()==0;key(0x11,False)
        checks.append('OFF preserves an actual long TRACK press')
        if args.persistence:
            save_project()
            saved_baseline=project_files()
            assert any(n.endswith('project.strd') for n in saved_baseline), 'no stored project'
            (out/'baseline-card.private.img').write_bytes(card_path.read_bytes())
            checks.append('actual stock SAVE PROJECT establishes a saved baseline')
        if args.menu:
            # PROJECT > CONTROL > SEQUENCER, then its fourth row.
            for code in (0x1c,0x20,0x20,0x21,0x20,0x20,0x31,0x20,0x20,0x20): tap(code)
            screenshot('track-solo-off')
            tap(0x31)
            screenshot('track-solo-hold')
            assert read32(symbols['modwerk_runtime_api']) & 0x10000, 'stock menu did not enable HOLD'
            for _ in range(2): tap(0x32)
            wait_clear_screen()
            checks.append('stock SEQUENCER row renders OFF/HOLD and enables through its actual YES handler')
        else: enabled(True)
        if args.audio:
            key(0x28);key(0x28,False);advance(300)
            baseline_audio=audio_levels()
            assert all(v>10 for v in baseline_audio),baseline_audio
            print('DSP audio baseline: all eight generated tones present',flush=True)
            checks.append('eight generated tones play through both DSP cores before solo')
        baseline=emu.read(0x80000008,4)
        screenshot('before-arming')
        emu.command(f"watchmem {base+own['ts']+21:#x} 2")
        arming_trace=[gesture_state()]
        key(0x11);arming_trace.append(gesture_state())
        for _ in range(36):
            advance(50)
            if gesture_state()['anchor']==8:
                screenshot('arming-cancelled')
                raise AssertionError(('arming cancelled',gesture_state(),emu.command('writes')))
        assert overlay()==0
        arming_trace.append(gesture_state())
        advance(300)
        if overlay()!=2:
            raise AssertionError(('no solo after hold',arming_trace,gesture_state(),emu.command('writes')))
        selected=emu.read(0x80000000,1)
        assert emu.read(0x80000008,4)==baseline
        if args.audio:
            solo_audio=audio_levels()
            assert solo_audio[1]>10 and all(v<1 for t,v in enumerate(solo_audio) if t!=1),solo_audio
            print('DSP audio solo: T2 present, seven others silent',flush=True)
            checks.append('DSP stem capture: T2 audible, the other seven silent')
        checks.append('real UART T2 hold crosses threshold on the base UI tick')
        key(0x12);assert overlay()==6
        key(0x12,False);assert overlay()==6
        if args.audio:
            group_audio=audio_levels()
            assert all(group_audio[t]>10 for t in (1,2)) and all(v<1 for t,v in enumerate(group_audio) if t not in (1,2)),group_audio
            print('DSP audio group: T2 and T3 present, six others silent',flush=True)
            checks.append('DSP stem capture: T2 and T3 audible, the other six silent')
        key(0x12);assert overlay()==2
        key(0x12,False)
        assert emu.read(0x80000000,1)==selected, 'joining a track must not select it'
        checks.append('real T3 presses toggle membership without changing active track')
        for t in (0,2,3,4,5,6,7): key(0x10+t);key(0x10+t,False)
        assert overlay()==255
        key(0x11,False);assert overlay()==0
        assert emu.read(0x80000008,4)==baseline
        if args.audio:
            restored_audio=audio_levels()
            assert all(v>10 for v in restored_audio),restored_audio
            print('DSP audio release: all eight generated tones return',flush=True)
            checks.append('DSP stem capture: all eight tones return after release')
        checks.append('all eight audio tracks join; anchor release restores underlying state')
        if args.audio:
            # Test-only synthetic underlying masks, observed through real DSP
            # stems. Production never writes this canonical word.
            original=int.from_bytes(baseline,'big')
            masked=(original&0xffff0000)|0x0201  # T1 solo; T2 muted
            emu.u32(0x80000008,masked);advance(100)
            levels=audio_levels()
            assert levels[0]>10 and all(v<1 for t,v in enumerate(levels) if t!=0),levels
            key(0x11);advance(2100);assert overlay()==2
            levels=audio_levels()
            assert levels[1]>10 and all(v<1 for t,v in enumerate(levels) if t!=1),levels
            assert read32(0x80000008)==masked
            key(0x11,False)
            levels=audio_levels()
            assert levels[0]>10 and all(v<1 for t,v in enumerate(levels) if t!=0),levels
            key(0x11);advance(2100);assert overlay()==2
            changed=(original&0xffff0000)|0x0104  # T3 solo; T1 muted
            emu.u32(0x80000008,changed);advance(100)
            levels=audio_levels()
            assert levels[1]>10 and all(v<1 for t,v in enumerate(levels) if t!=1),levels
            key(0x11,False)
            levels=audio_levels()
            assert levels[2]>10 and all(v<1 for t,v in enumerate(levels) if t!=2),levels
            assert read32(0x80000008)==changed
            emu.u32(0x80000008,original);advance(100)
            checks.append('DSP stems with synthetic underlying masks: muted anchor can solo; previous solo returns; changes made during hold survive release')
            print('DSP underlying-state cases: muted anchor, existing solo and mid-hold changes pass',flush=True)
        advance(50);key(0x11);advance(2100);assert overlay()==2
        key(0x2d);assert overlay()==0  # FUNC shortcut cancels
        key(0x2d,False);key(0x11,False)
        checks.append('FUNC cancels active solo and reaches stock')
        if args.audio:
            # Existing base contract: no active tracks or recorders when a
            # module set changes. A BUSY refusal during playback is correct.
            assert call('modwerk_machine_stopped')==0
            tap(0x27);tap(0x27);advance(200)
            assert call('modwerk_machine_stopped')==1
            checks.append('base requires idle tracks for package changes; two STOP presses satisfy that existing guard')
        if args.persistence:
            advance(50);key(0x11);advance(2100);assert overlay()==2
            save_project()  # original TRACK stays physically held throughout
            assert overlay()==0, 'opening PROJECT must cancel the performance overlay'
            key(0x11,False)
            saved_after=project_files()
            different=[n for n in saved_baseline if saved_baseline[n]!=saved_after.get(n)]
            assert not different, ('saved project changed',different)
            checks.append('SAVE PROJECT while anchor held leaves every work/stored project file byte-identical to baseline')
        advance(50);key(0x11);advance(2100);assert overlay()==2
        key(0x12);assert overlay()==6  # remove with a swallowed join also held
        # Actual removal with the anchor still physically held. The site and
        # canonical state must return without any module cleanup callback.
        ident=struct.unpack_from('>I',data,28)[0]
        remove=struct.pack('>4sHH6I',b'MWRM',4,0,0,0,0,0,0,ident)
        install(remove);installed=False
        assert emu.read(0x40004dcc,6)==before
        assert emu.read(0x80000008,4)==baseline
        key(0x12,False);key(0x11,False)
        checks.append('actual runtime removal while held restores the site and leaves mute/solo untouched')
    finally:
        # The whole emulator is disposable. No physical device is accessed.
        emu.close()
        (out/'panel-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    if args.persistence:
        reload=reload_project(args,card_path,out)
        checks.extend(reload['checks'])
    result={'result':'passed','checks':checks,'model':'MKII emulator',
        'packageSha256':hashlib.sha256(data).hexdigest(),
        'baseMainSha256':hashlib.sha256(args.base_main.read_bytes()).hexdigest(),
        'reloadMainSha256':reload['mainSha256'] if args.persistence else None,
        'limits':['direct backend calls, not USB transport or review/trial/Keep/Undo',
                  'no physical reboot qualification'] + ([] if args.persistence else ['no saved-project qualification']) + ([] if args.audio else ['no DSP audio qualification'])}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('emulator','base-main','base-symbols','package','symbols','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--fixture',type=Path)
    p.add_argument('--audio',action='store_true')
    p.add_argument('--persistence',action='store_true')
    p.add_argument('--reload-main',type=Path,help='Exact module-free firmware MAIN for fresh-boot reload')
    p.add_argument('--reload-dsp',action='store_true',help='Enable DSP emulation during the separate reload')
    p.add_argument('--menu',action='store_true')
    p.add_argument('--panel-decoder',type=Path)
    args=p.parse_args()
    if args.persistence and (not args.fixture or not args.reload_main or args.audio):
        p.error('--persistence needs --fixture and --reload-main and is separate from --audio')
    run(args)
