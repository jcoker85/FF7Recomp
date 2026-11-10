#!/usr/bin/env python3
"""Write games/ff7/aot/overlays.json from your own Disc 1 (facts only).

The profile tells psxrecomp's AOT pipeline which disc files FF7 runs as code,
how its loader unpacks them and where it puts them. Everything here is read
from SCUS_941.63's loader code and asserted against the disc; the profile pins
each fact with a `words` check or a hash, so the pipeline refuses any disc
these facts do not describe. It holds addresses, sizes and hashes, no game
bytes.

Usage (from the repository root):
  python tools/make_aot_profile.py "games/ff7/disc/Final Fantasy VII - Disc 1.cue"

Loader facts (SCUS_941.63, USA):
  0x80048D24  module table {lba, size}; modules are read to 0x80180000 and
              unpacked to 0x800A0000 by 0x80015CA0 (header {decoded size, zeroed
              tail size}, then a gzip member), or read raw to 0x800A0000
  0x80048F60  menu table {lba, size}; 0x800211C4 reads entry N to *(gp+168),
              which the EXE initialises to 0x801D0000
"""
import sys,struct,hashlib,json,zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
fw = str(ROOT / 'psxrecomp' / 'tools')
cue = sys.argv[1]
out = str(ROOT / 'games' / 'ff7' / 'aot' / 'overlays.json')
sys.path.insert(0, fw)
from aot_overlay_pipeline import Disc, digest
d=Disc(cue)
EXE='SCUS_941.63'; exe=d.read(EXE); EB=0x80010000-0x800
W=lambda a: struct.unpack_from('<I',exe,a-EB)[0]
sha=lambda b: hashlib.sha256(b).hexdigest()
def span(lo,hi): return {hex(a): hex(W(a)) for a in range(lo,hi+4,4)}

checks=[]; prepared=[]; images=[]
bylba_all={lba:n for n,(lba,s) in d.files.items()}
DATA_TAILS={'MINI/SNOBO.BIN':0x800BFD74, 'MAGIC/BERSERK.BIN':0x801B0858,
  'MAGIC/PHOENIX.BIN':0x801B48FC, 'MAGIC/SPARK.BIN':0x801B228C, 'MAGIC/S_BEAM.BIN':0x801B2308,
  'MAGIC/LAMU.BIN':0x801B3A9C}
def exe_words(values, why):
    checks.append(dict(method='words', file=EXE, base=hex(EB), values=values, reason=why))

def gzip_image(name):
    """A gzip-packed module as the gunzip routine 0x80015CA0 leaves it in RAM."""
    raw=d.read(name)
    usize,bss=struct.unpack_from('<II',raw)
    inf=zlib.decompressobj(31); body=inf.decompress(raw[8:]); assert inf.eof and len(body)==usize
    consumed=len(raw)-8-len(inf.unused_data)
    pname='PREPARED/'+name
    spec=dict(name=pname, method='gzip_member', source=dict(file=name, file_offset='0x8'),
        consumed=hex(consumed), source_sha256=sha(raw[8:8+consumed]))
    if struct.unpack_from('<I',body,len(body)-4)[0]==0x03E00008:
        # The image ends on `jr $ra`: its delay slot is the first word of the
        # tail the gunzip routine zero-fills (bss, pinned below).
        assert bss>=4; spec['zero_tail']='0x4'; body+=bytes(4)
    spec.update(size=hex(len(body)), sha256=sha(body))
    prepared.append(spec)
    checks.append(dict(method='words', file=name, values={'0x0':hex(usize),'0x4':hex(bss)},
        reason=f'{name}: header the gunzip routine 0x80015CA0 reads (decoded size, zero-filled tail)'))
    return pname, body

def exclude_data_tail(image, name, body, B):
    """Images whose data after .text holds words that decode as a prologue.

    .text ends at the image's last `jr $ra` plus its delay slot; the rest stays
    interpreted (a fallback, never a native producer)."""
    if name not in DATA_TAILS:
        return
    jr=[o for o in range(0,len(body),4) if struct.unpack_from('<I',body,o)[0]==0x03E00008]
    start=B+jr[-1]+8
    assert start==DATA_TAILS[name], (name, hex(start))
    image['excluded_ranges']=[dict(start=hex(start), end=hex(B+len(body)), sha256=sha(body[start-B:]),
        reason='Data after the last function (its final jr $ra + delay slot ends .text); '
               'a word there decodes as a stack-frame prologue')]

