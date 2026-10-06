# -*- coding: utf-8 -*-
"""와인품질_재검증분석.ipynb 생성기.

출력은 손으로 쓰지 않는다. 이 스크립트로 셀을 만들고
`jupyter nbconvert --to notebook --execute --inplace` 로 실제 실행해 출력을 채운다.
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
C = []
def md(s): C.append(nbf.v4.new_markdown_cell(s.strip()))
def co(s): C.append(nbf.v4.new_code_cell(s.strip()))

md("""
# 와인 품질 회귀분석 — 재검증

**원본**: 2023년 회귀분석 조별과제 (UCI Wine Quality)
**재검증**: 2026-09-08 (1부), 2026-10-06 (2부)

원본 분석은 노트북 7개에 흩어져 있고, 거기엔 **서로 다른 두 개의 분석 트랙**이 들어 있다.

| 트랙 | 노트북 | 접근 |
|---|---|---|
| **1부** | `Red_Wine(박찬종).ipynb`, `residuals.ipynb`, `wine.ipynb` | 적포도주 1,599건 단독. OLS·잔차진단·변수선택 중심의 통계적 접근 |
| **2부** | `회귀분석최종코드.ipynb`, `회귀분석_팀플.ipynb` | 백+적 6,497건 병합. 리샘플링·변수변환·6개 모델 벤치마크의 ML 접근 |

이 노트북은 원본을 대체하지 않는다. **원본이 무엇을 주장했는지 확인하고, 그 주장이 데이터에서 성립하는지 다시 재는 것**이 목적이다.

### 1부 — 적포도주 단독 분석 (§1~§8)

| # | 원본의 주장 | 결과 |
|---|---|---|
| 1 | `density`가 품질에 가장 큰 영향 (계수 −10.35) | §4 |
| 2 | `density`~`residual sugar` 고상관이 핵심 이슈 | §3 |
| 3 | 다중공선성 처리가 이 분석의 핵심 과제 | §3 |
| 4 | RandomForest R² = 1.0 | §5 |

### 2부 — 백+적 병합 ML 분석 (§9~§13)

| # | 원본의 주장/절차 | 결과 |
|---|---|---|
| 5 | 변환(log/sqrt/reciprocal)별로 성능을 비교 | §9 |
| 6 | 업샘플링으로 불균형을 해소하고 RandomForest R² 0.712 달성 | §10 |
| 7 | 상호작용 특성 추가가 예측 능력을 높인다 | §11 |
| 8 | 하드코딩된 결과표·Lasso·부트스트랩 신뢰구간 | §12 |
| 9 | 백+적을 병합해 분석하는 것이 타당한가 | §13 |
""")

co("""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.miscmodels.ordinal_model import OrderedModel
from sklearn.model_selection import cross_val_score, KFold, GroupKFold, train_test_split
from sklearn.linear_model import LinearRegression, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.utils import resample
from sklearn.metrics import mean_squared_error, r2_score

