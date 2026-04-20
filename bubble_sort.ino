#include <Arduino.h>
#include <FastLED.h>

// How many leds in your strip?

#define screen_x 27
#define screen_y 18
#define NUM_LEDS 486



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
    //Serial.println("BLINK setup starting");
    
    // Uncomment/edit one of the following lines for your leds arrangement.
    //Serial.println("Setup complete");
    FastLED.addLeds<WS2813, 3>(leds, NUM_LEDS);

    //generate numbers to sort
    randomSeed(analogRead(0));
    for (int i=0; i < screen_x; i++)
    {
      numbers[i] = random(0, screen_y);
    }
    



}

void loop() {   
  if(sorted){
    sorted = false;
    for (int i=0; i < screen_x; i++){
      if(i==screen_x-1){
        
      }
      else{
        if(numbers[i] > numbers[i+1]){
          int dummy = numbers[i];
          numbers[i]= numbers[i+1];
          numbers[i+1] = dummy;
          sorted = true;
        }
      }
      Serial.print(numbers[i]);
      for (int j=0; j < screen_y; j++){
        if (j <= numbers[i]){
          screen[i][j][0]=255;
          screen[i][j][1]=255;
          screen[i][j][2]=255;
        }
        else{
          screen[i][j][0]=0;
          screen[i][j][1]=0;
          screen[i][j][2]=0;
        }
        
      }
      draw(leds, screen);
      delay(10);
    }
    Serial.println();
    
  }
  
  delay(10);
}
