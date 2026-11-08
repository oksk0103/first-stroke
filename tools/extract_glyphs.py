#!/usr/bin/env python3
"""리디바탕에서 음절 글리프의 윤곽을 꺼내 '조립 조각'과 '연한 글자'(전체)를 SVG 경로로 저장.
모든 음절이 조각으로 나뉜다. 초성·모음이 붙어 있는 글리프는 모음 줄기(세로/가로 막대) 경계에서 잘라 나눈다.
출력: glyphs.json  { "아": {"upm":1000, "adv":..., "bbox":[x0,y0,x1,y1], "ghost":"M...", "pieces":[{"d":"M...","bbox":[...]}, ...]} }
좌표는 글꼴 단위, y는 위가 +. 페이지에서 뒤집어 그린다."""
import json, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import pathops

FONT = sys.argv[1] if len(sys.argv) > 1 else "fonts/RIDIBatang.otf"
SYLS = list("가고구기나노누니아오우이") + list("태루마빠엄")  # 쓰기 12 + 이름 음절
ONSETS=list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"); VOWELS=list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
def decompose(s):
    c=ord(s)-0xAC00; return ONSETS[c//588], VOWELS[(c%588)//28], c%28

f=TTFont(FONT); gs=f.getGlyphSet(); cmap=f.getBestCmap(); upm=f["head"].unitsPerEm

def rect(x0,y0,x1,y1):
    p=pathops.Path(); p.moveTo(x0,y0); p.lineTo(x1,y0); p.lineTo(x1,y1); p.lineTo(x0,y1); p.close(); return p
def clip(path, x0,y0,x1,y1):
    return pathops.op(path, rect(x0,y0,x1,y1), pathops.PathOp.INTERSECTION)
def svg(path):
    p=SVGPathPen(gs); path.draw(p); return p.getCommands()
def cover(path, x0,y0,x1,y1):
    """사각형 안에 글자가 차지하는 bbox (없으면 None)"""
    c=clip(path,x0,y0,x1,y1); b=c.bounds
    return None if not b or b[2]-b[0]==0 and b[3]-b[1]==0 else b

def stem_left_edge(path, bb, from_left=False):
    """세로 줄기(높이 60% 이상)의 왼쪽 가장자리 x. 기본은 가장 오른쪽 줄기, from_left면 가장 왼쪽 줄기(ㅐㅔ)"""
    x0,y0,x1,y1=bb; gh=y1-y0; step=3
    xs = range(int(x0), int(x1), step) if from_left else range(int(x1)-step, int(x0), -step)
    inside=False; left=None
    for x in xs:
        b=cover(path, x, y0-1, x+step, y1+1)
        tall = bool(b) and (b[3]-b[1])>gh*0.6
        if tall:
            if from_left and not inside: return x
            inside=True; left=x
        elif inside: break
    return left
def bar_top_edge(path, bb):
    """가로 막대(너비 60% 이상) 중 가장 아래 것의 위 가장자리 y, 그리고 그 위 좁은 구간(세로 꼭지)의 중간 y"""
    x0,y0,x1,y1=bb; gw=x1-x0; step=3
    inside=False; top=None
    for y in range(int(y0), int(y1), step):
        b=cover(path, x0-1, y, x1+1, y+step)
        wide = bool(b) and (b[2]-b[0])>gw*0.6
        if wide: inside=True; top=y+step
        elif inside: break
    if top is None: return None
    # 막대 위로 좁은 구간(꼭지) 끝 찾기
    narrow_end=top
    for y in range(top, int(y1), step):
        b=cover(path, x0-1, y, x1+1, y+step)
        if b and (b[2]-b[0])<gw*0.3: narrow_end=y+step
        else: break
    return (top+narrow_end)/2 if narrow_end>top else top

out={}
for syl in SYLS:
    gname=cmap.get(ord(syl))
    if not gname: continue
    g=gs[gname]
    full=pathops.Path(); g.draw(full.getPen(glyphSet=gs)); full.simplify()
    bb=full.bounds; x0,y0,x1,y1=bb
    onset,vowel,final=decompose(syl)
    M=50  # 여유
    pieces=[]
    if vowel in "ㅏㅐㅑㅒㅓㅔㅕㅖㅣ":          # 세로 모음: 줄기 왼쪽에서 자름
        sx=stem_left_edge(full, (x0,y0,x1,y1) if final==0 else (x0, y0+(y1-y0)*0.45, x1, y1), from_left=vowel in "ㅐㅒㅔㅖ")
        if final==0:
            pieces=[clip(full,x0-M,y0-M,sx,y1+M), clip(full,sx,y0-M,x1+M,y1+M)]
        else:
            # 받침: 받침 윗선 = 아래쪽에서 가로로 넓은 구간이 끝나는 y
            fy=bar_top_edge(full,(x0,y0,x1,y0+(y1-y0)*0.5)) or (y0+(y1-y0)*0.42)
            pieces=[clip(full,x0-M,fy,sx,y1+M), clip(full,sx,fy,x1+M,y1+M), clip(full,x0-M,y0-M,x1+M,fy)]
    elif vowel in "ㅗㅛㅜㅠㅡ":              # 가로 모음: 막대 위(꼭지 중간)에서 자름
        cy=bar_top_edge(full, bb)
        pieces=[clip(full,x0-M,cy,x1+M,y1+M), clip(full,x0-M,y0-M,x1+M,cy)]
    pieces=[p for p in pieces if p.bounds]
    out[syl]={"upm":upm,"adv":g.width,"bbox":list(bb),"ghost":svg(full),
              "pieces":[{"d":svg(p),"bbox":list(p.bounds)} for p in pieces]}
    print(syl, onset, vowel, "final" if final else "", "pieces",len(pieces), [tuple(round(v) for v in p.bounds) for p in pieces])
json.dump(out,open("glyphs.json","w",encoding="utf-8"),ensure_ascii=False)
