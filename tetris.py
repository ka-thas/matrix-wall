"""
Tetris for 27x18 LED matrix via Arduino serial.
Game board: 10x20 (cols 0-9, rows 0-19 from top)

layout:
  SCREEN: 18 wide x 27 tall
  BOARD:  10 wide x 22 tall displayed (x=1..10, y=0..21)
  TODO: hold
  TODO: next queue (3 pieces)
"""

import serial
import time
import random
import sys
from pynput import keyboard

# ── Config ──────────────────────────────────────────────────────────────────
PORT = "/dev/cu.usbmodem1101"   # adjust to your port
BAUD = 115200
FPS  = 60
TICK_NORMAL   = 0.5   # seconds per gravity drop
TICK_SOFT_DROP = 0.05

SCREEN_W = 18
SCREEN_H = 27

BOARD_W = 10
BOARD_H = 22          # internal height (top 2 rows are hidden spawn buffer)
BOARD_VISIBLE = 20    # rows shown on screen
BOARD_HIDDEN  = BOARD_H - BOARD_VISIBLE  # 2

# Board top-left on screen (x offset, y offset)
BOARD_X = 1
BOARD_Y = 0   # screen y=0 maps to board row BOARD_HIDDEN

# Preview panel x start
PANEL_X = 13

# ── Colors (index → tetrominoColors on Arduino) ──────────────────────────
COLOR_EMPTY  = 0
COLOR_I      = 1
COLOR_O      = 2
COLOR_T      = 3
COLOR_S      = 4
COLOR_Z      = 5
COLOR_J      = 6
COLOR_L      = 7
COLOR_BORDER = 3   # reuse purple for UI borders / labels

# ── Tetrominoes ──────────────────────────────────────────────────────────────
# Each piece: list of 4 rotations, each rotation: list of (row, col) offsets
PIECES = {
    "I": {
        "color": COLOR_I,
        "rotations": [
            [(0,0),(0,1),(0,2),(0,3)],
            [(0,0),(1,0),(2,0),(3,0)],
            [(0,0),(0,1),(0,2),(0,3)],
            [(0,0),(1,0),(2,0),(3,0)],
        ]
    },
    "O": {
        "color": COLOR_O,
        "rotations": [
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
        ]
    },
    "T": {
        "color": COLOR_T,
        "rotations": [
            [(0,1),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(1,1),(2,0)],
            [(1,0),(1,1),(1,2),(2,1)],
            [(0,1),(1,0),(1,1),(2,1)],
        ]
    },
    "S": {
        "color": COLOR_S,
        "rotations": [
            [(0,1),(0,2),(1,0),(1,1)],
            [(0,0),(1,0),(1,1),(2,1)],
            [(0,1),(0,2),(1,0),(1,1)],
            [(0,0),(1,0),(1,1),(2,1)],
        ]
    },
    "Z": {
        "color": COLOR_Z,
        "rotations": [
            [(0,0),(0,1),(1,1),(1,2)],
            [(0,1),(1,0),(1,1),(2,0)],
            [(0,0),(0,1),(1,1),(1,2)],
            [(0,1),(1,0),(1,1),(2,0)],
        ]
    },
    "J": {
        "color": COLOR_J,
        "rotations": [
            [(0,0),(1,0),(1,1),(1,2)],
            [(0,0),(0,1),(1,0),(2,0)],
            [(1,0),(1,1),(1,2),(2,2)],
            [(0,1),(1,1),(2,0),(2,1)],
        ]
    },
    "L": {
        "color": COLOR_L,
        "rotations": [
            [(0,2),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(2,0),(2,1)],
            [(1,0),(1,1),(1,2),(2,0)],
            [(0,0),(0,1),(1,1),(2,1)],
        ]
    },
}

PIECE_NAMES = list(PIECES.keys())

def random_bag():
    bag = PIECE_NAMES[:]
    random.shuffle(bag)
    return bag

