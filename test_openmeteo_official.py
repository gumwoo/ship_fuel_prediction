#!/usr/bin/env python3
"""
Open-Meteo 공식 Python 코드 테스트
7일치 Marine 데이터 수집 확인
"""

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def test_openmeteo_official():
    """Open-Meteo 공식 코드 테스트"""
    print("Open-Meteo 공식 Python 클라이언트 테스트 시작...")
    
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": 54.544587,
        "longitude": 10.227487,
        "hourly": ["wave_height", "wave_direction", "wind_wave_height", "swell_wave_height", "ocean_current_velocity", "ocean_current_direction", "sea_surface_temperature"],
        "start_date": "2024-12-01",
        "end_date": "2024-12-07"
    }
    
    print(f"API 호출 중...")
    print(f"URL: {url}")
    print(f"파라미터: {params}")
    
    try:
        responses = openmeteo.weather_api(url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]
        print(f"\n=== 응답 정보 ===")
        print(f"좌표: {response.Latitude()}°N {response.Longitude()}°E")
        print(f"고도: {response.Elevation()} m asl")
        print(f"시간대: {response.Timezone()}{response.TimezoneAbbreviation()}")
        print(f"GMT 차이: {response.UtcOffsetSeconds()} 초")

        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_wave_height = hourly.Variables(0).ValuesAsNumpy()
        hourly_wave_direction = hourly.Variables(1).ValuesAsNumpy()
        hourly_wind_wave_height = hourly.Variables(2).ValuesAsNumpy()
        hourly_swell_wave_height = hourly.Variables(3).ValuesAsNumpy()
        hourly_ocean_current_velocity = hourly.Variables(4).ValuesAsNumpy()
        hourly_ocean_current_direction = hourly.Variables(5).ValuesAsNumpy()
        hourly_sea_surface_temperature = hourly.Variables(6).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        )}

        hourly_data["wave_height"] = hourly_wave_height
        hourly_data["wave_direction"] = hourly_wave_direction
        hourly_data["wind_wave_height"] = hourly_wind_wave_height
        hourly_data["swell_wave_height"] = hourly_swell_wave_height
        hourly_data["ocean_current_velocity"] = hourly_ocean_current_velocity
        hourly_data["ocean_current_direction"] = hourly_ocean_current_direction
        hourly_data["sea_surface_temperature"] = hourly_sea_surface_temperature

        hourly_dataframe = pd.DataFrame(data = hourly_data)
        
        print(f"\n=== 데이터 분석 ===")
        print(f"총 데이터 포인트: {len(hourly_dataframe)}")
        print(f"기간: {hourly_dataframe['date'].min()} ~ {hourly_dataframe['date'].max()}")
        print(f"컬럼: {list(hourly_dataframe.columns)}")
        
        print(f"\n=== 첫 5행 데이터 ===")
        print(hourly_dataframe.head())
        
        print(f"\n=== 데이터 통계 ===")
        print(hourly_dataframe.describe())
        
        # 성공 여부 판단
        expected_points = 7 * 24  # 7일 × 24시간
        if len(hourly_dataframe) == expected_points:
            print(f"\n✅ 테스트 성공! {expected_points}개 데이터 포인트 확인")
            return True
        else:
            print(f"\n❌ 테스트 실패! 예상: {expected_points}, 실제: {len(hourly_dataframe)}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_openmeteo_official()
    
    if success:
        print("\n🎉 Open-Meteo 공식 클라이언트 테스트 성공!")
        print("weather_collector.py 수정 준비 완료!")
    else:
        print("\n💥 테스트 실패 - 문제 해결 필요")
