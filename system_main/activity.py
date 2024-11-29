import pandas as pd
import numpy as np
import math
from geopy.distance import geodesic

############################ 데이터 로드 ############################

def load_datasets():
    df_tv = pd.read_csv("data/tn_travel_여행.csv", encoding='ANSI')
    df_tm = pd.read_csv('data/tn_traveller_master_여행객 Master.csv', encoding='ANSI')
    df_acthis = pd.read_csv('data/tn_activity_his_활동내역.csv', encoding='utf-8')
    df_visarea = pd.read_csv('data/tn_visit_area_info_방문지정보2nd.csv')
    df_code = pd.read_csv('data/tc_codeb_코드B.csv', encoding='ANSI')
    df_cluster = pd.read_csv('data/temp_cluster.csv', encoding='ANSI')
    return df_tv, df_tm, df_acthis, df_visarea, df_code, df_cluster

############################ 전처리 단계 ############################

def preprocess_data():
    # 데이터 로드
    df_tv, df_tm, df_acthis, df_visarea, df_code, df_cluster = load_datasets()

    # 여행 데이터 병합
    df_tm = merge_travel_data(df_tm, df_tv)
    
    # 여행 목적 매핑 및 병합
    df_tm = map_and_merge_travel_purpose(df_tm, df_tv)
    
    # 활동 데이터 처리 및 매핑
    df_tm = process_and_map_activity(df_tm, df_acthis, df_code)
    
    # 방문지 데이터 전처리
    processed_df = preprocessed(df_visarea, df_acthis, df_code, df_tm)
    
    # 가중치 계산
    final_df = calculate_weights(processed_df, df_cluster)
    
    return final_df

############################ 보조 함수들 ############################

# 여행 데이터 병합
def merge_travel_data(df_tm, df_tv):
    return df_tm.merge(df_tv[['TRAVELER_ID', 'TRAVEL_ID']], on='TRAVELER_ID', how='left')

# 여행 목적 매핑 및 병합
def map_and_merge_travel_purpose(df_tm, df_tv):
    mapping_dict = {
        1: 2, 2: 3, 3: 4, 4: 4, 5: 3, 6: 4, 7: 3, 8: 5,
        9: 4, 10: 5, 11: 3, 12: 4, 13: 6, 21: 5, 22: 4, 23: 5,
        24: 4, 25: 4, 26: 4, 27: 3, 28: 3
    }

    def map_travel_purpose(purpose_str):
        purpose_codes = map(int, purpose_str.split(';'))
        return ';'.join([str(mapping_dict.get(code, code)) for code in purpose_codes])

    df_tv['TRAVEL_PURPOSE'] = df_tv['TRAVEL_PURPOSE'].apply(map_travel_purpose)
    return df_tm.merge(df_tv[['TRAVEL_ID', 'TRAVEL_PURPOSE']], on='TRAVEL_ID', how='left')

# 활동 데이터 처리 및 매핑
def process_and_map_activity(df_tm, df_acthis, df_code):
    df_list = df_acthis.groupby('TRAVEL_ID')['ACTIVITY_TYPE_CD'].apply(list).reset_index()
    df_tm = pd.merge(df_tm, df_list[['TRAVEL_ID', 'ACTIVITY_TYPE_CD']], on='TRAVEL_ID', how='left')

    df_tm['TRAVEL_PURPOSE'] = df_tm['TRAVEL_PURPOSE'].apply(lambda x: list(map(int, x.split(';'))))

    def calculate_weighted_activity(row):
        activity_values = row['ACTIVITY_TYPE_CD']
        travel_purpose_values = row['TRAVEL_PURPOSE']
        filtered_values = [value for value in activity_values if value in travel_purpose_values]
        weighted_values = [activity_values.count(value) * (2 if value in travel_purpose_values else 1) for value in filtered_values]
        return filtered_values[weighted_values.index(max(weighted_values))] if weighted_values else 99

    df_tm['ACTIVITY'] = df_tm.apply(calculate_weighted_activity, axis=1)
    df_tm['ACTIVITY'] = df_tm['ACTIVITY'].astype(str)
    df_tm['ACTIVITY'] = df_tm['ACTIVITY'].map(df_code[df_code['cd_a'] == 'ACT'].set_index('cd_b')['cd_nm'])
    return df_tm

