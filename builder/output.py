# ============================================================
# builder/output.py
# 커서 세트 최종 출력 생성
#  - .cur : 다중 레이어 빌드 (핫스팟 비례 스케일링 포함)
#  - .ani : 원본 그대로 복사 (v1)
# ============================================================
import os
import shutil

from PIL import Image

from . import anio, curio
from .hotspot import compute_hotspot, scale_hotspot, scale_rect


def build_cursor_set(cursor_list, hotspot_map, layer_sizes, out_dir,
                     progress=None):
    """커서 파일들을 변환하여 out_dir 에 생성.

    cursor_list : loader.scan_input 결과
    hotspot_map : {파일명: {'rect':(x1,y1,x2,y2), 'mode':str}}
                  rect 는 대표 이미지(원본 크기) 기준 좌표.
                  각 레이어 크기로 rect 를 스케일한 뒤 그 레이어 이미지에서
                  mode(tip/center/corner)에 따라 핫스팟을 재계산한다.
    layer_sizes : [16,24,...] 출력 레이어 크기
    progress    : 콜백(name, status) 선택적

    반환: [(status, name, [메모])] — status: convert/copy/skip/error
    """
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for meta in cursor_list:
        name = meta['name']
        try:
            if meta.get('error'):
                results.append(('error', name, meta['error']))
                if progress:
                    progress(name, 'error')
                continue

            if meta['ext'] == '.ani':
                shutil.copy2(meta['path'], os.path.join(out_dir, name))
                results.append(('copy', name, ''))
                if progress:
                    progress(name, 'copied')
                continue

            # 변환 대상(.cur/.img/.gif)은 핫스팟 필요
            if name not in hotspot_map:
                results.append(('skip', name, '핫스팟 미지정'))
                if progress:
                    progress(name, 'skipped')
                continue

            if meta['ext'] == 'gif':
                # GIF -> .ani: 대표 프레임에서 핫스팟 계산, 전체 프레임 동일 적용
                spec = hotspot_map[name]
                mode = spec.get('mode', 'center')
                src = meta['preview_size']
                if mode == 'point':
                    hs = spec['point']
                else:
                    hs = compute_hotspot(meta['preview'], spec['rect'], mode)
                data = anio.build_ani(meta['frames'], hs, layer_sizes,
                                      rates=meta.get('rates'))
                out_name = os.path.splitext(name)[0] + '.ani'
            else:
                # .cur / 정적 이미지 -> .cur
                hx_spec = hotspot_map[name]
                src_size = meta['preview_size']
                base_img = meta['preview']
                mode = hx_spec.get('mode', 'center')
                if mode == 'point':
                    px, py = hx_spec.get('point', (0, 0))
                    hotspots = [scale_hotspot((px, py), src_size, s)
                                for s in layer_sizes]
                else:
                    rect = hx_spec['rect']
                    hotspots = []
                    for s in layer_sizes:
                        layer_img = base_img.resize((s, s), Image.LANCZOS)
                        r = scale_rect(rect, src_size, s)
                        hotspots.append(compute_hotspot(layer_img, r, mode))
                data = curio.build_cur(layer_sizes, hotspots, base_img)
                out_name = (os.path.splitext(name)[0] + '.cur'
                            if meta['ext'] == 'img' else name)

            with open(os.path.join(out_dir, out_name), 'wb') as f:
                f.write(data)
            results.append(('convert', out_name, ''))
            if progress:
                progress(out_name, 'converted')

        except Exception as e:
            results.append(('error', name, str(e)))
            if progress:
                progress(name, 'error')

    return results