plt.rcParams['font.family'] = ['AppleGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
pd.set_option('display.width', 120)
RANDOM_STATE = 42
CV = KFold(5, shuffle=True, random_state=RANDOM_STATE)
print('준비 완료')
""")

md("""
## 1. 데이터 로드

UCI Machine Learning Repository — [Wine Quality](https://archive.ics.uci.edu/dataset/186/wine+quality).
원본 CSV는 공개 데이터라 저장소에 포함하지 않는다 (`.gitignore`). 위 링크에서 받아 `wine+quality/` 에 두면 실행된다.

**적포도주(red)와 백포도주(white)를 모두 읽는다.** §3에서 필요하다.
""")

co("""
red   = pd.read_csv('wine+quality/winequality-red.csv',   sep=';')
white = pd.read_csv('wine+quality/winequality-white.csv', sep=';')

print(f'red   {red.shape}')
print(f'white {white.shape}')
print(f'\\n결측치 — red: {red.isnull().sum().sum()}개, white: {white.isnull().sum().sum()}개')
red.head(3)
""")

md("""
## 2. 진단 — 원본이 확인하지 않은 것

결측치는 없다. 원본 분석도 이것은 확인했다. 확인하지 않은 것이 하나 있다.
""")

co("""
dup_red   = red.duplicated().sum()
dup_white = white.duplicated().sum()
print(f'완전 중복 행 — red: {dup_red}행 ({dup_red/len(red)*100:.1f}%),  white: {dup_white}행 ({dup_white/len(white)*100:.1f}%)')
print(f'red 고유 조합: {len(red.drop_duplicates())}행 / 전체 {len(red)}행')

print('\\n등급 분포:')
dist = red['quality'].value_counts().sort_index()
print(pd.DataFrame({'건수': dist, '비율(%)': (dist/len(red)*100).round(1)}).to_string())
print(f"\\n5~6등급이 전체의 {dist[[5,6]].sum()/len(red)*100:.1f}%")
""")

md("""
11개 측정값이 소수점까지 전부 같은 행이 **240행(15.0%)** 있다.

ID 컬럼이 없어서 이것이 입력 오류인지, 같은 배치에서 나온 서로 다른 병인지 **데이터만으로는 판정할 수 없다**.
그래서 제거 여부를 단정하지 않고, §6에서 제거했을 때와 안 했을 때를 모두 측정한다.

등급은 3~8의 **이산 서열값**이고 5~6등급에 82.5%가 몰려 있다. 이 점은 §7에서 다시 다룬다.
""")

md("""
## 3. 주장 검증 ① — "density ~ residual sugar 고상관"과 다중공선성

원본 보고서는 `density`와 `residual sugar`의 강한 상관을 이 분석의 핵심 이슈로 들고,
다중공선성 처리를 주요 과제로 서술한다. 실제로 그런지 두 데이터셋에서 같이 잰다.
""")

co("""
pair = ('density', 'residual sugar')
print(f"{pair[0]} ~ {pair[1]} 상관계수")
print(f"  red   : {red[list(pair)].corr().iloc[0,1]:+.3f}")
print(f"  white : {white[list(pair)].corr().iloc[0,1]:+.3f}   \\u2190 보고서가 서술한 값과 일치")

def top_pairs(df, n=4):
    c = df.drop(columns='quality').corr().abs()
    m = c.where(np.triu(np.ones(c.shape), k=1).astype(bool)).stack().sort_values(ascending=False)
    return m.head(n)

print('\\n[red] 변수 간 상관 상위 4쌍');   print(top_pairs(red).round(3).to_string())
print('\\n[white] 변수 간 상관 상위 4쌍'); print(top_pairs(white).round(3).to_string())
""")

md("""
`density ~ residual sugar` 상관은 **적포도주에서 +0.355(약함), 백포도주에서 +0.839(매우 강함)**이다.

원본은 적포도주를 분석했는데, 보고서가 핵심 이슈로 서술한 상관 구조는 **백포도주의 특성**이다.
두 CSV를 함께 열어보다 서술이 섞인 것으로 보인다.

그렇다면 적포도주에 다중공선성 문제가 실제로 있는가? VIF로 잰다.
""")

co("""
X_red = red.drop(columns='quality'); y_red = red['quality']
Xc = sm.add_constant(X_red)
vif = pd.Series([variance_inflation_factor(Xc.values, i) for i in range(1, Xc.shape[1])],
                index=X_red.columns).sort_values(ascending=False)
print('VIF (적포도주)'); print(vif.round(2).to_string())
print(f'\\n최대 VIF = {vif.max():.2f}  (통상 기준 10 초과 시 문제)')
print('10 초과 변수:', list(vif[vif > 10].index) or '없음')
""")

co("""
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, (name, df_) in zip(axes, [('red (원본 분석 대상)', red), ('white (보고서 서술과 일치)', white)]):
    sns.heatmap(df_.corr(), annot=True, fmt='.2f', cmap='coolwarm', center=0,
                ax=ax, cbar=False, annot_kws={'size': 7})
    ax.set_title(f'{name}\\ndensity~residual sugar = {df_["density"].corr(df_["residual sugar"]):+.3f}')
plt.tight_layout(); plt.show()
""")

md("""
**결론 ①**: 적포도주의 최대 VIF는 `fixed acidity` 7.77로 통상 기준 10을 넘지 않는다.
다중공선성은 이 분석의 핵심 과제가 아니었다. 핵심 과제로 서술된 근거(`density~residual sugar`)는 다른 데이터셋의 것이다.
""")

md("""
## 4. 주장 검증 ② — "density가 품질에 가장 큰 영향"

원본은 회귀계수의 절대값 크기로 영향력을 판단했다. 계수 표를 그대로 재현한다.

> 원본 보고서의 계수(`density` −10.35 등)는 80/20 **분할** 적합값이고, 아래는 **전수** 적합값이라
> 숫자가 조금씩 다르다(density −17.88, chlorides −1.87 …). 순위와 결론은 동일하다.
""")

co("""
ols = sm.OLS(y_red, sm.add_constant(X_red)).fit()
print(f'R² = {ols.rsquared:.4f}   Adj.R² = {ols.rsquared_adj:.4f}   F = {ols.fvalue:.2f}   N = {int(ols.nobs)}')

Xs = pd.DataFrame(StandardScaler().fit_transform(X_red), columns=X_red.columns)
ols_s = sm.OLS(y_red, sm.add_constant(Xs)).fit()

tab = pd.DataFrame({
    '원계수': ols.params[X_red.columns],
    'p값': ols.pvalues[X_red.columns],
    '표준화계수': ols_s.params[X_red.columns],
    '변수 표준편차': X_red.std(),
})
tab['유의(p<.05)'] = np.where(tab['p값'] < 0.05, '○', '✗')
tab['원계수 순위']   = tab['원계수'].abs().rank(ascending=False).astype(int)
tab['표준화 순위']   = tab['표준화계수'].abs().rank(ascending=False).astype(int)
print()
print(tab.sort_values('원계수 순위').round(4).to_string())
""")

md("""
변수들의 단위가 제각각이다. `density`의 표준편차는 **0.0019**, `total sulfur dioxide`는 **32.9** — 만 배 이상 차이난다.
단위가 다른 계수의 절대값을 비교하면 **작은 단위를 쓰는 변수가 자동으로 커 보인다**. 표준화해서 다시 비교한다.
""")

co("""
comp = tab[['원계수 순위', '표준화 순위', '표준화계수', 'p값', '유의(p<.05)']].sort_values('표준화 순위')
print('표준화 후 영향력 순위'); print(comp.round(4).to_string())

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
tab['원계수'].sort_values().plot.barh(ax=axes[0], color='#c44')
axes[0].set_title('원본이 본 것 — 원계수 (단위 제각각)'); axes[0].axvline(0, c='k', lw=.8)
tab['표준화계수'].sort_values().plot.barh(ax=axes[1], color='#37a')
axes[1].set_title('표준화 계수 (같은 척도)'); axes[1].axvline(0, c='k', lw=.8)
plt.tight_layout(); plt.show()

d = tab.loc['density']
print(f"\\ndensity — 원계수 {d['원계수']:.2f} (크기 {int(d['원계수 순위'])}위)  →  "
      f"표준화 {d['표준화계수']:+.3f} ({int(d['표준화 순위'])}위),  p = {d['p값']:.3f}")
print('p>0.05 인 변수:', [c for c in X_red.columns if ols.pvalues[c] > 0.05])
""")

md("""
**결론 ②**: `density`의 계수가 가장 큰 것은 영향력이 커서가 아니라 **단위가 가장 작아서**다.

같은 척도로 놓으면 `density`는 11개 중 **10위**이고, **p = 0.409로 통계적으로 유의하지 않다**.
`citric acid`, `residual sugar`, `fixed acidity`도 마찬가지로 유의하지 않다.

실제 영향력 순위는 **alcohol(+0.294) > volatile acidity(−0.194) > sulphates(+0.155)** 이다.
원본이 "품질에 가장 큰 영향"으로 지목한 변수는 유의하지 않은 변수였다.
""")

md("""
## 5. 주장 검증 ③ — RandomForest R² = 1.0의 원인

원본 `wine.ipynb` 마지막 셀의 출력은 다음과 같다.

```
MSE: 0.0
R2 Score: 1.0
                      Importance
volatile acidity             0.0
citric acid                  0.0
...
alcohol                      0.0
quality                      1.0     ← 정답이 특성에 들어있다
```

중요도 표의 **인덱스가 `volatile acidity`에서 시작해 `quality`로 끝난다**.
즉 학습에 쓰인 특성 행렬은 `fixed acidity`를 뺀 11열이었고, 그 안에 **예측 대상인 `quality`가 포함**되어 있었다.

같은 노트북 앞쪽 셀은 `X = red_wine_data.drop('quality', axis=1)` 로 올바르게 정의한다.
**이 행렬을 만든 코드는 어느 노트북에도 남아 있지 않다** (`fixed acidity` 제거, `.iloc` 슬라이싱, 컬럼 목록 지정 모두 검색해 확인).

노트북이 저장된 상태 자체가 어긋나 있다는 정황은 있다 — 실행 카운트가 셀 1(=7)과 셀 8(=3)에만 남아 있고
나머지 셀은 전부 `null`인데도 출력은 갖고 있다. **저장 시점의 셀 구성이 실행 시점과 달랐다**는 뜻이다.
다만 `X`가 정확히 어떻게 만들어졌는지는 **확정하지 못했다.** 확인할 수 있는 것은 결과뿐이다 — 정답이 특성에 들어 있었다.

재현해서 확인한다.
""")

co("""
# 원본이 실제로 학습한 것으로 보이는 행렬: quality 포함, fixed acidity 제외
X_leak = red.drop(columns='fixed acidity')
Xtr, Xte, ytr, yte = train_test_split(X_leak, y_red, test_size=0.2, random_state=RANDOM_STATE)
rf_leak = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE).fit(Xtr, ytr)
pred = rf_leak.predict(Xte)

print(f'MSE = {mean_squared_error(yte, pred)}')
print(f'R²  = {r2_score(yte, pred)}')
print('\\n특성 중요도:')
print(pd.Series(rf_leak.feature_importances_, index=X_leak.columns).round(3).to_string())
""")

md("""
**결론 ③**: 원본 출력이 그대로 재현된다. MSE 0.0, R² 1.0, `quality` 중요도 1.0, 나머지 전부 0.0.

모델은 아무것도 학습하지 않았다. **정답을 그대로 베껴서 답한 것**이다.
숲의 모든 트리가 `quality` 하나로 완전히 갈라지므로 다른 변수는 쓸 일이 없어 중요도가 0이 된다.

이것은 성능이 아니라 **타깃 누수(target leakage)**이며, R² = 1.0은 무효다.
""")

md("""
## 6. 중복 240행이 만드는 폴드 간 누수

§2에서 미룬 문제다. 중복 행은 교차검증에서 **같은 행이 훈련과 테스트에 동시에 들어갈 수 있다**.
그러면 모델은 답을 외워서 맞힐 수 있다. 얼마나 일어나는지 센다.
""")

co("""
grp = red.groupby(list(red.columns), sort=False).ngroup()   # 동일 행끼리 같은 그룹
leaked = sum(grp.iloc[te].isin(set(grp.iloc[tr]) & set(grp.iloc[te])).sum()
             for tr, te in CV.split(X_red))
print(f'고유 조합 {grp.nunique()}개 / 전체 {len(red)}행')
print(f'테스트 폴드에 있으면서 훈련 폴드에도 동일한 행이 존재: {leaked}행 ({leaked/len(red)*100:.1f}%)')
""")

co("""
models = {'OLS': LinearRegression(),
          'RandomForest': RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1)}
