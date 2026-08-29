# ============================================================
# main.py
# 커서 빌더 GUI 진입점
# 시스템 로케일 감지 -> 언어 적용 -> 메인 윈도우 실행
# ============================================================
import os
import sys

# PyInstaller --onefile 환경에서도 패키지를 찾도록 경로 보정
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

import tkinter as tk

import ttkbootstrap as tb

from builder.i18n import I18n, detect_lang
from ui.main_window import MainWindow

# 시작 기본 테마 (2020년대 모던 룩)
DEFAULT_THEME = 'bootstrap-dark'


def main():
    i18n = I18n()
    i18n.set_lang(detect_lang())
    root = tb.Window(themename=DEFAULT_THEME)
    MainWindow(root, i18n)
    root.mainloop()


if __name__ == '__main__':
    main()
