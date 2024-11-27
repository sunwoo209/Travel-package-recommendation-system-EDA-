import math
import pandas as pd

# Define mappings
category_mapping = {
    1: '자가용(승용/승합/트럭 등등)',
    2: '렌터카(승용/승합/버스 등등)',
    3: '캠핑카(자차 및 렌탈)',
    4: '택시',
    5: '지하철',
    6: '고속전철(ITX 등)',
    7: 'KTX/SRT(고속열차)',
    8: '새마을/무궁화열차',
    9: '항공기',
    10: '배/선박',
    11: '관광버스',
    12: '시외/고속버스',
    13: '시내/마을버스',
    14: '자전거',
    15: '도보',
    16: '기타',
    50: '버스 + 지하철'
}

transport_priority = {
    '자가용(승용/승합/트럭 등등)' : 4,
    '렌터카(승용/승합/버스 등등)' : 3,
    '캠핑카(자차 및 렌탈)' : 3,
    '택시' : 2,
    '지하철' : 1,
    '고속전철(ITX 등)' : 4,
    'KTX/SRT(고속열차)' : 4,
    '새마을/무궁화열차' : 4,
    '항공기' : 10,
    '배/선박' : 4,
    '관광버스' : 3,
    '시외/고속버스' : 3,
    '시내/마을버스' : 1,
    '자전거' : 1,
    '도보' : 0.1,
    '기타' : 0.01,
    '출발' : 0
}


# 1. 하버사인 거리 계산
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # 지구 반지름 (km)
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    delta_lat, delta_lon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# 2. START와 END 조건 추가
def add_start_end_flags(df, boundary, input_coords):
    df['START_DISTANCE'] = df.apply(
        lambda row: haversine(input_coords['PREV_Y_COORD'], input_coords['PREV_X_COORD'], row['Y_COORD'], row['X_COORD']),
        axis=1
    )
    df['END_DISTANCE'] = df.apply(
        lambda row: haversine(input_coords['Y_COORD'], input_coords['X_COORD'], row['Y_COORD'], row['X_COORD']),
        axis=1
    )
    df['START'] = df['START_DISTANCE'] <= boundary
    df['END'] = df['END_DISTANCE'] <= boundary
    return df

# 3. 가능한 경로 생성
def generate_possible_routes(temp):
    start_points = temp[temp['START']][['TRAVEL_ID', 'VISIT_AREA_ID', 'START_DISTANCE']].rename(
        columns={'VISIT_AREA_ID': 'START_AREA'}
    )
    end_points = temp[temp['END']][['TRAVEL_ID', 'VISIT_AREA_ID', 'END_DISTANCE']].rename(
        columns={'VISIT_AREA_ID': 'END_AREA'}
    )
    possible_routes = pd.merge(start_points, end_points, on='TRAVEL_ID')
    possible_routes = possible_routes[possible_routes['START_AREA'] < possible_routes['END_AREA']]
    possible_routes['DISTANCE'] = (possible_routes['START_DISTANCE'] + possible_routes['END_DISTANCE']) / 2
    return possible_routes[['TRAVEL_ID', 'START_AREA', 'END_AREA', 'DISTANCE']]

# 4. 이동 수단 연결 및 중복 제거
def compress_transport_modes(route, category_mapping):
    route['MVMN_CD_1'] = route['MVMN_CD_1'].map(category_mapping)
    transport_modes = route['MVMN_CD_1'].tolist()
    # 두 번째 지점부터 이동 수단 표시
    if len(transport_modes) <= 1:  # 데이터가 하나뿐이면 빈 이동 수단 반환
        return ''
    transport_modes = transport_modes[1:]
    compressed_modes = [transport_modes[0]]
    for mode in transport_modes[1:]:
        if mode != compressed_modes[-1]:
            compressed_modes.append(mode)
    return '->'.join(compressed_modes)

# 5. 우선순위 기반 대표 이동 수단 선정
def determine_representative_transport_with_priority(sequence, priority_mapping):
    transports = sequence.split('->')
    transport_scores = {transport: priority_mapping.get(transport, 0) for transport in transports}
    return max(transport_scores, key=transport_scores.get)

