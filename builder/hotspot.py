# ============================================================
# builder/hotspot.py
# 드래그 영역 -> 핫스팟 계산, 레이어 크기 비례 스케일링
# ============================================================


def compute_hotspot(img, rect, mode):
    """이미지의 드래그 영역에서 핫스팟(점)을 계산한다.

    rect: (x1, y1, x2, y2) — 드래그로 잡은 영역 (포인터가 놓인 곳)
    mode:
      'tip'    : 영역 내 좌상단에서 첫 불투명 픽셀 (화살표/포인터 팁)
      'center' : 영역 내 불투명 픽셀의 무게중심 (양방향/4방향/I빔형)
      'corner' : 영역 좌상단 모서리 그대로

    불투명 픽셀이 없으면 영역 중심을 반환한다.
    """
    x1, y1, x2, y2 = rect
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.width, x2), min(img.height, y2)

    if mode == 'corner':
        return (x1, y1)

    pts = []
    for y in range(y1, y2):
        for x in range(x1, x2):
            if img.getpixel((x, y))[3] > 0:
                pts.append((x, y))

    if not pts:
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    if mode == 'tip':
        return min(pts, key=lambda p: (p[1], p[0]))  # y 우선, 그 다음 x

    # 'center' : 무게중심
    cx = sum(p[0] for p in pts) // len(pts)
    cy = sum(p[1] for p in pts) // len(pts)
    return (cx, cy)


def scale_rect(rect, src_size, dst_size):
    """드래그 영역(rect)을 원본 크기 기준에서 대상 크기로 비례 스케일."""
    x1, y1, x2, y2 = rect
    f = dst_size / src_size
    return (round(x1 * f), round(y1 * f),
            round(x2 * f), round(y2 * f))


def scale_hotspot(hotspot, src_size, dst_size):
    """핫스팟을 원본 크기 기준에서 대상 레이어 크기로 비례 스케일링."""
    hx, hy = hotspot
    return (round(hx * dst_size / src_size),
            round(hy * dst_size / src_size))


def suggested_sizes(src_size):
    """원본 크기 기준 레이어 크기 자동 제안.

    원본보다 작은 배수 2개 + 원본 + 큰 배수 2개, 각각 정수/홀수 처리.
    """
    def norm(n):
        return max(1, int(round(n)))
    half = norm(src_size / 2)
    two_thirds = norm(src_size * 2 / 3)
    three_halves = norm(src_size * 3 / 2)
    double = norm(src_size * 2)
    sizes = sorted(set([half, two_thirds, src_size, three_halves, double]))
    # 중복 제거 후 원본이 포함된 3~5개
    if len(sizes) > 5:
        sizes = sizes[:5]
    return sizes