# ── Game State ───────────────────────────────────────────────────────────────
class Tetris:
    def __init__(self):
        self.board = [[COLOR_EMPTY]*BOARD_W for _ in range(BOARD_H)]
        self.bag = random_bag()
        self.next_queue = [self._draw() for _ in range(3)]
        self.hold = None
        self.hold_used = False
        self.score = 0
        self.game_over = False
        self.soft_drop = False
        self._spawn()

        # input flags (set by keyboard thread)
        self.inp_left  = False
        self.inp_right = False
        self.inp_rot_cw  = False
        self.inp_rot_ccw = False
        self.inp_hard_drop = False
        self.inp_hold = False

    def _draw(self):
        if not self.bag:
            self.bag = random_bag()
        return self.bag.pop()

    def _spawn(self):
        name = self.next_queue.pop(0)
        self.next_queue.append(self._draw())
        self.cur_name = name
        self.cur_rot  = 0
        self.cur_row  = BOARD_HIDDEN
        self.cur_col  = BOARD_W // 2 - 2
        self.hold_used = False
        if not self._valid(self.cur_row, self.cur_col, self.cur_rot):
            self.game_over = True

    def _cells(self, row, col, rot, name=None):
        n = name or self.cur_name
        return [(row+dr, col+dc) for dr,dc in PIECES[n]["rotations"][rot]]

    def _valid(self, row, col, rot, name=None):
        for r,c in self._cells(row, col, rot, name):
            if r < 0 or r >= BOARD_H or c < 0 or c >= BOARD_W:
                return False
            if self.board[r][c] != COLOR_EMPTY:
                return False
        return True

    def _lock(self):
        color = PIECES[self.cur_name]["color"]
        for r,c in self._cells(self.cur_row, self.cur_col, self.cur_rot):
            self.board[r][c] = color
        self._clear_lines()
        self._spawn()

    def _clear_lines(self):
        new_board = [row for row in self.board if any(c == COLOR_EMPTY for c in row)]
        cleared = BOARD_H - len(new_board)
        self.score += [0,100,300,500,800][cleared]
        for _ in range(cleared):
            new_board.insert(0, [COLOR_EMPTY]*BOARD_W)
        self.board = new_board

    def do_hold(self):
        if self.hold_used:
            return
        if self.hold is None:
            self.hold = self.cur_name
            self._spawn()
        else:
            self.hold, self.cur_name = self.cur_name, self.hold
            self.cur_rot = 0
            self.cur_row = BOARD_HIDDEN
            self.cur_col = BOARD_W // 2 - 2
        self.hold_used = True

    def do_rotate(self, cw=True):
        new_rot = (self.cur_rot + (1 if cw else -1)) % 4
        # wall kick: try offsets
        for dc in [0, -1, 1, -2, 2]:
            if self._valid(self.cur_row, self.cur_col+dc, new_rot):
                self.cur_col += dc
                self.cur_rot = new_rot
                return

    def do_move(self, dc):
        if self._valid(self.cur_row, self.cur_col+dc, self.cur_rot):
            self.cur_col += dc

    def do_gravity(self):
        if self._valid(self.cur_row+1, self.cur_col, self.cur_rot):
            self.cur_row += 1
            return True
        else:
            self._lock()
            return False

    def do_hard_drop(self):
        while self._valid(self.cur_row+1, self.cur_col, self.cur_rot):
            self.cur_row += 1
        self._lock()

    def ghost_row(self):
        r = self.cur_row
        while self._valid(r+1, self.cur_col, self.cur_rot):
            r += 1
        return r

    def process_input(self):
        if self.inp_left:      self.do_move(-1);          self.inp_left = False
        if self.inp_right:     self.do_move(1);           self.inp_right = False
        if self.inp_rot_cw:    self.do_rotate(True);      self.inp_rot_cw = False
        if self.inp_rot_ccw:   self.do_rotate(False);     self.inp_rot_ccw = False
        if self.inp_hard_drop: self.do_hard_drop();       self.inp_hard_drop = False
        if self.inp_hold:      self.do_hold();             self.inp_hold = False

# ── Rendering ────────────────────────────────────────────────────────────────
def make_screen():
    return [[COLOR_EMPTY]*SCREEN_W for _ in range(SCREEN_H)]

def draw_piece_preview(scr, name, sx, sy):
    """Draw a 4x4 piece preview at screen position (sx,sy)."""
    cells = PIECES[name]["rotations"][0]
    color = PIECES[name]["color"]
    for dr,dc in cells:
        r, c = sy+dr, sx+dc
        if 0 <= r < SCREEN_H and 0 <= c < SCREEN_W:
            scr[r][c] = color