rows = []
for name, m in models.items():
    a = cross_val_score(m, X_red, y_red, cv=CV, scoring='r2')
    b = cross_val_score(m, X_red, y_red, cv=GroupKFold(5), scoring='r2', groups=grp)
    rows.append({'모델': name, '일반 KFold': f'{a.mean():+.3f} ± {a.std():.3f}',
                 'GroupKFold(중복 분리)': f'{b.mean():+.3f} ± {b.std():.3f}',
                 '차이': f'{b.mean()-a.mean():+.3f}'})
print(pd.DataFrame(rows).to_string(index=False))
""")

md("""
테스트 행의 **24.1%**가 훈련 쪽에 똑같은 쌍둥이를 갖고 있다.

중복을 분리하면 **RandomForest는 R²가 0.129 떨어지고, OLS는 0.009밖에 안 떨어진다**.
선형모델은 개별 행을 외울 수 없어서 영향이 없고, 트리 모델만 외운 만큼을 잃는다.

즉 RandomForest가 OLS보다 크게 앞서 보이던 차이의 상당 부분은 **성능이 아니라 중복 행을 외운 것**이었다.
""")

md("""
## 7. 모델 사다리

원본은 선형회귀와 (무효인) RandomForest만 비교했다. 기준선부터 쌓아 올린다.

- **① 평균 예측** — 아무것도 학습하지 않는 하한선. R² ≈ 0
- **② alcohol 단일 회귀** — 품질과 상관이 가장 높은(+0.476) 변수 하나
- **③ 전체 11변수 OLS** — 원본의 모델
- **④ RandomForest** — 정상 학습
""")

co("""
red_dedup = red.drop_duplicates()
ladder = [('① 평균 예측(Dummy)', DummyRegressor(strategy='mean'), None),
          ('② alcohol 단일 OLS', LinearRegression(), ['alcohol']),
          ('③ 전체 11변수 OLS',  LinearRegression(), None),
          ('④ RandomForest',    RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1), None)]

def cv_r2(m, d, cols):
    X = d.drop(columns='quality') if cols is None else d[cols]
    s = cross_val_score(m, X, d['quality'], cv=CV, scoring='r2')
    return s.mean(), s.std()

rows = []
for name, m, cols in ladder:
    a, sa = cv_r2(m, red, cols)
    b, sb = cv_r2(m, red_dedup, cols)
    rows.append({'모델': name,
                 '원본 1,599행': f'{a:+.3f} ± {sa:.3f}',
                 '중복 행 제거 1,359행': f'{b:+.3f} ± {sb:.3f}'})
res = pd.DataFrame(rows)
print('5-fold 교차검증 R²'); print(res.to_string(index=False))

alc, _  = cv_r2(LinearRegression(), red, ['alcohol'])
full, _ = cv_r2(LinearRegression(), red, None)
print(f'\\nalcohol 한 변수가 전체 11변수 모델 성능의 {alc/full*100:.0f}%를 설명한다')
""")

md("""
읽는 법:

- 원본이 보고한 단일 분할 R² **0.403**은 5-fold 평균 **0.342 ± 0.064**보다 높다.
  분할 하나만 보면 폴드마다 ±0.06씩 흔들리는 값 중 운 좋은 쪽을 집은 것이 된다.
- **`alcohol` 하나로 전체 모델의 65%**가 설명된다. 나머지 10개 변수가 더하는 몫은 R² 0.12 정도다.
- 중복을 제거하면 OLS는 그대로(0.342→0.347)지만 RandomForest는 0.493→0.385로 떨어진다 (§6과 같은 이야기).
""")

md("""
## 8. 선형회귀의 구조적 한계와 순서형 로지스틱

`quality`는 3~8의 **정수 등급**이다. 선형회귀는 이를 연속값으로 다루므로 5.37 같은 값을 내놓는다.
예측값을 반올림해서 실제로 어떤 등급을 맞히는지 본다.
""")

co("""
lin = LinearRegression().fit(X_red, y_red)
raw  = lin.predict(X_red)
pred_lin = np.clip(np.round(raw), 3, 8)

print(f'반올림 전 예측 범위: {raw.min():.2f} ~ {raw.max():.2f}   (실제 등급 범위 3 ~ 8)')
print('\\n선형회귀가 실제로 내놓는 등급:')
print(pd.Series(pred_lin).value_counts().sort_index().to_string())
print('\\n실제 등급 분포:')
print(y_red.value_counts().sort_index().to_string())
""")

md("""
선형회귀는 **3, 4, 8등급을 사실상 예측하지 못한다**. 예측이 5와 6에 몰린다.
데이터의 82.5%가 5~6등급이므로 평균 근처로 답하는 것이 제곱오차상 유리하기 때문이다.

