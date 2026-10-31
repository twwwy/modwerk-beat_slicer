#!/usr/bin/env python3
"""Historical 0.1.x scenario; use ux_test.py for revised 0.2.0 UX.

Broader private Track Solo emulator checks; never connects to hardware.

No native module/base changes. Ordinary stock solo is the audio control.
Routing flags and mode settings are explicitly synthetic test inputs; notes,
CCs, program changes and buttons use the emulator's real UART inputs.
"""
import argparse,hashlib,json,math,shutil,struct
from pathlib import Path
from emulator_test import Emulator,assert_frame_progress

class FixtureError(AssertionError):pass

class LoggedEmulator(Emulator):
 def __init__(self,binary,image,out,extra=()):
  self.commands=(out/'commands.private.log').open('w')
  super().__init__(binary,image,out,extra)
 def command(self,value):
  self.commands.write(value+'\n');self.commands.flush()
  return super().command(value)
 def close(self):
  try:super().close()
  finally:self.commands.close()

def run(a):
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 card=out/'card.private.img';shutil.copy2(a.fixture/'card.private.img',card)
 base_sym=json.loads(a.base_symbols.read_text());own=json.loads(a.symbols.read_text());pkg=a.package.read_bytes()
 extra=['--card',card,'--mount','--set','SOLO','--project','TEST','--load-ms','30000','--rtc','1793318400','--dsp','--frame','--audio-in','tones','--audio-in-from-boot']
 e=LoggedEmulator(a.emulator,a.base_main,out,extra=extra);rows=[0]*8;observations=[];module_base=None;companion=False;arg_bytes=0;fatal=None
 def record(category,name,status,**detail):
  row=dict(category=category,case=name,status=status,**detail);observations.append(row)
  (out/'observations.json').write_text(json.dumps(observations,indent=2)+'\n');print(json.dumps(row),flush=True)
 def advance(ms):
  r=e.command('run '+str(ms))
  if 'stop=time' not in r:raise RuntimeError(('emulator did not continue',r))
 def read32(at):return int.from_bytes(e.read(at,4),'big')
 def read16(at):return int.from_bytes(e.read(at,2),'big')
 def task_window():
  for _ in range(3000):
   if read32(0x46104d4e)==0:return
   advance(.01)
  raise RuntimeError('no task window outside frame')
 def canonical(value=None):
  task_window()
  if value is not None:e.u32(0x80000008,value)
  return read32(0x80000008)
 def invoke(at,*args):
  nonlocal arg_bytes
  e.command('frame off');advance(10)
  try:
   for n in range(100):
    try:
     value=e.call(at,*args);arg_bytes+=4*len(args);return value
    except RuntimeError as err:
     if "not main's spin" not in str(err) or n==99:raise
     advance(1)
  finally:e.command('frame on');advance(10)
 def call(name,*args):return invoke(base_sym[name],*args)
 def install(data):
  for at in range(0,len(data),4096):e.write(0x47010000+at,data[at:at+4096])
  assert call('modwerk_backend_prepare',0,0x47010000,len(data))==1,'prepare refused'
  assert call('modwerk_backend_publish',0)==1,'publish refused'
  assert call('modwerk_backend_retire',0)==1,'retire refused'
 def key(code,on=True):
  row,bit=code>>3,1<<(code&7);rows[row]=rows[row]|bit if on else rows[row]&~bit
  e.command(f'key {0x20|row} {rows[row]}');advance(40)
 def tap(code):key(code);key(code,False);advance(100)
 def release():
  for row in range(8):
   for bit in range(8):
    if rows[row]&(1<<bit):key(row*8+bit,False)
 def enabled(on):invoke(module_base+own['ts_set'],1 if on else -1,0);advance(50)
 def overlay():return read32(module_base+own['ts_overlay'])
 def midi(*data):e.command('midi '+' '.join(f'{x:02x}' for x in data))
 def cc(track,number,value):midi(0xb0+track,number,value);advance(80)
 def pc(number,wait=2300):midi(0xc8,number);advance(wait)
 def audio(ms=500):
  e.command('audio start tracks');advance(ms);f=e.command('audio read').split();n=int(f[1]);samples=struct.unpack('<%dh'%(len(f[2])//4),bytes.fromhex(f[2]))
  assert n>1000 and len(samples)==n*24,(n,len(samples))
  def level(l,r):return round(math.sqrt(sum(v*v for i,v in enumerate(samples) if i%24 in (l,r))/(n*2)),3)
  return {'main':level(2,3),'cue':level(4,5),'tracks':[level(8+2*t,9+2*t) for t in range(8)],'frames':n}
 def mode(value=0):
  if companion:task_window();e.u32(0x800000dc,value)
 def reset(value=0):
  release();enabled(False);canonical(0);midi(0x82,84,0);tap(0x27);tap(0x27);advance(100);mode(value)
  canonical(0)
 def start(word=0,warm=300):canonical(word);tap(0x28);advance(warm)
 def arm(t=1,join=()):
  enabled(True);key(0x10+t);advance(2100)
  assert overlay()==1<<t,('hold did not arm',t,overlay(),{'state':e.read(module_base+own['ts'],24).hex(),'matrix':e.read(0x46100b18,8).hex(),'midiMode':read32(0x80000012),'popup':hex(read32(0x460d175c))})
  for j in join:key(0x10+j);key(0x10+j,False)
  assert overlay()==sum(1<<x for x in (t,*join))
 def expect_audio(control,actual):
  for label,cvals,avals in [('main',[control['main']],[actual['main']]),('cue',[control['cue']],[actual['cue']]),('tracks',control['tracks'],actual['tracks'])]:
   for i,(c,v) in enumerate(zip(cvals,avals)):
    if c<1:assert v<3,(label,i,'expected silence',c,v)
    elif c>8:assert v>3 and .60<c/v<1.67,(label,i,'stock/held solo differs',c,v)
 def compare(t,word=0,join=(),warm=300):
  def prepare_input():
   if a.profile=='machines' and t==6:
    tap(0x16);tap(0x2b);advance(2200);tap(0x2c);advance(200)
   if a.profile=='machines' and t==7:
    for number,value in [(16,1),(17,127),(23,127),(24,127)]:cc(7,number,value)
    advance(200)
  reset();start(word,warm);prepare_input();pre=audio();mask=sum(1<<x for x in (t,*join))
  if a.profile!='master' and pre['tracks'][t]<3:raise FixtureError(('stock fixture track is silent',t+1,pre))
  canonical((word&0xffff0000)|mask);advance(150);control=audio()
  reset();start(word,warm);prepare_input();arm(t,join);advance(150);actual=audio()
  assert canonical()==word,('underlying state changed',canonical(),word)
  expect_audio(control,actual);key(0x10+t,False);assert overlay()==0
  assert canonical()==word
  return {'control':control,'heldSolo':actual,'underlyingPreserved':True}
 def case(category,name,fn):
  if getattr(a,'categories',None) and category not in a.categories:return
  if getattr(a,'cases',None) and name not in a.cases:return
  try:detail=fn() or {};record(category,name,'passed',**detail)
  except FixtureError as err:record(category,name,'fixture-inconclusive',error=repr(err))
  except AssertionError as err:record(category,name,'failed',error=repr(err))
  finally:
   release();enabled(False)
   if read32(0x80000012):tap(0x35)
   popup=read32(0x460d175c)
   if 0x46000000<=popup<0x47000000 and not popup&1 and read32(popup+32)&0x20:
    tap(0x32);tap(0x32);advance(2100)
 def routing(studio,cue_mutes):
  reset();task_window();e.write(0x80000037,bytes([studio]));e.u32(0x8000009c,cue_mutes)
  for t in range(8):cc(t,47,100)
  result=compare(1,word=0x50000);result.update(studio=studio,cueMutesTrack=cue_mutes,syntheticRoutingFlags=True)
  return result
 def midi_cc():
  reset();task_window();e.write(0x80000037,b'\0');e.u32(0x8000009c,0);start();arm()
  cc(2,49,127);w1=canonical()
  if not w1&0x400:raise FixtureError(('mute CC did not reach stock',hex(w1)))
  cc(0,50,127);w2=canonical()
  if not w2&1:raise FixtureError(('solo CC did not reach stock',hex(w2)))
  cc(3,51,127);w3=canonical()
  if not w3&0x80000:raise FixtureError(('cue CC did not reach stock',hex(w3)))
  assert overlay()==2;active=audio(150);key(0x11,False);assert overlay()==0 and canonical()==w3
  return {'canonicalWords':[hex(x) for x in (w1,w2,w3)],'overlayDuringEdits':2,'releasedWord':hex(canonical()),'activeAudio':active}
 def transitions():
  reset();start();arm();changes=[]
  for number in (1,2,16):
   pc(number)
   seq=e.read(0x800065bd,2)
   for _ in range(400):
    if tuple(seq)==(number//16,number%16):break
    advance(50);seq=e.read(0x800065bd,2)
   bank,pattern=e.read(0x80000002,1)[0],e.read(0x80000004,1)[0]
   if (bank,pattern)!=(number//16,number%16) or tuple(seq)!=(number//16,number%16):raise FixtureError(('MIDI program change did not land',number,bank,pattern,list(seq)))
   assert overlay()==2,('automatic transition cancelled or changed solo',number,overlay())
   engine=e.read(0x80001828,2)
   if tuple(engine)!=(bank,pattern%4):raise FixtureError(('expected Part did not reach engine',number,list(engine)))
   changes.append({'bank':bank,'pattern':pattern,'sequencerBankPattern':list(seq),'engineBankPart':list(engine),'overlay':overlay(),'fx':e.read(0x80000ec4,16).hex()})
  word=canonical();key(0x11,False);assert overlay()==0 and canonical()==word
  return {'changes':changes,'releasePreservesCurrentWord':True}
 def contexts():
  reset();pc(0);start();results=[]
  for name,code in [('MIDI',0x35),('PART',0x1d),('PATTERN',0x2e),('BANK',0x2f),('RECORD',0x29),('STOP',0x27)]:
   reset();start()
   before={'midiMode':read32(0x80000012),'popup':hex(read32(0x460d175c))}
   popup=int(before['popup'],16)
   before['popupFlags']=read32(popup+32) if 0x46000000<=popup<0x47000000 and not popup&1 else 0
   if before['midiMode'] or before['popupFlags']&0x20:raise FixtureError(('invalid context before arming',name,before))
   try:arm()
   except AssertionError as error:raise AssertionError(('hold failed in valid context',name,before,str(error)))
   key(code);assert overlay()==0,(name,overlay());key(code,False);key(0x11,False)
   after_action=read32(0x80000012);midi_cleanup=name=='MIDI' and bool(after_action)
   if midi_cleanup:tap(0x35)
   if name in ('PART','PATTERN','BANK'):
    tap(0x32);tap(0x32);advance(2100)
   if name=='RECORD':tap(0x29)
   results.append({'context':name,'midiModeAfterAction':after_action,'midiCleanupTap':midi_cleanup,'midiModeAfterCleanup':read32(0x80000012)})
  return {'cancellationContexts':results}
 def clock_test():
  reset();pc(0);start();enabled(True);task_window();old=e.read(0x80000028,1)[0];e.write(0x80000028,bytes([old|1]));key(0x11)
  try:
   for _ in range(60):midi(0xf8);advance(1000/48)
   assert overlay()==0,'hold activated before two seconds at MIDI clock'
   for _ in range(60):midi(0xf8);advance(1000/48)
   assert overlay()==2,('hold did not arm under MIDI clock',overlay())
   before=read32(0x8000181c)
   for _ in range(48):midi(0xf8);advance(1000/96)
   assert overlay()==2;key(0x11,False);assert overlay()==0
   return {'clockPulses':168,'clockRatesBpm':[120,240],'observedTempo24':[before,read32(0x8000181c)],'clockByteSyntheticEnable':True}
  finally:task_window();e.write(0x80000028,bytes([old]));release()
 def stress():
  reset();pc(2);start();enabled(True);max_group=0
  reference=(a.fixture/'project/bank01.work').read_bytes();expected=reference[0x8eed6+2*0x18bb+0x11:0x8eed6+2*0x18bb+0x19]
  actual=e.read(0x80000ec4+8,8)
  if actual!=expected:raise FixtureError(('FX stress Part did not reach every track',expected.hex(),actual.hex()))
  pattern=0x400e21e0+2*36568
  scales=[e.read(pattern+t*2330+0x51,1)[0] for t in range(8)]
  swing=[e.read(pattern+t*2330+0x52,1)[0] for t in range(8)]
  if set(scales)!=set(range(7)) or swing!=[20]*8:raise FixtureError(('speed/swing fixture not active',scales,swing))
  for anchor in range(8):
   key(0x10+anchor);advance(2100);assert overlay()==1<<anchor,(anchor,overlay())
   for t in range(8):
    if t!=anchor:key(0x10+t);key(0x10+t,False)
   assert overlay()==255;max_group=255;key(0x10+anchor,False);assert overlay()==0
   advance(50)
  for i in range(24):
   t=i%8;key(0x10+t);advance(50);key(0x10+t,False);assert overlay()==0
  advance(20000);assert canonical()==0 and overlay()==0
  return {'anchorsTested':8,'largestGroup':max_group,'shortHolds':24,'additionalSteadyRunMs':20000,'pattern':2,'effects':'eight stock delays in Part 3','scales':scales,'swingRaw':swing,'scope':'bounded emulator stress, no hardware CPU/timing qualification'}
 def midi_note_test(value):
  reset(value);pc(15);tap(0x27);tap(0x27);tap(0x11);advance(100)
  canonical(6);e.command('audio start tracks');midi(0x92,84,100);advance(300)
  f=e.command('audio read').split();n=int(f[1]);data=struct.unpack('<%dh'%(len(f[2])//4),bytes.fromhex(f[2]));control=math.sqrt(sum(v*v for i,v in enumerate(data) if i%24 in (12,13))/(n*2))
  if control<10:raise FixtureError(('ordinary-solo MIDI control is silent',value,control))
  reset(value);pc(15);tap(0x27);tap(0x27);canonical(0x400);arm(1,(2,));e.command('audio start tracks');midi(0x92,84,100);advance(300)
  f=e.command('audio read').split();n=int(f[1]);data=struct.unpack('<%dh'%(len(f[2])//4),bytes.fromhex(f[2]));held=math.sqrt(sum(v*v for i,v in enumerate(data) if i%24 in (12,13))/(n*2))
  word=canonical();key(0x11,False);assert word==0x400 and canonical()==0x400
  assert held>10,('joined, previously muted track cannot start from external MIDI',value,control,held)
  return {'muteMode':value,'stockSoloT3Rms':round(control,3),'heldSoloT3Rms':round(held,3),'realMidiBytes':True,'sequencerPatternSilent':True}
 try:
  if not e.project_loaded:raise FixtureError('project did not finish loading')
  install(pkg);rec=call('modwerk_runtime_module',0);module_base=read32(rec+8)-own['ts_tick']
  for _ in range(3):tap(0x32)
  advance(2100)
  print(json.dumps({'stage':'booted','profile':a.profile,'packageSha256':hashlib.sha256(pkg).hexdigest()}),flush=True)
  if a.profile=='control':
   for studio in (0,1):
    for cue_mutes in (0,1):case('routing',f'studio-{studio}-cue-mutes-{cue_mutes}',lambda s=studio,c=cue_mutes:routing(s,c))
   case('MIDI','mute-solo-cue-CC-during-hold',midi_cc)
   case('transitions','automatic-pattern-Part-bank',transitions)
   case('transitions','panel-context-cancellation',contexts)
   case('MIDI','external-clock-tempo-change',clock_test)
   case('stress','eight-anchors-full-groups-and-repeated-holds',stress)
   if a.mute_package:
    reset();assert call('modwerk_machine_stopped')==1;install(a.mute_package.read_bytes());companion=True
    for name,value in [('OT',0),('OTFX',3),('OTFX-T',1),('DT-T',2)]:case('MIDI','external-note-cold-joined-'+name,lambda v=value:midi_note_test(v))
  elif a.profile=='machines':
   for track,name in [(1,'Static'),(2,'short-one-shot'),(3,'retrigger'),(4,'recorder-buffer'),(5,'Neighbor'),(6,'Pickup'),(7,'Thru')]:
    case('machines',name,lambda t=track:compare(t,warm=2500))
  elif a.profile=='master':
   if e.read(0x80000034,1)!=b'\x01':raise FixtureError('MASTER_TRACK not enabled by project load')
   for t in (0,1,7):case('machines',f'T8-Master-anchor-T{t+1}',lambda t=t:compare(t))
   def master_group(t,join):
    result=compare(t,join=join)
    if result['control']['main']<3:raise FixtureError(('master group control is silent',t,join,result))
    assert result['heldSolo']['main']>3,('held master group is silent',t,join,result)
    return result
   for t,join in ((0,(7,)),(1,(7,)),(7,(0,))):
    name=f'T8-Master-group-anchor-T{t+1}-join-T{join[0]+1}'
    case('machines',name,lambda t=t,j=join:master_group(t,j))
 except Exception as err:fatal=repr(err);record('harness','fatal','failed',error=fatal)
 finally:
  e.close()
  try:frame_observations=assert_frame_progress(out/'emulator.private.log')
  except Exception as err:frame_observations=None;record('liveness','frame-progress','failed',error=repr(err))
  failed=[r for r in observations if r['status']=='failed'];incomplete=[r for r in observations if r['status']=='fixture-inconclusive']
  report={'result':'failed' if failed else 'partial' if incomplete else 'passed','profile':a.profile,'observations':observations,'fatal':fatal,'frameProgressObservations':frame_observations,'packageSha256':hashlib.sha256(pkg).hexdigest(),'baseMainSha256':hashlib.sha256(a.base_main.read_bytes()).hexdigest(),'fixtureSha256':hashlib.sha256((a.fixture/'card.private.img').read_bytes()).hexdigest(),'hardwareTested':False,'syntheticCallArgumentBytes':arg_bytes,'limits':['existing save regression remains unresolved','read-only backing card; no SAVE PROJECT qualification','synthetic routing/mode inputs; actual UART gestures/MIDI and DSP audio','periodic frame liveness is not glitch-free or hardware CPU qualification']}
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'stage':'complete','profile':a.profile,'result':report['result'],'failed':len(failed),'inconclusive':len(incomplete)}),flush=True)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('emulator','base-main','base-symbols','package','symbols','fixture','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--profile',choices=['control','machines','master'],required=True);p.add_argument('--mute-package',type=Path)
 p.add_argument('--categories',nargs='+',choices=['routing','MIDI','transitions','stress','machines'])
 p.add_argument('--cases',nargs='+',help='Run only these exact case names for a targeted repeat')
 report=run(p.parse_args())
 raise SystemExit(0 if report['result']=='passed' else 1)
