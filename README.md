# Python Data Analysis / ML Portfolio

데이터 분석 및 머신러닝 프로젝트 모음입니다. 각 프로젝트는 팀/개인 과제로 진행했으며, 폴더별 README에 문제 정의·접근 방법·결과를 정리했습니다.

## 프로젝트 목록

| 프로젝트 | 주제 | 핵심 내용 |
|---|---|---|
| [MachineLearning_Data_Related_Job_Salary](./MachineLearning_Data_Related_Job_Salary) | 데이터 직무 연봉 분석/예측 | **과거 분석 재검증 후 회귀로 재구축.** 리키지로 알던 변수가 실제로는 중복 변수였음을 규명. Ridge+log1p, 교차검증 R² 0.500±0.069 (MAPE 42.6%) |
| [데사프_프로젝트](./데사프_프로젝트) | 뇌졸중 발병 예측 (팀 과제) | **과거 분석 재검증 후 불균형 관점으로 재구축.** "정확도 95%"가 환자 0명 검출 모델의 수치임을 확인. PR-AUC 0.225±0.043 (무작위 기준선 0.049), 재현율 0.787 |
| [인공지능 프로젝트](./인공지능%20프로젝트) | 표정 분류 CNN | **7개 감정 분류 CNN, 검증 정확도 0.5628** (무작위 기준선 0.1429의 3.9배). 부가 시도였던 이모지 변환 실패의 원인이 "라이선스"가 아니라 **`draw.text()` 누락**이었음을 규명 |
| [회귀분석_조별과제](./회귀분석_조별과제) | 와인 품질 회귀분석 (팀 과제) | 다중공선성 진단 후 변수 제거 실험, OLS R² 0.361 (N=1,599). **특성 중요도가 전부 0인데 R²=1.0으로 기록된 랜덤포레스트 결과를 무효로 판정** |

## 사용 기술

- Python, pandas, numpy
- scikit-learn (Random Forest, XGBoost, Logistic/Linear Regression, SMOTE)
- statsmodels (OLS, VIF)
- matplotlib, seaborn
- Jupyter Notebook

## 참고

- 각 노트북은 수업/스터디 팀 과제로 작성되었으며, 팀 과제의 경우 본인이 담당한 분석 파트를 중심으로 포함되어 있습니다.
- `MachineLearning_Data_Related_Job_Salary`에는 실제 분석에서 검증된 규칙을 정리한 `CLAUDE.md`가 포함되어 있어, 분석 과정에서의 의사결정 근거를 확인할 수 있습니다.
