#!/usr/bin/env python3
"""
AIS 데이터 탐색적 분석 (EDA) 스크립트

7일치 AIS 데이터를 분석하여:
1. 데이터 구조 및 품질 파악
2. 선박별 궤적 및 속도 패턴 분석
3. 연료 소비 예측을 위한 기본 피처 생성
4. 이상치 탐지 및 데이터 정제
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정 (Windows)
try:
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
except:
    print("한글 폰트 설정 실패 - 영어로 표시됩니다")

def analyze_single_ais_file(file_path, sample_size=10000):
    """단일 AIS 파일 분석 (메모리 효율성을 위해 샘플링)"""
    print(f"\n=== {file_path} 분석 중 ===")
    
    # 파일 크기 및 기본 정보
    try:
        # 전체 행 수 확인
        total_rows = sum(1 for line in open(file_path, 'r', encoding='utf-8')) - 1  # 헤더 제외
        print(f"총 레코드 수: {total_rows:,}")
        
        # 샘플 데이터 로딩
        if total_rows > sample_size:
            # 균등 샘플링
            skip_n = max(1, total_rows // sample_size)
            df = pd.read_csv(file_path, skiprows=lambda x: x % skip_n != 0 and x != 0)
            print(f"샘플링된 레코드 수: {len(df):,} (전체의 {len(df)/total_rows:.1%})")
        else:
            df = pd.read_csv(file_path)
            print(f"전체 데이터 로딩: {len(df):,}")
        
        return df, total_rows
        
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None, 0

def basic_data_analysis(df, file_name):
    """기본 데이터 분석"""
    print(f"\n--- {file_name} 기본 분석 ---")
    
    # 컬럼 정보
    print(f"컬럼 수: {len(df.columns)}")
    print(f"컬럼명: {list(df.columns)}")
    
    # 결측치 분석
    missing_data = df.isnull().sum()
    missing_percent = (missing_data / len(df)) * 100
    missing_info = pd.DataFrame({
        'Missing_Count': missing_data,
        'Missing_Percent': missing_percent
    }).sort_values('Missing_Percent', ascending=False)
    
    print(f"\n결측치 현황:")
    print(missing_info[missing_info['Missing_Count'] > 0])
    
    # 주요 컬럼 통계
    numeric_columns = ['LAT', 'LON', 'SOG', 'COG', 'Length', 'Width', 'Draft']
    available_numeric = [col for col in numeric_columns if col in df.columns]
    
    if available_numeric:
        print(f"\n주요 수치형 변수 통계:")
        print(df[available_numeric].describe())
    
    return missing_info

def vessel_analysis(df):
    """선박 분석"""
    print(f"\n--- 선박 분석 ---")
    
    # 선박 타입 분포
    if 'VesselType' in df.columns:
        vessel_types = df['VesselType'].value_counts().head(10)
        print(f"주요 선박 타입 (상위 10개):")
        for vtype, count in vessel_types.items():
            print(f"  {vtype}: {count:,} ({count/len(df):.1%})")
    
    # 선박 크기 분포
    if 'Length' in df.columns and 'Width' in df.columns:
        # 선박 크기 카테고리 생성
        df_copy = df.copy()
        df_copy['Length_Category'] = pd.cut(df_copy['Length'], 
                                          bins=[0, 50, 100, 200, 500, float('inf')],
                                          labels=['소형(<50m)', '중소형(50-100m)', '중형(100-200m)', 
                                                 '대형(200-500m)', '초대형(>500m)'])
        
        length_dist = df_copy['Length_Category'].value_counts()
        print(f"\n선박 크기 분포:")
        for category, count in length_dist.items():
            print(f"  {category}: {count:,} ({count/len(df_copy):.1%})")
    
    # 고유 선박 수
    if 'MMSI' in df.columns:
        unique_vessels = df['MMSI'].nunique()
        print(f"\n고유 선박 수 (MMSI): {unique_vessels:,}")
        avg_records_per_vessel = len(df) / unique_vessels
        print(f"선박당 평균 레코드 수: {avg_records_per_vessel:.1f}")

def speed_analysis(df):
    """속도 및 운항 패턴 분석"""
    print(f"\n--- 속도 및 운항 패턴 분석 ---")
    
    if 'SOG' in df.columns:
        # 속도 통계
        speed_stats = df['SOG'].describe()
        print(f"속도 통계 (SOG - knots):")
        print(speed_stats)
        
        # 속도 카테고리 분석
        df_copy = df.copy()
        df_copy['Speed_Category'] = pd.cut(df_copy['SOG'], 
                                         bins=[-1, 0, 5, 10, 15, 25, float('inf')],
                                         labels=['정박(0)', '저속(0-5)', '중속(5-10)', 
                                               '고속(10-15)', '고속+(15-25)', '초고속(25+)'])
        
        speed_dist = df_copy['Speed_Category'].value_counts()
        print(f"\n속도 분포:")
        for category, count in speed_dist.items():
            print(f"  {category}: {count:,} ({count/len(df_copy):.1%})")
    
    if 'COG' in df.columns:
        # 방향 분석
        cog_stats = df['COG'].describe()
        print(f"\nCourse Over Ground 통계 (도):")
        print(cog_stats)

def geographic_analysis(df):
    """지리적 분포 분석"""
    print(f"\n--- 지리적 분포 분석 ---")
    
    if 'LAT' in df.columns and 'LON' in df.columns:
        # 위도/경도 범위
        lat_range = (df['LAT'].min(), df['LAT'].max())
        lon_range = (df['LON'].min(), df['LON'].max())
        
        print(f"위도 범위: {lat_range[0]:.3f}° ~ {lat_range[1]:.3f}°")
        print(f"경도 범위: {lon_range[0]:.3f}° ~ {lon_range[1]:.3f}°")
        
        # 지역별 대략적 분포
        print(f"\n지역별 대략적 분포:")
        
        # 북미 동부 해안
        us_east = ((df['LAT'] >= 25) & (df['LAT'] <= 45) & 
                   (df['LON'] >= -85) & (df['LON'] <= -65)).sum()
        print(f"  미국 동부 해안: {us_east:,} ({us_east/len(df):.1%})")
        
        # 북미 서부 해안
        us_west = ((df['LAT'] >= 30) & (df['LAT'] <= 50) & 
                   (df['LON'] >= -130) & (df['LON'] <= -115)).sum()
        print(f"  미국 서부 해안: {us_west:,} ({us_west/len(df):.1%})")
        
        # 멕시코만
        gulf = ((df['LAT'] >= 25) & (df['LAT'] <= 32) & 
                (df['LON'] >= -98) & (df['LON'] <= -80)).sum()
        print(f"  멕시코만: {gulf:,} ({gulf/len(df):.1%})")
        
        # 태평양
        pacific = ((df['LAT'] >= -20) & (df['LAT'] <= 50) & 
                   (df['LON'] >= 120) & (df['LON'] <= 180)).sum()
        print(f"  태평양: {pacific:,} ({pacific/len(df):.1%})")

def time_analysis(df):
    """시간 패턴 분석"""
    print(f"\n--- 시간 패턴 분석 ---")
    
    if 'BaseDateTime' in df.columns:
        # 시간 변환
        df_copy = df.copy()
        df_copy['BaseDateTime'] = pd.to_datetime(df_copy['BaseDateTime'])
        
        # 시간 범위
        time_range = (df_copy['BaseDateTime'].min(), df_copy['BaseDateTime'].max())
        print(f"시간 범위: {time_range[0]} ~ {time_range[1]}")
        
        # 시간별 분포
        df_copy['Hour'] = df_copy['BaseDateTime'].dt.hour
        hourly_dist = df_copy['Hour'].value_counts().sort_index()
        
        print(f"\n시간별 레코드 분포 (상위 5시간):")
        top_hours = hourly_dist.head()
        for hour, count in top_hours.items():
            print(f"  {hour:02d}시: {count:,} ({count/len(df_copy):.1%})")

def create_basic_features(df):
    """연료 소비 예측을 위한 기본 피처 생성"""
    print(f"\n--- 기본 피처 생성 ---")
    
    df_features = df.copy()
    feature_count = 0
    
    # 선박 크기 관련 피처
    if 'Length' in df.columns and 'Width' in df.columns:
        df_features['Ship_Area'] = df_features['Length'] * df_features['Width']
        feature_count += 1
        print(f"생성된 피처: Ship_Area (선박 면적)")
    
    if 'Length' in df.columns and 'Width' in df.columns and 'Draft' in df.columns:
        df_features['Ship_Volume'] = (df_features['Length'] * 
                                     df_features['Width'] * 
                                     df_features['Draft'])
        feature_count += 1
        print(f"생성된 피처: Ship_Volume (선박 부피)")
    
    # 속도 관련 피처
    if 'SOG' in df.columns:
        df_features['Speed_Squared'] = df_features['SOG'] ** 2
        feature_count += 1
        print(f"생성된 피처: Speed_Squared (속도 제곱)")
        
        # 속도 카테고리
        df_features['Is_Moving'] = (df_features['SOG'] > 1).astype(int)
        feature_count += 1
        print(f"생성된 피처: Is_Moving (운항 여부)")
    
    # 시간 관련 피처
    if 'BaseDateTime' in df.columns:
        df_features['BaseDateTime'] = pd.to_datetime(df_features['BaseDateTime'])
        df_features['Hour'] = df_features['BaseDateTime'].dt.hour
        df_features['Day_of_Week'] = df_features['BaseDateTime'].dt.dayofweek
        feature_count += 2
        print(f"생성된 피처: Hour, Day_of_Week (시간 정보)")
    
    print(f"총 생성된 피처 수: {feature_count}")
    return df_features

def detect_outliers(df):
    """이상치 탐지"""
    print(f"\n--- 이상치 탐지 ---")
    
    outlier_info = {}
    
    # 속도 이상치 (SOG > 50 knots는 일반적으로 이상)
    if 'SOG' in df.columns:
        high_speed = (df['SOG'] > 50).sum()
        negative_speed = (df['SOG'] < 0).sum()
        outlier_info['high_speed'] = high_speed
        outlier_info['negative_speed'] = negative_speed
        print(f"고속 이상치 (>50 knots): {high_speed:,} ({high_speed/len(df):.2%})")
        print(f"음수 속도: {negative_speed:,} ({negative_speed/len(df):.2%})")
    
    # 위치 이상치 (육상 좌표)
    if 'LAT' in df.columns and 'LON' in df.columns:
        invalid_lat = ((df['LAT'] < -90) | (df['LAT'] > 90)).sum()
        invalid_lon = ((df['LON'] < -180) | (df['LON'] > 180)).sum()
        outlier_info['invalid_coordinates'] = invalid_lat + invalid_lon
        print(f"잘못된 좌표: 위도 {invalid_lat:,}, 경도 {invalid_lon:,}")
    
    # 선박 크기 이상치
    if 'Length' in df.columns:
        zero_length = (df['Length'] <= 0).sum()
        huge_length = (df['Length'] > 500).sum()
        outlier_info['vessel_size'] = zero_length + huge_length
        print(f"선박 크기 이상치: 길이≤0 {zero_length:,}, 길이>500m {huge_length:,}")
    
    return outlier_info

def main():
    """메인 분석 함수"""
    print("AIS 데이터 탐색적 분석 시작")
    print("=" * 50)
    
    # AIS 파일 목록
    data_dir = Path("data")
    ais_files = [
        data_dir / "AIS_2024_12_01.csv",
        data_dir / "AIS_2024_12_02.csv", 
        data_dir / "AIS_2024_12_03.csv",
        data_dir / "AIS_2024_12_04.csv",
        data_dir / "AIS_2024_12_05.csv",
        data_dir / "AIS_2024_12_06.csv",
        data_dir / "AIS_2024_12_07.csv"
    ]
    
    # 존재하는 파일만 필터링
    existing_files = [f for f in ais_files if f.exists()]
    print(f"분석 대상 파일: {len(existing_files)}개")
    
    if not existing_files:
        print("❌ AIS 데이터 파일을 찾을 수 없습니다!")
        return
    
    # 전체 통계 저장
    total_records = 0
    all_missing_info = []
    all_outliers = {}
    sample_combined = []
    
    # 각 파일별 분석
    for file_path in existing_files[:3]:  # 처음 3개 파일만 상세 분석
        df, total_rows = analyze_single_ais_file(file_path, sample_size=50000)
        
        if df is not None:
            total_records += total_rows
            
            # 기본 분석
            missing_info = basic_data_analysis(df, file_path.name)
            all_missing_info.append(missing_info)
            
            # 선박 분석
            vessel_analysis(df)
            
            # 속도 분석
            speed_analysis(df)
            
            # 지리적 분석
            geographic_analysis(df)
            
            # 시간 분석
            time_analysis(df)
            
            # 피처 생성
            df_with_features = create_basic_features(df)
            
            # 이상치 탐지
            outliers = detect_outliers(df)
            all_outliers[file_path.name] = outliers
            
            # 샘플 데이터 수집 (나중에 결합 분석용)
            sample_combined.append(df.sample(min(10000, len(df))))
            
            print("\n" + "="*50)
    
    # 전체 요약
    print(f"\n전체 분석 요약")
    print(f"총 분석 파일: {len(existing_files)}")
    print(f"총 레코드 수: {total_records:,}")
    
    # 결합 분석 (메모리 효율성을 위해 샘플만)
    if sample_combined:
        print(f"\n결합 샘플 분석 (총 {sum(len(df) for df in sample_combined):,} 레코드)")
        combined_sample = pd.concat(sample_combined, ignore_index=True)
        
        # 전체적인 패턴 분석
        print(f"\n전체 샘플 기본 통계:")
        numeric_cols = ['LAT', 'LON', 'SOG', 'COG', 'Length', 'Width', 'Draft']
        available_cols = [col for col in numeric_cols if col in combined_sample.columns]
        if available_cols:
            print(combined_sample[available_cols].describe())
        
        # 전체 선박 타입 분포
        if 'VesselType' in combined_sample.columns:
            print(f"\n전체 선박 타입 분포 (상위 10개):")
            vessel_dist = combined_sample['VesselType'].value_counts().head(10)
            for vtype, count in vessel_dist.items():
                print(f"  {vtype}: {count:,}")
    
    print(f"\nAIS 데이터 탐색적 분석 완료!")
    print(f"주요 발견사항:")
    print(f"   - 총 {total_records:,}개 레코드 보유")
    print(f"   - 7일간의 선박 운항 데이터")
    print(f"   - 연료 소비 예측을 위한 기본 피처 생성 가능")
    print(f"   - 다음 단계: 기상 데이터와의 매칭 준비 완료")

if __name__ == "__main__":
    main()
