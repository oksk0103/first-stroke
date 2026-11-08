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
    # 조각 선택: 모음이 ㅏㅗㅜㅣ면 모음 획, 아니면 초성 획. 받침 있으면 조립 없음(None).
    target=None
    if final==0:
        if vowel in "ㅏㅣ":   # 오른쪽에 붙는 모음: 왼쪽 끝이 글자 가운데보다 오른쪽인 윤곽
            mid=(bb_all[0]+bb_all[2])/2
            target=[c for c in contours if bbox([c])[0]>mid]
        elif vowel in "ㅗㅜ":  # 아래 모음: 위쪽 끝이 글자 가운데보다 아래인 윤곽
            mid=(bb_all[1]+bb_all[3])/2
            target=[c for c in contours if bbox([c])[3]<mid]
        elif onset in "ㄱㄴ":  # 초성 조립 (모음이 조립 대상이 아닐 때)
            mid=(bb_all[0]+bb_all[2])/2
            target=[c for c in contours if (lambda b:(b[0]+b[2])/2<mid)(bbox([c]))]
        # 모음 ㅏㅗㅜㅣ이면서 초성이 ㄱㄴ인 글자(가·고·구·기·나·노·누·니)는 모음 우선 — 첫 경험은 성공이어야 하니 조각 수 적은 쪽
        if vowel in "ㅏㅗㅜㅣ" and onset in "ㄱㄴ":
            mid=(bb_all[0]+bb_all[2])/2
            onset_cs=[c for c in contours if (lambda b:(b[0]+b[2])/2<mid)(bbox([c]))] if vowel in "ㅏㅣ" else [c for c in contours if (lambda b:(b[1]+b[3])/2>=mid)(bbox([c]))]
            # ㄱ·ㄴ은 보통 한 윤곽 → 조각 1개. 모음이 2개면 모음, 1개면 초성.
            if target and len(target)>=2: pass
            else: target=onset_cs
    pieces=[{"d":to_svg([c]),"bbox":bbox([c])} for c in (target or [])]
    out[syl]={"upm":upm,"adv":g.width,"bbox":bb_all,"ghost":to_svg(contours),"pieces":pieces}
    print(syl, onset, vowel, "final" if final else "", "contours",len(contours),"pieces",len(pieces))
json.dump(out,open("glyphs.json","w",encoding="utf-8"),ensure_ascii=False)
