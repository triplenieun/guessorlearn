### 64*64로 변환 후 저장, 3000장
import numpy as np

# Bresenham's line algorithm을 이용하여 두 좌표를 연결하는 함수
def draw_line(x0, y0, x1, y1, matrix):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < 64 and 0 <= y0 < 64:  # 좌표가 행렬 범위 내에 있을 때만 적용
            matrix[y0, x0] = 1  # 좌표를 1로 설정
        if x0 == x1 and y0 == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

def transformer_vec_img(drawing):
    for i in range(len(drawing)):
        for j in range(len(drawing[i])):
            for k in range(len(drawing[i][j])):
                drawing[i][j][k] = int(drawing[i][j][k]/4)
    # print(drawing)
    # 64X64 빈 행렬 생성
    matrix = np.zeros((1, 1, 64, 64), dtype=np.uint8)

    # 좌표를 행렬에 매핑 (선이 겹치는 경우 제외)
    for stroke in drawing:
        x_coords = stroke[0]
        y_coords = stroke[1]

        # 각 좌표 간에 선을 그림
        for i in range(len(x_coords) - 1):
            x0, y0 = x_coords[i], y_coords[i]
            x1, y1 = x_coords[i + 1], y_coords[i + 1]
            draw_line(x0, y0, x1, y1, matrix[0][0])

    return matrix