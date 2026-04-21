"""
LED Matrix Simulator — 27x18 via pygame
Reads the same serial protocol as the Arduino:
  x, y, color  (3 bytes per cell)
  255,255,255  (frame delimiter)
"""

import sys
import serial
import pygame
import threading

# ── Config ───────────────────────────────────────────────────────────────────
PORT   = "/dev/cu.usbmodem1101"
BAUD   = 115200

SCREEN_W = 27
SCREEN_H = 18
CELL     = 28    # pixels per LED cell
GAP      = 3     # gap between cells
PAD      = 16    # window padding

WIN_W = PAD*2 + SCREEN_W * (CELL + GAP) - GAP
WIN_H = PAD*2 + SCREEN_H * (CELL + GAP) - GAP

# LED color palette — matches Arduino tetrominoColors[]
PALETTE = {
    0: (10,  10,  10),   # empty  (dim background)
    1: (0,   240, 240),  # I  cyan
    2: (240, 240, 0),    # O  yellow
    3: (160, 0,   240),  # T  purple
    4: (0,   240, 0),    # S  green
    5: (240, 0,   0),    # Z  red
    6: (0,   0,   240),  # J  blue
    7: (240, 120, 0),    # L  orange
}
BG_COLOR  = (18, 18, 18)
LED_OFF   = (10, 10, 10)

# ── Shared state ─────────────────────────────────────────────────────────────
matrix      = [[0]*SCREEN_W for _ in range(SCREEN_H)]
pending     = [[0]*SCREEN_W for _ in range(SCREEN_H)]
frame_ready = threading.Event()
lock        = threading.Lock()

# ── Serial reader thread ──────────────────────────────────────────────────────
def serial_reader(ser):
    buf = bytearray()
    while True:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        buf += chunk

        while len(buf) >= 3:
            x, y, color = buf[0], buf[1], buf[2]
            buf = buf[3:]

            if x == 255 and y == 255 and color == 255:
                # frame complete — swap pending → matrix
                with lock:
                    for row in range(SCREEN_H):
                        matrix[row][:] = pending[row]
                frame_ready.set()
            else:
                if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
                    pending[y][x] = color

# ── Draw ─────────────────────────────────────────────────────────────────────
def cell_rect(x, y):
    px = PAD + x * (CELL + GAP)
    py = PAD + y * (CELL + GAP)
    return pygame.Rect(px, py, CELL, CELL)

def draw(surface):
    surface.fill(BG_COLOR)
    with lock:
        snap = [row[:] for row in matrix]

    for y in range(SCREEN_H):
        for x in range(SCREEN_W):
            color_idx = snap[y][x]
            rgb = PALETTE.get(color_idx, LED_OFF)
            rect = cell_rect(x, y)

            # glow effect for lit LEDs
            if color_idx != 0:
                glow = pygame.Surface((CELL+8, CELL+8), pygame.SRCALPHA)
                glow_color = (*rgb, 40)
                pygame.draw.ellipse(glow, glow_color, glow.get_rect())
                surface.blit(glow, (rect.x-4, rect.y-4))

            pygame.draw.ellipse(surface, rgb, rect)

            # specular highlight
            if color_idx != 0:
                highlight = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                pygame.draw.ellipse(
                    highlight,
                    (255, 255, 255, 60),
                    pygame.Rect(CELL//4, CELL//6, CELL//2, CELL//3)
                )
                surface.blit(highlight, rect.topleft)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    port = sys.argv[1] if len(sys.argv) > 1 else PORT

    print(f"Opening {port} @ {BAUD}...")
    ser = serial.Serial(port, BAUD, timeout=1)
    print("Connected.")

    t = threading.Thread(target=serial_reader, args=(ser,), daemon=True)
    t.start()

    pygame.init()
    surface = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("LED Matrix Simulator")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        draw(surface)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    ser.close()

if __name__ == "__main__":
    main()