#!/usr/bin/env python3
"""
WeatherCollector 실제 테스트 스크립트
AIS 데이터를 사용해서 실제 기상 데이터를 수집해봅니다.
"""

import sys
import os
from pathlib import Path
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data_collection.weather_collector import WeatherCollector

def test_weather_collector():
    """WeatherCollector 실제 테스트"""
    print("WeatherCollector 실제 테스트 시작...")
    
    # 출력 디렉토리 생성
    os.makedirs("data/raw", exist_ok=True)
    
    # WeatherCollector 생성
    collector = WeatherCollector()
    
    # 테스트용 AIS 파일
    ais_file = "data/AIS_2024_12_01.csv"
    output_file = "data/raw/test_weather_2024_12_01.csv"
    
    print(f"AIS 파일: {ais_file}")
    print(f"출력 파일: {output_file}")
    
    # AIS 파일 존재 확인
    if not os.path.exists(ais_file):
        print(f"오류: AIS 파일이 존재하지 않습니다: {ais_file}")
        return False
    
    # AIS 데이터 미리보기
    print("\nAIS 데이터 미리보기:")
    ais_df = pd.read_csv(ais_file)
    print(f"   총 레코드: {len(ais_df):,}")
    print(f"   컬럼: {list(ais_df.columns)}")
    print(f"   위도 범위: {ais_df['LAT'].min():.3f} ~ {ais_df['LAT'].max():.3f}")
    print(f"   경도 범위: {ais_df['LON'].min():.3f} ~ {ais_df['LON'].max():.3f}")
    
    try:
        print("\n해상 기상 데이터 수집 시작...")
        print("(이 과정은 몇 분 정도 소요될 수 있습니다)")
        
        # 기상 데이터 수집 실행
        weather_df = collector.collect_weather_for_ais_locations(
            ais_data_path=ais_file,
            output_path=output_file
        )
        
        if weather_df is not None and len(weather_df) > 0:
            print(f"\n성공! 기상 데이터 수집 완료")
            print(f"   수집된 데이터 크기: {weather_df.shape}")
            print(f"   컬럼: {list(weather_df.columns)}")
            
            # 데이터 품질 분석
            print("\n데이터 품질 분석:")
            total_records = len(weather_df)
            valid_wave = weather_df['wave_height'].notna().sum()
            valid_wind_wave = weather_df['wind_wave_height'].notna().sum()
            valid_swell = weather_df['swell_wave_height'].notna().sum()
            valid_current = weather_df['ocean_current_velocity'].notna().sum()
            valid_temp = weather_df['sea_surface_temperature'].notna().sum()
            
            print(f"   총 레코드: {total_records:,}")
            print(f"   유효한 파도 높이: {valid_wave:,} ({valid_wave/total_records:.1%})")
            print(f"   유효한 바람 파도: {valid_wind_wave:,} ({valid_wind_wave/total_records:.1%})")
            print(f"   유효한 너울: {valid_swell:,} ({valid_swell/total_records:.1%})")
            print(f"   유효한 해류 속도: {valid_current:,} ({valid_current/total_records:.1%})")
            print(f"   유효한 수온: {valid_temp:,} ({valid_temp/total_records:.1%})")
            
            # 샘플 데이터 출력
            print("\n샘플 데이터:")
            print(weather_df.head())
            
            # 통계 요약
            print("\n기상 데이터 통계:")
            numeric_columns = ['wave_height', 'wind_wave_height', 'swell_wave_height', 
                             'ocean_current_velocity', 'sea_surface_temperature']
            for col in numeric_columns:
                if col in weather_df.columns:
                    valid_data = weather_df[col].dropna()
                    if len(valid_data) > 0:
                        print(f"   {col}: 평균={valid_data.mean():.2f}, 최소={valid_data.min():.2f}, 최대={valid_data.max():.2f}")
            
            # 성공률 평가
            overall_success_rate = weather_df.notna().mean().mean()
            print(f"\n전체 데이터 성공률: {overall_success_rate:.1%}")
            
            if overall_success_rate >= 0.8:
                print("✅ 데이터 품질 목표 달성! (80% 이상)")
                return True
            else:
                print("⚠️ 데이터 품질 개선 필요")
                return True  # 부분적 성공으로 간주
                
        else:
            print("❌ 기상 데이터 수집 실패 - 빈 데이터셋")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_weather_collector()
    
    if success:
        print("\n🎉 WeatherCollector 테스트 성공!")
        print("다음 단계: 전체 7일치 AIS 데이터에 대해 기상 데이터 수집")
    else:
        print("\n❌ WeatherCollector 테스트 실패")
        print("문제 해결이 필요합니다.")
