# Giftuner

AULA F108 Pro (독거미 F108 Pro) LCD용 GIF 편집기.
1.14" TFT LCD (240×135, 최대 141 프레임) 타겟으로 GIF를 생성/편집합니다.

## 기능

- **멀티 포맷 입력**: GIF, MP4, WebP, APNG, PNG, MOV, MKV, WebM, AVI
- **16:9 비율 락**: 폭 또는 높이 중 하나만 입력해도 자동으로 나머지 계산 (예: 480 → 270)
- **프레임 자동 캡**: 141프레임 초과 시 균등 샘플링으로 자동 축소 (원본 전체 길이는 유지)
- **RIFE 프레임 보간** (선택): 2x / 4x
- **Real-ESRGAN 업스케일** (선택): 2x / 3x / 4x
- **실시간 애니메이션 미리보기**
- **GIF 출력** (Pillow)

## 설치

```bash
pip install -r requirements.txt
```

### 외부 바이너리 (선택 기능)

RIFE / Real-ESRGAN 기능을 쓰려면 아래 바이너리를 받아 PATH에 추가해 주세요. GPU 드라이버만 있으면 Vulkan으로 동작하므로 PyTorch 설치는 필요 없습니다.

- **RIFE**: [rife-ncnn-vulkan releases](https://github.com/nihui/rife-ncnn-vulkan/releases)
- **Real-ESRGAN**: [Real-ESRGAN releases](https://github.com/xinntao/Real-ESRGAN/releases) (`realesrgan-ncnn-vulkan`)

## 실행

```bash
python -m giftuner.main
```

## 사용 흐름

1. **Load file…** 로 GIF / MP4 / WebP 등 로드
2. 필요하면 RIFE / 업스케일 옵션 켜기
3. 원하는 폭 또는 높이 입력 (비율 자동 락)
4. **Process preview** 로 결과 확인
5. **Export GIF…** 로 저장
6. 저장된 GIF를 AULA 순정 드라이버의 `TFT Screen → Import` 로 올리기

## 파이프라인

```
Input → (RIFE?) → (Upscale?) → Resize(16:9) → FrameCap(141) → GIF
```

## 타겟 하드웨어

AULA F108 Pro 1.14" TFT LCD:
- 해상도: 240 × 135
- 최대 프레임: 141
- 업로드: Windows 전용 드라이버 + USB-C 유선 (순정 드라이버로 진행)

---

## 📦 배포용 EXE 빌드 (개발자용)

PyInstaller `--onedir` 로 Windows 실행 파일을 만들고 ZIP으로 패키징합니다.

### 1. 바이너리 배치 (선택)

RIFE / Real-ESRGAN 을 번들하려면 `bin/` 폴더에 미리 넣어두세요.
자세한 배치 방법은 [`bin/README.md`](bin/README.md) 참고.

`bin/` 을 비워두면 빌드는 되지만 사용자가 수동으로 바이너리를 설치해야 RIFE/업스케일 기능이 동작합니다.

### 2. 빌드

```powershell
.\build.ps1
```

이 스크립트가 하는 일:
- `pyinstaller` 설치
- `build/`, `dist/` 정리
- `giftuner.spec` 기반으로 빌드
- `dist\Giftuner\output\` 폴더 미리 생성

완료되면 `dist\Giftuner\Giftuner.exe` 가 생깁니다. 더블클릭해서 바로 테스트 가능.

### 3. ZIP 패키징

```powershell
.\package.ps1
```

`dist\Giftuner-v0.1.0-windows.zip` 생성. 사용자는 이 ZIP을 받아서:
1. 원하는 곳에 압축 해제
2. `Giftuner.exe` 더블클릭

### 배포 폴더 구조

```
Giftuner\
├── Giftuner.exe               ← 실행 파일
├── _internal\                 ← PyInstaller 런타임 (Qt, Pillow 등)
├── bin\                       ← 번들된 RIFE / Real-ESRGAN
│   ├── rife-ncnn-vulkan.exe
│   ├── realesrgan-ncnn-vulkan.exe
│   └── ... (모델 파일들)
└── output\                    ← GIF가 여기 저장됨
```

### 주의사항

- `--onefile` 이 아니라 `--onedir` 입니다. 하나의 EXE처럼 보이고 싶다면 폴더째 ZIP으로 압축해서 배포하세요.
- 배포 크기는 번들한 바이너리/모델에 따라 보통 **200~300MB** 정도입니다 (ZIP 압축 후 ~100MB).
- 사용자 환경의 **Vulkan 지원 GPU 드라이버**가 필요합니다. GPU가 없거나 드라이버가 구형이면 GPU 가속은 동작하지 않습니다.
