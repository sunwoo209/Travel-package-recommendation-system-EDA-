import pandas as pd

def load_data():
    lodging_data= pd.read_csv('data/tn_visit_area_info_방문지정보2nd.csv')
    lodging_data= lodging_data[lodging_data['VISIT_AREA_TYPE_CD'] == 24]

    # 숙박일수를 통해 같은 이름의 숙박 업소가 여러번 나오더라도 실제 숙박 일수를 알아내기 위해 추가
    lodging_data['VISIT_START_YMD'] = pd.to_datetime(lodging_data['VISIT_START_YMD'])
    lodging_data['VISIT_END_YMD'] = pd.to_datetime(lodging_data['VISIT_END_YMD'])
    lodging_data['SLEEP'] = (lodging_data['VISIT_END_YMD'] - lodging_data['VISIT_START_YMD']).dt.days

    tv = pd.read_csv('data/tn_travel_여행.csv', encoding='ANSI')
    tm = pd.read_csv('data/tn_traveller_master_여행객 Master.csv', encoding='ANSI')

    lodging_data = pd.merge(lodging_data, tv[['TRAVEL_ID', 'TRAVELER_ID', 'MVMN_NM']], on='TRAVEL_ID', how='left')
    lodging_data = pd.merge(lodging_data, tm[['TRAVELER_ID','TRAVEL_STATUS_ACCOMPANY']], on='TRAVELER_ID', how='left')
    #lodging_data['MVMN_NM'].fillna("자가용", inplace=True)
    
    return lodging_data

def load_lodging_data():
    lodging_data = load_data()

    lodging_data['TRAVEL_STATUS_ACCOMPANY'] = lodging_data['TRAVEL_STATUS_ACCOMPANY'].map(accompany_mapping)

    # 대중교통 여행 횟수만 세서 나중에 보정해주기 
    # 대중교통 여행 횟수 / 전체 여행 횟수 => 이 비율에 따라 대중교통 여행인지 아닌지에 따라 추가 점수 주기 
    mvmn_map = {
        '자가용' : 0,
        '대중교통 등' : 1
    }
    lodging_data['MVMN_NM'] = lodging_data['MVMN_NM'].map(mvmn_map)

    # 보정 함수 적용
    # REVISIT_INTENTION based on RCMDTN_INTENTION
    lodging_data['CORRECTED_REVISIT_INTENTION'] = lodging_data['REVISIT_INTENTION'] * (
        1 - 0.1 * (lodging_data['RCMDTN_INTENTION'] < 3).astype(float)
    )

    # RCMDTN_INTENTION based on REVISIT_INTENTION
    lodging_data['CORRECTED_RCMDTN_INTENTION'] = lodging_data['RCMDTN_INTENTION'] * (
        1 - 0.1 * (lodging_data['REVISIT_INTENTION'] < 3).astype(float)
    )

    # 가중치 계산
    lodging_data['FINAL_RECOMMENDATION_SCORE'] = (
        0.20 * lodging_data['REVISIT_YN'].replace({'Y': 1, 'N': 0}) +
        0.35 * lodging_data['DGSTFN'] +
        0.25 * lodging_data['CORRECTED_REVISIT_INTENTION'] +
        0.20 * lodging_data['CORRECTED_RCMDTN_INTENTION']
    )

    # 한 숙소를 여러번 들린 경우도 있어서 그룹화하여 처리
    grouped_lodgings = lodging_data.groupby(['VISIT_AREA_NM']).agg({
        'FINAL_RECOMMENDATION_SCORE' : ['mean', 'max', 'min'],
        'MVMN_NM' : 'sum',
        'TRAVEL_STATUS_ACCOMPANY' : 'sum',
        'X_COORD' : 'first',
        'Y_COORD' : 'first',
        'ROAD_NM_ADDR' : 'first',
        'TRAVEL_ID' : 'count',
        'SLEEP' : 'sum'
    }).reset_index()

    grouped_lodgings.columns = ['VISIT_AREA_NM', 'AVG_SCORE', 'MAX_SCORE', 'MIN_SCORE', 'SUM_MVMN_TYPE', 'SUM_FAMILY_TPYE', 'X_COORD', 'Y_COORD', 'ROAD_NM_ADDR', 'TOTAL_COUNT', 'TOTAL_SLEEP']

    grouped_lodgings = grouped_lodgings[~grouped_lodgings['Y_COORD'].isna()]

    return grouped_lodgings

import math

# X = 경도 / y = 위도
def haversine(lat1, lon1, lat2, lon2): 
    # 지구의 반지름 (킬로미터 단위)
    R = 6371.0
    
    # 위도와 경도를 라디안 단위로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도와 경도의 차이 계산
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    
    # 하버사인 공식 적용
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # 거리 계산
    distance = R * c
    
    return distance

# 가족 여행 횟수만 세서 나중에 보정해주기 
# 가족 여행 횟수 / 전체 여행 횟수 => 이 비율에 따라 가족 여행인지 아닌지에 따라 추가 점수 주기 
accompany_mapping = {
    '2인 여행(가족 외)' : 0,
    '자녀 동반 여행' : 1,
    '나홀로 여행' : 0,
    '3인 이상 여행(가족 외)' : 0,
    '2인 가족 여행' : 1,
    '부모 동반 여행' : 1,
    '3대 동반 여행(친척 포함)' : 1,
    '3인 이상 가족 여행(친척 포함)' : 1
}

simple_category_mapping = {
    '자가용(승용/승합/트럭 등등)' : '자가용',
    '렌터카(승용/승합/버스 등등)' : '렌터카',
    '캠핑카(자차 및 렌탈)' : '렌터카',
    '택시' : '택시',
    '지하철' : '지하철',
    '고속전철(ITX 등)' : '기차',
    'KTX/SRT(고속열차)' : '기차',
    '새마을/무궁화열차' : '기차',
    '항공기' : '항공기',
    '배/선박' : '배/선박',
    '관광버스' : '버스',
    '시외/고속버스' : '버스',
    '시내/마을버스' : '버스',
    '자전거' : '도보',
    '도보' : '도보',
    '기타' : '기타'
}

def get_lodging_score_result(x_coord, y_coord, boundary, mvmn, family):
    df = load_lodging_data()

    n_mvmn = 0 if (mvmn == '자가용') else 1
    n_family = accompany_mapping[family]

    #거리 측정
    df['DISTANCE'] = df.apply(
        lambda row: haversine(y_coord, x_coord, row['Y_COORD'], row['X_COORD']),
        axis=1
    )
    
    filtered_df = df[df['DISTANCE'] <= boundary]

    #점수 가산
    filtered_df = filtered_df.copy() 
    filtered_df.loc[:, 'FINAL_SCORE'] = filtered_df.apply(
        lambda row: row['AVG_SCORE'] 
        + ((row['SUM_MVMN_TYPE'] / row['TOTAL_COUNT']) if n_mvmn == 1 else ((row['TOTAL_COUNT'] - row['SUM_MVMN_TYPE']) / row['TOTAL_COUNT'])) * 0.5
        + ((row['SUM_FAMILY_TPYE'] / row['TOTAL_COUNT']) if n_family == 1 else ((row['TOTAL_COUNT'] - row['SUM_FAMILY_TPYE']) / row['TOTAL_COUNT'])) * 0.5
        , axis=1
    )
    return filtered_df.sort_values(['FINAL_SCORE'], ascending=False).head(1)

# # 예제 코드 
# test_case = get_lodging_score_result(126.915684, 33.501715, 3, '기차', '자녀 동반 여행')
# print(test_case)