# 방문지 데이터 전처리
def preprocessed(df_visarea, df_acthis, df_code, df_tm):
    exclude_values = [9,10, 11, 12, 21, 22, 23, 24]
    filtered_df = df_visarea[~df_visarea['VISIT_AREA_TYPE_CD'].isin(exclude_values)]
    filtered_df = filtered_df[['VISIT_AREA_ID', 'TRAVEL_ID', 'VISIT_AREA_NM', 'ROAD_NM_ADDR', 
                               'X_COORD', 'Y_COORD', 'REVISIT_YN', 'DGSTFN', 
                               'REVISIT_INTENTION', 'RCMDTN_INTENTION', 'Calculated_Final_Score', 'SIDO_NM', 'SGG_NM', 'DONG_NM']]
    df = pd.merge(filtered_df, df_acthis[['VISIT_AREA_ID', 'TRAVEL_ID', 'ACTIVITY_TYPE_CD']], on=['VISIT_AREA_ID', 'TRAVEL_ID'], how='left')
    df['ACTIVITY_TYPE_CD'].fillna(99, inplace=True)
    df['ACTIVITY_TYPE_CD'] = df['ACTIVITY_TYPE_CD'].astype(int).astype(str)
    df['ACTIVITY_TYPE_CD'] = df['ACTIVITY_TYPE_CD'].map(df_code[df_code['cd_a'] == 'ACT'].set_index('cd_b')['cd_nm'])
    df = pd.merge(df, df_tm[['TRAVEL_ID', 'ACTIVITY']], on='TRAVEL_ID', how='left')
    df['REVISIT_YN'] = df['REVISIT_YN'].replace({'Y': 1, 'N': 0})
    return df

# 가중치 계산
def calculate_weights(df, df_cluster):
    df['ACT_WEIGHT'] = np.where(
        df['ACTIVITY_TYPE_CD'] == df['ACTIVITY'],
        df['DGSTFN'] * 0.4 + df['REVISIT_YN'] * 0.3 + df['REVISIT_INTENTION'] * 0.15 + df['RCMDTN_INTENTION'] * 0.15,
        0
    )
    df['ACT_WEIGHT'] /= df['ACT_WEIGHT'].max()
    df['TOTAL_WEIGHT'] = df['Calculated_Final_Score'] + df['ACT_WEIGHT']
    return pd.merge(df, df_cluster[['TRAVEL_ID', 'Cluster']], on='TRAVEL_ID', how='left')

############################ 추천 함수 ############################

def activity_first_rmd(cluster_label, user_lat, user_lon, top_n=10):
    df = preprocess_data()
    cluster_data = df[df['Cluster'] == cluster_label].copy()
    grouped_data = cluster_data.groupby(['X_COORD', 'Y_COORD'], as_index=False).agg({'TOTAL_WEIGHT': 'mean'}).rename(columns={'TOTAL_WEIGHT': 'TOTAL_WEIGHT_avg'})
    merged_data = pd.merge(cluster_data, grouped_data, on=['X_COORD', 'Y_COORD'], how='left')
    top_recommendations = merged_data.sort_values(by='TOTAL_WEIGHT_avg', ascending=False).drop_duplicates(subset=['X_COORD', 'Y_COORD']).head(top_n).reset_index(drop=True)

    def calculate_distance(row):
        return geodesic((user_lat, user_lon), (row['Y_COORD'], row['X_COORD'])).km

    top_recommendations['distance_to_user'] = top_recommendations.apply(calculate_distance, axis=1).round(2)
    return top_recommendations[['VISIT_AREA_NM', 'ROAD_NM_ADDR', 'X_COORD', 'Y_COORD', 'TOTAL_WEIGHT_avg', 'distance_to_user', 'Cluster']]