# ---- module slot 0x800A0000: table {lba,size} at 0x80048D24 -------------
TABLE=0x80048D24
modules = {  # index: (file, gzip?, [(site_lo, site_hi_incl_entry_jal)], entries)
 0:('FIELD/FIELD.BIN',True,[(0x800118B4,0x8001190C)],[0x800A16CC,0x800CF60C]),
 1:('WORLD/WORLD.BIN',True,[(0x8001132C,0x8001135C)],[]),
 2:('MINI/CONDOR.BIN',True,[(0x80012618,0x80012650)],[0x800B6B58]),
 3:('MINI/SNOBO.BIN',True,[(0x80012590,0x800125C8)],[0x800A0390]),
 4:('MINI/SNOBO2.BIN',True,[(0x800125D4,0x8001260C)],[0x800A0448]),
 5:('FIELD/DSCHANGE.X',False,[(0x80011DDC,0x80011E00),(0x8001277C,0x8001279C)],[0x800A0000,0x800A0C58]),
 6:('FIELD/ENDING.X',False,[(0x80011CB8,0x80011CEC),(0x80011D24,0x80011D44)],[0x800A0030,0x800A04C4]),
 7:('MINI/CHOCOBO.BIN',True,[(0x8001254C,0x80012584)],[0x800A02D0]),
 8:('MINI/JET.BIN',True,[(0x8001265C,0x80012694)],[0x800A0450]),
 9:('MINI/SUBMAR.BIN',True,[(0x800126BC,0x80012700)],[0x800A00BC]),
 10:('MINI/HIGHWAY.BIN',True,[(0x80012508,0x80012540)],[0x800A00D0]),
}
# WORLD's entry: the world path continues after the gunzip at 0x80011358.
modules[1][3].append(0x800A460C)
modules[1][2].append((0x800113E0,0x80011400))
for i,(name,gz,sites,entries) in modules.items():
    lba,size=d.files[name]
    a=TABLE+8*i
    assert (W(a),W(a+4))==(lba,size), name
    vals={hex(a):hex(lba), hex(a+4):hex(size)}
    for lo,hi in sites: vals.update(span(lo,hi))
    for e in entries:
        assert any(int(v,16)==(0x0C000000|((e&0x0FFFFFFF)>>2)) for v in vals.values()), (name,hex(e))
    exe_words(vals, f'{name}: loader table entry {i} and its load/call sequence')
    src,body=(gzip_image(name) if gz else (name,d.read(name)))
    image=dict(method='fixed_address_files', files=[src], load_addr='0x800A0000',
        allow_missing=True, entries=[hex(e) for e in sorted(entries)])
    exclude_data_tail(image, name, body, 0x800A0000)
    images.append(image)

# gunzip routine contract: header words, inflate from src+8 into a1, zero bss.
exe_words(span(0x80015CA0,0x80015CF4), 'gunzip 0x80015CA0: size/bss header, inflate src+8 -> dst, zero tail')

# ---- menu slot: loader 0x800211C4 reads table 0x80048F60 into *(gp+168) ----
exe_words({**span(0x800211B8,0x800211F0), '0x80011140':hex(W(0x80011140)), '0x80011144':hex(W(0x80011144)),
           '0x80062dec': hex(W(0x80062DEC))},
          'menu loader: gp=0x80062D44, destination word gp+168 initialised to 0x801D0000')
assert W(0x80062DEC)==0x801D0000
MT=0x80048F60
menu_sites={13:[(0x80024D98,0x80024DB8)],14:[(0x80024DE4,0x80024DFC)],15:[(0x80024E28,0x80024E40)],
  16:[(0x80024E64,0x80024E7C)],10:[(0x80024E9C,0x80024EB4)],
  1:[(0x80024ED4,0x80024EEC),(0x80024F0C,0x80024F24),(0x80024F4C,0x80024F64),(0x80024F90,0x80024FA8),(0x80024FD4,0x80024FEC),(0x80025010,0x80025028)],
  12:[(0x800250BC,0x800250D4),(0x800250FC,0x80025114),(0x80025140,0x80025158)],7:[(0x800260A8,0x800260C0)]}
bylba={lba:n for n,(lba,s) in d.files.items()}
menus={}
for i in range(1,17):
    lba=W(MT+8*i); name=bylba[lba]; menus.setdefault(name,[]).append(i)
for name,idxs in sorted(menus.items()):
    vals={}; entries=[]
    for i in idxs:
        vals[hex(MT+8*i)]=hex(W(MT+8*i)); vals[hex(MT+8*i+4)]=hex(W(MT+8*i+4))
        for lo,hi in menu_sites.get(i,[]):
            vals.update(span(lo,hi)); w=W(hi); entries.append(0x80000000|((w&0x3ffffff)<<2))
    exe_words(vals, f'{name}: menu table indices {idxs} and their load/call sequences')
    images.append(dict(method='fixed_address_files', files=[name], load_addr='0x801D0000',
        allow_missing=True, entries=[hex(e) for e in sorted(set(entries))]))


