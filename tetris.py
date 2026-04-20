import serial

def send_board(board, ser)
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            ser.write(bytes([y, x, cell]))
    ser.write(bytes([255, 255, 255]))


def main():