#include <Arduino.h>
#include <FastLED.h>

#define SCREEN_W 27
#define SCREEN_H 18
#define NUM_LEDS (SCREEN_W * SCREEN_H)  // 486

CRGB leds[NUM_LEDS];

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

inline int ledIndex(byte x, byte y) {
  byte mappedY = (SCREEN_H - 1) - y;
  return (mappedY % 2 == 0)
    ? mappedY * SCREEN_W + x
    : mappedY * SCREEN_W + (SCREEN_W - 1 - x);
}

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<WS2813, 3>(leds, NUM_LEDS);
  FastLED.clear();
  FastLED.show();
}

void loop() {
  while (Serial.available() >= 3) {
    byte x = Serial.read();
    byte y = Serial.read();
    byte color = Serial.read();

    if (x == 255 && y == 255 && color == 255) {
      FastLED.show();
      return;
    }

    if (x < SCREEN_W && y < SCREEN_H && color < 8) {
      leds[ledIndex(x, y)] = tetrominoColors[color];
    }
  }
}