# ---- battle: INIT/YAMADA.BIN is the battle file table ------------------------
# 0x80014610 reads LBA 0x266 (YAMADA.BIN) and copies its 0x50 bytes over the
# table at 0x80048D84. 0x80014578(index, dst, cb) reads entry N to dst;
# 0x80014658(index, entry) reads it to 0x801B0000, gunzips it to 0x800A0000 and
# calls entry.
YT=0x80048D84
assert d.files['INIT/YAMADA.BIN'][0]==0x266
yam=d.read('INIT/YAMADA.BIN')
YW=lambda i: struct.unpack_from('<II',yam,8*i)
exe_words({**span(0x80014578,0x800145A8), **span(0x80014610,0x80014644), **span(0x80014658,0x8001468C)},
          'battle file table: YAMADA.BIN (LBA 0x266) copied to 0x80048D84; reader 0x80014578; '
          'load/gunzip/call 0x80014658')
battle_calls={3:('BATTLE/BROM.X',(0x800146F0,0x800146FC),0x800A00CC),
              5:('BATTLE/BATTLE.X',(0x80014710,0x8001471C),0x800A1158)}
for i,(name,(lo,hi),entry) in battle_calls.items():
    assert YW(i)==d.files[name] or (YW(i)[0]==d.files[name][0] and YW(i)[1]==d.files[name][1]), name
    assert W(lo)==0x3C05800A and (W(lo+4)&0xFFFF0000)==0x24A50000 and 0x800A0000+(W(lo+4)&0xFFFF)==entry
    exe_words(span(lo,hi), f'{name}: 0x80014658(index {i}, entry {entry:#x})')
    checks.append(dict(method='words', file='INIT/YAMADA.BIN', values={hex(8*i):hex(YW(i)[0]), hex(8*i+4):hex(YW(i)[1])},
        reason=f'{name}: battle file table entry {i} (LBA, size)'))
    src,body=gzip_image(name)
    images.append(dict(method='fixed_address_files', files=[src], load_addr='0x800A0000',
        allow_missing=True, entries=[hex(entry)]))
BX='PREPARED/BATTLE/BATTLE.X'
bx=[p for p in prepared if p['name']==BX][0]
bxbody=zlib.decompressobj(31).decompress(d.read('BATTLE/BATTLE.X')[8:])
BW=lambda a: struct.unpack_from('<I',bxbody,a-0x800A0000)[0]
bspan=lambda lo,hi: {hex(a): hex(BW(a)) for a in range(lo,hi+4,4)}
def battle_words(values, why):
    checks.append(dict(method='words', file=BX, base='0x800A0000', values=values, reason=why))
# BATTLE.X loads BATINI (6) and BATRES (8) to 0x801C0000, gunzips them to
# 0x801B0000 and calls them.
batini=bspan(0x800A1214,0x800A1274); batres=bspan(0x800A16FC,0x800A1730)
battle_words(batini, 'BATTLE.X: BATINI.X (index 6) -> 0x801C0000, gunzip to 0x801B0000, jalr 0x801B0490 / 0x801B0050')
battle_words(batres, 'BATTLE.X: BATRES.X (index 8) -> 0x801C0000, gunzip to 0x801B0000, jal 0x801B0000')
for i,name,entries in ((6,'BATTLE/BATINI.X',[0x801B0050,0x801B0490]),(8,'BATTLE/BATRES.X',[0x801B0000])):
    assert YW(i)==d.files[name], name
    checks.append(dict(method='words', file='INIT/YAMADA.BIN', values={hex(8*i):hex(YW(i)[0]), hex(8*i+4):hex(YW(i)[1])},
        reason=f'{name}: battle file table entry {i} (LBA, size)'))
    src,body=gzip_image(name)
    images.append(dict(method='fixed_address_files', files=[src], load_addr='0x801B0000',
        allow_missing=True, entries=[hex(e) for e in entries]))
# Battle effects: BATTLE.X's table at 0x800EEBB8 holds {LBA, sector-rounded
# size}; 0x800D14E0.. reads entry N and calls 0x800D088C, which reads it raw to
# 0x801B0000. The .BIN members are code; the .LZS members are packed data.
MTAB=0x800EEBB8
battle_words({**bspan(0x800D088C,0x800D08B4), **bspan(0x800D14E0,0x800D151C)},
             'BATTLE.X: effect loader 0x800D088C reads table 0x800EEBB8 entry raw to 0x801B0000')