등급이 서열을 가진다는 것을 모델에 알려주는 대안이 순서형 로지스틱 회귀다.
""")

co("""
ord_m = OrderedModel(y_red, Xs, distr='logit').fit(method='bfgs', disp=False)
print(f'Log-Likelihood = {ord_m.llf:.1f}   Pseudo R² = {ord_m.prsquared:.4f}   AIC = {ord_m.aic:.1f}')
print('\\n표준화 계수 (절대값 상위 5):')
print(ord_m.params[X_red.columns].sort_values(key=abs, ascending=False).head(5).round(3).to_string())

pred_ord = np.asarray(ord_m.predict(Xs)).argmax(1) + 3
print('\\n등급 정확 일치율')
print(f'  최빈값(5등급)으로 다 찍기 : {(y_red == 5).mean():.3f}')
print(f'  선형회귀 (반올림)        : {(pred_lin == y_red).mean():.3f}')
print(f'  순서형 로지스틱          : {(pred_ord == y_red).mean():.3f}')
""")

md("""
순서형 로지스틱의 정확도(0.595)는 선형회귀 반올림(0.592)과 **사실상 같다**.
모델을 바꿔도 나아지지 않는다 — 한계는 모델이 아니라 **데이터에 5~6등급이 82.5% 몰려 있는 구조**에 있다.

다만 영향력 순위는 두 모델이 일치한다(alcohol > volatile acidity > sulphates). §4의 결론이 모델과 무관하게 유지된다는 뜻이다.
""")

md("""
# 2부 — 백포도주 + 적포도주 병합 분석 (`회귀분석최종코드.ipynb`)

여기서부터는 **다른 노트북**을 다룬다. 1부가 적포도주 1,599건을 OLS로 분석했다면,
`회귀분석최종코드.ipynb`(49셀)와 그 전신 `회귀분석_팀플.ipynb`(31셀)는 백+적 6,497건을 병합하고
리샘플링·변수변환·6개 모델(Linear/Ridge/Lasso/DecisionTree/RandomForest/GradientBoosting) 벤치마크로 접근한다.

규모가 가장 크고 파일명도 "최종코드"지만, 1부의 재검증 범위 밖에 있었다. 여기서 같은 방식으로 다시 잰다.
""")

co("""
w_, r_ = white.copy(), red.copy()
w_['wine_type'], r_['wine_type'] = 0, 1
merged = pd.concat([w_, r_], ignore_index=True)

print(f'병합 데이터: {merged.shape}  (white {len(white)} + red {len(red)})')
print(f"white 비중 {len(white)/len(merged)*100:.1f}%  /  red 비중 {len(red)/len(merged)*100:.1f}%")

dup_w, dup_r = white.duplicated().sum(), red.duplicated().sum()
dup_m = merged.drop(columns='wine_type').duplicated().sum()
print(f'\\n완전 중복 행')
print(f'  red   : {dup_r}행 ({dup_r/len(red)*100:.1f}%)    \\u2190 1부 §2에서 확인')
print(f'  white : {dup_w}행 ({dup_w/len(white)*100:.1f}%)   \\u2190 적포도주보다 심하다')
print(f'  병합  : {dup_m}행 ({dup_m/len(merged)*100:.1f}%)')
""")

md("""
먼저 눈에 띄는 것: **백포도주의 중복이 937행(19.1%)으로 적포도주(240행, 15.0%)보다 많다.**
1부에서 찾은 문제가 2부 데이터에서는 더 크다. §10·§13에서 이 영향을 측정한다.
""")

md("""
## 9. 주장 검증 ⑤ — 변환 비교에서 타겟까지 함께 변환됨

`회귀분석최종코드.ipynb`의 49셀 중 약 40셀이 같은 패턴을 반복한다:
원본 / log / sqrt / reciprocal 네 가지 데이터셋에 6개 모델을 돌리고 R²를 나란히 비교한다.

변환을 수행하는 함수는 다음과 같다.

```python
def apply_selected_transformations(df):
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    positive_numeric_cols = [col for col in numeric_cols if (df[col] > 0).all()]
    log_transformed_df = df.copy()
    for col in positive_numeric_cols:
        log_transformed_df[col] = np.log(df[col])
    ...
```

`quality`는 `int64`이고 최솟값이 3이므로 **`positive_numeric_cols`에 포함된다.**
그리고 다음 셀에서 `y = log_transformed_df['quality']` 로 그 값을 타겟으로 쓴다.

즉 변환된 데이터셋의 R²는 **log(quality)를 예측한 R²**이고, 원본 데이터셋의 R²는 **quality를 예측한 R²**다.
타겟이 서로 다르면 R²의 분모(타겟 분산)가 달라지므로 **두 수치는 같은 축에서 비교할 수 없다.**
확인한다.
""")

co("""
def apply_transform(df, kind):
    num = df.select_dtypes(include=['float64', 'int64']).columns
    pos = [c for c in num if (df[c] > 0).all()]
    out = df.copy()
    for c in pos:
        if   kind == 'log':        out[c] = np.log(df[c])
        elif kind == 'sqrt':       out[c] = np.sqrt(df[c])
        elif kind == 'reciprocal': out[c] = 1 / df[c]
    return out, pos

_, pos_cols = apply_transform(red, 'log')
print(f'변환 대상으로 선택된 열 {len(pos_cols)}개')
print(f"  quality 포함 여부: {'quality' in pos_cols}   (dtype={red['quality'].dtype}, min={red['quality'].min()})")
print()
for kind in ['log', 'sqrt', 'reciprocal']:
    t, _ = apply_transform(red, kind)
    print(f"  {kind:10s} 후 타겟 범위: {t['quality'].min():.3f} ~ {t['quality'].max():.3f}"
          f"   (원본 {red['quality'].min()} ~ {red['quality'].max()})")
""")

co("""
MODELS = lambda: {
    'LinearRegression': LinearRegression(),
    'RandomForest':     RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1),
}

def split_fit(d, target_from=None):
    \"\"\"target_from이 주어지면 타겟만 그 시리즈로 되돌린다(= 특성만 변환).\"\"\"
    d = d.copy()
    if target_from is not None:
        d['quality'] = target_from.values
    X, y = d.drop(columns='quality'), d['quality']
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
    return {n: r2_score(yte, m.fit(Xtr, ytr).predict(Xte)) for n, m in MODELS().items()}

