# Python Data Analysis / ML Portfolio

데이터 분석 및 머신러닝 프로젝트 모음입니다. 각 프로젝트는 팀/개인 과제로 진행했으며, 폴더별 README에 문제 정의·접근 방법·결과를 정리했습니다.

## 프로젝트 목록

| 프로젝트 | 주제 | 핵심 내용 |
|---|---|---|
| [MachineLearning_Data_Related_Job_Salary](./MachineLearning_Data_Related_Job_Salary) | 데이터 직무 연봉 분석/예측 | 타겟 누수 진단, 3-class 분류 (정확도 ~67.5%), Random Forest/XGBoost 비교 |
| [데사프_프로젝트](./데사프_프로젝트) | 뇌졸중 발병 예측 (팀 과제) | 언더샘플링 기반 클래스 불균형 처리, RF 교차검증 Accuracy 93.6% |
| [시공간데이터_프로젝트](./시공간데이터_프로젝트) | 서울 지하철 시공간 데이터 분석 | 노선·역·시간대별 이용 패턴 히트맵 시각화 |
| [인공지능 프로젝트](./인공지능%20프로젝트) | 표정 분류 오토인코더 | 데이터 라이선스 제약으로 인한 실패 사례와 원인 분석 |
| [회귀분석_조별과제](./회귀분석_조별과제) | 와인 품질 회귀분석 (팀 과제) | 다중공선성 진단(VIF), 변수 선택, 잔차 분석 |

## 사용 기술

- Python, pandas, numpy
- scikit-learn (Random Forest, XGBoost, Logistic/Linear Regression, SMOTE)
- statsmodels (OLS, VIF)
- matplotlib, seaborn
- Jupyter Notebook

## 참고

- 각 노트북은 수업/스터디 팀 과제로 작성되었으며, 팀 과제의 경우 본인이 담당한 분석 파트를 중심으로 포함되어 있습니다.
- `MachineLearning_Data_Related_Job_Salary`에는 실제 분석에서 검증된 규칙을 정리한 `CLAUDE.md`가 포함되어 있어, 분석 과정에서의 의사결정 근거를 확인할 수 있습니다.
