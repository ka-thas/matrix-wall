import serial
import sys
import time

PORT = "/dev/cu.usbmodem1401"
BAUD = 115200

# Must match tetris.ino receiver dimensions.
SCREEN_W = 27
SCREEN_H = 18

COLOR_EMPTY = 0
COLOR_TEXT = 2

# 5x7 glyphs, rows are top-to-bottom, bits are left-to-right.
FONT_5X7 = {
	"S": [
		0b01,
		0b10,
		0b01,
		0b10,
	],
	"O": [
		0b010,
		0b101,
		0b101,
		0b010,
	],
	"N": [
		0b110,
		0b101,
		0b101,
		0b101,
	],
	"E": [
		0b111,
		0b110,
		0b100,
		0b111,
	],
}


def make_screen():
	return [[COLOR_EMPTY] * SCREEN_W for _ in range(SCREEN_H)]


def draw_text_5x7(screen, text, x, y, color):
	cursor_x = x
	for ch in text:
		glyph = FONT_5X7.get(ch)

		for row, bits in enumerate(glyph):
			for col in range(5):
				if bits & (1 << (4 - col)):
					px = cursor_x + col
					py = y + row
					if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
						screen[py][px] = color

		cursor_x += 4


def send_screen(ser, screen):
	frame = bytearray()
	for y in range(SCREEN_H):
		for x in range(SCREEN_W):
			frame += bytes([x, y, screen[y][x]])
	frame += bytes([255, 255, 255])
	ser.write(frame)


def main():
	port = sys.argv[1] if len(sys.argv) > 1 else PORT

	print(f"Connecting to {port} @ {BAUD}...")
	ser = serial.Serial(port, BAUD, timeout=1)
	time.sleep(2)

	screen = make_screen()
	text = "SONEN"

	# center text on screen
	start_x = 0
	start_y = 4

	draw_text_5x7(screen, text, start_x, start_y, COLOR_TEXT)

	# Send several frames so the display has time to latch before close.
	for _ in range(20):
		send_screen(ser, screen)
		time.sleep(0.02)

	print("Displayed SONEN")
	ser.close()


if __name__ == "__main__":
	main()
	