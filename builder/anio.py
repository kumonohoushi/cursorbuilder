# ============================================================
# builder/anio.py
# .ani (RIFF/ACON) 파싱 — 프레임 이미지/크기/대표 프레임 추출
#
# v1: 파싱은 프레임별 CUR 데이터를 읽어 표시용 대표 이미지를 얻는 데
#     사용한다. .ani 의 완전한 변환(프레임별 리사이즈+핫스팟)은 후속 단계.
# ============================================================
import struct

from . import curio
from .hotspot import scale_hotspot


def parse_ani(data):
    """ANI 바이트 -> 프레임 이미지 목록 [{size, image(RGBA)}]

    RIFF/ACON 구조에서 LIST 'fram' 내부의 'icon' 청크(CUR 데이터)를
    curio.parse_cur 로 해석해 각 프레임의 대표 이미지를 추출한다.
    """
    if data[:4] != b'RIFF':
        raise ValueError('RIFF 형식 아님')
    frames = []

    def walk(start, end):
        i = start
        while i + 8 <= end:
            tag = data[i:i + 4]
            sz = struct.unpack('<I', data[i + 4:i + 8])[0]
            body_start = i + 8
            body_end = body_start + sz
            if body_end > end:
                break
            if tag == b'LIST':
                typ = data[body_start:body_start + 4]
                if typ == b'fram':
                    j = body_start + 4
                    while j + 8 <= body_end:
                        t2 = data[j:j + 4]
                        s2 = struct.unpack('<I', data[j + 4:j + 8])[0]
                        if t2 == b'icon':
                            try:
                                layers = curio.parse_cur(
                                    data[j + 8:j + 8 + s2])
                                rep = max(layers, key=lambda l: l['size'])
                                frames.append({
                                    'size': rep['size'],
                                    'image': rep['image'],
                                })
                            except Exception:
                                pass
                        j = j + 8 + s2 + (s2 & 1)
            i = i + 8 + sz + (sz & 1)

    walk(12, len(data))
    if not frames:
        raise ValueError('프레임을 찾지 못함')
    return frames


def read_ani(path):
    with open(path, 'rb') as f:
        data = f.read()
    return parse_ani(data)


def build_ani(frames, hotspot, layer_sizes, rates=None):
    """프레임(RGBA)들을 다중 레이어 .ani 로 빌드 (RIFF/ACON).

    frames      : [{size, image}] 각 프레임의 대표(원본) 이미지
    hotspot     : (hx,hy) — 원본 크기 기준 좌표. 모든 프레임에 동일 적용
    layer_sizes : [16,24,...] 각 프레임 내부 레이어 크기
    rates       : [1/60초] 프레임별 지속시간 (없으면 기본 10)

    구조: RIFF 'ACON'
            LIST 'anih'  애니메이션 정보
            LIST 'fram'  프레임별 'icon' (CUR 데이터)
            LIST 'rate'  프레임 지속시간
            LIST 'seq '  프레임 순서
    """
    n = len(frames)
    if rates is None:
        rates = [10] * n
    src = frames[0]['size']
    maxs = layer_sizes[-1]

    # 프레임별 다중 레이어 CUR 데이터
    cur_list = []
    for fr in frames:
        hs = [scale_hotspot(hotspot, src, s) for s in layer_sizes]
        cur_list.append(curio.build_cur(layer_sizes, hs, fr['image']))

    # anih
    anih_body = struct.pack('<IIIIIIHHII', 36, n, 1, maxs, maxs, 0,
                            1, 32, 0, 0)
    anih_chunk = b'anih' + struct.pack('<I', 36) + anih_body
    anih_list = (b'LIST' + struct.pack('<I', 4 + len(anih_chunk))
                 + b'anih' + anih_chunk)
    # fram
    fram_body = b'fram'
    for c in cur_list:
        fram_body += b'icon' + struct.pack('<I', len(c)) + c
    fram_list = (b'LIST' + struct.pack('<I', len(fram_body)) + fram_body)
    # rate
    rate_body = b'rate'
    for r in rates:
        rate_body += struct.pack('<I', r)
    rate_list = (b'LIST' + struct.pack('<I', len(rate_body)) + rate_body)
    # seq
    seq_body = b'seq '
    for i in range(n):
        seq_body += struct.pack('<I', i)
    seq_list = (b'LIST' + struct.pack('<I', len(seq_body)) + seq_body)

    riff_body = (b'ACON' + anih_list + fram_list + rate_list + seq_list)
    riff = b'RIFF' + struct.pack('<I', len(riff_body)) + riff_body
    return riff
