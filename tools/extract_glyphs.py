#!/usr/bin/env python3
"""리디바탕에서 음절 글리프의 윤곽을 꺼내, '조립 조각'(모음 또는 초성의 획들)과 '연한 글자'(전체)를 SVG 경로로 저장.
출력: glyphs.json  { "아": {"upm":1000, "adv":..., "bbox":[x0,y0,x1,y1], "ghost":"M...", "pieces":[{"d":"M...","bbox":[...]}, ...]} }
좌표는 글꼴 단위, y는 위가 +. 페이지에서 뒤집어 그린다."""
import json, sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen

FONT = sys.argv[1] if len(sys.argv) > 1 else "fonts/RIDIBatang.otf"
SYLS = list("가고구기나노누니아오우이") + list("태루마빠엄")  # 쓰기 12 + 이름 음절
ONSETS=list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"); VOWELS=list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
def decompose(s):
    c=ord(s)-0xAC00; return ONSETS[c//588], VOWELS[(c%588)//28], c%28

f=TTFont(FONT); gs=f.getGlyphSet(); cmap=f.getBestCmap(); upm=f["head"].unitsPerEm
out={}
for syl in SYLS:
    gname=cmap.get(ord(syl))
    if not gname: continue
    g=gs[gname]
    rec=RecordingPen(); g.draw(rec)
    # 윤곽(contour) 단위로 자르기: moveTo ~ closePath
    contours=[]; cur=[]
    for op,args in rec.value:
        cur.append((op,args))
        if op in ("closePath","endPath"): contours.append(cur); cur=[]
    if cur: contours.append(cur)
    def to_svg(cs):
        p=SVGPathPen(gs)
        for c in cs:
            for op,args in c: getattr(p,op)(*args)
        return p.getCommands()
    def bbox(cs):
        b=BoundsPen(gs)
        for c in cs:
            for op,args in c: getattr(b,op)(*args)
        return b.bounds
    onset,vowel,final=decompose(syl)
    bb_all=bbox(contours)
    # 조각 = 초성 묶음 + 모음 묶음 (둘 다 떨어져 있을 때만). 받침 있으면 조립 없음.
    # 묶음 나누기: 가로 모음(ㅏㅣ)은 x 가운데 기준, 세로 모음(ㅗㅜ)은 y 가운데 기준으로 윤곽을 둘로 가른다.
    groups=[]
    if final==0 and len(contours)>=2:
        if vowel in "ㅏㅣ":
            mid=(bb_all[0]+bb_all[2])/2
            on=[c for c in contours if bbox([c])[0]<=mid]; vo=[c for c in contours if bbox([c])[0]>mid]
        elif vowel in "ㅗㅜ":
            mid=(bb_all[1]+bb_all[3])/2
            on=[c for c in contours if bbox([c])[3]>=mid]; vo=[c for c in contours if bbox([c])[3]<mid]
        else:
            on,vo=contours,[]
        if on and vo: groups=[on,vo]          # 두 묶음 다 있어야 조립
    target=groups
    pieces=[{"d":to_svg(g_),"bbox":bbox(g_)} for g_ in target]
    out[syl]={"upm":upm,"adv":g.width,"bbox":bb_all,"ghost":to_svg(contours),"pieces":pieces}
    print(syl, onset, vowel, "final" if final else "", "contours",len(contours),"pieces",len(pieces))
json.dump(out,open("glyphs.json","w",encoding="utf-8"),ensure_ascii=False)
