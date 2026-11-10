#!/usr/bin/env python3
"""Look for MIPS code the AOT profile does not compile natively.

Static only; nothing is run. Two checks:

  discs    Every file on the given discs, every gzip stream embedded in one and
           every LZS file unpacked, scored for function shapes (a stack-frame
           prologue that saves $ra, and `jr $ra`). Code-shaped contents the
           profile does not cover are listed.
  modules  For each profile image, the bytes no compiled function covers
           (matched by the guard CRC of the function's own bytes, the way the
           runtime matches them) and not excluded on purpose, searched for
           function shapes.

Usage (from the repository root, after tools/generate.sh):
  python tools/check_aot_coverage.py discs   "<Disc 1.cue>" ["<Disc 2.cue>" ...]
  python tools/check_aot_coverage.py modules "<Disc 1.cue>"

A clean result does not prove every function runs natively: code reached only
through jumps the compiler cannot follow shows up only at runtime
(overlay_cache = true records it).
"""
import collections, hashlib, json, os, re, struct, sys, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'psxrecomp' / 'tools'))
from aot_overlay_pipeline import Disc
import prepared_files
PROFILE = ROOT / 'games' / 'ff7' / 'aot' / 'overlays.json'
DISPATCH = ROOT / 'games' / 'ff7' / 'generated' / 'overlays_static.c'

def check_discs(cues):
    prof=json.loads(PROFILE.read_text(encoding="utf-8"))

    def fns(b):
        """(function-shaped prologues, jr $ra count)."""
        n=len(b)//4; w=struct.unpack_from(f'<{n}I',b,0) if n else ()
        pro=0
        for i,x in enumerate(w):
            if x>>16==0x27BD and x&0x8000:
                for y in w[i+1:i+8]:
                    if y>>16==0xAFBF: pro+=1; break
        return pro, sum(1 for x in w if x==0x03E00008)

    def lzs(b):
        """FF7 LZS: u32 packed size, then Okumura LZSS (4K ring, start 0xFEE)."""
        size=struct.unpack_from('<I',b)[0]
        if size+4>len(b) or size<8 or size+4<len(b)-2048: return None
        ring=bytearray(4096); r=0xFEE; out=bytearray(); i=4; end=4+size
        try:
            while i<end:
                flags=b[i]; i+=1
                for bit in range(8):
                    if i>=end: break
                    if flags>>bit&1:
                        c=b[i]; i+=1; out.append(c); ring[r]=c; r=(r+1)&0xFFF
                    else:
                        o=b[i]|((b[i+1]&0xF0)<<4); l=(b[i+1]&0xF)+3; i+=2
                        for k in range(l):
                            c=ring[(o+k)&0xFFF]; out.append(c); ring[r]=c; r=(r+1)&0xFFF
                    if len(out)>8<<20: return None
        except IndexError: return None
        return bytes(out)

    def gz_members(b):
        out=[]; p=0
        while True:
            p=b.find(b'\x1f\x8b\x08',p)
            if p<0: break
            try:
                d=zlib.decompressobj(31); r=d.decompress(b[p:]);
                if d.eof and len(r)>=64: out.append((p,r)); p+=len(b[p:])-len(d.unused_data); continue
            except zlib.error: pass
            p+=1
        return out

    # What the profile already compiles: raw file bytes and decoded images.
    covered=set(); covered_names=set()
    d1=Disc(cues[0])
    for im in prof['images']:
        f=im['files'][0]; name=f.replace('PREPARED/','')
        covered_names.add(name)
        raw=d1.read(name); covered.add(hashlib.sha1(raw).hexdigest())
        if raw[8:10]==b'\x1f\x8b': covered.add(hashlib.sha1(zlib.decompressobj(31).decompress(raw[8:])).hexdigest())
    covered.add(hashlib.sha1(d1.read('SCUS_941.63')).hexdigest())

    seen={}; findings=[]
    for di,cue in enumerate(cues,1):
        d=Disc(cue)
        for name in sorted(d.files):
            raw=d.read(name)
            cands=[('raw',raw)]
            cands+= [(f'gzip@{p:#x}',r) for p,r in gz_members(raw)]
            if name.endswith('.LZS'):
                r=lzs(raw)
                if r: cands.append(('lzs',r))
            for how,b in cands:
                h=hashlib.sha1(b).hexdigest()
                if h in seen: seen[h][1].append(f'D{di}:{name}'); continue
                pro,jr=fns(b)
                seen[h]=[(name,how,len(b),pro,jr,h in covered),[f'D{di}:{name}']]
    rows=[v for v in seen.values() if v[0][4]>=1 and (v[0][3]>=1 or v[0][4]>=2)]
    print('distinct contents scanned:',len(seen))
    print('code-shaped contents:',len(rows))
    unc=[v for v in rows if not v[0][5]]
    print('...not covered by the profile:',len(unc))
    for (name,how,size,pro,jr,cov),where in sorted(unc,key=lambda v:-v[0][3]):
        print(f'  {name:28s} {how:12s} {size:8d}B prologues={pro:4d} jr_ra={jr:4d} on {",".join(sorted(set(w[:2] for w in where)))}')