rows = []
for kind in ['원본', 'log', 'sqrt', 'reciprocal']:
    d = red.copy() if kind == '원본' else apply_transform(red, kind)[0]
    bad  = split_fit(d)                              # 원본 절차: 타겟도 변환됨
    fair = split_fit(d, target_from=red['quality'])  # 공정 비교: 타겟 고정
    rows.append({'변환': kind,
                 '원본 절차 Linear': f"{bad['LinearRegression']:+.3f}",
                 '원본 절차 RF':     f"{bad['RandomForest']:+.3f}",
                 '타겟 고정 Linear': f"{fair['LinearRegression']:+.3f}",
                 '타겟 고정 RF':     f"{fair['RandomForest']:+.3f}"})
print('적포도주 — 변환별 R² (80/20 분할)')
print(pd.DataFrame(rows).to_string(index=False))
""")

md("""
**결론 ⑤**: 원본 절차에서는 변환에 따라 R²가 눈에 띄게 움직인다
(Linear 0.403 → 0.392 → 0.402 → 0.351, RF 0.539 → 0.502 → 0.522 → 0.431).
그래서 "변환이 성능에 영향을 준다"는 결론이 나온다.

그런데 **타겟을 원본 `quality`로 고정하고 특성만 변환하면 그 차이가 사라진다**
(Linear 0.403 / 0.409 / 0.408 / 0.399 — 폭 0.010). RF는 소수점 셋째 자리까지 거의 동일하다.

즉 원본이 관찰한 "변환 효과"는 특성 변환의 효과가 아니라 **타겟이 함께 변환되어 R²의 기준이 바뀐 것**이다.
`reciprocal`에서 가장 크게 떨어진 것도 1/quality가 0.125~0.333의 좁은 범위로 압축되기 때문이고,
변환이 모델에 불리해서가 아니다. 이 노트북의 변환 비교 셀 약 40개가 모두 같은 문제를 공유한다.
""")

md("""
## 10. 주장 검증 ⑥ — 업샘플링을 분할 **전에** 수행

`회귀분석_팀플.ipynb`는 레드와 화이트의 개수 차이를 업샘플링으로 맞춘 뒤 RandomForest R² 0.712를 보고한다.
코드 순서는 이렇다.

```python
red_wine_upsampled = resample(red_wine, replace=True,
                              n_samples=len(white_wine), random_state=123)
combined_resampled = pd.concat([white_wine, red_wine_upsampled])
X = combined_resampled.drop('quality', axis=1)
...
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, ...)
```

`replace=True`로 1,599행을 4,898행까지 복제한 **뒤에** 분할한다.
따라서 같은 원본 행의 복제본이 훈련과 테스트 양쪽에 들어간다. 얼마나 들어가는지 센다.
""")

co("""
red_up = resample(merged[merged.wine_type == 1], replace=True,
                  n_samples=int((merged.wine_type == 0).sum()), random_state=123)
comb_leak = pd.concat([merged[merged.wine_type == 0], red_up]).reset_index(drop=True)

key = comb_leak.astype(str).agg('|'.join, axis=1)
idx_tr, idx_te = train_test_split(np.arange(len(comb_leak)), test_size=0.2, random_state=RANDOM_STATE)
twin = key.iloc[idx_te].isin(set(key.iloc[idx_tr])).sum()

print(f'업샘플링 후: {len(comb_leak)}행  (화이트 {len(white)} + 레드 복제 {len(red_up)})')
print(f'그중 고유 조합: {len(comb_leak.drop_duplicates())}행')
rep = red_up.astype(str).agg('|'.join, axis=1).value_counts()
print(f'레드 행 복제 횟수: 평균 {rep.mean():.2f}회, 최대 {rep.max()}회')
print(f'\\n테스트 {len(idx_te)}행 중 훈련에 동일 행이 존재: {twin}행 ({twin/len(idx_te)*100:.1f}%)')
print('  (1부 §6의 적포도주 단독 교차검증에서는 24.1%였다)')
""")

co("""
Xm, ym = merged.drop(columns='quality'), merged['quality']
Xtr_m, Xte_m, ytr_m, yte_m = train_test_split(Xm, ym, test_size=0.2, random_state=RANDOM_STATE)

# (b) 분할 후 훈련셋만 업샘플링
_tr = Xtr_m.copy(); _tr['quality'] = ytr_m
_tr_up = resample(_tr[_tr.wine_type == 1], replace=True,
                  n_samples=int((_tr.wine_type == 0).sum()), random_state=123)
tr_b = pd.concat([_tr[_tr.wine_type == 0], _tr_up])

def fit_eval(Xtr, ytr, Xte, yte):
    return {n: r2_score(yte, m.fit(Xtr, ytr).predict(Xte)) for n, m in MODELS().items()}

Xa, ya = comb_leak.drop(columns='quality'), comb_leak['quality']
Xtr_a, Xte_a, ytr_a, yte_a = train_test_split(Xa, ya, test_size=0.2, random_state=RANDOM_STATE)

res = {
 '(a) 업샘플링 → 분할  [원본 절차]': fit_eval(Xtr_a, ytr_a, Xte_a, yte_a),
 '(b) 분할 → 훈련셋만 업샘플링':      fit_eval(tr_b.drop(columns='quality'), tr_b['quality'], Xte_m, yte_m),
 '(c) 리샘플링 없음':                 fit_eval(Xtr_m, ytr_m, Xte_m, yte_m),
}
out = pd.DataFrame(res).T.round(3)
out.columns = [f'{c} R²' for c in out.columns]
print('동일한 병합 데이터에 절차만 바꿔 측정'); print(out.to_string())
print(f"\\n원본 보고 값: RandomForest R² 0.712  /  (a) 재현값 {res['(a) 업샘플링 → 분할  [원본 절차]']['RandomForest']:.3f}")
""")

md("""
**결론 ⑥**: 원본 절차 (a)를 그대로 재현하면 RandomForest R² **0.707**이 나온다 — 보고서의 0.712와 사실상 일치한다.
Linear도 0.316으로 보고서의 0.317과 맞는다. 절차가 정확히 재현된 것이다.

그런데 순서만 바로잡으면:

- (b) **분할 후 훈련셋만** 업샘플링 → RF **0.548**
- (c) 리샘플링을 아예 안 함 → RF **0.553**

**0.712가 아니라 0.55 수준이다.** 차이 약 0.16은 모델 성능이 아니라 복제본이 테스트로 새어 들어간 양이다.
테스트 행의 **59.6%**가 훈련에 동일한 행을 갖고 있었다 — 레드 행은 평균 3.75회, 최대 15회까지 복제된다.

또한 (b)와 (c)가 거의 같다는 점에 주목할 만하다. **업샘플링은 올바르게 수행해도 이득이 없었다.**
이유는 §13에서 다룬다.
""")

md("""
### 덧붙임 — 리샘플링의 대상이 타겟이 아니다

