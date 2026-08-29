# ============================================================
# builder/curio.py
# .cur 파일 파싱/빌드 일반화 모듈
#
# 기존 convert_cursors.py 의 load_cur_single / build_cur 를 일반화하여,
# 임의의 레이어 구조를 읽고, 임의의 레이어 크기 목록으로 다시 빌드한다.
# ============================================================
import struct
from PIL import Image


def parse_cur(data):
    """CUR 바이트 -> 레이어 목록 [{size, hotspot, image(RGBA)}]

    단일/다중 레이어 모두 처리. 각 레이어는 32bpp DIB 로 가정하고
    bottom-up 저장을 보정하여 상하 반전 이미지로 반환한다.
    """
    rsv, typ, cnt = struct.unpack_from('<HHH', data, 0)
    if typ != 2:
        raise ValueError('CUR type 아님 (type=%d)' % typ)
    layers = []
    for i in range(cnt):
        off = 6 + i * 16
        wb, hb, cc, rs = struct.unpack_from('<BBBB', data, off)
        hx, hy = struct.unpack_from('<HH', data, off + 4)
        nb, io = struct.unpack_from('<II', data, off + 8)
        bis, = struct.unpack_from('<I', data, io)
        w, bh = struct.unpack_from('<ii', data, io + 4)
        bpp = struct.unpack_from('<H', data, io + 14)[0]
        stride = ((w * bpp + 31) // 32) * 4
        px_start = io + bis
        ah = abs(bh) // 2
        img = Image.new('RGBA', (w, ah))
        p = img.load()
        for y in range(ah):
            row = px_start + y * stride
            for x in range(w):
                b, g, r, a = data[row + x * 4: row + x * 4 + 4]
                p[x, y] = (r, g, b, a)
        if bh > 0:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        layers.append({'size': w, 'hotspot': (hx, hy), 'image': img})
    return layers


def read_cur(path):
    """파일에서 .cur 읽기 -> parse_cur 결과"""
    with open(path, 'rb') as f:
        data = f.read()
    return parse_cur(data)


def pick_preview(layers):
    """레이어 목록 중 대표 이미지(최대 크기 레이어) 선택"""
    return max(layers, key=lambda l: l['size'])


def build_cur(sizes, hotspots, img):
    """이미지(RGBA)를 다중 레이어 32bpp .cur 로 빌드 (bottom-up 저장)

    sizes:    [16,24,...] 레이어 크기 목록 (정사각형)
    hotspots: [(hx,hy), ...] 각 레이어 핫스팟 (sizes 와 1:1 대응)
    """
    entries = []
    images = []
    offset = 6 + 16 * len(sizes)
    for idx, s in enumerate(sizes):
        im = img.resize((s, s), Image.LANCZOS)
        rgba = im.tobytes()
        w = h = s
        bpp = 32
        stride = ((w * bpp + 31) // 32) * 4
        rows = [rgba[y * stride: (y + 1) * stride] for y in range(h)]
        rows.reverse()  # bottom-up
        bottom_data = b''.join(rows)
        and_stride = ((w + 31) // 32) * 4
        and_mask = b'\x00' * (and_stride * h)
        header = struct.pack('<IiiHHIIiiII', 40, s, s * 2, 1, bpp, 0,
                             w * h * 4, 0, 0, 0, 0)
        imgdata = header + bottom_data + and_mask
        hx, hy = hotspots[idx]
        entries.append((s, s, 0, 0, hx, hy, len(imgdata), offset))
        images.append(imgdata)
        offset += len(imgdata)
    buf = struct.pack('<HHH', 0, 2, len(sizes))
    for wb, hb, cc, rs, hx, hy, nb, io in entries:
        buf += struct.pack('<BBBBHHII', wb, hb, cc, rs, hx, hy, nb, io)
    for im in images:
        buf += im
    return buf
