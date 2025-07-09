"""
AIS-기상 데이터 시공간 매칭 모듈

AIS 샘플 데이터와 기상 데이터를 시간과 공간 기준으로 매칭하여
ML 학습용 통합 데이터셋을 생성합니다.
"""

import pandas as pd
import numpy as np
import yaml
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataMatcher:
    """AIS-기상 데이터 시공간 매칭 클래스"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        DataMatcher 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()
        self._setup_paths()
        
        logger.info("DataMatcher 초기화 완료")
        logger.info(f"설정 파일: {config_path}")
        
    def _load_config(self) -> Dict:
        """YAML 설정 파일을 로드합니다."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                logger.info(f"설정 파일 로드 성공: {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML 파일 파싱 오류: {e}")
            raise
            
    def _setup_logging(self):
        """WeatherCollector 패턴과 동일한 로깅 설정"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 로깅 레벨 설정
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        
        # 핸들러 설정
        handler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        
        # 기존 핸들러 제거 후 새 핸들러 추가
        logger.handlers.clear()
        logger.addHandler(handler)
        
        logger.info("로깅 설정 완료")
        
    def _setup_paths(self):
        """경로 설정 및 디렉토리 생성"""
        paths = self.config.get('paths', {})
        
        self.raw_data_path = paths.get('raw_data', 'data/raw/')
        self.processed_data_path = paths.get('processed_data', 'data/processed/')
        self.models_path = paths.get('models', 'data/models/')
        self.logs_path = paths.get('logs', 'logs/')
        
        # 필요한 디렉토리 생성
        for path in [self.processed_data_path, self.models_path, self.logs_path]:
            Path(path).mkdir(parents=True, exist_ok=True)
            
        logger.info("경로 설정 완료")
        logger.info(f"  원시 데이터: {self.raw_data_path}")
        logger.info(f"  처리된 데이터: {self.processed_data_path}")
        logger.info(f"  모델: {self.models_path}")
        logger.info(f"  로그: {self.logs_path}")
        
    def get_feature_config(self) -> Dict:
        """설정 파일에서 피처 정보를 가져옵니다."""
        return self.config.get('features', {})
        
    def get_model_config(self) -> Dict:
        """설정 파일에서 모델 정보를 가져옵니다."""
        return self.config.get('model', {})
        
    def get_data_sources_config(self) -> Dict:
        """설정 파일에서 데이터 소스 정보를 가져옵니다."""
        return self.config.get('data_sources', {})


    def load_ais_sample_data(self) -> pd.DataFrame:
        """
        AIS 샘플 데이터를 로드하고 전처리를 수행합니다.
        
        Returns:
            전처리된 AIS 데이터 DataFrame
        """
        logger.info("AIS 샘플 데이터 로드 시작")
        
        # AIS 원본 파일들에서 샘플링하여 로드
        ais_files = [
            f"{self.raw_data_path}ais/AIS_2024_12_01.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_02.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_03.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_04.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_05.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_06.csv",
            f"{self.raw_data_path}ais/AIS_2024_12_07.csv"
        ]
        
        # 각 파일에서 샘플링하여 로드
        samples_per_file = 5000  # 테스트용으로 파일당 5천개씩 (총 3.5만개)
        all_samples = []
        
        for i, ais_file in enumerate(ais_files):
            if not os.path.exists(ais_file):
                logger.warning(f"AIS 파일을 찾을 수 없습니다: {ais_file}")
                continue
                
            logger.info(f"AIS 파일 처리 중 ({i+1}/{len(ais_files)}): {ais_file}")
            
            try:
                # 파일 크기 확인을 위한 행 수 계산
                total_rows = sum(1 for line in open(ais_file, 'r', encoding='utf-8')) - 1
                logger.info(f"  전체 레코드: {total_rows:,}")
                
                # 메모리 효율적인 샘플링
                if total_rows > samples_per_file:
                    # 균등 간격으로 샘플링
                    skip_interval = max(1, total_rows // samples_per_file)
                    sample_indices = list(range(0, total_rows, skip_interval))[:samples_per_file]
                    
                    # pandas로 특정 행만 읽기
                    df_sample = pd.read_csv(ais_file, skiprows=lambda x: x not in sample_indices and x != 0)
                else:
                    # 전체 데이터가 목표보다 작으면 모두 로드
                    df_sample = pd.read_csv(ais_file)
                
                # 날짜 및 소스 정보 추가
                df_sample['date'] = f"2024-12-{i+1:02d}"
                df_sample['file_source'] = ais_file
                
                all_samples.append(df_sample)
                logger.info(f"  샘플링된 레코드: {len(df_sample):,}")
                
            except Exception as e:
                logger.error(f"파일 처리 중 오류 발생 {ais_file}: {e}")
                continue
        
        if not all_samples:
            raise ValueError("로드된 AIS 데이터가 없습니다.")
        
        # 모든 샘플 결합
        combined_df = pd.concat(all_samples, ignore_index=True)
        logger.info(f"전체 결합된 레코드: {len(combined_df):,}")
        
        # 전처리 수행
        processed_df = self._preprocess_ais_data(combined_df)
        
        logger.info(f"전처리 완료. 최종 레코드: {len(processed_df):,}")
        return processed_df
    
    def _preprocess_ais_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        AIS 데이터 전처리를 수행합니다.
        
        Args:
            df: 원본 AIS 데이터 DataFrame
            
        Returns:
            전처리된 AIS 데이터 DataFrame
        """
        logger.info("AIS 데이터 전처리 시작")
        original_count = len(df)
        
        # 1. 컬럼명 정규화 (이미 표준 형식)
        logger.info("컬럼명 확인 및 정규화")
        required_columns = ['MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', 'VesselType']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
        
        # 2. 시간 데이터 파싱 및 UTC 변환
        logger.info("시간 데이터 변환")
        df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'], errors='coerce')
        df = df.dropna(subset=['BaseDateTime'])
        logger.info(f"시간 변환 후 레코드: {len(df):,}")
        
        # 3. 위치 데이터 유효성 검증
        logger.info("위치 데이터 검증")
        df = self._validate_location_data(df)
        logger.info(f"위치 검증 후 레코드: {len(df):,}")
        
        # 4. 속도 및 항로 데이터 검증
        logger.info("속도 및 항로 데이터 검증")
        df = self._validate_navigation_data(df)
        logger.info(f"항해 데이터 검증 후 레코드: {len(df):,}")
        
        # 5. 선박 타입 및 크기 정보 처리
        logger.info("선박 정보 처리")
        df = self._process_vessel_info(df)
        
        # 6. 중복 제거
        logger.info("중복 데이터 제거")
        df = df.drop_duplicates(subset=['MMSI', 'BaseDateTime'], keep='first')
        logger.info(f"중복 제거 후 레코드: {len(df):,}")
        
        # 7. 데이터 정렬
        df = df.sort_values(['BaseDateTime', 'MMSI']).reset_index(drop=True)
        
        logger.info(f"전처리 완료: {original_count:,} → {len(df):,} 레코드 ({len(df)/original_count*100:.1f}% 유지)")
        return df
    
    def _validate_location_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """위치 데이터 유효성 검증"""
        # 위도: -90 ~ 90
        # 경도: -180 ~ 180
        valid_mask = (
            (df['LAT'] >= -90) & (df['LAT'] <= 90) &
            (df['LON'] >= -180) & (df['LON'] <= 180) &
            (df['LAT'] != 0) & (df['LON'] != 0)  # 0,0 좌표 제외
        )
        
        invalid_count = len(df) - valid_mask.sum()
        if invalid_count > 0:
            logger.warning(f"유효하지 않은 위치 데이터 {invalid_count:,}개 제거")
        
        return df[valid_mask].copy()
    
    def _validate_navigation_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """항해 데이터 유효성 검증"""
        # SOG (Speed Over Ground): 0 ~ 50 노트 (일반적인 상선 속도 범위)
        # COG (Course Over Ground): 0 ~ 360도
        valid_mask = (
            (df['SOG'] >= 0) & (df['SOG'] <= 50) &
            (df['COG'] >= 0) & (df['COG'] <= 360)
        )
        
        invalid_count = len(df) - valid_mask.sum()
        if invalid_count > 0:
            logger.warning(f"유효하지 않은 항해 데이터 {invalid_count:,}개 제거")
        
        return df[valid_mask].copy()
    
    def _process_vessel_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """선박 정보 처리 및 정제"""
        # VesselType을 숫자형으로 변환 (문자열인 경우 처리)
        if df['VesselType'].dtype == 'object':
            df['VesselType'] = pd.to_numeric(df['VesselType'], errors='coerce')
        
        # 결측값이 있는 경우 기본값 설정
        df['VesselType'] = df['VesselType'].fillna(0)
        
        # Length, Width, Draft 등의 선박 제원 데이터 정제
        numeric_columns = ['Length', 'Width', 'Draft']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(df[col].median())
        
        return df


def main():
    """테스트용 메인 함수"""
    try:
        matcher = DataMatcher()
        
        # 설정 정보 출력
        print("DataMatcher 설정 정보:")
        print(f"  프로젝트: {matcher.config['project']['name']}")
        print(f"  버전: {matcher.config['project']['version']}")
        print(f"  작성자: {matcher.config['project']['author']}")
        
        feature_config = matcher.get_feature_config()
        print(f"  AIS 피처 수: {len(feature_config.get('ais_features', []))}")
        print(f"  기상 피처 수: {len(feature_config.get('weather_features', []))}")
        print(f"  엔지니어링 피처 수: {len(feature_config.get('engineered_features', []))}")
        
        print("DataMatcher 클래스 초기화 성공!")
        
        # AIS 데이터 로드 테스트
        print("\nAIS 데이터 로드 테스트...")
        ais_data = matcher.load_ais_sample_data()
        print(f"로드된 AIS 데이터: {len(ais_data):,} 레코드")
        print(f"데이터 기간: {ais_data['BaseDateTime'].min()} ~ {ais_data['BaseDateTime'].max()}")
        print(f"위치 범위: 위도 {ais_data['LAT'].min():.2f}~{ais_data['LAT'].max():.2f}, 경도 {ais_data['LON'].min():.2f}~{ais_data['LON'].max():.2f}")
        print(f"속도 범위: {ais_data['SOG'].min():.1f}~{ais_data['SOG'].max():.1f} 노트")
        
    except Exception as e:
        print(f"DataMatcher 초기화 실패: {e}")
        logger.error(f"초기화 실패: {e}")
        

if __name__ == "__main__":
    main()
