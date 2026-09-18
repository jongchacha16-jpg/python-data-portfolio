# -*- coding: utf-8 -*-
"""감정 벡터 → 이모지 매칭 규칙.

`인공지능 프로젝트/이모지_매칭_파이프라인.ipynb` §3~§6의 RULES / intensity /
assign_emoji 를 그대로 옮긴 것이다 — 서비스가 노트북과 다른 이모지를 내놓으면
안 되므로, 로직을 바꾸지 않고 모듈로만 재포장했다.
"""
import numpy as np
import pandas as pd

FER = ['angry', 'disgusted', 'fearful', 'happy', 'neutral', 'sad', 'surprised']

RULES = [
    ('angry',     ['angry', 'enraged', 'steam from nose']),
    ('disgusted', ['nauseated', 'vomiting']),
    ('fearful',   ['fearful', 'anxious', 'anguished', 'screaming in fear']),
    ('sad',       ['crying', 'sad but', 'worried', 'frowning', 'disappointed', 'downcast',
                   'pensive', 'weary', 'holding back tears', 'pleading', 'confounded', 'persevering']),
    ('surprised', ['astonished', 'hushed', 'open mouth', 'flushed']),
    ('happy',     ['grinning', 'smiling', 'laughing', 'tears of joy', 'beaming',
                   'star-struck', 'partying']),
    ('neutral',   ['neutral', 'expressionless', 'without mouth', 'dotted line']),
]

STRONG = ['loudly', 'rolling on the floor', 'beaming', 'enraged', 'screaming',
          'astonished', 'squinting', 'star-struck', 'tears of joy']
WEAK = ['slightly', 'sad but relieved']


def _to_fer(name: str):
    n = name.lower()
    for cls, kws in RULES:
        for k in kws:
            if k in n:
                return cls, k
    return None, None


def _intensity(name: str) -> float:
    n = name.lower()
    if any(k in n for k in WEAK):
        return 0.30
    if any(k in n for k in STRONG):
        return 0.90
    return 0.60


def build_mapping(emoji_csv_path: str) -> pd.DataFrame:
    """emoji_df.csv → 매핑표 (원본 노트북과 동일하게 앞 105개 = 사람 표정 이모지만)."""
    emoji_df = pd.read_csv(emoji_csv_path)
    sel = emoji_df.iloc[0:105].reset_index(drop=True)
    sel[['fer', 'matched_kw']] = sel['name'].apply(lambda n: pd.Series(_to_fer(n)))
    mapped = sel.dropna(subset=['fer']).copy()
    mapped['intensity'] = mapped['name'].apply(_intensity)
    return mapped


def assign_emoji(vec, table: pd.DataFrame):
    """7차원 감정 벡터 → (이모지, 클래스, 확신도, 이모지 이름).

    1) 최대 클래스를 고른다
    2) 그 클래스 안에서 확신도와 강도가 가장 가까운 이모지를 고른다
    """
    v = np.asarray(vec, dtype=float)
    cls = FER[int(v.argmax())]
    conf = float(v.max())
    cand = table[table.fer == cls].copy()
    if cand.empty:
        return None, cls, conf, None
    cand['dist'] = (cand.intensity - conf).abs()
    cand = cand.sort_values(['dist', 'name'])
    top = cand.iloc[0]
    return top.emoji, cls, conf, top['name']
