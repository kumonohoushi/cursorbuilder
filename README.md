# CursorBuilder

**한국어** · [English](README.en.md) · [日本語](README.ja.md)

마우스 커서(**`.cur` / `.ani`**)를 만드는 GUI 도구입니다.
zip 또는 폴더의 커서/이미지를 읽어, 미리보기 위에서 핫스팟을 지정하고
다중 레이어 커서로 변환합니다.

## 주요 기능

- **입력 소스**: zip 또는 폴더 스캔
  - `.cur` / `.ani` : 기존 커서 그대로 처리
  - 정적 이미지(`.png .jpg .bmp .ico .webp .tiff ...`) : **`.cur`** 로 변환
  - `.gif` : **`.ani`** 로 변환 (프레임별 지속시간 반영)
- **핫스팟 지정** (4가지 방식)
  - 사각형 드래그 + 무게중심 / 팁 / 좌상단 모서리
  - 직접 지정 (클릭) — 이미지를 클릭해 픽셀 단위로 지정
  - 지정된 영역은 창 크기 조절처럼 **8개 핸들로 미세 조절**
- **변환**: 다중 레이어 `.cur`(16/24/32/48/64/96...) 생성, `.ani` 복사
- **i18n**: 시스템 로케일에 따라 **한국어 / English / 日本語** 자동 적용 (수동 전환 가능)
- **테마**: 2020년대 스타일 모던 테마 16종 실시간 전환
  (bootstrap / catppuccin / tokyo-night / dracula / vapor / nord / gruvbox / one)

## 실행

```bash
python -m pip install -r requirements.txt
python main.py
```

## 스탠드얼론 빌드 (PyInstaller)

```bash
build.bat
# 산출물: dist/CursorBuilder.exe
```

아이콘은 `icons/app.ico`가 있으면 자동 적용됩니다.

## 프로젝트 구조

```
cursorbuilder/
├── main.py               # 진입점 (로케일 감지 → 테마 적용 → 메인 윈도우)
├── builder/              # 순수 로직 (GUI 비의존)
│   ├── curio.py          # .cur 파싱/빌드
│   ├── anio.py           # .ani 파싱/빌드 (RIFF/ACON)
│   ├── loader.py         # zip/폴더 스캔 + 정사각화 + GIF 프레임 추출
│   ├── hotspot.py        # 드래그 영역 → 핫스팟 계산, 비례 스케일
│   ├── output.py         # 다중 레이어 .cur / .ani 생성
│   └── i18n.py           # 로케일 감지 + 번역 사전
├── ui/main_window.py     # Tkinter + ttkbootstrap UI
├── locales/              # ko / en / ja 번역
└── requirements.txt
```

## 라이선스

[Apache License 2.0](LICENSE)

> **주의**: 커서를 재배포·수정할 때는 원본 작성자의 저작권·라이선스 약관을
> 반드시 확인하십시오. 본 도구는 커서 생성/변환을 위한 도구일 뿐이며,
> 포함된 커서 자산에 대한 권리를 부여하지 않습니다.
