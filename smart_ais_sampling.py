#!/usr/bin/env python3
"""
지능적 AIS 데이터 샘플링 전략

2,470만 레코드에서 AI 모델 학습에 최적화된 고품질 샘플을 추출합니다.
목표: 50만 레코드 (전체의 2%)로 축소하되 다양성과 품질 유지
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def smart_ais_sampling():
    """지능적 AIS 데이터 샘플링"""
    print("지능적 AIS 데이터 샘플링 시작")
    print("목표: 50만 레코드 고품질 샘플 생성")
    print("=" * 60)
    
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
    
    # 각 파일당 목표 샘플 수 (총 50만개)
    samples_per_file = 500000 // len(ais_files)  # 약 71,428개씩
    
    all_samples = []
    total_original = 0
    total_sampled = 0
    
    for i, ais_file in enumerate(ais_files):
        if not os.path.exists(ais_file):
            continue
            
        print(f"\n=== {ais_file} 처리 중 ===")
        
        # 파일 크기 확인
        row_count = count_file_rows(ais_file)
        total_original += row_count
        print(f"원본 레코드: {row_count:,}")
        
        # 지능적 샘플링
        sample_df = intelligent_sampling(ais_file, samples_per_file)
        
        if sample_df is not None and len(sample_df) > 0:
            # 날짜 정보 추가
            sample_df['date'] = f"2024-12-{i+1:02d}"
            sample_df['file_source'] = ais_file
            
            all_samples.append(sample_df)
            total_sampled += len(sample_df)
            
            print(f"샘플링된 레코드: {len(sample_df):,}")
            print(f"샘플링 비율: {len(sample_df)/row_count*100:.2f}%")
        else:
            print("❌ 샘플링 실패")
    
    # 전체 샘플 결합
    if all_samples:
        combined_sample = pd.concat(all_samples, ignore_index=True)
        
        # 최종 정제 및 검증
        final_sample = post_process_sample(combined_sample)
        
        # 저장
        output_file = "data/processed/ais_intelligent_sample.csv"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        final_sample.to_csv(output_file, index=False)
        
        # 결과 요약
        print(f"\n{'='*60}")
        print(f"샘플링 완료!")
        print(f"  원본 데이터: {total_original:,} 레코드")
        print(f"  샘플 데이터: {len(final_sample):,} 레코드")
        print(f"  압축 비율: {len(final_sample)/total_original*100:.2f}%")
        print(f"  저장 파일: {output_file}")
        
        # 데이터 품질 분석
        analyze_sample_quality(final_sample)
        
        return final_sample
    else:
        print("❌ 샘플링된 데이터가 없습니다.")
        return None

def count_file_rows(file_path):
    """파일의 행 수를 빠르게 계산"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for line in f) - 1  # 헤더 제외
    except:
        return 0

def intelligent_sampling(file_path, target_count):
    """지능적 샘플링 전략"""
    print(f"지능적 샘플링 전략 적용...")
    
    try:
        # 1. 전체 행 수 확인
        total_rows = count_file_rows(file_path)
        
        if total_rows == 0:
            return None
            
        # 2. 샘플링 비율 계산
        sampling_ratio = min(target_count / total_rows, 1.0)
        
        # 3. 전략적 샘플링
        if sampling_ratio >= 0.1:  # 10% 이상이면 랜덤 샘플링
            return random_sampling(file_path, target_count)
        else:  # 10% 미만이면 계층적 샘플링
            return stratified_sampling(file_path, target_count)
            
    except Exception as e:
        print(f"샘플링 오류: {e}")
        return None

def random_sampling(file_path, target_count):
    """랜덤 샘플링"""
    total_rows = count_file_rows(file_path)
    skip_prob = 1 - (target_count / total_rows)
    
    # 확률적 스킵을 사용한 샘플링
    skip_rows = lambda x: x != 0 and np.random.random() < skip_prob
    
    df = pd.read_csv(file_path, skiprows=skip_rows)
    print(f"  랜덤 샘플링 적용")
    
    return df

