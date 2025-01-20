  #include <Adafruit_GFX.h>    // Core graphics library
  #include "src/TFTLib/Adafruit_TFTLCD_8bit_STM32.h"
  
  
  // Assign human-readable names to some common 16-bit color values:
  #define  BLACK   0x0000
  #define BLUE    0x001F
  #define RED     0xF800
  #define GREEN   0x07E0
  #define CYAN    0x07FF
  #define MAGENTA 0xF81F
  #define YELLOW  0xFFE0
  #define WHITE   0xFFFF
  
  // Use hardware-specific library
  #define LCD_CS A3 // Chip Select goes to Analog 3
  #define LCD_CD A2 // Command/Data goes to Analog 2
  #define LCD_WR A1 // LCD Write goes to Analog 1
  #define LCD_RD A0 // LCD Read goes to Analog 0
  #define LCD_RESET A4 // Can alternately just connect to Arduino's reset pin
  
  Adafruit_TFTLCD_8bit_STM32 tft;
  
  void setup() {
    // Initialize the display
    tft.reset();
    
    // You can try different init routines depending on your display
    uint16_t identifier = tft.readID();
    if(identifier == 0x9325) {
      tft.begin(0x9325);
    } else if(identifier == 0x9328) {
      tft.begin(0x9328);
    } else if(identifier == 0x7575) {
      tft.begin(0x7575);
    } else if(identifier == 0x9341) {
      tft.begin(0x9341);
    } else if(identifier == 0x8357) {
      tft.begin(0x8357);
    } else {
      tft.begin(0x9325); // Default to this if ID cannot be found
    }
    
    tft.fillScreen(BLACK);
    tft.setCursor(0, 0);
    tft.setTextColor(WHITE);  
    tft.setTextSize(2);
    tft.println("Hello, DSO-138!");
  }
  
  void loop() {
    // Nothing needed here
  }
