# ============================================================
# builder/i18n.py
# 시스템 로케일 감지 + 번역 사전 관리
#
# 감지 우선순위:
#   1) Windows UI 언어 (GetUserDefaultUILanguage) -> ko/en/ja 매칭
#   2) locale.getdefaultlocale() 폴백
#   3) 그 외 -> 'en' 폴백
# 사용자가 UI 에서 수동 오버라이드 가능.
# ============================================================
import ctypes
import json
import locale
import os

SUPPORTED = ('ko', 'en', 'ja')
LANG_NAMES = {'ko': '한국어', 'en': 'English', 'ja': '日本語'}


def detect_lang():
    """시스템 UI 언어 감지 -> 'ko'/'en'/'ja' (지원 외는 'en')."""
    # 1) Windows UI 언어
    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        code = locale.windows_locale.get(langid, '')
        if code:
            code = code.split('_')[0].lower()
            if code in SUPPORTED:
                return code
    except Exception:
        pass
    # 2) 기본 로케일 폴백
    try:
        code, _ = locale.getdefaultlocale()
        if code:
            code = code.split('_')[0].lower()
            if code in SUPPORTED:
                return code
    except Exception:
        pass
    return 'en'


class I18n:
    """번역 사전. tr(key, **kwargs) 로 문자열 조회."""

    def __init__(self, locales_dir=None):
        self._tables = {}
        self._lang = 'en'
        base = locales_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'locales')
        for lang in SUPPORTED:
            p = os.path.join(base, '%s.json' % lang)
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f:
                    self._tables[lang] = json.load(f)

    def set_lang(self, lang):
        if lang in self._tables:
            self._lang = lang

    def get_lang(self):
        return self._lang

    def tr(self, key, **kw):
        s = self._tables.get(self._lang, {}).get(key)
        if s is None:
            s = self._tables.get('en', {}).get(key, key)
        if kw:
            for k, v in kw.items():
                s = s.replace('{%s}' % k, str(v))
        return s