def stratified_sampling(file_path, target_count):
    """계층적 샘플링 (선박 타입, 속도, 지역별 균등)"""
    print(f"  계층적 샘플링 적용")
    
    # 청크별로 읽기 (메모리 효율성)
    chunk_size = 100000
    samples = []
    samples_collected = 0
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        if samples_collected >= target_count:
            break
            
        # 청크에서 다양성 확보 샘플링
        chunk_sample = diverse_chunk_sampling(chunk, 
                                             min(target_count - samples_collected, 
                                                 len(chunk) // 10))
        
        if len(chunk_sample) > 0:
            samples.append(chunk_sample)
            samples_collected += len(chunk_sample)
    
    if samples:
        return pd.concat(samples, ignore_index=True)
    else:
        return pd.DataFrame()

def diverse_chunk_sampling(chunk, sample_size):
    """청크 내에서 다양성을 고려한 샘플링"""
    if len(chunk) <= sample_size:
        return chunk
    
    # 1. 기본 필터링 (품질 확보)
    filtered = chunk.dropna(subset=['LAT', 'LON', 'SOG'])
    
    if len(filtered) == 0:
        return pd.DataFrame()
    
    # 2. 다양성 기준 설정
    diversity_samples = []
    remaining_quota = sample_size
    
    # 선박 타입별 균등 샘플링
    if 'VesselType' in filtered.columns and remaining_quota > 0:
        vessel_sample = sample_by_category(filtered, 'VesselType', 
                                         remaining_quota // 3)
        diversity_samples.append(vessel_sample)
        remaining_quota -= len(vessel_sample)
    
    # 속도 구간별 샘플링
    if remaining_quota > 0:
        speed_sample = sample_by_speed_range(filtered, remaining_quota // 2)
        diversity_samples.append(speed_sample)
        remaining_quota -= len(speed_sample)
    
    # 지역별 샘플링
    if remaining_quota > 0:
        geo_sample = sample_by_geography(filtered, remaining_quota)
        diversity_samples.append(geo_sample)
    
    # 결합
    if diversity_samples:
        combined = pd.concat(diversity_samples, ignore_index=True)
        # 중복 제거
        combined = combined.drop_duplicates()
        return combined.sample(min(sample_size, len(combined)))
    else:
        return filtered.sample(min(sample_size, len(filtered)))

def sample_by_category(df, column, sample_size):
    """카테고리별 균등 샘플링"""
    if sample_size <= 0 or column not in df.columns:
        return pd.DataFrame()
    
    categories = df[column].value_counts()
    samples_per_category = max(1, sample_size // len(categories))
    
    samples = []
    for category in categories.index:
        category_data = df[df[column] == category]
        sample_count = min(samples_per_category, len(category_data))
        if sample_count > 0:
            samples.append(category_data.sample(sample_count))
    
    if samples:
        return pd.concat(samples, ignore_index=True)
    else:
        return pd.DataFrame()

def sample_by_speed_range(df, sample_size):
    """속도 구간별 샘플링"""
    if sample_size <= 0:
        return pd.DataFrame()
    
    # 속도 구간 정의
    df_copy = df.copy()
    df_copy['speed_range'] = pd.cut(df_copy['SOG'], 
                                   bins=[-1, 0, 5, 10, 15, 999],
                                   labels=['정박', '저속', '중속', '고속', '초고속'])
    
    return sample_by_category(df_copy, 'speed_range', sample_size)

def sample_by_geography(df, sample_size):
    """지역별 샘플링"""
    if sample_size <= 0:
        return pd.DataFrame()
    
    # 간단한 지역 구분
    df_copy = df.copy()
    
    # 지역 분류
    conditions = [
        (df_copy['LON'] < -115),  # 서부
        (df_copy['LON'] > -85),   # 동부
        True                      # 중부/멕시코만
    ]
    choices = ['서부', '동부', '중부']
    df_copy['region'] = np.select(conditions, choices, default='기타')
    
    return sample_by_category(df_copy, 'region', sample_size)

def post_process_sample(df):
    """샘플 후처리 및 품질 향상"""
    print(f"\n샘플 후처리 중...")
    print(f"후처리 전: {len(df):,} 레코드")
    
    # 1. 기본 품질 필터링
    df_clean = df.copy()
    
    # 필수 컬럼 결측치 제거
    essential_cols = ['LAT', 'LON', 'SOG', 'MMSI']
    available_cols = [col for col in essential_cols if col in df_clean.columns]
    df_clean = df_clean.dropna(subset=available_cols)
    
    # 2. 이상치 제거
    # 위치 이상치
    df_clean = df_clean[
        (df_clean['LAT'] >= -90) & (df_clean['LAT'] <= 90) &
        (df_clean['LON'] >= -180) & (df_clean['LON'] <= 180)
    ]
    
    # 속도 이상치 (102 knots 이상은 오류)
    df_clean = df_clean[df_clean['SOG'] <= 102]
    
    # 3. 연료 소비 예측을 위한 필수 피처 생성
    df_clean = create_fuel_prediction_features(df_clean)
    
    print(f"후처리 후: {len(df_clean):,} 레코드")
    print(f"데이터 손실: {(len(df) - len(df_clean))/len(df)*100:.1f}%")
    
    return df_clean

def create_fuel_prediction_features(df):
    """연료 소비 예측을 위한 피처 생성"""
    print("연료 소비 예측 피처 생성 중...")
    
    df_features = df.copy()
    
    # 1. 선박 크기 관련 피처
    if all(col in df.columns for col in ['Length', 'Width']):
        df_features['ship_area'] = df_features['Length'] * df_features['Width']
    
    if all(col in df.columns for col in ['Length', 'Width', 'Draft']):
        df_features['ship_volume'] = (df_features['Length'] * 
                                     df_features['Width'] * 
                                     df_features['Draft'])
    
    # 2. 속도 관련 피처 (연료 소비는 속도의 3제곱에 비례)
    df_features['speed_squared'] = df_features['SOG'] ** 2
    df_features['speed_cubed'] = df_features['SOG'] ** 3
    df_features['is_moving'] = (df_features['SOG'] > 1).astype(int)
    
    # 3. 시간 관련 피처
    if 'BaseDateTime' in df.columns:
        df_features['BaseDateTime'] = pd.to_datetime(df_features['BaseDateTime'])
        df_features['hour'] = df_features['BaseDateTime'].dt.hour
        df_features['day_of_week'] = df_features['BaseDateTime'].dt.dayofweek
        df_features['is_weekend'] = df_features['day_of_week'].isin([5, 6]).astype(int)
    
    # 4. 선박 타입 원핫 인코딩 (상위 10개만)
    if 'VesselType' in df.columns:
        top_vessel_types = df_features['VesselType'].value_counts().head(10).index
        for vtype in top_vessel_types:
            df_features[f'vessel_type_{vtype}'] = (df_features['VesselType'] == vtype).astype(int)
    
    # 5. 예상 연료 소비량 (간단한 추정식)
    df_features['estimated_fuel_consumption'] = estimate_fuel_consumption(df_features)
    
    print(f"생성된 피처 수: {len(df_features.columns) - len(df.columns)}")
    
    return df_features

def estimate_fuel_consumption(df):
    """간단한 연료 소비량 추정 (실제 타겟 변수)"""
    # 기본 연료 소비 공식 (매우 단순화된 버전)
    # 실제로는 더 복잡한 엔지니어링 공식 사용
    
    base_consumption = 10  # 기본 소비량 (톤/일)
    
    # 선박 크기 영향
    size_factor = 1
    if 'ship_area' in df.columns:
        size_factor = np.log1p(df['ship_area'].fillna(100) / 100)
    
    # 속도 영향 (3제곱 관계)
    speed_factor = (df['SOG'] / 10) ** 3
    
    # 선박 타입 영향
    type_factor = 1
    if 'VesselType' in df.columns:
        # 화물선과 유조선은 연료 소비가 높음
        high_consumption_types = [37.0, 31.0, 70.0]  # Cargo, Tanker, Container
        type_factor = df['VesselType'].isin(high_consumption_types).astype(float) * 0.5 + 1
    
    # 최종 연료 소비량 (톤/일)
    fuel_consumption = base_consumption * size_factor * speed_factor * type_factor
    
    # 현실적 범위로 클리핑 (0.1 ~ 500 톤/일)
    fuel_consumption = np.clip(fuel_consumption, 0.1, 500)
    
    return fuel_consumption

def analyze_sample_quality(df):
    """샘플 품질 분석"""
    print(f"\n샘플 품질 분석:")
    
    # 1. 기본 통계
    print(f"  총 레코드: {len(df):,}")
    print(f"  고유 선박 수: {df['MMSI'].nunique():,}")
    print(f"  날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
    
    # 2. 지역별 분포
    if all(col in df.columns for col in ['LAT', 'LON']):
        print(f"  위도 범위: {df['LAT'].min():.2f} ~ {df['LAT'].max():.2f}")
        print(f"  경도 범위: {df['LON'].min():.2f} ~ {df['LON'].max():.2f}")
    
    # 3. 속도 분포
    speed_dist = df['SOG'].describe()
    print(f"  속도 통계: 평균 {speed_dist['mean']:.1f}, 최대 {speed_dist['max']:.1f} knots")
    
    # 4. 선박 타입 분포
    if 'VesselType' in df.columns:
        top_types = df['VesselType'].value_counts().head(5)
        print(f"  주요 선박 타입:")
        for vtype, count in top_types.items():
            print(f"    {vtype}: {count:,} ({count/len(df)*100:.1f}%)")
    
    # 5. 연료 소비 분포
    if 'estimated_fuel_consumption' in df.columns:
        fuel_stats = df['estimated_fuel_consumption'].describe()
        print(f"  연료 소비 통계: 평균 {fuel_stats['mean']:.1f} 톤/일")

if __name__ == "__main__":
    result = smart_ais_sampling()
    if result is not None:
        print(f"\n✅ 지능적 AIS 샘플링 완료!")
        print(f"다음 단계: 기상 데이터와 매칭하여 ML 학습 데이터셋 구축")
    else:
        print(f"\n❌ AIS 샘플링 실패")