lzs=[]
for i in range(318):
    lba,size=BW(MTAB+8*i),BW(MTAB+8*i+4); name=bylba_all[lba]
    assert d.files[name][0]==lba and (d.files[name][1]+2047)//2048*2048==size, name
    if name.endswith('.LZS'): lzs.append(name); continue
    battle_words({hex(MTAB+8*i):hex(lba), hex(MTAB+8*i+4):hex(size)}, f'{name}: effect table entry {i}')
    image=dict(method='fixed_address_files', files=[name], load_addr='0x801B0000', allow_missing=True, entries=[])
    exclude_data_tail(image, name, d.read(name), 0x801B0000)
    images.append(image)
profile=dict(schema='psxrecomp AOT methods v1', game_id='SCUS-94163',
  disc_hashes={'sha256': digest(d.binary)},
  static_output='generated/overlays_static.c',
  strict_bounds=True,
  generic_exclude_files=[dict(files=sorted(lzs), reason='LZSS-packed effect data (textures, models); '
     'the battle effect code unpacks it, nothing runs it')],
  prepared_files=prepared, checks=checks, images=images, expected_records=len(images))
open(out,'w',encoding='utf-8',newline='\n').write(json.dumps(profile, indent=1)+'\n')
print(len(images),'images',len(prepared),'prepared',len(checks),'checks')

# ---- Disc 3: the one code module Disc 1 does not carry -----------------------
# Effect table entry 318 is SNOVA/LASBOSS3.BIN (the final boss), only on Disc 3.
# Every other module on Disc 3 is byte-identical to Disc 1's, so the static
# shard above already serves it. aot/disc3.json builds just this one into an
# audited DLL cache (aot_overlay_pipeline.py release) that the runtime loads
# beside the static shard. Run with the Disc 3 cue as a second argument.
if len(sys.argv) > 2:
    d3=Disc(sys.argv[2]); out3=str(ROOT / 'games' / 'ff7' / 'aot' / 'disc3.json')
    BOOT='BOOT/SCUS_941'
    assert d3.read('SCUS_941.65')==exe and d3.read('BATTLE/BATTLE.X')==d.read('BATTLE/BATTLE.X') \
        and d3.read('INIT/YAMADA.BIN')==yam
    name='SNOVA/LASBOSS3.BIN'; i=318
    lba,size=BW(MTAB+8*i),BW(MTAB+8*i+4)
    assert d3.files[name][0]==lba and (d3.files[name][1]+2047)//2048*2048==size
    keep=lambda c: (c.get('file')=='SCUS_941.63' and any(k in c['reason'] for k in ('battle file table','BATTLE/BATTLE.X','gunzip')))\
        or c.get('file') in (BX,'BATTLE/BATTLE.X') and ('effect' in c['reason'] or 'header' in c['reason'])\
        or (c.get('file')=='INIT/YAMADA.BIN' and 'BATTLE/BATTLE.X' in c['reason'])
    checks3=[]
    for c in checks:
        if keep(c) and not ('effect table entry' in c['reason']):
            checks3.append({**c, 'file': BOOT} if c['file']=='SCUS_941.63' else c)
    checks3.append(dict(method='words', file=BX, base='0x800A0000',
        values={hex(MTAB+8*i):hex(lba), hex(MTAB+8*i+4):hex(size)}, reason=f'{name}: effect table entry {i}'))
    body3=d3.read(name)
    image=dict(method='fixed_address_files', files=[name], load_addr='0x801B0000', allow_missing=True, entries=[])
    jr=[o for o in range(0,len(body3),4) if struct.unpack_from('<I',body3,o)[0]==0x03E00008]
    start=0x801B0000+jr[-1]+8
    image['excluded_ranges']=[dict(start=hex(start), end=hex(0x801B0000+len(body3)), sha256=sha(body3[start-0x801B0000:]),
        reason='Data after the last function (its final jr $ra + delay slot ends .text)')]
    # Only files the generic detector can take for code need excluding (the
    # full list overflows a Windows command line); it stops on anything else.
    others=sorted(n for n in d3.files if n!=name and n.split('/')[0] in ('MAGIC','MENU','MINI','BATTLE','WORLD','FIELD','SNOVA') and not n.startswith('FIELD/') or n.startswith('FIELD/') and n.endswith(('.X','.BIN')))
    profile3=dict(schema='psxrecomp AOT methods v1', game_id='SCUS-94163',
      disc_hashes={'sha256': digest(d3.binary)},
      file_aliases={BOOT: ['SCUS_941.63','SCUS_941.64','SCUS_941.65']},
      strict_bounds=True,
      generic_exclude_files=[dict(files=others, reason='Disc 3 copies of modules aot/overlays.json '
          'compiles from Disc 1 (byte-identical), and data')],
      prepared_files=[p for p in prepared if p['name']==BX], checks=checks3, images=[image], expected_records=1)
    open(out3,'w',encoding='utf-8',newline='\n').write(json.dumps(profile3, indent=1)+'\n')
    print('disc3:', len(checks3), 'checks; text ends', hex(start))
