# ============================================================
# ui/main_window.py
# Tkinter 기반 메인 윈도우
#  - 입력(zip/폴더) 선택, 커서 목록, 미리보기+드래그 핫스팟, 설정, 변환
# ============================================================
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import ttkbootstrap as tb
from PIL import Image, ImageTk

from builder import loader, output
from builder.hotspot import compute_hotspot
from builder.i18n import detect_lang, LANG_NAMES

# 2020년대 모던 테마 선택지 (ttkbootstrap 2.x 프리셋)
THEMES = ['bootstrap-dark', 'bootstrap-light',
          'catppuccin-dark', 'catppuccin-light',
          'tokyo-night-dark', 'tokyo-night-light',
          'dracula-dark', 'dracula-light',
          'vapor-dark', 'vapor-light',
          'nord-dark', 'nord-light',
          'gruvbox-dark', 'gruvbox-light',
          'one-dark', 'one-light']

# 차분한 강조 색 (강렬한 #ff0000 대신 부드러운 빨강)
ACCENT = '#e05555'


class MainWindow:
    CANVAS = 440  # 미리보기 캔버스 표시 크기(px)

    def __init__(self, root, i18n):
        self.root = root
        self.i18n = i18n
        self.meta_list = []
        self.current = None
        self.rect = None
        self.drag_start = None
        self.resize_mode = None
        self.point = None         # point(직접 지정) 모드의 핫스팟 좌표
        self.point_active = False
        self.hotspots = {}   # name -> {'rect':..|'point':.., 'mode':..}
        self.scale = 8
        self._imgtk = None
        self._theme_fg = '#000000'

        self._build_ui()
        self._apply_canvas_colors()   # 먼저 테마 색 적용 (문구 그리기 전)
        self._apply_lang()

    # ---------------- UI 구성 ----------------
    def _build_ui(self):
        root = self.root
        root.geometry('1040x760')
        root.minsize(1024, 768)

        # 상단: 입력 선택
        top = ttk.Frame(root, padding=8)
        top.pack(fill='x')
        self.lbl_input = ttk.Label(top, text='')
        self.lbl_input.pack(side='left')
        self.btn_folder = ttk.Button(top, text='', command=self._pick_folder)
        self.btn_folder.pack(side='left', padx=3)
        self.btn_zip = ttk.Button(top, text='', command=self._pick_zip)
        self.btn_zip.pack(side='left', padx=3)
        self.var_input = tk.StringVar()
        ttk.Label(top, textvariable=self.var_input, relief='sunken',
                  anchor='w').pack(side='left', fill='x', expand=True, padx=4)

        # 메인 3열
        main = ttk.Frame(root, padding=8)
        main.pack(fill='both', expand=True)

        # 좌: 커서 목록
        left = ttk.LabelFrame(main)
        left.grid(row=0, column=0, sticky='ns', padx=4)
        self.lbl_list = ttk.Label(left, text='')
        self.lbl_list.pack(anchor='w', padx=6, pady=4)
        lrow = ttk.Frame(left)
        lrow.pack(fill='both', expand=True)
        self.lst = tk.Listbox(lrow, width=30, height=24)
        self.lst.pack(side='left', fill='y')
        sb = ttk.Scrollbar(lrow, command=self.lst.yview)
        sb.pack(side='right', fill='y')
        self.lst.config(yscrollcommand=sb.set)
        self.lst.bind('<<ListboxSelect>>', self._on_select)

        # 중앙: 미리보기
        center = ttk.LabelFrame(main)
        center.grid(row=0, column=1, sticky='nsew', padx=4)
        self.lbl_preview = ttk.Label(center, text='')
        self.lbl_preview.pack(anchor='w', padx=6, pady=4)
        self.canvas = tk.Canvas(center, width=self.CANVAS, height=self.CANVAS,
                                bg='white', highlightthickness=1)
        self.canvas.pack(padx=6, pady=2)
        self.canvas.bind('<Button-1>', self._on_drag_start)
        self.canvas.bind('<B1-Motion>', self._on_drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._on_drag_end)
        self.canvas.bind('<Motion>', self._on_motion)
        self.lbl_meta = ttk.Label(center, text='', wraplength=430,
                                  justify='left', font=('TkDefaultFont', 9))
        self.lbl_meta.pack(anchor='w', padx=6, pady=(2, 0))
        self.lbl_status = ttk.Label(center, text='', wraplength=430,
                                    justify='left', foreground='#c00')
        self.lbl_status.pack(anchor='w', padx=6, pady=(0, 4))

        # 우: 설정
        right = ttk.LabelFrame(main)
        right.grid(row=0, column=2, sticky='ns', padx=4)
        self.lbl_options = ttk.Label(right, text='')
        self.lbl_options.pack(anchor='w', padx=8, pady=4)
        self._build_options(right)

        main.columnconfigure(1, weight=1)

        # 하단: 변환 + 로그 + 상태
        bottom = ttk.Frame(root, padding=8)
        bottom.pack(fill='both', expand=True)
        self.btn_convert = ttk.Button(bottom, text='', command=self._convert)
        self.btn_convert.pack(fill='x', pady=(0, 6))
        self.lbl_log = ttk.Label(bottom, text='')
        self.lbl_log.pack(anchor='w')
        self.log = tk.Text(bottom, height=8, state='disabled')
        self.log.pack(fill='both', expand=True)
        self.status = ttk.Label(root, text='', relief='sunken', anchor='w')
        self.status.pack(fill='x')

    def _build_options(self, parent):
        # 핫스팟 계산식
        self.lbl_hotspot = ttk.Label(parent, text='')
        self.lbl_hotspot.pack(anchor='w', padx=8, pady=(4, 2))
        self.mode_var = tk.StringVar(value='center')
        self.rb_center = ttk.Radiobutton(
            parent, text='', value='center', variable=self.mode_var,
            command=self._redraw_canvas)
        self.rb_tip = ttk.Radiobutton(
            parent, text='', value='tip', variable=self.mode_var,
            command=self._redraw_canvas)
        self.rb_corner = ttk.Radiobutton(
            parent, text='', value='corner', variable=self.mode_var,
            command=self._redraw_canvas)
        self.rb_point = ttk.Radiobutton(
            parent, text='', value='point', variable=self.mode_var,
            command=self._redraw_canvas)
        for rb in (self.rb_center, self.rb_tip, self.rb_corner,
                   self.rb_point):
            rb.pack(anchor='w', padx=18)

        # 레이어 크기
        self.lbl_layers = ttk.Label(parent, text='')
        self.lbl_layers.pack(anchor='w', padx=8, pady=(10, 2))
        self.var_layers = tk.StringVar(value='16, 24, 32, 48, 64')
        self.ent_layers = ttk.Entry(parent, textvariable=self.var_layers,
                                    width=26)
        self.ent_layers.pack(padx=8)

        # 출력 경로
        self.lbl_out = ttk.Label(parent, text='')
        self.lbl_out.pack(anchor='w', padx=8, pady=(10, 2))
        orow = ttk.Frame(parent)
        orow.pack(fill='x', padx=8)
        self.var_out = tk.StringVar()
        self.ent_out = ttk.Entry(orow, textvariable=self.var_out)
        self.ent_out.pack(side='left', fill='x', expand=True)
        self.btn_out = ttk.Button(orow, text='', command=self._pick_out)
        self.btn_out.pack(side='left')

        # 모두 적용
        self.btn_apply_all = ttk.Button(parent, text='',
                                        command=self._apply_all)
        self.btn_apply_all.pack(padx=8, pady=(10, 2), fill='x')

        # 언어
        self.lbl_lang = ttk.Label(parent, text='')
        self.lbl_lang.pack(anchor='w', padx=8, pady=(10, 2))
        self.lang_combo = ttk.Combobox(parent, state='readonly', width=24)
        self.lang_combo.pack(padx=8, anchor='w')
        self.lang_combo.bind('<<ComboboxSelected>>', self._on_lang_change)

        # 테마
        self.lbl_theme = ttk.Label(parent, text='')
        self.lbl_theme.pack(anchor='w', padx=8, pady=(10, 2))
        self.theme_combo = ttk.Combobox(parent, state='readonly', width=24)
        self.theme_combo['values'] = THEMES
        self.theme_combo.set(THEMES[0])
        self.theme_combo.pack(padx=8, anchor='w')
        self.theme_combo.bind('<<ComboboxSelected>>', self._on_theme_change)

    # ---------------- 언어 ----------------
    def _lang_display_map(self):
        return {'auto': self.i18n.tr('lang_auto'),
                'ko': LANG_NAMES['ko'],
                'en': LANG_NAMES['en'],
                'ja': LANG_NAMES['ja']}

    def _apply_lang(self):
        tr = self.i18n.tr
        self.root.title(tr('app_title'))
        self.lbl_input.config(text=tr('input_label') + '  ')
        self.btn_folder.config(text=tr('btn_open_folder'))
        self.btn_zip.config(text=tr('btn_open_zip'))
        self.lbl_list.config(text=tr('list_label'))
        self.lbl_preview.config(text=tr('preview_label'))
        self.lbl_options.config(text=tr('hotspot_label'))
        self.lbl_hotspot.config(text=tr('hotspot_label'))
        self.rb_center.config(text=tr('mode_center'))
        self.rb_tip.config(text=tr('mode_tip'))
        self.rb_corner.config(text=tr('mode_corner'))
        self.rb_point.config(text=tr('mode_point'))
        self.lbl_layers.config(text=tr('layer_label'))
        self.lbl_out.config(text=tr('out_label'))
        self.btn_out.config(text=tr('btn_out'))
        self.btn_apply_all.config(text=tr('btn_apply_all'))
        self.lbl_lang.config(text=tr('lang_label'))
        self.lbl_theme.config(text=tr('theme_label'))
        self.btn_convert.config(text=tr('btn_convert'))
        self.lbl_log.config(text=tr('log_title'))

        # 언어 콤보 값 갱신
        dmap = self._lang_display_map()
        self.lang_combo['values'] = list(dmap.values())
        code = 'auto' if not hasattr(self, '_user_lang') else self._user_lang
        self.lang_combo.set(dmap.get(code, dmap['auto']))

        if not self.meta_list and not self.current:
            self.lbl_meta.config(text=tr('preview_empty'))
        if self.current is None:
            self._redraw_canvas()
        self._refresh_meta_label()

    def _on_lang_change(self, _=None):
        dmap = self._lang_display_map()
        sel = self.lang_combo.get()
        code = next((k for k, v in dmap.items() if v == sel), 'auto')
        self._user_lang = code
        lang = detect_lang() if code == 'auto' else code
        self.i18n.set_lang(lang)
        self._apply_lang()
        self._redraw_canvas()

    def _on_theme_change(self, _=None):
        """테마 콤보 선택 시 ttkbootstrap 테마 전환."""
        name = self.theme_combo.get()
        if not name:
            return
        try:
            style = tb.Style.get_instance()
            style.theme_use(name)
            self._apply_canvas_colors()
            self._redraw_canvas()
        except Exception:
            pass

    def _apply_canvas_colors(self):
        """테마 색을 tk 위젯(Canvas/Listbox/Text)에 반영."""
        try:
            style = tb.Style.get_instance()
            bg = style.colors.bg
            fg = style.colors.fg
            primary = style.colors.primary
        except Exception:
            bg, fg, primary = '#ffffff', '#000000', '#1a73e8'
        self.canvas.config(bg=bg)
        self.lst.config(bg=bg, fg=fg, selectbackground=primary,
                        selectforeground='#ffffff')
        self.log.config(bg=bg, fg=fg)
        self._theme_fg = fg

    # ---------------- 입력 로드 ----------------
    def _pick_folder(self):
        p = filedialog.askdirectory(title=self.i18n.tr('btn_open_folder'))
        if p:
            self._do_load(p)

    def _pick_zip(self):
        p = filedialog.askopenfilename(
            title=self.i18n.tr('btn_open_zip'),
            filetypes=[('ZIP', '*.zip'), ('All', '*.*')])
        if p:
            self._do_load(p)

    def _do_load(self, path):
        try:
            meta_list, base, is_temp = loader.scan_input(path)
            self._temp_base = base if is_temp else None
        except Exception as e:
            messagebox.showerror(self.i18n.tr('error_title'), str(e))
            return
        if not meta_list:
            messagebox.showwarning(self.i18n.tr('error_title'),
                                   self.i18n.tr('msg_no_cursor'))
            return
        self.meta_list = meta_list
        self.var_input.set(path)
        self.lst.delete(0, 'end')
        for m in meta_list:
            self.lst.insert('end', m['name'] + (' [!]' if m.get('error') else ''))
        self.current = None
        self.rect = None
        self._refresh_meta_label()
        self._redraw_canvas()
        self.status.config(text=self.i18n.tr('status_loaded',
                                             n=len(meta_list)))

    # ---------------- 목록 선택 ----------------
    def _on_select(self, _=None):
        sel = self.lst.curselection()
        if not sel:
            return
        m = self.meta_list[sel[0]]
        self.current = m
        spec = self.hotspots.get(m['name'])
        if spec and spec.get('mode') == 'point':
            self.mode_var.set('point')
            self.point = spec.get('point')
            self.rect = None
        elif spec:
            self.mode_var.set(spec.get('mode', 'center'))
            self.rect = spec.get('rect')
            self.point = None
        else:
            self.rect = None
            self.point = None
        self._refresh_meta_label()
        self._redraw_canvas()

    def _refresh_meta_label(self):
        tr = self.i18n.tr
        m = self.current
        if m is None:
            self.lbl_meta.config(text=tr('status_select'))
            return
        if m.get('error'):
            self.lbl_meta.config(
                text=tr('error_meta', name=m['name'], msg=m['error']))
        elif m['ext'] == '.cur':
            self.lbl_meta.config(
                text=tr('cur_meta', name=m['name'], size=m['preview_size'],
                        layers=m['layers']))
        elif m['ext'] == '.ani':
            self.lbl_meta.config(
                text=tr('ani_meta', name=m['name'], frames=m['frames']))
        elif m['ext'] == 'gif':
            self.lbl_meta.config(
                text=tr('ani_meta', name=m['name'],
                        frames=m['frames_count']))
        else:  # img
            self.lbl_meta.config(
                text=tr('img_meta', name=m['name'],
                        size=m['preview_size']))

    # ---------------- 미리보기 ----------------
    def _compose(self, img):
        """체커보드 배경 위에 알파 합성한 RGB 이미지 생성."""
        size = img.width
        out = Image.new('RGB', (size, size))
        px = img.load()
        op = out.load()
        for y in range(size):
            for x in range(size):
                r, g, b, a = px[x, y]
                if a == 0:
                    op[x, y] = (0xd0, 0xd0, 0xd0) if (x + y) % 2 else (0xff, 0xff, 0xff)
                elif a == 255:
                    op[x, y] = (r, g, b)
                else:
                    f = a / 255.0
                    bg = (0xd0, 0xd0, 0xd0) if (x + y) % 2 else (0xff, 0xff, 0xff)
                    op[x, y] = (round(r * f + bg[0] * (1 - f)),
                                round(g * f + bg[1] * (1 - f)),
                                round(b * f + bg[2] * (1 - f)))
        return out

    def _mode_label(self):
        key = {'center': 'mode_center', 'tip': 'mode_tip',
               'corner': 'mode_corner', 'point': 'mode_point'}[
                   self.mode_var.get()]
        return self.i18n.tr(key)

    def _redraw_canvas(self):
        cw = self.CANVAS
        self.canvas.delete('all')
        cur = self.current
        if cur is None or cur.get('error'):
            self.canvas.create_text(cw // 2, cw // 2,
                                    text=self.i18n.tr('preview_empty'),
                                    width=cw - 20, fill=self._theme_fg)
            self.lbl_status.config(text='')
            return

        img = cur['preview']
        size = cur['preview_size']
        self.scale = max(1, min(24, cw // size))
        dim = size * self.scale
        ox = (cw - dim) // 2
        oy = (cw - dim) // 2

        comp = self._compose(img).resize((dim, dim), Image.NEAREST)
        self._imgtk = ImageTk.PhotoImage(comp)
        self.canvas.create_image(ox, oy, image=self._imgtk, anchor='nw')

        for i in range(size + 1):
            self.canvas.create_line(ox + i * self.scale, oy,
                                    ox + i * self.scale, oy + dim,
                                    fill='#888888')
            self.canvas.create_line(ox, oy + i * self.scale,
                                    ox + dim, oy + i * self.scale,
                                    fill='#888888')

        if self.mode_var.get() == 'point':
            # 직접 지정(클릭) 모드: 점 + 십자선 마커
            if self.point is not None:
                px, py = self.point
                r = max(3, self.scale // 2)
                self.canvas.create_line(ox + px * self.scale - 2 * r,
                                        oy + py * self.scale,
                                        ox + px * self.scale + 2 * r,
                                        oy + py * self.scale,
                                        fill=ACCENT, width=1)
                self.canvas.create_line(ox + px * self.scale,
                                        oy + py * self.scale - 2 * r,
                                        ox + px * self.scale,
                                        oy + py * self.scale + 2 * r,
                                        fill=ACCENT, width=1)
                self.canvas.create_oval(ox + px * self.scale - r,
                                        oy + py * self.scale - r,
                                        ox + px * self.scale + r,
                                        oy + py * self.scale + r,
                                        fill=ACCENT, outline='#000000')
                self.lbl_status.config(
                    text=self.i18n.tr('status_hotspot', x=px, y=py) +
                    '  ·  ' + self._mode_label())
            else:
                self.lbl_status.config(text=self.i18n.tr('point_hint'))
        elif self.rect:
            x1, y1, x2, y2 = self.rect
            self.canvas.create_rectangle(ox + x1 * self.scale,
                                         oy + y1 * self.scale,
                                         ox + x2 * self.scale,
                                         oy + y2 * self.scale,
                                         outline=ACCENT, width=2)
            # 8개 조절 핸들 (4코너 + 4엣지)
            hs = max(3, self.scale // 3)
            for hx, hy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2),
                           ((x1 + x2) // 2, y1), ((x1 + x2) // 2, y2),
                           (x1, (y1 + y2) // 2), (x2, (y1 + y2) // 2)]:
                self.canvas.create_rectangle(
                    ox + hx * self.scale - hs // 2,
                    oy + hy * self.scale - hs // 2,
                    ox + hx * self.scale + hs // 2,
                    oy + hy * self.scale + hs // 2,
                    fill='white', outline=ACCENT, width=1)
            hx, hy = compute_hotspot(img, self.rect, self.mode_var.get())
            r = max(3, self.scale // 2)
            self.canvas.create_oval(ox + hx * self.scale - r,
                                    oy + hy * self.scale - r,
                                    ox + hx * self.scale + r,
                                    oy + hy * self.scale + r,
                                    fill=ACCENT, outline='#000000')
            self.lbl_status.config(
                text=self.i18n.tr('status_hotspot', x=hx, y=hy) +
                '  ·  ' + self._mode_label() +
                '  ·  ' + self.i18n.tr('resize_hint'))
        else:
            self.lbl_status.config(
                text=self.i18n.tr('hotspot_label') + ': ' +
                     self._mode_label())

    def _canvas_to_img(self, cx, cy):
        size = self.current['preview_size']
        dim = size * self.scale
        ox = (self.CANVAS - dim) // 2
        oy = (self.CANVAS - dim) // 2
        x = (cx - ox) // self.scale
        y = (cy - oy) // self.scale
        return max(0, min(size - 1, x)), max(0, min(size - 1, y))

    # 핸들 방향 -> 마우스 커서 (창 크기 조절 커서와 동일 계열)
    _CURSOR_MAP = {
        'nw': 'size_nw_se', 'se': 'size_nw_se',
        'ne': 'size_ne_sw', 'sw': 'size_ne_sw',
        'n': 'size_ns', 's': 'size_ns',
        'e': 'size_we', 'w': 'size_we',
    }
    _HANDLES = [  # (x비율 기준) 4코너 + 4엣지 중앙
        'nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w',
    ]

    def _hit_test(self, ix, iy):
        """이미지 좌표가 핸들/테두리 위인지 판별 -> 방향 코드 or None."""
        if not self.rect:
            return None
        x1, y1, x2, y2 = self.rect
        tol = max(1, round(8 / self.scale))  # 캔버스 8px 를 이미지 좌표로 환산
        if abs(ix - x1) <= tol and abs(iy - y1) <= tol:
            return 'nw'
        if abs(ix - x2) <= tol and abs(iy - y1) <= tol:
            return 'ne'
        if abs(ix - x1) <= tol and abs(iy - y2) <= tol:
            return 'sw'
        if abs(ix - x2) <= tol and abs(iy - y2) <= tol:
            return 'se'
        if abs(iy - y1) <= tol and x1 <= ix <= x2:
            return 'n'
        if abs(iy - y2) <= tol and x1 <= ix <= x2:
            return 's'
        if abs(ix - x1) <= tol and y1 <= iy <= y2:
            return 'w'
        if abs(ix - x2) <= tol and y1 <= iy <= y2:
            return 'e'
        return None

    def _on_motion(self, evt):
        """핸들 위에선 크기 조절 커서로 변경."""
        if self.current is None or self.current.get('error'):
            return
        if self.drag_start is not None:
            return  # 드래그 중에는 그대로
        ix, iy = self._canvas_to_img(evt.x, evt.y)
        mode = self._hit_test(ix, iy)
        self.canvas.config(cursor=self._CURSOR_MAP.get(mode, ''))

    def _resize_rect(self, mode, ix, iy):
        """핸들 방향에 따라 rect 크기 조절 (최소 1x1 유지)."""
        x1, y1, x2, y2 = self.rect
        if 'n' in mode:
            y1 = min(iy, y2 - 1)
        if 's' in mode:
            y2 = max(iy, y1 + 1)
        if 'w' in mode:
            x1 = min(ix, x2 - 1)
        if 'e' in mode:
            x2 = max(ix, x1 + 1)
        self.rect = (x1, y1, x2, y2)

    def _save_hotspot(self):
        """현재 커서의 핫스팟을 현재 모드에 따라 저장."""
        if not self.current or self.current.get('error'):
            return
        name = self.current['name']
        mode = self.mode_var.get()
        if mode == 'point':
            if self.point is not None:
                self.hotspots[name] = {'mode': 'point', 'point': self.point}
        else:
            if self.rect is not None:
                self.hotspots[name] = {'mode': mode, 'rect': self.rect}

    def _on_drag_start(self, evt):
        if self.current is None or self.current.get('error'):
            return
        ix, iy = self._canvas_to_img(evt.x, evt.y)
        if self.mode_var.get() == 'point':
            # 직접 지정: 클릭 위치가 곧 핫스팟
            self.point = (ix, iy)
            self.point_active = True
            self._save_hotspot()
            self._redraw_canvas()
            return
        mode = self._hit_test(ix, iy)
        if mode:
            # 기존 영역 핸들 조절 시작
            self.resize_mode = mode
            self.drag_start = (ix, iy)
            return
        # 새 영역 그리기 시작
        self.resize_mode = None
        self.drag_start = (ix, iy)
        self.rect = (ix, iy, ix + 1, iy + 1)

    def _on_drag_move(self, evt):
        if self.point_active:
            # 직접 지정: 눌린 채 움직이면 점이 따라다님
            ix, iy = self._canvas_to_img(evt.x, evt.y)
            self.point = (ix, iy)
            self._save_hotspot()
            self._redraw_canvas()
            return
        if self.drag_start is None:
            return
        ix, iy = self._canvas_to_img(evt.x, evt.y)
        if self.resize_mode:
            self._resize_rect(self.resize_mode, ix, iy)
        else:
            x1, y1 = self.drag_start
            self.rect = (min(x1, ix), min(y1, iy),
                         max(x1, ix) + 1, max(y1, iy) + 1)
        self._redraw_canvas()

    def _on_drag_end(self, _=None):
        if self.point_active:
            self.point_active = False
            return
        if self.drag_start is None:
            return
        self.drag_start = None
        self.resize_mode = None
        self._save_hotspot()
        self._redraw_canvas()

    # ---------------- 핫스팟 관리 ----------------
    def _apply_all(self):
        tr = self.i18n.tr
        if self.current is None:
            messagebox.showwarning(tr('error_title'),
                                   tr('status_select'))
            return
        mode = self.mode_var.get()
        if mode == 'point':
            if self.point is None:
                messagebox.showwarning(tr('error_title'),
                                       tr('status_select'))
                return
            spec = {'mode': 'point', 'point': self.point}
        else:
            if self.rect is None:
                messagebox.showwarning(tr('error_title'),
                                       tr('status_select'))
                return
            spec = {'mode': mode, 'rect': self.rect}
        n = 0
        for m in self.meta_list:
            if m['ext'] == '.cur' and not m.get('error'):
                self.hotspots[m['name']] = dict(spec)
                n += 1
        self.status.config(text=tr('msg_apply_all', n=n))

    # ---------------- 출력 ----------------
    def _pick_out(self):
        p = filedialog.askdirectory(title=self.i18n.tr('btn_out'))
        if p:
            self.var_out.set(p)

    def _convert(self):
        tr = self.i18n.tr
        if not self.meta_list:
            messagebox.showwarning(tr('error_title'), tr('msg_no_cursor'))
            return
        out_dir = self.var_out.get().strip()
        if not out_dir:
            messagebox.showwarning(tr('error_title'), tr('out_label'))
            return
        try:
            layer_sizes = [int(x.strip()) for x in
                           self.var_layers.get().split(',') if x.strip()]
            if not layer_sizes or any(s < 1 for s in layer_sizes):
                raise ValueError
        except ValueError:
            messagebox.showwarning(tr('error_title'), tr('layer_label'))
            return

        hotspot_map = {}
        missing = 0
        for m in self.meta_list:
            if m['ext'] in ('.cur', 'img', 'gif') and not m.get('error'):
                if m['name'] in self.hotspots:
                    hotspot_map[m['name']] = self.hotspots[m['name']]
                else:
                    missing += 1

        self._clear_log()
        results = output.build_cursor_set(
            self.meta_list, hotspot_map, layer_sizes, out_dir,
            progress=self._log_progress)

        nconv = sum(1 for r in results if r[0] == 'convert')
        ncopy = sum(1 for r in results if r[0] == 'copy')
        nskip = sum(1 for r in results if r[0] == 'skip')
        self._log('')
        if missing:
            self._log(tr('status_need_hotspot') +
                      ' (missing: %d)' % missing)
        self.status.config(text=tr('status_converted',
                                   n=nconv + ncopy, path=out_dir))

    # ---------------- 로그 ----------------
    def _clear_log(self):
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.config(state='disabled')

    def _log(self, text):
        self.log.config(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.config(state='disabled')

    def _log_progress(self, name, status):
        tr = self.i18n.tr
        if status == 'converted':
            self._log(tr('log_converted', name=name))
        elif status == 'copied':
            self._log(tr('log_copied', name=name))
        elif status == 'skipped':
            self._log(tr('log_skipped', name=name))
        elif status == 'error':
            self._log(tr('log_error', name=name, msg=''))
