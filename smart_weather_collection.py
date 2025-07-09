#!/usr/bin/env python3
"""
효율적 기상 데이터 수집 전략

7일치 AIS 데이터에서 지리적/시간적으로 대표적인 위치들을 선택하여
효율적으로 기상 데이터를 수집합니다.
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'src'))

from data_collection.weather_collector import WeatherCollector

def smart_weather_collection():
    """지능적 기상 데이터 수집"""
    print("지능적 기상 데이터 수집 시작")
    print("=" * 50)
    
    collector = WeatherCollector()
    
    # AIS 파일 목록
    ais_files = [
        "data/AIS_2024_12_01.csv",
        "data/AIS_2024_12_02.csv", 
        "data/AIS_2024_12_03.csv",
        "data/AIS_2024_12_04.csv",
        "data/AIS_2024_12_05.csv",
        "data/AIS_2024_12_06.csv",
        "data/AIS_2024_12_07.csv"
    ]
    
    # 각 파일에서 대표 위치 추출
    all_locations = []
    dates = ['2024-12-01', '2024-12-02', '2024-12-03', '2024-12-04', 
             '2024-12-05', '2024-12-06', '2024-12-07']
    
    for i, ais_file in enumerate(ais_files):
        if not os.path.exists(ais_file):
            continue
            
        print(f"\n{ais_file} 분석 중...")
        
        # 샘플링으로 파일 읽기 (메모리 효율성)
        df = pd.read_csv(ais_file, skiprows=lambda x: x % 100 != 0 and x != 0)
        print(f"샘플 데이터: {len(df):,} 레코드")
        
        # 지역별 클러스터링
        locations = extract_representative_locations(df, target_count=30)
        
        # 날짜 정보 추가
        for lat, lon in locations:
            all_locations.append({
                'latitude': lat,
                'longitude': lon,
                'date': dates[i],
                'file': ais_file
            })
        
        print(f"추출된 대표 위치: {len(locations)}개")
    
    print(f"\n총 수집 대상 위치: {len(all_locations)}개")
    
    # 기상 데이터 수집
    weather_data = []
    success_count = 0
    
    for i, location in enumerate(all_locations):
        lat, lon, date = location['latitude'], location['longitude'], location['date']
        
        print(f"\n기상 데이터 수집 ({i+1}/{len(all_locations)}): {date} - {lat:.3f}, {lon:.3f}")
        
        try:
            weather = collector.get_marine_weather(
                latitude=lat,
                longitude=lon,
                start_date=date,
                end_date=date
            )
            
            if weather and 'hourly' in weather:
                weather_df = collector._process_weather_data(weather, lat, lon)
                weather_df['source_file'] = location['file']
                weather_data.append(weather_df)
                success_count += 1
                
                # 데이터 품질 체크
                valid_wave_data = weather_df['wave_height'].notna().sum()
                print(f"  성공: {len(weather_df)}시간, 유효 파고 데이터 {valid_wave_data}/{len(weather_df)}")
            else:
                print(f"  실패: 빈 응답")
                
        except Exception as e:
            print(f"  오류: {e}")
        
        # API 과부하 방지 (0.5초 대기)
        time.sleep(0.5)
        
        # 중간 저장 (50개마다)
        if (i + 1) % 50 == 0:
            save_intermediate_results(weather_data, f"data/raw/weather_intermediate_{i+1}.csv")
    
    # 최종 결과 저장
    if weather_data:
        combined_weather = pd.concat(weather_data, ignore_index=True)
        output_file = "data/raw/weather_7days_comprehensive.csv"
        combined_weather.to_csv(output_file, index=False)
        
        print(f"\n수집 완료!")
        print(f"  성공률: {success_count}/{len(all_locations)} ({success_count/len(all_locations)*100:.1f}%)")
        print(f"  저장 파일: {output_file}")
        print(f"  데이터 크기: {combined_weather.shape}")
        print(f"  날짜 범위: {combined_weather['datetime'].min()} ~ {combined_weather['datetime'].max()}")
        
        # 데이터 품질 분석
        analyze_weather_data_quality(combined_weather)
        
        return combined_weather
    else:
        print("수집된 데이터가 없습니다.")
        return None

def extract_representative_locations(df, target_count=30):
    """AIS 데이터에서 대표적인 위치들을 추출"""
    
    # 유효한 위치 데이터만 필터링
    valid_df = df.dropna(subset=['LAT', 'LON'])
    
    if len(valid_df) == 0:
        return []
    
    # 위도/경도 범위 기반 그리드 샘플링
    lat_min, lat_max = valid_df['LAT'].min(), valid_df['LAT'].max()
    lon_min, lon_max = valid_df['LON'].min(), valid_df['LON'].max()
    
    # 그리드 크기 계산
    grid_size = int(np.sqrt(target_count))
    lat_bins = np.linspace(lat_min, lat_max, grid_size + 1)
    lon_bins = np.linspace(lon_min, lon_max, grid_size + 1)
    
    locations = []
    
    # 각 그리드 셀에서 중심점 선택
    for i in range(grid_size):
        for j in range(grid_size):
            # 그리드 셀 범위
            lat_low, lat_high = lat_bins[i], lat_bins[i+1]
            lon_low, lon_high = lon_bins[j], lon_bins[j+1]
            
            # 해당 셀의 데이터
            cell_data = valid_df[
                (valid_df['LAT'] >= lat_low) & (valid_df['LAT'] < lat_high) &
                (valid_df['LON'] >= lon_low) & (valid_df['LON'] < lon_high)
            ]
            
            if len(cell_data) > 0:
                # 셀 내 중심에 가까운 점 선택
                center_lat = (lat_low + lat_high) / 2
                center_lon = (lon_low + lon_high) / 2
                
                # 중심에서 가장 가까운 실제 AIS 포인트 찾기
                distances = np.sqrt(
                    (cell_data['LAT'] - center_lat)**2 + 
                    (cell_data['LON'] - center_lon)**2
                )
                closest_idx = distances.idxmin()
                
                rep_lat = cell_data.loc[closest_idx, 'LAT']
                rep_lon = cell_data.loc[closest_idx, 'LON']
                
                locations.append((float(rep_lat), float(rep_lon)))
    
    return locations

def save_intermediate_results(weather_data, filename):
    """중간 결과 저장"""
    if weather_data:
        combined = pd.concat(weather_data, ignore_index=True)
        combined.to_csv(filename, index=False)
        print(f"  중간 저장: {filename} ({combined.shape})")

def analyze_weather_data_quality(df):
    """기상 데이터 품질 분석"""
    print(f"\n데이터 품질 분석:")
    
    # 각 변수별 유효 데이터 비율
    weather_columns = ['wave_height', 'wave_direction', 'wind_wave_height', 
                      'swell_wave_height', 'ocean_current_velocity', 
                      'ocean_current_direction', 'sea_surface_temperature']
    
    for col in weather_columns:
        if col in df.columns:
            valid_count = df[col].notna().sum()
            total_count = len(df)
            validity = valid_count / total_count * 100
            print(f"  {col}: {validity:.1f}% ({valid_count}/{total_count})")
    
    # 지역별 데이터 분포
    print(f"\n지역별 분포:")
    region_counts = df.groupby(['latitude', 'longitude']).size().describe()
    print(f"  위치당 평균 시간 데이터: {region_counts['mean']:.1f}")
    print(f"  최소/최대: {region_counts['min']:.0f}/{region_counts['max']:.0f}")
    
    # 시간별 분포
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour
    hourly_dist = df['hour'].value_counts().sort_index()
    print(f"\n시간별 데이터 분포 (균등성):")
    print(f"  최소/최대 시간당 데이터: {hourly_dist.min()}/{hourly_dist.max()}")

if __name__ == "__main__":
    result = smart_weather_collection()
    if result is not None:
        print("\n지능적 기상 데이터 수집 완료!")
        print("다음 단계: AIS-기상 데이터 매칭 시스템 구축")
    else:
        print("\n기상 데이터 수집 실패")
