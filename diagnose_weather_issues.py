#!/usr/bin/env python3
"""
기상 데이터 수집 문제 진단

실패한 위치들을 분석하고 원인을 파악합니다.
"""

import pandas as pd
import sys
import os
from pathlib import Path
import requests
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'src'))

from data_collection.weather_collector import WeatherCollector

def diagnose_weather_collection_issues():
    """기상 데이터 수집 문제 진단"""
    print("기상 데이터 수집 문제 진단 시작")
    
    # AIS 데이터 파일
    ais_file = "data/AIS_2024_12_01.csv"
    ais_df = pd.read_csv(ais_file, nrows=1000)
    
    # 이전 테스트에서 실패한 위치들
    failed_locations = [
        (35.209, -90.061),  # 멕시코만
        (30.047, -90.649)   # 멕시코만
    ]
    
    successful_locations = [
        (33.847, -118.397),  # 로스앤젤레스 근해
        (30.894, -117.052),  # 샌디에고 근해
        (29.712, -95.020)    # 휴스턴 근해
    ]
    
    print(f"\n실패한 위치들 분석:")
    for i, (lat, lon) in enumerate(failed_locations):
        print(f"\n=== 실패 위치 {i+1}: {lat:.3f}, {lon:.3f} ===")
        analyze_location(lat, lon)
    
    print(f"\n\n성공한 위치들 분석:")
    for i, (lat, lon) in enumerate(successful_locations):
        print(f"\n=== 성공 위치 {i+1}: {lat:.3f}, {lon:.3f} ===")
        analyze_location(lat, lon)
    
    # 추가 테스트: 다양한 지역
    print(f"\n\n추가 지역 테스트:")
    additional_test_locations = [
        (40.7, -74.0),    # 뉴욕 근해
        (25.8, -80.2),    # 마이애미 근해
        (47.6, -122.3),   # 시애틀 근해
        (61.2, -149.9),   # 알래스카 근해
        (21.3, -157.8),   # 하와이 근해
    ]
    
    collector = WeatherCollector()
    success_count = 0
    
    for i, (lat, lon) in enumerate(additional_test_locations):
        print(f"\n추가 테스트 {i+1}: {lat:.3f}, {lon:.3f}")
        
        try:
            weather = collector.get_marine_weather(
                latitude=lat,
                longitude=lon,
                start_date='2024-12-01',
                end_date='2024-12-01'
            )
            
            if weather and 'hourly' in weather:
                hourly = weather['hourly']
                hours_count = len(hourly.get('time', []))
                print(f"  성공: {hours_count}시간 데이터")
                success_count += 1
            else:
                print(f"  실패: 빈 응답")
                print(f"  응답 내용: {weather}")
                
        except Exception as e:
            print(f"  오류: {e}")
    
    print(f"\n추가 테스트 성공률: {success_count}/{len(additional_test_locations)} ({success_count/len(additional_test_locations)*100:.1f}%)")

def analyze_location(lat, lon):
    """특정 위치 분석"""
    # 1. 기본 정보
    print(f"위도: {lat:.3f}, 경도: {lon:.3f}")
    
    # 2. 지역 판단
    region = determine_region(lat, lon)
    print(f"지역: {region}")
    
    # 3. 육지/바다 여부 (간단한 판단)
    is_ocean = is_likely_ocean(lat, lon)
    print(f"해양 지역 여부: {is_ocean}")
    
    # 4. Open-Meteo API 직접 테스트
    test_openmeteo_api(lat, lon)

def determine_region(lat, lon):
    """지역 판단"""
    if 25 <= lat <= 32 and -98 <= lon <= -80:
        return "멕시코만"
    elif 32 <= lat <= 50 and -130 <= lon <= -115:
        return "미국 서부 해안"
    elif 25 <= lat <= 45 and -85 <= lon <= -65:
        return "미국 동부 해안"
    elif lat >= 50:
        return "북극해/알래스카"
    elif lat <= 25:
        return "카리브해/중앙아메리카"
    else:
        return "기타 지역"

def is_likely_ocean(lat, lon):
    """간단한 해양 지역 여부 판단"""
    # 매우 간단한 육지 필터링 (실제로는 더 정교한 방법 필요)
    
    # 명백한 육지 좌표들
    if -125 <= lon <= -65 and 25 <= lat <= 50:
        # 미국 본토 대략적 범위 내에서 해안가인지 확인
        
        # 서부 해안
        if lon < -115 and (lat < 35 or lat > 45):
            return True
            
        # 동부 해안
        if lon > -85 and 25 <= lat <= 45:
            return True
            
        # 멕시코만
        if -98 <= lon <= -80 and 25 <= lat <= 32:
            return True
            
        # 오대호 지역은 육지로 간주
        if -95 <= lon <= -75 and 40 <= lat <= 50:
            return False
            
        return False  # 기본적으로 미국 본토 내부는 육지
    
    return True  # 미국 본토 밖은 대부분 바다

def test_openmeteo_api(lat, lon):
    """Open-Meteo API 직접 테스트"""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': '2024-12-01',
        'end_date': '2024-12-01',
        'hourly': 'wave_height'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"API 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'hourly' in data and data['hourly']:
                wave_heights = data['hourly'].get('wave_height', [])
                valid_heights = [h for h in wave_heights if h is not None]
                print(f"  유효한 파고 데이터: {len(valid_heights)}/{len(wave_heights)}")
                if valid_heights:
                    print(f"  파고 범위: {min(valid_heights):.2f}~{max(valid_heights):.2f}m")
            else:
                print(f"  응답에 hourly 데이터 없음")
                print(f"  응답 키: {list(data.keys())}")
        else:
            print(f"API 오류: {response.text}")
            
    except Exception as e:
        print(f"API 호출 실패: {e}")

if __name__ == "__main__":
    diagnose_weather_collection_issues()