더 근본적인 문제가 있다. 이 과제의 타겟은 `quality`인데, 코드가 균형을 맞춘 것은 `wine_type`(레드/화이트)이다.
원본 코드의 주석도 스스로 확신하지 못한다.

```python
# 데이터셋의 클래스 불균형 해결 (예: 'wine_type' 컬럼을 사용한다고 가정)
```

업/다운샘플링은 **불균형 분류**에서 타겟 클래스 비율을 맞추는 처방이다.
여기서는 (1) 문제가 분류가 아니라 회귀이고, (2) 균형을 맞춘 변수가 타겟이 아니라 특성이다.
1부 §2에서 확인한 진짜 불균형 — `quality`가 5·6등급에 82.5% 몰려 있는 것 — 은 이 처리로 전혀 해소되지 않는다.
""")

md("""
## 11. 주장 검증 ⑦ — 상호작용 특성 추가의 효과

원본은 상관관계가 높은 변수 쌍으로 합·곱·역수 특성 6개를 만들고,
"특성 추가가 모델의 예측 능력에 긍정적인 영향을 미칠 수 있음을 확인할 수 있습니다"라고 적는다.

그 판단의 근거가 된 수치는 §10에서 확인한 누수된 절차에서 나온 것이다.
누수를 제거하고 — 중복 행을 같은 폴드로 묶는 `GroupKFold`로 — 다시 잰다.
""")

co("""
def add_interactions(d):
    d = d.copy()
    d['acidity_sugar_sum']  = d['fixed acidity'] + d['residual sugar']
    d['sugar_sulfur_sum']   = d['residual sugar'] + d['free sulfur dioxide']
    d['inverse_density']    = 1 / d['density']
    d['acidity_sugar_interaction']  = d['fixed acidity'] * d['residual sugar']
    d['sulfur_dioxide_interaction'] = d['free sulfur dioxide'] * d['total sulfur dioxide']
    d['inverse_alcohol_density_interaction'] = 1 / (d['density'] * d['alcohol'])
    return d

base_cols = [c for c in merged.columns if c not in ('quality', 'wine_type')]
grp_m = merged.drop(columns='wine_type').groupby(base_cols + ['quality'], sort=False).ngroup()

rows = []
for label, d in [('특성 추가 전', merged), ('특성 추가 후', add_interactions(merged))]:
    Xa = d.drop(columns=['quality', 'wine_type']); ya = d['quality']
    row = {'데이터': label, '특성 수': Xa.shape[1]}
    for n, m in [('OLS', LinearRegression()),
                 ('RandomForest', RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1))]:
        s = cross_val_score(m, Xa, ya, cv=GroupKFold(5), groups=grp_m, scoring='r2')
        row[n] = f'{s.mean():+.4f}'
    rows.append(row)
print('GroupKFold(5) — 중복 행을 폴드로 분리한 R²')
print(pd.DataFrame(rows).to_string(index=False))
""")

md("""
**결론 ⑦**: 특성 6개를 추가해도 OLS는 +0.287 → +0.296 (**+0.010**), RandomForest는 +0.384 → +0.382 (**−0.002**)다.

사실상 변화가 없다. 추가된 특성이 기존 변수의 합·곱·역수라 **새로운 정보를 담고 있지 않기 때문**이다
(`inverse_density`는 `density`의 단조변환이고, RandomForest는 단조변환에 불변이다).

원본이 관찰한 "특성 추가의 긍정적 영향"은 §10의 누수가 만들어낸 변동이었다.
""")

md("""
## 12. 주장 검증 ⑧ — 수치를 신뢰할 수 없게 만드는 절차상 결함 세 가지

주장 자체는 아니지만, 2부 노트북의 결과를 그대로 인용할 수 없게 만드는 문제들이다.

### ① 결과표가 하드코딩되어 있고, 두 사본이 서로 다르다

`보고서 작성자료(wine).ipynb`와 `회귀분석_팀플.ipynb` 둘 다 모델 성능표를 **딕셔너리에 직접 타이핑**해
막대그래프만 그린다. 계산하는 코드가 없다. 그런데 두 표의 값이 어긋난다.

| 모델 | `보고서 작성자료(wine)` | `회귀분석_팀플` CODE 25 |
|---|---|---|
| LinearRegression | MSE 0.495 / R² 0.316 | MSE 0.494 / R² 0.317 |
| **DecisionTree** | **MSE 0.353 / R² 0.512** | **MSE 0.412 / R² 0.431** |
| RandomForest | MSE 0.210 / R² 0.710 | MSE 0.208 / R² 0.712 |

DecisionTree는 R²가 0.512 대 0.431로 **0.08 차이**가 난다. 반올림 오차가 아니라 서로 다른 실행 회차의 값이다.
원인은 명확하다 — 원본 코드에서 `DecisionTreeRegressor()`, `RandomForestRegressor()`,
`GradientBoostingRegressor()`에 **`random_state`가 지정되어 있지 않다.** 실행할 때마다 결과가 달라지므로
어느 쪽도 재현할 수 없고, 발표에 쓰인 차트는 노트북으로 되돌아가 확인할 방법이 없다.

(이 재검증 노트북은 모든 모델에 `random_state=42`를 지정한다.)
""")

co("""
# ② Lasso R² ≈ -0.000 의 원인
Xl, yl = comb_leak.drop(columns='quality'), comb_leak['quality']
Xtr_l, Xte_l, ytr_l, yte_l = train_test_split(Xl, yl, test_size=0.2, random_state=RANDOM_STATE)

for name, m in [('Lasso() 기본 alpha=1.0',          Lasso()),
                ('표준화 + Lasso() alpha=1.0',       make_pipeline(StandardScaler(), Lasso())),
                ('표준화 + Lasso(alpha=0.01)',       make_pipeline(StandardScaler(), Lasso(alpha=0.01)))]:
    m.fit(Xtr_l, ytr_l)
    print(f'  {name:32s} R² = {r2_score(yte_l, m.predict(Xte_l)):+.4f}')

l0 = Lasso().fit(Xtr_l, ytr_l)
print(f'\\n  기본 Lasso의 0이 아닌 계수: {int((l0.coef_ != 0).sum())} / {len(l0.coef_)}개')
""")

md("""
### ② Lasso의 R² ≈ 0은 모델의 성능이 아니다

원본은 "Lasso 회귀는 0에 가까운 R² 값을 가지며, 이는 모델이 데이터의 변동성을 거의 설명하지 못함을 의미합니다"라고
모델에 대한 판정으로 적는다. 실제로는 **기본 `alpha=1.0`에서 12개 계수가 전부 0으로 수축되어
절편(평균)만 예측하는 모델이 된 것**이다.

