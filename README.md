https://34.64.109.253/

flask 기반 웹입니다.

모델 파라미터는 용량이 커 따로 보관합니다.

모델 파라미터 파일(senet_final.pth) : https://drive.google.com/file/d/1akMvuFX5chIpQ0faDK1Yd7yGiAw2R7Ir/view?usp=sharing

## 전처리 벤치마크

같은 모델 가중치로 Quick, Draw! 원본의 32개 클래스에서 클래스당 20장씩 총 640장을 평가했습니다. 브라우저 비교에서는 같은 그림을 Chrome에서 재생해 획 종료 시점 3,174쌍을 측정했습니다. 표본 시드는 `guessorlearn-benchmark-v1`입니다. [Quick, Draw! 데이터 문서](https://github.com/googlecreativelab/quickdraw-dataset#the-quick-draw-dataset)

| 평가 경로 | Top-1 | Top-5 | 획당 응답 시간 p50 / p95 | 획당 평균 전송량 |
|---|---:|---:|---:|---:|
| Canvas PNG | 1.72% (11/640) | 13.91% (89/640) | 49.6 / 65.3 ms | 22,523 B |
| 브라우저 벡터 | 74.22% (475/640) | 94.38% (604/640) | 39.6 / 49.4 ms | 998 B |
| 오프라인 모델 평가 | 74.22% (475/640) | 94.69% (606/640) | — | — |

Canvas PNG 경로는 512×512 캔버스를 PNG로 보내고, 서버에서 회색조로 변환한 뒤 `BOX` 리샘플링으로 64×64로 줄입니다. 브라우저 벡터 경로는 기록된 좌표를 보내고, 기존 Bresenham 변환으로 64×64 이진 입력을 만듭니다. 오프라인 평가는 원본 획의 좌표를 모두 유지해 64×64 이진 입력을 만들고 모델에 입력합니다.

정확도는 완성 그림 기준입니다. 응답 시간은 Chrome에서 요청 데이터 준비를 시작한 시점부터 응답 JSON을 파싱하기까지이며, 전송량은 HTTP 요청 본문 크기입니다. 브라우저 측정은 Windows의 Chrome과 CPU 추론 스레드 4개로 진행했습니다.

정확도 차이에는 좌표 필터, 선 두께, 축소 방식, 안티앨리어싱의 영향이 함께 반영됩니다. 평가 표본과 학습 데이터의 중복 여부는 확인되지 않았습니다.

### 재현 방법

위 링크의 `senet_final.pth`를 프로젝트 루트에 둡니다. 새 Windows 가상환경을 준비하려면 아래 명령을 실행합니다.

```powershell
python -m venv project_env
.\project_env\Scripts\python.exe -m pip install flask numpy pillow
.\project_env\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

표본을 준비한 뒤 오프라인 평가와 브라우저 벤치마크를 실행합니다.

```powershell
.\project_env\Scripts\python.exe benchmark_data.py
.\project_env\Scripts\python.exe benchmark_offline.py
.\project_env\Scripts\python.exe benchmark.py
```

표본 목록은 `project_env/benchmark/dataset.json`에 저장되고, 오프라인 평가는 정확도와 정답 수를 터미널에 출력합니다. Chrome에서 [벤치마크 페이지](http://127.0.0.1:5001/)를 열어 **벤치마크 실행**을 누릅니다. 실행별 보고서와 CSV는 `project_env/benchmark/runs`에 저장되며, CSV의 `final=True` 행에는 완성 그림의 예측이 담깁니다.
