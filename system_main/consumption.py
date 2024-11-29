import pandas as pd
from geocoding import get_region_from_coords


visited_places = set()  # 방문한 지역 정보를 관리하는 세트

def food_top_place(x, y, cluster):
    """
    클러스터와 좌표 정보를 기반으로 상위 1개 음식점을 가중 확률로 추천하며,
    방문한 지역은 제외합니다. 음식점 정보를 모두 사용했을 경우 클러스터 제한을 해제합니다.
    """
    try:
        # 데이터 로드
        consumption_data = pd.read_csv('data/consumption_category.csv', encoding='utf-8-sig')
        cluster_data = pd.read_csv('data/temp_cluster.csv', encoding='cp949')

        # 1. 입력된 좌표를 기반으로 시/도(SIDO_NM) 및 구 단위(SGG_NM) 추출
        sido_nm, sgg_nm = get_region_from_coords(x, y)
        if not sido_nm or not sgg_nm or sido_nm == "알 수 없음" or sgg_nm == "알 수 없음":
            print(f"좌표 ({x}, {y})에서 지역 정보를 찾을 수 없어 기본값을 사용합니다.")
            return None

        # 2. 클러스터에서 TRAVEL_ID 필터링
        relevant_travelers = cluster_data[cluster_data['Cluster'] == cluster]['TRAVEL_ID']

        # 3. 필터링 데이터 생성 함수
        def filter_data(consumption_data, travelers_filter=True):
            """필터링된 데이터를 반환합니다."""
            return consumption_data[
                ((consumption_data['TRAVEL_ID'].isin(relevant_travelers)) if travelers_filter else True) &  # 클러스터 필터 옵션
                (consumption_data['SIDO_NM'] == sido_nm) &                 # 시/도 필터
                (consumption_data['SGG_NM'] == sgg_nm) &                   # 구 단위 필터
                (consumption_data['CATEGORY'] == "음식점") &               # 음식점 필터
                (~consumption_data['VISIT_AREA_NM'].isin(visited_places))  # 중복 제거
            ]

        # 4. 데이터 필터링
        filtered_consumption = filter_data(consumption_data, travelers_filter=True)

        # 5. 클러스터 데이터가 부족할 경우 클러스터 제한 해제
        if filtered_consumption.empty:
            filtered_consumption = filter_data(consumption_data, travelers_filter=False)

        # 6. 재추천할 데이터가 없는 경우
        if filtered_consumption.empty:
            print("추천할 음식점이 더 이상 없습니다.")
            return None

        # 명시적으로 복사본을 생성
        filtered_consumption = filtered_consumption.copy()

        #7. 점수 양수화
        min_score = filtered_consumption['Calculated_Final_Score'].min()
        if min_score < 0:
            filtered_consumption['Calculated_Final_Score'] -= min_score  # 모든 점수를 양수로 변환


        # 8. 상위 10개 추출
        top_places = filtered_consumption.nlargest(10, 'Calculated_Final_Score')
        if top_places.empty:
            print("상위 10개 데이터를 추출할 수 없습니다.")
            return None

        # 9. 가중치 계산
        top_places.loc[:, 'Weight'] = (
            top_places['Calculated_Final_Score'] / 
            top_places['Calculated_Final_Score'].sum()
        ).fillna(0)

        # 10. 가중 확률 기반으로 1개 랜덤 선택
        recommended_place = top_places.sample(n=1, weights=top_places['Weight'])

        # 11. 결과 구성
        result = {
            'VISIT_AREA_NM': recommended_place.iloc[0].get('VISIT_AREA_NM', '정보 없음'),
            'ROAD_NM_ADDR': recommended_place.iloc[0].get('ROAD_NM_ADDR', '정보 없음'),
            'X_COORD': recommended_place.iloc[0].get('X_COORD', '정보 없음'),
            'Y_COORD': recommended_place.iloc[0].get('Y_COORD', '정보 없음')
        }

        # 12. 방문한 지역에 추가
        visited_places.add(result['VISIT_AREA_NM'])

        return result

    except FileNotFoundError as e:
        print(f"파일을 찾을 수 없습니다: {e}")
        return None
    except Exception as e:
        print(f"알 수 없는 에러가 발생했습니다: {e}")
        return None

# for i in range(20):
#     result = food_top_place(126.9780, 37.5665, cluster=1)
#     print(result)


