# bin/

이 폴더에 **RIFE** 와 **Real-ESRGAN** 바이너리가 들어 있습니다. Giftuner가 실행 시 자동으로 감지해서 사용합니다.

## 현재 구성

```
bin/
├── rife-ncnn-vulkan.exe        ← RIFE 실행 파일
├── realesrgan-ncnn-vulkan.exe  ← Real-ESRGAN 실행 파일
├── vcomp140.dll                ← 런타임 DLL (공통)
├── rife-v4.6/                  ← RIFE 모델 (Giftuner 기본값)
│   ├── flownet.bin
│   └── flownet.param
└── models/                     ← Real-ESRGAN 모델 (animevideov3 only)
    ├── realesr-animevideov3-x2.bin
    ├── realesr-animevideov3-x2.param
    ├── realesr-animevideov3-x3.bin
    ├── realesr-animevideov3-x3.param
    ├── realesr-animevideov3-x4.bin
    └── realesr-animevideov3-x4.param
```

Giftuner는 Real-ESRGAN의 `realesr-animevideov3` 모델만 사용합니다 — 비디오 프레임 간 일관성이 좋고, 2x/3x/4x 배율을 모두 지원하며 속도가 가장 빠르기 때문입니다. 불필요한 다른 모델(`realesrgan-x4plus`, `realesrgan-x4plus-anime`)은 배포에서 제외했습니다.

## 출처

| 구성 요소 | 다운로드 |
|---|---|
| `rife-ncnn-vulkan.exe` + `rife-v4.6/` | https://github.com/nihui/rife-ncnn-vulkan/releases |
| `realesrgan-ncnn-vulkan.exe` + `models/` | https://github.com/xinntao/Real-ESRGAN/releases |

## 모델 변경

Giftuner는 기본적으로 `rife-v4.6` 모델을 사용합니다. 다른 RIFE 모델(예: `rife-anime`)을 사용하려면:

1. 원본 zip에서 해당 모델 폴더를 이 `bin/` 폴더에 복사
2. `giftuner/core/rife.py` 의 `model` 파라미터 변경

## 확인

Giftuner 실행 후 **GPU 가속 그룹 → GPU 다시 검색** 버튼을 누르면 감지된 GPU 이름이 표시됩니다. 이게 뜨면 바이너리 배치가 정상입니다.
