import requests

# 카카오 API 키 설정
API_KEY = ""

# 지오코딩 함수 정의
def get_coordinates(address, timeout=5):
    """
    주소나 키워드를 입력받아 위도(Y_COORD), 경도(X_COORD), 그리고 지역 정보를 반환하는 함수.
    순서: 도로명 주소 → 일반 주소 → 키워드 검색
    """
    headers = {"Authorization": f"KakaoAK {API_KEY}"}

    # 1. 도로명 주소 검색
    try:
        url_road = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        response_road = requests.get(url_road, headers=headers, timeout=timeout)
        if response_road.status_code == 200:
            result_road = response_road.json()
            if result_road.get('documents'):
                document = result_road['documents'][0]
                x_coord = document['x']  # 경도
                y_coord = document['y']  # 위도
                region = document.get('address', {}).get('region_2depth_name', "알 수 없음")
                return x_coord, y_coord, region
    except requests.exceptions.RequestException as e:
        print(f"도로명 주소 요청 중 오류 발생: {e}")

    # 2. 일반 주소 검색
    try:
        url_general = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        response_general = requests.get(url_general, headers=headers, timeout=timeout)
        if response_general.status_code == 200:
            result_general = response_general.json()
            if result_general.get('documents'):
                document = result_general['documents'][0]
                x_coord = document['x']  # 경도
                y_coord = document['y']  # 위도
                region = document.get('address', {}).get('region_2depth_name', "알 수 없음")
                return x_coord, y_coord, region
    except requests.exceptions.RequestException as e:
        print(f"일반 주소 요청 중 오류 발생: {e}")

    # 3. 키워드 검색
    try:
        url_keyword = f"https://dapi.kakao.com/v2/local/search/keyword.json?query={address}"
        response_keyword = requests.get(url_keyword, headers=headers, timeout=timeout)
        if response_keyword.status_code == 200:
            result_keyword = response_keyword.json()
            if result_keyword.get('documents'):
                document = result_keyword['documents'][0]
                x_coord = document['x']  # 경도
                y_coord = document['y']  # 위도
                region = document.get('address_name', "알 수 없음")
                return x_coord, y_coord, region
    except requests.exceptions.RequestException as e:
        print(f"키워드 검색 요청 중 오류 발생: {e}")

    # 모든 단계 실패 시 None 반환
    return None, None, "검색 결과 없음"


# 정규화 함수 추가
def normalize_region_name(region_name):
    """
    SIDO_NM(시/도 명칭)을 정규화하여 데이터셋 형식과 일치시킵니다.
    """
    normalization_map = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주"
    }
    return normalization_map.get(region_name, region_name)  # 매핑되지 않은 값은 원래 값 반환

def get_region_from_coords(x, y, timeout=5):
    """
    좌표(x, y)를 입력받아 시/도 및 구 단위 정보를 반환하는 함수.
    """
    headers = {"Authorization": f"KakaoAK {API_KEY}"}

    try:
        # 카카오 지도 API 요청
        url = f"https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x={x}&y={y}"
        response = requests.get(url, headers=headers, timeout=timeout)

        if response.status_code == 200:
            result = response.json()
            if result.get('documents'):
                document = result['documents'][0]
                sido_nm = normalize_region_name(document.get('region_1depth_name', "알 수 없음"))  # 시/도 정규화
                sgg_nm = document.get('region_2depth_name', "알 수 없음")   # 구 단위 정보
                return sido_nm, sgg_nm  # 시/도 및 구 단위 반환

    except requests.exceptions.RequestException as e:
        print(f"좌표 기반 역지오코딩 요청 중 오류 발생: {e}")

    # 실패 시 기본값 반환
    return "알 수 없음", "알 수 없음"
