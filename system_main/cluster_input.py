import pandas as pd
import pickle
import os
from sklearn.preprocessing import StandardScaler
from kmodes import kprototypes

# 파일 경로 설정
MODEL_FILE = './kprototype_model.pkl'
CLUSTER_FILE = './data/temp_cluster.csv'

# 데이터 및 모델 로드 함수
def load_data_and_model():
    """
    temp_clutster.csv와 kmeans_model.pkl 파일을 로드합니다.
    """
    if os.path.exists(CLUSTER_FILE) and os.path.exists(MODEL_FILE):
        try:
            # CSV 파일 읽기 (utf-8-sig 인코딩)
            df_cluster = pd.read_csv(CLUSTER_FILE, encoding='utf-8-sig')
        except UnicodeDecodeError:
            try:
                # 만약 utf-8-sig가 실패하면 cp949로 시도
                df_cluster = pd.read_csv(CLUSTER_FILE, encoding='cp949')
            except Exception as e:
                raise ValueError(f"CSV 파일 읽기 중 문제가 발생했습니다: {e}")

        try:
            # Pickle로 모델 로드
            with open(MODEL_FILE, 'rb') as f:
                model = pickle.load(f)
            # 모델에서 학습된 피처 이름 가져오기
            model_features = model.feature_names_in_ if hasattr(model, 'feature_names_in_') else None

        except Exception as e:
            raise ValueError(f"모델 로드 중 오류 발생: {e}")
        
        return df_cluster, model, model_features
    else:
        raise FileNotFoundError("필요한 파일이 누락되었습니다: CSV 또는 모델 파일")

# 데이터 전처리 함수
def preprocessing_dataframe(df, model_features):
    """
    입력 데이터를 학습된 데이터와 동일한 형태로 전처리합니다.
    """
    ## 범주형 데이터를 원-핫 인코딩
    #df = pd.get_dummies(df)

    # # 학습된 피처 이름 기준으로 정렬 및 누락된 피처 추가
    # for feature in model_features:
    #     if feature not in df.columns:
    #         df[feature] = 0  # 누락된 피처를 기본값 0으로 추가
    # df = df[model_features]

    # 정규화 수행
    numeric_features = ['AGE_GRP', 'TRAVEL_COMPANIONS_NUM', 'SLEEP']
    if all(col in df.columns for col in numeric_features):
        scaler = StandardScaler()
        df[numeric_features] = scaler.fit_transform(df[numeric_features])
    return df

# 클러스터 예측 함수
def cluster_predict(age_grp, cp_num, cp_status, day, purpose, traffic):
    """
    입력 데이터를 받아 클러스터를 예측합니다.
    """

    # 입력값을 데이터프레임 형태로 준비
    input_data = pd.DataFrame({
        'AGE_GRP': [age_grp],
        'TRAVEL_COMPANIONS_NUM': [cp_num],
        'TRAVEL_STATUS_ACCOMPANY': [cp_status],
        'SLEEP': [day - 1],
        'ACTIVITY': [', '.join(purpose) if isinstance(purpose, list) else purpose],
        'RESULT_MVMN': [traffic]
    })
    
    # 데이터 및 모델 로드
    df_cluster, model, model_features = load_data_and_model()

    # ACTIVITY 컬럼을 문자열 형태로 변환
    df_cluster['ACTIVITY'] = df_cluster['ACTIVITY'].apply(
        lambda x: ', '.join(x) if isinstance(x, list) else x
    )

    # 기존 데이터와 입력 데이터를 병합
    try:
        combined_data = pd.concat([df_cluster.drop(columns=['TRAVEL_ID', 'Cluster']), input_data], ignore_index=True)
    except KeyError as e:
        raise KeyError(f"데이터 병합 중 오류 발생: {e}")
    
    # 데이터 전처리
    try:
        preprocessed_data = preprocessing_dataframe(combined_data, model_features)
    except Exception as e:
        raise Exception(f"데이터 전처리 중 오류 발생: {e}")

    # 클러스터 예측
    try:
        categorical_indices = [preprocessed_data.columns.get_loc(col) for col in preprocessed_data.select_dtypes(include=['object', 'category']).columns]     
        predicted_cluster = model.predict(preprocessed_data.tail(1), categorical=categorical_indices)
    except ValueError as e:
        raise ValueError(f"클러스터 예측 중 오류 발생: {e}")
    return predicted_cluster[0]