흔히 "표준화를 안 해서"라고 설명하지만, 측정해보면 표준화만으로는 바뀌지 않는다(여전히 −0.0000).
`quality`의 분산이 약 0.78로 작아서, alpha=1.0의 페널티가 어떤 척도에서도 모든 계수를 0으로 만든다.
`alpha=0.01`로 낮추면 **+0.308**로 Ridge·Linear와 같은 수준이 된다.

즉 이 수치는 Lasso가 이 데이터에 부적합하다는 증거가 아니라, **하이퍼파라미터를 조정하지 않았다는 기록**이다.

### ③ 부트스트랩 신뢰구간이 훈련오차의 구간이다

`회귀분석_팀플.ipynb` 마지막 셀의 함수는 다음과 같다.

```python
def bootstrap_confidence_interval(model, X, y, n_bootstrap=1000, ci=95):
    for _ in range(n_bootstrap):
        X_sample, y_sample = resample(X, y)
        model.fit(X_sample, y_sample)
        y_pred = model.predict(X)        # ← 건네받은 X 그대로
        mse = mean_squared_error(y, y_pred)
```

부트스트랩 표본으로 적합한 뒤 **그 표본이 아니라 입력 전체 `X`로 예측**하고, 호출부는 `X_train`을 넘긴다.
부트스트랩 표본은 평균적으로 원본의 63.2%를 포함하므로, 예측 대상의 대부분이 학습에 쓰인 행이다.
따라서 이 구간은 일반화 성능의 신뢰구간이 아니라 **훈련오차에 가까운 값의 구간**이며, 실제보다 좁고 낙관적이다.
(1,000회 RandomForest 적합이 필요해 여기서 재실행하지는 않았다 — 코드만으로 판정 가능한 결함이다.)
""")

md("""
## 13. 주장 검증 ⑨ — 백+적을 병합하는 것이 타당한가

2부의 전제 자체를 확인한다. 레드와 화이트를 하나의 데이터셋으로 합쳐 모델을 적합하는 것이
각각 따로 적합하는 것보다 나은가. 누수 없이 비교한다.
""")

co("""
rows = []
for label, d in [('화이트 단독', white), ('적포도주 단독', red)]:
    Xa, ya = d.drop(columns='quality'), d['quality']
    g = d.groupby(list(d.columns), sort=False).ngroup()
    row = {'데이터셋': label, 'N': len(d)}
    for n, m in [('OLS', LinearRegression()),
                 ('RandomForest', RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1))]:
        s = cross_val_score(m, Xa, ya, cv=GroupKFold(5), groups=g, scoring='r2')
        row[n] = f'{s.mean():+.3f}'
    rows.append(row)

Xa, ya = merged.drop(columns=['quality', 'wine_type']), merged['quality']
row = {'데이터셋': '병합 (리샘플링 없음)', 'N': len(merged)}
for n, m in [('OLS', LinearRegression()),
             ('RandomForest', RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1))]:
    s = cross_val_score(m, Xa, ya, cv=GroupKFold(5), groups=grp_m, scoring='r2')
    row[n] = f'{s.mean():+.3f}'
rows.append(row)
print('GroupKFold(5) R² — 중복 분리'); print(pd.DataFrame(rows).to_string(index=False))

print('\\n두 품종의 상관 구조가 같은가 (1부 §3에서 확인한 쌍):')
for nm, d in [('red  ', red), ('white', white)]:
    print(f"  {nm} density ~ residual sugar = {d['density'].corr(d['residual sugar']):+.3f}")
""")

co("""
rows = []
for nm, m in [('OLS', LinearRegression()),
              ('RandomForest', RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1))]:
    a = cross_val_score(m, merged.drop(columns=['quality','wine_type']), merged['quality'],
                        cv=KFold(5, shuffle=True, random_state=RANDOM_STATE), scoring='r2')
    b = cross_val_score(m, merged.drop(columns=['quality','wine_type']), merged['quality'],
                        cv=GroupKFold(5), groups=grp_m, scoring='r2')
    rows.append({'모델': nm, '일반 KFold': f'{a.mean():+.3f} ± {a.std():.3f}',
                 'GroupKFold(중복 분리)': f'{b.mean():+.3f} ± {b.std():.3f}',
                 '차이': f'{b.mean()-a.mean():+.3f}'})
print('병합 데이터의 중복 행 영향 (1부 §6과 같은 측정)')
print(pd.DataFrame(rows).to_string(index=False))
""")

md("""
**결론 ⑨**: 병합이 주는 이득이 사실상 없다.

| 데이터셋 | N | OLS R² | RandomForest R² |
|---|---|---|---|
| 화이트 단독 | 4,898 | +0.271 | +0.372 |
| 적포도주 단독 | 1,599 | +0.334 | +0.364 |
| 병합 | 6,497 | +0.287 | +0.384 |

병합 모델은 화이트 단독보다 RandomForest 기준 **+0.012**, 적포도주 단독보다 **+0.020** 높다.
표본이 적포도주 기준 4배로 늘었는데 얻은 것이 그 정도다. OLS는 오히려 적포도주 단독(+0.334)이 병합(+0.287)보다 높다.

이유는 1부 §3에서 이미 나왔다. **두 품종은 변수 간 구조가 다르다** —
`density ~ residual sugar` 상관이 적포도주 +0.355, 백포도주 +0.839다.
서로 다른 관계를 가진 두 모집단에 하나의 계수 집합을 강요하면, 어느 쪽에도 맞지 않는 평균적인 모델이 된다.
1부에서 "보고서가 백포도주 상관을 적포도주 분석에 서술했다"고 지적한 그 구조적 차이가,
2부에서는 "두 품종을 병합한 것" 자체의 타당성 문제로 되돌아온다.

그리고 병합 데이터에서도 중복 행 문제는 그대로다 — `GroupKFold`로 분리하면
RandomForest가 **−0.142** 떨어지고 OLS는 −0.003에 그친다. 1부 §6의 적포도주 결과(−0.129 / −0.009)와 같은 양상이다.
""")

md("""
## 14. 결론

### 1부 — 적포도주 단독 분석의 주장 판정

| 원본의 주장 | 재검증 결과 |
|---|---|
| `density`가 품질에 가장 큰 영향 (계수 −10.35) | **틀림.** 표준화하면 11개 중 10위, p=0.409로 비유의. 계수가 컸던 건 표준편차가 0.0019로 가장 작기 때문 |
| `density`~`residual sugar` 고상관이 핵심 이슈 | **적포도주 값이 아님.** red +0.355 / white +0.839 — 백포도주 특성을 적포도주 분석에 서술 |
| 다중공선성 처리가 핵심 과제 | **아님.** 최대 VIF 7.77로 기준 10 미만 |
| RandomForest R² = 1.0 | **무효.** `quality`가 특성에 포함된 타깃 누수. 정상 학습 시 0.493, 중복을 폴드로 분리하면 0.364 |