def check_modules(cue):
    prof=json.loads(PROFILE.read_text(encoding="utf-8")); disp=DISPATCH.read_text(encoding="utf-8")
    d=prepared_files.prepare(Disc(cue), prof)
    ranges={m.group(1):[int(x,16) for x in re.findall(r'0x([0-9A-F]+)u',m.group(2))]
            for m in re.finditer(r'static const uint32_t (psx_ov_static_ranges_\d+)\[\] = \{([^}]*)\}',disp)}
    variants=[]
    for m in re.finditer(r'\{ (psx_ov_static_ranges_\d+), (\d+)u, 0x([0-9A-F]+)u, ov_',disp):
        r=ranges[m.group(1)]
        variants.append(([(r[i]|0x80000000,(r[i]|0x80000000)+r[i+1]) for i in range(0,len(r),2)], int(m.group(3),16)))
    def covered_by_bytes(body, base):
        out=[]
        for rr,crc in variants:
            if rr[0][0]<base or rr[-1][1]>base+len(body): continue
            c=0
            for lo,hi in rr: c=zlib.crc32(body[lo-base:hi-base],c)
            if c==crc: out+=rr
        return out
    W=lambda b,o: struct.unpack_from('<I',b,o)[0]
    tot_gap=0; rep=[]
    for im in prof['images']:
        name=im['files'][0]; base=int(im['load_addr'],16); body=d.read(name)
        iv=sorted(covered_by_bytes(body, base))
        excl=[(int(e['start'],16),int(e['end'],16)) for e in im.get('excluded_ranges',[])]
        # merge covered + excluded
        mark=bytearray(len(body)//4)
        for lo,hi in iv+excl:
            for a in range(max(lo,base),min(hi,base+len(body)),4): mark[(a-base)//4]=1
        # gaps
        i=0; n=len(mark)
        while i<n:
            if mark[i]: i+=1; continue
            j=i
            while j<n and not mark[j]: j+=1
            seg=body[4*i:4*j]; ws=[W(seg,k) for k in range(0,len(seg),4)]
            pro=[k for k,x in enumerate(ws) if x>>16==0x27BD and x&0x8000 and any(y>>16==0xAFBF for y in ws[k+1:k+8])]
            jr=sum(1 for x in ws if x==0x03E00008)
            if pro and jr:
                rep.append((name,base+4*i,base+4*j,len(pro),jr,[hex(base+4*(i+k)) for k in pro[:6]]))
            tot_gap+=j-i; i=j
        if not iv: rep.append((name,base,base+len(body),-1,-1,['NO COMPILED FUNCTIONS']))
    print('modules',len(prof['images']),'suspect gaps',len(rep))
    for r in sorted(rep,key=lambda r:-r[3])[:60]: print(f'  {r[0]:34s} {r[1]:#x}-{r[2]:#x} prologues={r[3]} jr_ra={r[4]} at {r[5]}')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('discs', 'modules'):
        sys.exit(__doc__)
    check_discs(sys.argv[2:]) if sys.argv[1] == 'discs' else check_modules(sys.argv[2])