def split_routes_by_private_car_after_generation(possible_routes, temp, boundary, input_coords):
    """
    자가용 경로를 기준으로 이미 생성된 경로를 분리하고 유효한 경로만 반환.
    """
    valid_routes = []

    for _, row in possible_routes.iterrows():
        travel_id = row['TRAVEL_ID']
        start_area = row['START_AREA']
        end_area = row['END_AREA']

        # 해당 경로에 해당하는 데이터를 추출
        route = temp[
            (temp['TRAVEL_ID'] == travel_id) &
            (temp['VISIT_AREA_ID'] >= start_area) &
            (temp['VISIT_AREA_ID'] <= end_area)
        ].sort_values('VISIT_AREA_ID')

        segments = []
        current_segment = []
        
        # 자가용을 기준으로 경로 분리
        for _, point in route.iterrows():
            if point['MVMN_CD_1'] == 1:  # 자가용
                if current_segment:
                    segments.append(pd.DataFrame(current_segment))
                current_segment = []  # 자가용 만나면 새 경로 시작
            else:
                current_segment.append(point)

        if current_segment:
            segments.append(pd.DataFrame(current_segment))  # 마지막 경로 추가

        # 유효 거리 내 서브 경로 확인
        for segment in segments:
            if segment.empty:
                continue

            # 서브 경로의 시작과 끝 좌표 추출
            start_point = segment.iloc[0]
            end_point = segment.iloc[-1]

            start_distance = haversine(
                input_coords['PREV_Y_COORD'], input_coords['PREV_X_COORD'],
                start_point['Y_COORD'], start_point['X_COORD']
            )
            end_distance = haversine(
                input_coords['Y_COORD'], input_coords['X_COORD'],
                end_point['Y_COORD'], end_point['X_COORD']
            )
            # 시작 지점과 도착 지점이 유효 범위 내에 있는지 확인
            if start_distance <= boundary and end_distance <= boundary:  
                valid_routes.append({
                    'TRAVEL_ID': travel_id,
                    'START_AREA': start_point['VISIT_AREA_ID'],
                    'END_AREA': end_point['VISIT_AREA_ID'],
                    'DISTANCE': ((start_distance + end_distance) / 2)
                })

    return pd.DataFrame(valid_routes)

def transport_pipeline(prev_lon, prev_lat, next_lon, next_lat, boundary=3, category_mapping=category_mapping, transport_priority=transport_priority):
    # 좌표를 사전으로 변환
    input_coords = {'PREV_X_COORD': prev_lon, 'PREV_Y_COORD': prev_lat, 'X_COORD': next_lon, 'Y_COORD': next_lat}

    # 데이터 로드
    mv = pd.read_csv('data/tn_move_his_이동내역.csv')
    vst = pd.read_csv('data/tn_visit_area_info_방문지정보2nd.csv')

    # 데이터 병합
    mv.rename(columns={'TRIP_ID': 'VISIT_AREA_ID'}, inplace=True)
    merged = pd.merge(mv, vst, on=['TRAVEL_ID', 'VISIT_AREA_ID'], how='inner')
    temp = merged[['TRAVEL_ID', 'VISIT_AREA_ID', 'MVMN_CD_1', 'X_COORD', 'Y_COORD']].copy()

    # START/END 플래그 추가
    temp = add_start_end_flags(temp, boundary, input_coords)

    # 가능한 경로 생성
    possible_routes = generate_possible_routes(temp)

    # 빈 결과 처리
    if possible_routes.empty:
        return pd.DataFrame(columns=['X_COORD', 'Y_COORD', 'TRANSPORT_MODES', 'PRIMARY_TRANSPORT'])

    # 이동 경로와 수단 연결
    for _, row in possible_routes.iterrows():
        travel_id = row['TRAVEL_ID']
        start_area = row['START_AREA']
        end_area = row['END_AREA']
        distance = row['DISTANCE']

        route = temp[
            (temp['TRAVEL_ID'] == travel_id) & 
            (temp['VISIT_AREA_ID'] >= start_area) & 
            (temp['VISIT_AREA_ID'] <= end_area)
        ].sort_values('VISIT_AREA_ID')

        transport_modes = compress_transport_modes(route, category_mapping)
        primary_transport = determine_representative_transport_with_priority(transport_modes, transport_priority)

        # 첫 번째 결과값만 반환
        return pd.DataFrame([{
            'X_COORD': next_lon,
            'Y_COORD': next_lat,
            'TRANSPORT_MODES': transport_modes,
            'PRIMARY_TRANSPORT': primary_transport
        }])

    # 빈 경우 처리
    return pd.DataFrame(columns=['X_COORD', 'Y_COORD', 'TRANSPORT_MODES', 'PRIMARY_TRANSPORT'])



# 필수 인자 정의
prev_x = 125.98157399467  # 이전 경도
prev_y = 36.2987714202851  # 이전 위도
x = 126.5303615        # 현재 경도
y = 34.6786846        # 현재 위도
boundary = 100     # 반경 (km)

# 함수 실행
result = transport_pipeline(prev_x, prev_y, x, y, boundary)

print(result)