### 2부 — 백+적 병합 ML 분석의 주장 판정

| 원본의 주장/절차 | 재검증 결과 |
|---|---|
| 변환(log/sqrt/reciprocal)별 성능 비교 | **비교 불가.** 변환 함수가 `quality`까지 변환해 서로 다른 타겟의 R²를 나란히 놓았음. 타겟 고정 시 변환 효과 소멸(Linear 0.403 vs 0.409/0.408/0.399) |
| 업샘플링 후 RandomForest R² 0.712 | **누수.** 복제 후 분할이라 테스트의 **59.6%**가 훈련에 쌍둥이 보유. 순서만 바로잡으면 **0.548**, 리샘플링 없으면 0.553 |
| 리샘플링으로 불균형 해소 | **대상이 틀림.** 타겟은 `quality`인데 균형을 맞춘 건 `wine_type`(특성). 실제 불균형(5·6등급 82.5%)은 그대로 |
| 상호작용 특성 추가가 성능 향상 | **효과 없음.** GroupKFold 기준 OLS +0.010, RandomForest **−0.002**. 기존 변수의 합·곱·역수라 새 정보가 없음 |
| Lasso R² ≈ 0 = "모델이 설명 못 함" | **모델 판정이 아님.** alpha=1.0에서 12개 계수 전부 0. 표준화해도 동일, alpha=0.01이면 **+0.308** |
| 발표용 결과표 | **재현 불가.** 하드코딩된 두 사본이 불일치(DecisionTree R² 0.512 vs 0.431). 트리 모델에 `random_state` 미지정 |
| 부트스트랩 95% 신뢰구간 | **훈련오차의 구간.** 부트스트랩 표본으로 적합한 뒤 입력 전체로 예측 — 일반화 성능이 아님 |
| 백+적 병합 분석 | **이득 거의 없음.** RF 병합 +0.384 vs 화이트 단독 +0.372 / 적포도주 단독 +0.364. 표본 4배에 +0.012 |

### 확인된 수치

**1부 — 적포도주 1,599행**

| 항목 | 값 |
|---|---|
| OLS (전체 데이터) | R² 0.361 / Adj 0.356 / F 81.35 / N 1,599 |
| OLS 5-fold CV | R² **0.342 ± 0.064** |
| RandomForest 5-fold CV | R² 0.493 ± 0.026 → 중복을 폴드로 분리(1,599행 유지) **0.364** / 중복 행 제거(1,359행) **0.385** |
| `alcohol` 단일 변수 | R² 0.224 — 전체 모델의 **65%** |
| 유의하지 않은 변수 (p>0.05) | `fixed acidity`, `citric acid`, `residual sugar`, `density` |
| 실제 영향력 1~3위 | alcohol +0.294 / volatile acidity −0.194 / sulphates +0.155 |
| 완전 중복 행 | 240행 (15.0%) — 교차검증 시 테스트의 24.1%가 훈련에 존재 |

**2부 — 백+적 병합 6,497행**

| 항목 | 값 |
|---|---|
| 업샘플링→분할 (원본 절차) | RF **0.707** / Linear 0.316 — 보고서 0.712 / 0.317 재현 |
| 분할→훈련셋만 업샘플링 | RF **0.548** |
| 리샘플링 없음 | RF **0.553** |
| 원본 절차의 누수량 | 테스트 1,960행 중 **1,169행(59.6%)**이 훈련에 동일 행 보유. 레드 행 평균 3.75회(최대 15회) 복제 |
| 완전 중복 행 | white **937행(19.1%)** / red 240행(15.0%) / 병합 1,179행 |
| 중복 분리(GroupKFold) 영향 | RandomForest **−0.142**, OLS −0.003 |
| 단독 vs 병합 (GroupKFold) | 화이트 RF +0.372 / 적포도주 +0.364 / 병합 **+0.384** |

### 배운 것

**1. 단위가 다른 계수의 크기를 비교하면 안 된다.**
1부 결론 전체가 여기서 어긋났다. `density`가 1위로 보인 것은 순전히 단위 때문이고, 표준화 한 줄이면 드러나는 문제였다.

**2. R² = 1.0은 축하할 일이 아니라 의심할 일이다.**
중요도가 한 변수에 1.0으로 몰리고 나머지가 전부 0이면, 그 변수가 정답 자체일 가능성부터 확인해야 한다.

**3. 중복 행은 조용히 성능을 부풀린다.**
결측치는 확인했지만 중복은 확인하지 않았다. 적포도주에서 RandomForest가 0.129만큼,
백포도주를 포함한 병합 데이터에서는 0.142만큼 좋아 보였고, 선형모델은 멀쩡했기 때문에 비교만으로는 눈치챌 수 없었다.

**4. 전처리의 순서가 성능 수치를 만든다.**
2부의 R² 0.712와 0.548 사이에는 모델 차이도, 데이터 차이도 없다. 복제를 분할 **전에** 했느냐 **후에** 했느냐뿐이다.
리샘플링·스케일링·결측대치처럼 데이터 전체를 보는 연산은 반드시 분할 **후** 훈련셋에서만 수행해야 한다.

**5. 변환은 특성에만 적용하고, 타겟을 건드렸다면 R²를 나란히 놓지 말아야 한다.**
2부의 변환 비교 40여 셀이 전부 이 한 가지 때문에 무효가 됐다.
"양수인 수치형 열 전부"라는 조건에 타겟이 조용히 포함된 것이 원인이다.

**6. 하이퍼파라미터를 조정하지 않은 결과는 모델의 성능이 아니다.**
Lasso의 R² ≈ 0을 "Lasso가 이 데이터를 설명하지 못한다"로 읽으면, 실제로는 alpha 하나로 해결되는 문제를 모델 탓으로 돌리게 된다.

**7. 남은 한계 — 이 재검증으로도 풀지 못한 것.**
중복 행이 입력 오류인지 같은 배치의 다른 병인지는 ID 컬럼이 없어 **판정 불가**다.
등급 3·8이 각각 10건·18건뿐이라 극단 등급 예측은 어떤 모델로도 신뢰하기 어렵다.
`quality`가 관능평가 중앙값이라는 점에서, 설명되지 않는 분산의 상당 부분은 평가자 간 차이일 수 있으나 데이터로는 확인할 수 없다.
2부 `wine.ipynb`의 R²=1.0을 만든 특성 행렬 생성 코드는 어느 노트북에도 남아 있지 않아, 결과만 재현했을 뿐 메커니즘은 확정하지 못했다.
""")

nb['cells'] = C
nb.metadata.kernelspec = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
nbf.write(nb, '와인품질_재검증분석.ipynb')
print(f'생성 완료: {len(C)}개 셀')
