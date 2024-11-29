import tkinter as tk
from tkinter import ttk
from geocoding import get_coordinates
from cluster_input import cluster_predict, load_data_and_model
import pandas as pd
import os
from activity import activity_first_rmd, des_act_rmd , activity_second_rmd
from Transports import haversine
from consumption import food_top_place
from Lodging import get_lodging_score_result  

# 동행 형태와 동행자 수 매핑
COMPANION_MAP = {
    "나홀로 여행": 0,
    "2인 여행(가족 외)": 1,
    "2인 가족 여행": 1,
}



# 숙박 일수 매핑
def day_to_numberic_day(day):
    type_day = {
        '당일': 0,
        '1박 2일': 1,
        '2박 3일': 2,
        '3박 4일': 3,
        '4박 5일': 4,  
        '5박 6일': 5,
        '6박 7일': 6,
        '7박 8일': 7
    }
    return type_day.get(day, -1)  # 잘못된 입력에 대해 -1 반환


def numberic_day_to_day(num):
    """
    숫자 값을 텍스트 숙박 일수로 변환
    """
    numeric_to_day = {
        0: '당일',
        1: '1박 2일',
        2: '2박 3일',
        3: '3박 4일',
        4: '4박 5일',
        5: '5박 6일',
        6: '6박 7일',
        7: '7박 8일'
    }
    return numeric_to_day.get(num, str(num))  # 변환 실패 시 숫자 그대로 반환

# 드롭다운 리스트
REGION_OPTIONS = ['상관없음', '경기', '서울', '인천', '경남', '부산', '충남', '전북특별자치도', 
                    '제주특별자치도', '대전', '강원특별자치도', '울산', '충북', '경북', 
                    '광주', '대구', '전남', '세종특별자치시']


# CSV 파일 경로
INPUTS_FILE = "user_inputs_save.csv"


# 이전 입력값 불러오기
def load_previous_inputs():
    if os.path.exists(INPUTS_FILE):
        try:
            previous_data = pd.read_csv(INPUTS_FILE).iloc[-1].to_dict()  # 마지막 입력값 불러오기
            # 숫자 숙박 일수를 텍스트로 변환
            if "숙박 일수" in previous_data:
                try:
                    previous_data["숙박 일수"] = numberic_day_to_day(int(previous_data["숙박 일수"]))
                except ValueError:
                    pass  # 변환 실패 시 원래 값 유지
            return previous_data
        except Exception as e:
            print(f"입력값 로드 중 오류 발생: {e}")
    return {}  # 입력값이 없거나 파일이 없으면 빈 딕셔너리 반환
# 나이를 숫자 연령대로 변환하는 함수
def age_to_age_grp(age):
    """
    나이를 10, 20, 30 등 숫자 범주의 연령대로 변환
    """
    if age < 20:
        return 10
    elif age < 30:
        return 20
    elif age < 40:
        return 30
    elif age < 50:
        return 40
    elif age < 60:
        return 50
    else:
        return 60