def activity_second_rmd(cluster_label, user_lat, user_lon, radius=5, top_n=10, exclude_coords=None):
    """
    첫 번째 추천 지역과 겹치지 않는 두 번째 추천 지역 반환.
    """
    df = preprocess_data()
    cluster_data = df[df['Cluster'] == cluster_label].copy()

    # 거리 계산
    cluster_data['DISTANCE'] = cluster_data.apply(
        lambda row: geodesic((user_lat, user_lon), (row['Y_COORD'], row['X_COORD'])).km,
        axis=1
    )
    nearby_data = cluster_data[cluster_data['DISTANCE'] <= radius]

    # 제외 좌표 필터링
    if exclude_coords:
        nearby_data = nearby_data[~nearby_data.apply(
            lambda row: (row['X_COORD'], row['Y_COORD']) in exclude_coords, axis=1
        )]

    # 가중치 계산 및 추천
    grouped_data = nearby_data.groupby(['X_COORD', 'Y_COORD'], as_index=False).agg({'TOTAL_WEIGHT': 'mean'})
    grouped_data.rename(columns={'TOTAL_WEIGHT': 'TOTAL_WEIGHT_avg'}, inplace=True)
    merged_data = pd.merge(nearby_data, grouped_data, on=['X_COORD', 'Y_COORD'], how='left')

    top_recommendations = (
        merged_data
        .sort_values(by='TOTAL_WEIGHT_avg', ascending=False)
        .drop_duplicates(subset=['X_COORD', 'Y_COORD'])
        .head(top_n)
        .reset_index(drop=True)
    )

    return top_recommendations[['VISIT_AREA_NM', 'ROAD_NM_ADDR', 'X_COORD', 'Y_COORD', 'TOTAL_WEIGHT_avg', 'DISTANCE']]

def des_act_rmd(cluster_label, target_sido, target_sgg=None, target_dong=None, top_n=10):
    df = preprocess_data()
    filtered_df = df[df['Cluster'] == cluster_label]
    if not target_sgg and not target_dong:
        filtered_df = filtered_df[filtered_df['SIDO_NM'].str.contains(target_sido, na=False)]
    elif not target_dong:
        filtered_df = filtered_df[filtered_df['SIDO_NM'].str.contains(target_sido, na=False) & filtered_df['SGG_NM'].str.contains(target_sgg, na=False)]
    else:
        filtered_df = filtered_df[filtered_df['SIDO_NM'].str.contains(target_sido, na=False) & filtered_df['SGG_NM'].str.contains(target_sgg, na=False) & filtered_df['DONG_NM'].str.contains(target_dong, na=False)]

    grouped_df = filtered_df.groupby(['X_COORD', 'Y_COORD'], as_index=False).agg({'TOTAL_WEIGHT': 'mean'})
    merged_df = pd.merge(filtered_df, grouped_df, on=['X_COORD', 'Y_COORD'], suffixes=('', '_avg'))
    unique_activities = merged_df.drop_duplicates(subset=['X_COORD', 'Y_COORD'])
    top_activities = unique_activities.nlargest(top_n, 'TOTAL_WEIGHT_avg').reset_index(drop=True)
    return top_activities[['VISIT_AREA_NM', 'ROAD_NM_ADDR', 'X_COORD', 'Y_COORD', 'TOTAL_WEIGHT_avg', 'Cluster']]

# # # 첫 번째 추천 결과
# first_recommendations = activity_first_rmd(cluster_label=1, user_lat=37.5665, user_lon=126.9780, top_n=5)
# print(first_recommendations)
# # # 첫 번째 추천 결과의 좌표 추출
# # exclude_coords = list(zip(first_recommendations['X_COORD'], first_recommendations['Y_COORD']))

# # # 두 번째 추천 결과
# # second_recommendations = activity_second_rmd(
# #     cluster_label=1, 
# #     user_lat=37.5665, 
# #     user_lon=126.9780, 
# #     radius=3, 
# #     top_n=3, 
# #     exclude_coords=exclude_coords
# # )

# # print("First Recommendations:")
# # print(first_recommendations)

# # print("\nSecond Recommendations (Excluding First):")
# # print(second_recommendations)
