# ============================================================
# builder/loader.py
# 입력(zip/폴더) 스캔 — .cur/.ani + 정적 이미지/.gif 감지,
# 대표 이미지/메타 추출, 정사각화(빈 배경 채우기)
# ============================================================
import glob
import os
import tempfile
import zipfile

from PIL import Image, ImageSequence

from . import anio, curio

# 정적 이미지 확장자 (→ .cur 로 변환)
IMG_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.ico', '.webp', '.tiff',
            '.tif')


def _collect_files(base):
    """base 아래에서 지원 확장자 파일 재귀 수집 (대소문자 무시)."""
    pats = ('.cur', '.ani', '.gif') + IMG_EXTS
    found = []
    for p in pats:
        found.extend(glob.glob(os.path.join(base, '**', '*' + p),
                               recursive=True))
        found.extend(glob.glob(os.path.join(base, '**', '*' + p.upper()),
                               recursive=True))
    return sorted(set(found))


def to_square(img):
    """비정사각 이미지를 빈(투명) 배경 채우기로 정사각화.

    비율 왜곡 없이 긴 변을 기준으로 정사각 캔버스를 만들고,
    이미지를 중앙에 배치하며 나머지는 투명으로 채운다.
    """
    w, h = img.size
    if w == h:
        return img
    n = max(w, h)
    canvas = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    canvas.paste(img, ((n - w) // 2, (n - h) // 2))
    return canvas


def _gif_rates(img):
    """GIF 프레임별 지속시간(1/60초 단위) 목록 추출."""
    rates = []
    for i, fr in enumerate(ImageSequence.Iterator(img)):
        ms = fr.info.get('duration', 100)
        rates.append(max(1, round(ms * 60 / 1000)))
    return rates


def read_gif(path):
    """GIF 파일 -> (frames, rates).

    frames: [{size, image(RGBA 정사각)}] — 첫 프레임 정사각 크기로 통일.
    rates : [1/60초 단위] 프레임별 지속시간.
    """
    img = Image.open(path)
    raw = [f.convert('RGBA') for f in ImageSequence.Iterator(img)]
    rates = _gif_rates(img)
    if not raw:
        raise ValueError('GIF 프레임 없음')
    n = to_square(raw[0]).width  # 기준 정사각 크기
    frames = []
    for fr in raw:
        w, h = fr.size
        canvas = Image.new('RGBA', (n, n), (0, 0, 0, 0))
        canvas.paste(fr, ((n - w) // 2, (n - h) // 2))
        frames.append({'size': n, 'image': canvas})
    return frames, rates


def scan_input(path):
    """zip 또는 폴더 스캔.

    반환: (meta_list, base_dir, is_temp)
      meta_list : [{path,name,ext,size,preview,preview_size,...}]
        ext: '.cur' | '.ani' | 'gif' | 'img'
    """
    is_temp = False
    base = path
    if os.path.isfile(path) and path.lower().endswith('.zip'):
        tmp = tempfile.mkdtemp(prefix='curbuilder_')
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        base = tmp
        is_temp = True

    meta_list = []
    for f in _collect_files(base):
        ext = os.path.splitext(f)[1].lower()
        meta = {
            'path': f,
            'name': os.path.basename(f),
            'ext': ext,
            'size': os.path.getsize(f),
        }
        try:
            if ext == '.cur':
                layers = curio.read_cur(f)
                rep = curio.pick_preview(layers)
                meta['layers'] = len(layers)
                meta['sizes'] = [l['size'] for l in layers]
                meta['preview'] = rep['image']
                meta['preview_size'] = rep['size']
            elif ext == '.ani':
                frames = anio.read_ani(f)
                rep = max(frames, key=lambda fr: fr['size'])
                meta['frames'] = len(frames)
                meta['sizes'] = [fr['size'] for fr in frames]
                meta['preview'] = rep['image']
                meta['preview_size'] = rep['size']
            elif ext == '.gif':
                frames, rates = read_gif(f)
                meta['ext'] = 'gif'
                meta['frames_count'] = len(frames)
                meta['frames'] = frames
                meta['rates'] = rates
                meta['sizes'] = [fr['size'] for fr in frames]
                meta['preview'] = frames[0]['image']
                meta['preview_size'] = frames[0]['size']
            else:
                # 정적 이미지
                im = Image.open(f).convert('RGBA')
                im = to_square(im)
                meta['ext'] = 'img'
                meta['preview'] = im
                meta['preview_size'] = im.width
            meta['error'] = None
        except Exception as e:
            meta['error'] = str(e)
        meta_list.append(meta)

    return meta_list, base, is_temp