# Tkinter GUI 만들기
def main_gui():
    # 모델과 데이터 로드
    try:
        df_cluster, kmeans_model, model_features = load_data_and_model()  # 반환값 3개로 수정
    except Exception as e:
        print(f"데이터 및 모델 로드 실패: {e}")
        return

    # 입력값 저장용 리스트
    input_data = []

    # 이전 입력값 로드
    previous_inputs = load_previous_inputs()

    root = tk.Tk()
    root.title("여행 패키지 추천 프로그램")
    # 숙박 일수 딕셔너리 정의
    type_day = {
        '당일': 0,
        '1박 2일': 1,
        '2박 3일': 2,
        '3박 4일': 3,
        '4박 5일': 4,
        '5박 6일': 5,
        '6박 7일': 6,
        '7박 8일': 7
    }
    
    

    # 입력 필드: 현재 위치 입력
    tk.Label(root, text="현재 위치 \n(도로명 주소,일반주소,장소이름 등):").grid(row=0, column=0, padx=10, pady=5)
    location_entry = tk.Entry(root, width=50)
    location_entry.grid(row=0, column=1, padx=10, pady=5)
    location_entry.insert(0, previous_inputs.get("현재 위치", ""))  # 이전 값 채우기

    # 입력 필드: 선호 지역 선택
    tk.Label(root, text="선호 지역:").grid(row=1, column=0, padx=10, pady=5)
    region_combo = ttk.Combobox(root, values=REGION_OPTIONS)
    region_combo.grid(row=1, column=1, padx=10, pady=5)
    region_combo.set(previous_inputs.get("선호 지역", ""))  # 이전 값 채우기

    # 입력 필드: 숙박 일수 선택
    tk.Label(root, text="숙박 일수:").grid(row=2, column=0, padx=10, pady=5)
    sleep_combo = ttk.Combobox(root, values=list(type_day.keys()))
    sleep_combo.grid(row=2, column=1, padx=10, pady=5)
    sleep_combo.set(previous_inputs.get("숙박 일수", ""))  # 이전 값 채우기

    # 입력 필드: 나이
    tk.Label(root, text="나이:").grid(row=3, column=0, padx=10, pady=5)
    age_entry = tk.Entry(root)
    age_entry.grid(row=3, column=1, padx=10, pady=5)
    age_entry.insert(0, previous_inputs.get("나이", ""))  # 이전 값 채우기

    # 입력 필드: 동행자 형태
    tk.Label(root, text="동행자 형태:").grid(row=4, column=0, padx=10, pady=5)
    cp_status_combo = ttk.Combobox(root, values=list(COMPANION_MAP.keys()) + ["자녀 동반 여행"] + ["3인 이상 여행(가족 외)"]
                                    + ["3대 동반 여행(친척 포함)"] + ["3인 이상 가족 여행(친척 포함)"])
    cp_status_combo.grid(row=4, column=1, padx=10, pady=5)
    cp_status_combo.set(previous_inputs.get("동행자 형태", ""))  # 이전 값 채우기

    # 입력 필드: 동행자 수
    tk.Label(root, text="동행자 수(본인제외):").grid(row=5, column=0, padx=10, pady=5)
    cp_num_entry = tk.Entry(root)
    cp_num_entry.grid(row=5, column=1, padx=10, pady=5)
    cp_num_entry.insert(0, previous_inputs.get("동행자 수", ""))  # 이전 값 채우기

    # 동행 형태 선택 시 자동으로 동행자 수 채우기
    def on_cp_status_selected(event):
        selected_status = cp_status_combo.get()
        if selected_status in COMPANION_MAP:
            cp_num_entry.delete(0, tk.END)
            cp_num_entry.insert(0, COMPANION_MAP[selected_status])
        else:
            cp_num_entry.delete(0, tk.END)

    cp_status_combo.bind("<<ComboboxSelected>>", on_cp_status_selected)

    # 이동 수단 선택
    tk.Label(root, text="이동 수단:").grid(row=6, column=0, padx=10, pady=5)
    traffic_combo = ttk.Combobox(root, values=['자가용', '버스', '기차', '지하철', '택시', '배/선박', '렌터카', '항공기', '도보', '기타'])
    traffic_combo.grid(row=6, column=1, padx=10, pady=5)
    traffic_combo.set(previous_inputs.get("이동 수단", ""))  # 이전 값 채우기

    # 여행 목적 드롭다운
    tk.Label(root, text="여행 목적:").grid(row=7, column=0, padx=10, pady=5)
    purpose_combo = ttk.Combobox(root, values=['없음', '쇼핑 / 구매', '체험 활동 / 입장 및 관람', '휴식', '단순 구경 / 산책 / 걷기', '기타 활동'])
    purpose_combo.grid(row=7, column=1, padx=10, pady=5)
    purpose_combo.set(previous_inputs.get("여행 목적", ""))  # 이전 값 채우기

    # 실행 버튼
    predict_button = tk.Button(root, text="선택 완료", command=lambda: selection_complete())
    predict_button.grid(row=8, column=0, columnspan=2, pady=10)

    # 결과 출력 레이블을 미리 생성
    result_label_cluster = tk.Label(root, text="클러스터: ", justify="left")
    result_label_cluster.grid(row=9, column=0, columnspan=2, padx=10, pady=5)

    result_label_region = tk.Label(root, text="시군구: ", justify="left")
    result_label_region.grid(row=10, column=0, columnspan=2, padx=10, pady=5)

    result_label_coords = tk.Label(root, text="좌표: ", justify="left")
    result_label_coords.grid(row=11, column=0, columnspan=2, padx=10, pady=5)

    def show_recommendations(current_location, preferred_region, cluster_label, traffic, cp_status, user_lat, user_lon, top_n):

        # 사용자의 위도와 경도를 float로 변환
        user_lat = float(user_lat)
        user_lon = float(user_lon)

        # 새로운 tkinter 창 생성
        new_window = tk.Toplevel()
        new_window.title("추천 결과")

        # 상단에 현재 위치와 선호 지역 표시
        info_text = f"현재 위치: {current_location} | 선호 지역: {preferred_region}"
        tk.Label(new_window, text=info_text, font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=10, pady=10)

        # 첫 번째 추천 지역 계산
        if preferred_region == "상관없음":
            recommendations = activity_first_rmd(cluster_label, user_lat, user_lon, top_n)
        else:
            recommendations = des_act_rmd(cluster_label, target_sido=preferred_region, top_n=top_n)

        # 추천 지역과 사용자의 거리 계산
        recommendations['직선 거리 (km)'] = recommendations.apply(
            lambda row: round(haversine(user_lat, user_lon, row['Y_COORD'], row['X_COORD']), 2),
            axis=1
        )

        # 음식점 추천 결과 추가 (점심)
        recommendations['점심'] = recommendations.apply(
            lambda row: food_top_place(row['X_COORD'], row['Y_COORD'], cluster_label),
            axis=1
        )

        # 숙박 정보 추가 (top_n > 1일 경우에만 실행)
        lodging_info_text = None
        if top_n > 1:  # 당일 여행이 아닌 경우
            first_activity = recommendations.iloc[0]  # 첫 번째 추천 액티비티
            lodging_info = get_lodging_score_result(
                first_activity['X_COORD'], 
                first_activity['Y_COORD'], 
                boundary=5,  # 숙박 기준 거리 반경 (예: 5km)
                mvmn=traffic, 
                family=cp_status
            )
            # 숙박 정보 텍스트 생성
            if not lodging_info.empty:
                lodging_info_text = f"{lodging_info.iloc[0]['VISIT_AREA_NM']} ({lodging_info.iloc[0]['ROAD_NM_ADDR']})"
            else:
                lodging_info_text = "추천 데이터 없음"

        # 첫 번째 추천 지역 GUI 출력
        display_columns = ['추천 액티비티', '도로명 주소', '목표 거리(km)', '점심']
        for idx, col_name in enumerate(display_columns):
            tk.Label(new_window, text=col_name, font=("Arial", 10, "bold")).grid(row=1, column=idx, padx=5, pady=5)

        for row_idx, row in recommendations.iterrows():
            for col_idx, col_name in enumerate(['VISIT_AREA_NM', 'ROAD_NM_ADDR', '직선 거리 (km)']):
                value = row[col_name] if col_name in recommendations.columns else "정보 없음"
                tk.Label(new_window, text=value).grid(row=row_idx + 2, column=col_idx, padx=5, pady=5)

            # 점심 정보 출력
            food_result = row['점심']
            if food_result:
                food_text = f"{food_result['VISIT_AREA_NM']} ({food_result['ROAD_NM_ADDR']})"
            else:
                food_text = "추천 데이터 없음"
            tk.Label(new_window, text=food_text).grid(row=row_idx + 2, column=len(display_columns) - 1, padx=5, pady=5)

        # 두 번째 추천 지역 계산
        exclude_coords = list(zip(recommendations['X_COORD'], recommendations['Y_COORD']))
        second_recommendations = []
        display_columns_second = ['추천 액티비티', '도로명 주소', '저녁']
        if not recommendations.empty:
            for row_idx, row in recommendations.iterrows():
                food_result = row['점심']
                if food_result and isinstance(food_result, dict):
                    food_lon = food_result.get('X_COORD')
                    food_lat = food_result.get('Y_COORD')

                    if food_lon and food_lat:
                        second_rec = activity_second_rmd(
                            cluster_label, food_lat, food_lon, radius=5, top_n=1, exclude_coords=exclude_coords
                        )
                        if not second_rec.empty:
                            second_rec['점심'] = f"{food_result['VISIT_AREA_NM']} ({food_result['ROAD_NM_ADDR']})"
                            second_recommendations.append(second_rec)

        # 두 번째 추천 지역 출력
        tk.Label(new_window, text="두 번째 추천 지역", font=("Arial", 12, "bold")).grid(row=len(recommendations) + 3, column=0, columnspan=10, pady=10)

        if second_recommendations:
            second_recommendations_df = pd.concat(second_recommendations, ignore_index=True)
            for idx, col_name in enumerate(display_columns_second):
                tk.Label(new_window, text=col_name, font=("Arial", 10, "bold")).grid(row=len(recommendations) + 4, column=idx, padx=5, pady=5)

            second_row_offset = len(recommendations) + 5
            for row_idx, row in second_recommendations_df.iterrows():
                for col_idx, col_name in enumerate(['VISIT_AREA_NM', 'ROAD_NM_ADDR']):
                    value = row[col_name] if col_name in second_recommendations_df.columns else "정보 없음"
                    tk.Label(new_window, text=value).grid(row=second_row_offset + row_idx, column=col_idx, padx=5, pady=5)

                second_food_result = food_top_place(row['X_COORD'], row['Y_COORD'], cluster_label)
                if second_food_result:
                    second_food_text = f"{second_food_result['VISIT_AREA_NM']} ({second_food_result['ROAD_NM_ADDR']})"
                else:
                    second_food_text = "추천 데이터 없음"
                tk.Label(new_window, text=second_food_text).grid(row=second_row_offset + row_idx, column=len(display_columns_second) - 1, padx=5, pady=5)

        # 숙박 정보 출력 (top_n > 1일 때만 표시)
        if lodging_info_text:
            tk.Label(new_window, text="숙박 추천", font=("Arial", 12, "bold")).grid(row=len(recommendations) + 4, column=len(display_columns_second), padx=5, pady=5)
            tk.Label(new_window, text=lodging_info_text).grid(row=len(recommendations) + 5, column=len(display_columns_second), padx=5, pady=5)



    def selection_complete():
        location = location_entry.get()
        preferred_region = region_combo.get()  # 선호 지역 값
        age = age_entry.get()
        cp_status = cp_status_combo.get()
        cp_num = cp_num_entry.get()
        selected_day = sleep_combo.get()  # 선택한 값 확인
        day = day_to_numberic_day(selected_day)

        if day is None:  # 매핑 실패 처리
            result_label_cluster.config(text="숙박 일수를 올바르게 선택하세요.")
            return

        traffic = traffic_combo.get()
        purpose = purpose_combo.get()  # 드롭다운에서 선택된 여행 목적 값

        if not location:
            result_label_cluster.config(text="현재 위치를 입력하세요.")
            return

        # 현재 위치의 시군구 정보 가져오기
        x_coord, y_coord, region = get_coordinates(location)
        if region:
            result_label_cluster.config(text=f"사용자 위치 시군구: {region}")
            result_label_coords.config(text=f"사용자 좌표: ({x_coord}, {y_coord})")
        else:
            result_label_cluster.config(text="위치 정보를 가져올 수 없습니다.")
            result_label_coords.config(text="")
            return

        # 필수 입력값 확인
        if not all([age, cp_status, cp_num, purpose, traffic]):
            result_label_cluster.config(text="모든 입력 필드를 채워주세요.")
            result_label_region.config(text="")
            result_label_coords.config(text="")
            return


        day = day + 1
        try:
            # 나이를 숫자 연령대로 변환
            age_grp = age_to_age_grp(int(age))
            
            # 클러스터 예측
            cluster = cluster_predict(age_grp, int(cp_num), cp_status, day-1, purpose, traffic)

            # 결과 레이블 갱신
            result_label_cluster.config(text=f"클러스터: {cluster}")
            result_label_region.config(text=f"시군구: {region} | 선호 지역: {preferred_region}")
            
            # 입력값 저장
            input_data.append({
                "현재 위치": location,
                "선호 지역": preferred_region,
                "나이": age,
                "동행자 형태": cp_status,
                "동행자 수": cp_num,
                "숙박 일수": day,
                "이동 수단": traffic,
                "여행 목적": purpose,
                "클러스터": cluster,
                "시군구": region,
                "좌표": f"{x_coord}, {y_coord}"
            })

            try:
                df = pd.DataFrame(input_data)
                df.to_csv(INPUTS_FILE, index=False, encoding="utf-8-sig")
                print(f"입력값이 '{INPUTS_FILE}'에 저장되었습니다.")
            except Exception as e:
                print(f"입력값 저장 중 오류 발생: {e}")

            # 선호 지역이 "상관없음"일 때 다른 창을 띄움
            if preferred_region == "상관없음":
                show_all_recommendations(location, cluster, y_coord, x_coord, day, top_n=5)
            else:
                show_recommendations(region, preferred_region, cluster, traffic, cp_status, y_coord, x_coord, top_n=day)

        except Exception as e:
            result_label_cluster.config(text=f"오류: {str(e)}")
            result_label_region.config(text="")


    def show_all_recommendations(current_location, cluster_label, user_lat, user_lon, day, top_n):
        import tkinter as tk
        from geocoding import get_region_from_coords

        user_lat = float(user_lat)
        user_lon = float(user_lon)

        all_recommendations_window = tk.Toplevel()
        all_recommendations_window.title("모든 추천 지역 보기")

        tk.Label(all_recommendations_window, text=f"현재 위치: {current_location}", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=4, pady=10
        )

        recommendations = activity_first_rmd(cluster_label, user_lat, user_lon, top_n)
        recommendations['distance_to_user'] = recommendations.apply(
            lambda row: haversine(user_lat, user_lon, row['Y_COORD'], row['X_COORD']),
            axis=1
        )
        recommendations['시/도'] = recommendations.apply(
            lambda row: get_region_from_coords(row['X_COORD'], row['Y_COORD'])[0], axis=1
        )

        display_columns = ['시/도', 'VISIT_AREA_NM', 'ROAD_NM_ADDR', 'distance_to_user']
        headers = ['시/도', '추천 액티비티', '도로명 주소', '직선 거리 (km)']

        for idx, header in enumerate(headers):
            tk.Label(all_recommendations_window, text=header, font=("Arial", 10, "bold")).grid(row=1, column=idx, padx=5, pady=5)

        for row_idx, row in recommendations.iterrows():
            values = [row['시/도'], row['VISIT_AREA_NM'], row['ROAD_NM_ADDR'], f"{row['distance_to_user']:.2f} km"]
            for col_idx, value in enumerate(values):
                tk.Label(all_recommendations_window, text=value).grid(row=row_idx + 2, column=col_idx, padx=5, pady=5)

            tk.Button(
                all_recommendations_window,
                text=f"선택 {row_idx + 1}",
                command=lambda r=row: select_recommendation(r,day)
            ).grid(row=row_idx + 2, column=len(display_columns), padx=5, pady=5)

        def select_recommendation(selected_row,day):
            """
            사용자가 선택한 추천 지역을 처리하는 함수.
            선택한 지역 정보를 로그에 출력하고 창을 닫습니다.
            """
            #print(f"사용자가 선택한 지역: {selected_row['VISIT_AREA_NM']}")
            #print(f"도로명 주소: {selected_row['ROAD_NM_ADDR']}")
            #print(f"좌표: ({selected_row['X_COORD']}, {selected_row['Y_COORD']})")

            # 선택한 정보를 이후 프로세스로 전달
            show_recommendations(
                current_location=current_location,
                preferred_region=selected_row['시/도'],
                cluster_label=cluster_label,
                traffic=traffic_combo.get(),
                cp_status=cp_status_combo.get(),
                user_lat=user_lat,
                user_lon=user_lon,
                top_n=day
            )

            # 창 닫기
            all_recommendations_window.destroy()



    # 종료 시 입력값 저장 제거
    def on_close():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

# 메인 실행
if __name__ == "__main__":
    main_gui()  # GUI 실행
