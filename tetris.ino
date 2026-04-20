#include <Arduino.h>
#include <FastLED.h>

#define screen_x 27
#define screen_y 18
#define NUM_LEDS 486

#define BOARD_W screen_x  // 27
#define BOARD_H screen_y  // 18

// Define the array of leds
CRGB leds[NUM_LEDS];
int s_map[screen_x][screen_y];
int screen[screen_x][screen_y][3];

int numbers[screen_x];

bool sorted = true;

void draw(CRGB ledstrip[NUM_LEDS], int image[screen_x][screen_y][3])
{
  for (int i = 0; i < screen_x; i++) {        // x: 0 .. screen_x-1
    for (int j = 0; j < screen_y; j++) {      // j: 0 .. screen_y-1 (top-based)

      // Convert to bottom-based row index
      //int y = screen_y - 1 - j;               // y: 0 = bottom row
      int y = j; // bottom based

      int index;
      if (y % 2 == 0) {
        // even row (from bottom): left -> right
        index = y * screen_x + i;
      } else {
        // odd row: right -> left
        index = y * screen_x + (screen_x - 1 - i);
      }

      ledstrip[index].setRGB(image[i][j][0], image[i][j][1], image[i][j][2]);
    }
  }
  FastLED.show();
}


void setup() { 
    Serial.begin(9600);

    FastLED.addLeds<WS2813, 3>(leds, NUM_LEDS);
}

CRGB tetrominoColors[] = {
  CRGB::Black,   // 0 = empty
  CRGB::Cyan,    // 1 = I
  CRGB::Yellow,  // 2 = O
  CRGB::Purple,  // 3 = T
  CRGB::Green,   // 4 = S
  CRGB::Red,     // 5 = Z
  CRGB::Blue,    // 6 = J
  CRGB::Orange,  // 7 = L
};

void loop() {
  while (Serial.available() >= 3) {
    byte y = Serial.read();
    byte x = Serial.read();
    byte color = Serial.read();

    if (y == 255) {          // delimiter → push frame
      FastLED.show();
      return;
    }

    int idx = y * 10 + x;   // adjust 10 for your matrix width
    int idx = (y % 2 == 0) ? y * 10 + x : y * 10 + (9 - x);
    leds[idx] = tetrominoColors[color];
  }
}
