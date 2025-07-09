#!/usr/bin/env python3
"""
Open-Meteo Marine API 직접 테스트
"""

import requests
import json 

def test_open_meteo_api():
    """Open-Meteo Marine API 테스트"""
    print("Open-Meteo Marine API 테스트 시작...")
    
    # API 엔드포인트
    url = "https://marine-api.open-meteo.com/v1/marine"
    
    # 테스트 파라미터 (로스앤젤레스 항구 근처)
    params = {
        'latitude': 33.847,
        'longitude': -118.397,
        'start_date': '2024-12-01',
        'end_date': '2024-12-01',
        'hourly': [
            'wave_height',
            'wave_direction',
            'wind_wave_height',
            'swell_wave_height',
            'ocean_current_velocity',
            'sea_surface_temperature'
        ]
    }
    
    print(f"테스트 위치: {params['latitude']}, {params['longitude']}")
    print(f"테스트 날짜: {params['start_date']}")
    print(f"API URL: {url}")
    
    try:
        # API 호출
        print("\nAPI 호출 중...")
        response = requests.get(url, params=params, timeout=30)
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 크기: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("API 호출 성공!")
            
            # JSON 파싱
            data = response.json()
            print(f"응답 키: {list(data.keys())}")
            
            # 시간별 데이터 확인
            if 'hourly' in data:
                hourly = data['hourly']
                print(f"시간별 데이터 키: {list(hourly.keys())}")
                
                # 데이터 포인트 수 확인
                if 'time' in hourly:
                    time_points = len(hourly['time'])
                    print(f"총 시간 포인트: {time_points}")
                    
                    # 샘플 데이터 출력
                    print("\n샘플 데이터:")
                    for i in range(min(3, time_points)):
                        time_str = hourly['time'][i]
                        wave_height = hourly.get('wave_height', [None])[i]
                        wind_wave_height = hourly.get('wind_wave_height', [None])[i]
                        swell_height = hourly.get('swell_wave_height', [None])[i]
                        ocean_velocity = hourly.get('ocean_current_velocity', [None])[i]
                        sea_temp = hourly.get('sea_surface_temperature', [None])[i]
                        
                        print(f"  {time_str}: 파도={wave_height}m, 바람파도={wind_wave_height}m, 너울={swell_height}m, 해류={ocean_velocity}km/h, 수온={sea_temp}°C")
                    
                    # 유효 데이터 비율 계산
                    wave_data = hourly.get('wave_height', [])
                    valid_wave_count = sum(1 for x in wave_data if x is not None)
                    valid_ratio = valid_wave_count / len(wave_data) if wave_data else 0
                    
                    print(f"\n데이터 품질:")
                    print(f"   - 유효한 파도 데이터: {valid_wave_count}/{len(wave_data)} ({valid_ratio:.1%})")
                    
                    if valid_ratio >= 0.8:
                        print("데이터 품질 양호!")
                        return True
                    else:
                        print("데이터 품질 주의")
                        return False
                else:
                    print("시간 데이터 없음")
                    return False
            else:
                print("시간별 데이터 없음")
                return False
                
        else:
            print(f"API 호출 실패: {response.status_code}")
            print(f"오류 내용: {response.text}")
            
            # 일반적인 오류 원인 안내
            if response.status_code == 400:
                print("\n가능한 원인:")
                print("   - 잘못된 위도/경도 좌표")
                print("   - 잘못된 날짜 형식")
                print("   - 지원하지 않는 파라미터")
            elif response.status_code == 429:
                print("\nAPI 호출 제한 초과 - 잠시 후 다시 시도하세요")
            elif response.status_code == 500:
                print("\n서버 오류 - Open-Meteo 서비스 문제일 수 있습니다")
            
            return False
            
    except requests.exceptions.Timeout:
        print("API 호출 타임아웃 (30초)")
        print("네트워크 연결을 확인하거나 잠시 후 다시 시도하세요")
        return False
        
    except requests.exceptions.ConnectionError:
        print("네트워크 연결 오류")
        print("인터넷 연결을 확인하세요")
        return False
        
    except json.JSONDecodeError:
        print("JSON 파싱 오류")
        print(f"응답 내용: {response.text[:500]}...")
        return False
        
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_open_meteo_api()
    
    if success:
        print("\nOpen-Meteo API 테스트 성공!")
        print("   WeatherCollector 사용 가능")
    else:
        print("\nOpen-Meteo API 테스트 실패!")
        print("   수동으로 해상 기상 데이터를 확보해야 합니다")
        
        print("\n수동 데이터 수집 방법:")
        print("1. https://open-meteo.com/en/docs/marine-weather-api 접속")
        print("2. 위도/경도 입력: AIS 데이터에서 추출한 좌표")
        print("3. 날짜 설정: 2024-12-01 ~ 2024-12-07")
        print("4. 변수 선택: Wave height, Wind speed, Wind direction")
        print("5. CSV 형식으로 다운로드")
        print("6. data/raw/ 폴더에 weather_YYYY_MM_DD.csv 형식으로 저장")
