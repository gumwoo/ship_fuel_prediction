"""
해상 기상 데이터 수집 모듈

Open-Meteo Marine API를 사용하여 해상 기상 데이터를 수집합니다.
AIS 데이터와 매칭되는 위치와 시간의 기상 데이터를 가져옵니다.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Tuple, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherCollector:
    """Open-Meteo Marine API를 사용한 해상 기상 데이터 수집기"""
    
    def __init__(self):
        self.base_url = "https://marine-api.open-meteo.com/v1/marine"
        self.session = requests.Session()
        
    def get_marine_weather(self, 
                          latitude: float, 
                          longitude: float, 
                          start_date: str, 
                          end_date: str) -> Dict:
        """
        특정 위치와 기간의 해상 기상 데이터를 가져옵니다.
        
        Args:
            latitude: 위도
            longitude: 경도
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            기상 데이터 딕셔너리
        """
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'start_date': start_date,
            'end_date': end_date,
            'hourly': [
                'wave_height',
                'wave_direction',
                'wind_wave_height',
                'swell_wave_height',
                'ocean_current_velocity',
                'ocean_current_direction',
                'sea_surface_temperature'
            ]
        }
        
        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"기상 데이터 수집 성공: {latitude:.2f}, {longitude:.2f}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"기상 데이터 수집 실패: {e}")
            return {}
    
    def collect_weather_for_ais_locations(self, 
                                        ais_data_path: str,
                                        output_path: str) -> pd.DataFrame:
        """
        AIS 데이터의 위치에 해당하는 기상 데이터를 수집합니다.
        
        Args:
            ais_data_path: AIS 데이터 파일 경로
            output_path: 출력 파일 경로
            
        Returns:
            기상 데이터 DataFrame
        """
        # AIS 데이터 읽기
        logger.info(f"AIS 데이터 읽는 중: {ais_data_path}")
        ais_df = pd.read_csv(ais_data_path)
        
        # 위치 정보 추출 (샘플링)
        locations = self._sample_locations(ais_df)
        
        # 날짜 범위 확인
        date_range = self._get_date_range_from_ais(ais_df)
        
        weather_data = []
        
        for i, (lat, lon) in enumerate(locations):
            logger.info(f"기상 데이터 수집 중 ({i+1}/{len(locations)}): {lat:.2f}, {lon:.2f}")
            
            weather = self.get_marine_weather(
                latitude=lat,
                longitude=lon,
                start_date=date_range['start'],
                end_date=date_range['end']
            )
            
            if weather:
                # 데이터 변환
                weather_df = self._process_weather_data(weather, lat, lon)
                weather_data.append(weather_df)
                
                # API 호출 제한 고려 (1초 대기)
                time.sleep(1)
        
        # 모든 기상 데이터 합치기
        if weather_data:
            combined_weather = pd.concat(weather_data, ignore_index=True)
            combined_weather.to_csv(output_path, index=False)
            logger.info(f"기상 데이터 저장 완료: {output_path}")
            return combined_weather
        else:
            logger.warning("수집된 기상 데이터가 없습니다.")
            return pd.DataFrame()
    
    def _sample_locations(self, ais_df: pd.DataFrame, max_locations: int = 20) -> List[Tuple[float, float]]:
        """AIS 데이터에서 대표적인 위치들을 샘플링합니다."""
        # 위도/경도 컬럼명 확인
        lat_col = None
        lon_col = None
        
        for col in ais_df.columns:
            col_lower = col.lower()
            if 'lat' in col_lower and lat_col is None:
                lat_col = col
            elif 'lon' in col_lower and lon_col is None:
                lon_col = col
        
        if not lat_col or not lon_col:
            logger.error("위도/경도 컬럼을 찾을 수 없습니다.")
            # 기본값으로 일반적인 컬럼명 시도
            possible_lat = ['LAT', 'Latitude', 'latitude', 'lat']
            possible_lon = ['LON', 'Longitude', 'longitude', 'lon', 'lng']
            
            for col in possible_lat:
                if col in ais_df.columns:
                    lat_col = col
                    break
                    
            for col in possible_lon:
                if col in ais_df.columns:
                    lon_col = col
                    break
        
        if not lat_col or not lon_col:
            logger.error(f"사용 가능한 컬럼: {list(ais_df.columns)}")
            return []
        
        # 유효한 위치 데이터만 필터링
        valid_data = ais_df.dropna(subset=[lat_col, lon_col])
        
        # 지역별로 클러스터링하여 대표 위치 선택
        if len(valid_data) > max_locations:
            # 균등하게 샘플링
            sample_indices = np.linspace(0, len(valid_data)-1, max_locations, dtype=int)
            sampled_data = valid_data.iloc[sample_indices]
        else:
            sampled_data = valid_data
        
        locations = [(float(row[lat_col]), float(row[lon_col])) 
                    for _, row in sampled_data.iterrows()]
        
        logger.info(f"샘플링된 위치 수: {len(locations)}")
        return locations
    
    def _get_date_range_from_ais(self, ais_df: pd.DataFrame) -> Dict[str, str]:
        """AIS 데이터에서 날짜 범위를 추출합니다."""
        # BaseDateTime 컬럼 찾기
        time_col = None
        for col in ais_df.columns:
            col_lower = col.lower()
            if 'time' in col_lower or 'date' in col_lower:
                time_col = col
                break
        
        if not time_col:
            # 기본값으로 2024년 12월 1-7일 사용
            logger.warning("시간 컬럼을 찾을 수 없어 기본 날짜 범위 사용")
            return {
                'start': '2024-12-01',
                'end': '2024-12-07'
            }
        
        # 날짜 변환 시도
        try:
            ais_df[time_col] = pd.to_datetime(ais_df[time_col])
            start_date = ais_df[time_col].min().strftime('%Y-%m-%d')
            end_date = ais_df[time_col].max().strftime('%Y-%m-%d')
            
            return {
                'start': start_date,
                'end': end_date
            }
        except:
            logger.warning("날짜 변환 실패, 기본 날짜 범위 사용")
            return {
                'start': '2024-12-01',
                'end': '2024-12-07'
            }
    
    def _process_weather_data(self, weather: Dict, lat: float, lon: float) -> pd.DataFrame:
        """기상 데이터를 DataFrame으로 변환합니다."""
        if 'hourly' not in weather:
            return pd.DataFrame()
        
        hourly = weather['hourly']
        
        # 시간 데이터 처리
        times = pd.to_datetime(hourly['time'])
        
        # DataFrame 생성
        weather_df = pd.DataFrame({
            'datetime': times,
            'latitude': lat,
            'longitude': lon,
            'wave_height': hourly.get('wave_height', [None] * len(times)),
            'wave_direction': hourly.get('wave_direction', [None] * len(times)),
            'wind_wave_height': hourly.get('wind_wave_height', [None] * len(times)),
            'swell_wave_height': hourly.get('swell_wave_height', [None] * len(times)),
            'ocean_current_velocity': hourly.get('ocean_current_velocity', [None] * len(times)),
            'ocean_current_direction': hourly.get('ocean_current_direction', [None] * len(times)),
            'sea_surface_temperature': hourly.get('sea_surface_temperature', [None] * len(times))
        })
        
        return weather_df

    def collect_weather_for_multiple_ais_files(self, 
                                             ais_files: List[str],
                                             output_dir: str) -> None:
        """
        여러 AIS 파일에 대해 기상 데이터를 수집합니다.
        
        Args:
            ais_files: AIS 파일 경로 리스트
            output_dir: 출력 디렉토리
        """
        for ais_file in ais_files:
            filename = ais_file.split('\\')[-1].replace('.csv', '_weather.csv')
            output_path = f"{output_dir}\\{filename}"
            
            logger.info(f"처리 중: {ais_file}")
            self.collect_weather_for_ais_locations(ais_file, output_path)


def main():
    """메인 실행 함수"""
    collector = WeatherCollector()
    
    # AIS 파일 목록
    ais_files = [
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_01.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_02.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_03.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_04.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_05.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_06.csv",
        "C:\\shipbuilding\\ship-fuel-prediction\\data\\AIS_2024_12_07.csv"
    ]
    
    # 출력 디렉토리
    output_dir = "C:\\shipbuilding\\ship-fuel-prediction\\data\\raw"
    
    # 기상 데이터 수집
    collector.collect_weather_for_multiple_ais_files(ais_files, output_dir)
    
    print("✅ 해상 기상 데이터 수집 완료!")


if __name__ == "__main__":
    main()