def render(game):
    scr = make_screen()

    # ── Board border (single pixel, color 3=purple) ──
    for y in range(BOARD_VISIBLE):
        scr[y][BOARD_X-1] = COLOR_BORDER              # left wall
        scr[y][BOARD_X+BOARD_W] = COLOR_BORDER        # right wall

    # ── Board cells ──
    for r in range(BOARD_H):
        sy = r - BOARD_HIDDEN  # screen y
        if sy < 0 or sy >= SCREEN_H:
            continue
        for c in range(BOARD_W):
            scr[sy][BOARD_X+c] = game.board[r][c]

    # ── Ghost piece ──
    ghost_r = game.ghost_row()
    ghost_color = PIECES[game.cur_name]["color"]
    for r,c in game._cells(ghost_r, game.cur_col, game.cur_rot):
        sy = r - BOARD_HIDDEN
        if 0 <= sy < SCREEN_H and 0 <= c < BOARD_W:
            if scr[sy][BOARD_X+c] == COLOR_EMPTY:
                scr[sy][BOARD_X+c] = ghost_color  # same color, dim handled by brightness trick
                # We can't easily dim on Arduino side, so just skip ghost or use a marker
                # Using color 0 would hide it — leave as same color for now (optional: skip)

    # ── Active piece ──
    cur_color = PIECES[game.cur_name]["color"]
    for r,c in game._cells(game.cur_row, game.cur_col, game.cur_rot):
        sy = r - BOARD_HIDDEN
        if 0 <= sy < SCREEN_H and 0 <= c < BOARD_W:
            scr[sy][BOARD_X+c] = cur_color

    # ── HOLD box (top-left of panel) ──
    # label: single bright pixel
    scr[0][PANEL_X] = COLOR_BORDER
    if game.hold:
        draw_piece_preview(scr, game.hold, PANEL_X, 1)

    # ── NEXT queue ──
    scr[6][PANEL_X] = COLOR_BORDER
    for i, name in enumerate(game.next_queue[:3]):
        draw_piece_preview(scr, name, PANEL_X, 7 + i*4)

    return scr

def send_screen(ser, scr):
    buf = bytearray()
    for y in range(SCREEN_H):
        for x in range(SCREEN_W):
            buf += bytes([x, y, scr[y][x]])
    buf += bytes([255, 255, 255])
    ser.write(buf)

# ── Keyboard ─────────────────────────────────────────────────────────────────
def setup_keyboard(game):
    def on_press(key):
        try:
            if key == keyboard.Key.left:        game.inp_left = True
            elif key == keyboard.Key.right:     game.inp_right = True
            elif key == keyboard.Key.up:        game.inp_rot_cw = True
            elif key == keyboard.Key.ctrl_r or (hasattr(key,'char') and key.char == 'z'):
                                                game.inp_rot_ccw = True
            elif key == keyboard.Key.space:     game.inp_hard_drop = True
            elif key == keyboard.Key.down:      game.soft_drop = True
            elif hasattr(key,'char') and key.char == 'c':
                                                game.inp_hold = True
            elif key == keyboard.Key.esc:
                return False
        except Exception:
            pass

    def on_release(key):
        if key == keyboard.Key.down:
            game.soft_drop = False

    return keyboard.Listener(on_press=on_press, on_release=on_release)

# ── Main loop ────────────────────────────────────────────────────────────────
def main():
    port = PORT
    if len(sys.argv) > 1:
        port = sys.argv[1]

    print(f"Connecting to {port} @ {BAUD}...")
    ser = serial.Serial(port, BAUD, timeout=1)
    time.sleep(2)  # wait for Arduino reset
    print("Connected! Starting Tetris...")
    print("Controls: ← → move | ↑ rotate CW | Z rotate CCW | Space hard drop | ↓ soft drop | C hold | ESC quit")

    game = Tetris()
    listener = setup_keyboard(game)
    listener.start()

    last_gravity = time.time()
    last_frame   = time.time()
    frame_dt = 1.0 / FPS

    try:
        while not game.game_over:
            now = time.time()

            # Cap frame rate
            if now - last_frame < frame_dt:
                time.sleep(0.001)
                continue
            last_frame = now

            game.process_input()

            # Gravity
            tick = TICK_SOFT_DROP if game.soft_drop else TICK_NORMAL
            if now - last_gravity >= tick:
                game.do_gravity()
                last_gravity = now

            scr = render(game)
            send_screen(ser, scr)

    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        # Clear screen on exit
        ser.write(bytes([255,255,255]))
        ser.close()
        print(f"Game over! Score: {game.score}")

if __name__ == "__main__":
    main()