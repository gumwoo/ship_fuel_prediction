#!/usr/bin/env python3
"""
기상 데이터 수집 테스트

첫 번째 AIS 파일의 일부 위치에서 기상 데이터를 수집해서 시스템이 정상 동작하는지 확인
"""

import pandas as pd
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'src'))

from data_collection.weather_collector import WeatherCollector

def test_weather_collection():
    """기상 데이터 수집 테스트"""
    print("기상 데이터 수집 테스트 시작")
    
    # AIS 데이터 파일
    ais_file = "data/AIS_2024_12_01.csv"
    
    if not os.path.exists(ais_file):
        print(f"AIS 파일을 찾을 수 없습니다: {ais_file}")
        return
    
    print(f"AIS 파일 로딩: {ais_file}")
    
    # AIS 데이터 샘플 읽기 (빠른 테스트를 위해 1000행만)
    ais_df = pd.read_csv(ais_file, nrows=1000)
    print(f"AIS 데이터 로딩 완료: {len(ais_df)} 레코드")
    print(f"컬럼: {list(ais_df.columns)}")
    print(f"위치 범위: 위도 {ais_df['LAT'].min():.2f}~{ais_df['LAT'].max():.2f}, 경도 {ais_df['LON'].min():.2f}~{ais_df['LON'].max():.2f}")
    
    # 기상 데이터 수집기 초기화
    collector = WeatherCollector()
    
    # 테스트용 위치 선택 (5개 위치)
    test_locations = [
        (ais_df['LAT'].iloc[0], ais_df['LON'].iloc[0]),
        (ais_df['LAT'].iloc[100], ais_df['LON'].iloc[100]),
        (ais_df['LAT'].iloc[200], ais_df['LON'].iloc[200]),
        (ais_df['LAT'].iloc[300], ais_df['LON'].iloc[300]),
        (ais_df['LAT'].iloc[400], ais_df['LON'].iloc[400])
    ]
    
    print(f"\n테스트 위치들:")
    for i, (lat, lon) in enumerate(test_locations):
        print(f"  {i+1}. 위도 {lat:.3f}, 경도 {lon:.3f}")
    
    # 기상 데이터 수집 테스트
    weather_data = []
    success_count = 0
    
    for i, (lat, lon) in enumerate(test_locations):
        print(f"\n기상 데이터 수집 중 ({i+1}/{len(test_locations)}): {lat:.3f}, {lon:.3f}")
        
        try:
            weather = collector.get_marine_weather(
                latitude=lat,
                longitude=lon,
                start_date='2024-12-01',
                end_date='2024-12-01'  # 테스트는 하루만
            )
            
            if weather and 'hourly' in weather:
                # 간단한 데이터 검증
                hourly = weather['hourly']
                hours_count = len(hourly.get('time', []))
                wave_height = hourly.get('wave_height', [])
                
                # null 값 안전 처리
                valid_wave_heights = [h for h in wave_height if h is not None]
                if valid_wave_heights:
                    wave_range = f"{min(valid_wave_heights):.2f}~{max(valid_wave_heights):.2f}m"
                    print(f"  성공: {hours_count}시간 데이터, 파고 범위 {wave_range} (유효 데이터: {len(valid_wave_heights)}/{len(wave_height)})")
                else:
                    print(f"  부분 성공: {hours_count}시간 데이터, 파고 데이터 없음 (null 값들)")
                
                success_count += 1
                
                # 데이터가 있든 없든 일단 저장 (후처리에서 필터링)
                weather_df = collector._process_weather_data(weather, lat, lon)
                weather_data.append(weather_df)
                
            else:
                print(f"  실패: 빈 응답")
                
        except Exception as e:
            print(f"  오류: {e}")
    
    # 결과 요약
    print(f"\n테스트 결과 요약:")
    print(f"  - 총 테스트 위치: {len(test_locations)}")
    print(f"  - 성공: {success_count}")
    print(f"  - 성공률: {success_count/len(test_locations)*100:.1f}%")
    
    if weather_data:
        # 결합된 기상 데이터 저장
        combined_weather = pd.concat(weather_data, ignore_index=True)
        output_file = "data/raw/test_weather_sample.csv"
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # CSV 저장
        combined_weather.to_csv(output_file, index=False)
        print(f"테스트 기상 데이터 저장: {output_file}")
        print(f"데이터 형태: {combined_weather.shape}")
        print(f"컬럼: {list(combined_weather.columns)}")
        
        # 샘플 데이터 출력
        print(f"\n샘플 데이터:")
        print(combined_weather.head())
        
        return True
    else:
        print("수집된 기상 데이터가 없습니다.")
        return False

if __name__ == "__main__":
    success = test_weather_collection()
    if success:
        print("\n기상 데이터 수집 시스템이 정상 동작합니다!")
        print("다음 단계: 전체 AIS 데이터에 대한 기상 데이터 수집")
    else:
        print("\n기상 데이터 수집 시스템에 문제가 있습니다.")
