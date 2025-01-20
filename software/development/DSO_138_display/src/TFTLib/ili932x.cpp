// IMPORTANT: LIBRARY MUST BE SPECIFICALLY CONFIGURED FOR EITHER TFT SHIELD
// OR BREAKOUT BOARD USAGE.  SEE RELEVANT COMMENTS IN Adafruit_TFTLCD.h

// Graphics library by ladyada/adafruit with init code from Rossum
// MIT license


#include "Adafruit_TFTLCD_8bit_STM32.h"
//#include "pin_magic.h"

#include "ili932x.h"

static uint8_t rotation;

/*****************************************************************************/
static const uint16_t ILI932x_regValues[] = {
  ILI932X_START_OSC        , 0x0001, // Start oscillator
  TFTLCD_DELAY             , 50,     // 50 millisecond delay
  ILI932X_DRIV_OUT_CTRL    , 0x0100,
  ILI932X_DRIV_WAV_CTRL    , 0x0700,
  ILI932X_ENTRY_MOD        , 0x1030,
  ILI932X_RESIZE_CTRL      , 0x0000,
  ILI932X_DISP_CTRL2       , 0x0202,
  ILI932X_DISP_CTRL3       , 0x0000,
  ILI932X_DISP_CTRL4       , 0x0000,
  ILI932X_RGB_DISP_IF_CTRL1, 0x0,
  ILI932X_FRM_MARKER_POS   , 0x0,
  ILI932X_RGB_DISP_IF_CTRL2, 0x0,
  ILI932X_POW_CTRL1        , 0x0000,
  ILI932X_POW_CTRL2        , 0x0007,
  ILI932X_POW_CTRL3        , 0x0000,
  ILI932X_POW_CTRL4        , 0x0000,
  TFTLCD_DELAY             , 200,
  ILI932X_POW_CTRL1        , 0x1690,
  ILI932X_POW_CTRL2        , 0x0227,
  TFTLCD_DELAY             , 50,
  ILI932X_POW_CTRL3        , 0x001A,
  TFTLCD_DELAY             , 50,
  ILI932X_POW_CTRL4        , 0x1800,
  ILI932X_POW_CTRL7        , 0x002A,
  TFTLCD_DELAY             , 50,
  ILI932X_GAMMA_CTRL1      , 0x0000,
  ILI932X_GAMMA_CTRL2      , 0x0000,
  ILI932X_GAMMA_CTRL3      , 0x0000,
  ILI932X_GAMMA_CTRL4      , 0x0206,
  ILI932X_GAMMA_CTRL5      , 0x0808,
  ILI932X_GAMMA_CTRL6      , 0x0007,
  ILI932X_GAMMA_CTRL7      , 0x0201,
  ILI932X_GAMMA_CTRL8      , 0x0000,
  ILI932X_GAMMA_CTRL9      , 0x0000,
  ILI932X_GAMMA_CTRL10     , 0x0000,
  ILI932X_GRAM_HOR_AD      , 0x0000,
  ILI932X_GRAM_VER_AD      , 0x0000,
  ILI932X_HOR_START_AD     , 0x0000,
  ILI932X_HOR_END_AD       , 0x00EF,
  ILI932X_VER_START_AD     , 0X0000,
  ILI932X_VER_END_AD       , 0x013F,
  ILI932X_GATE_SCAN_CTRL1  , 0xA700, // Driver Output Control (R60h)
  ILI932X_GATE_SCAN_CTRL2  , 0x0003, // Driver Output Control (R61h)
  ILI932X_GATE_SCAN_CTRL3  , 0x0000, // Driver Output Control (R62h)
  ILI932X_PANEL_IF_CTRL1   , 0X0010, // Panel Interface Control 1 (R90h)
  ILI932X_PANEL_IF_CTRL2   , 0X0000,
  ILI932X_PANEL_IF_CTRL3   , 0X0003,
  ILI932X_PANEL_IF_CTRL4   , 0X1100,
  ILI932X_PANEL_IF_CTRL5   , 0X0000,
  ILI932X_PANEL_IF_CTRL6   , 0X0000,
  ILI932X_DISP_CTRL1       , 0x0133, // Main screen turn on
};


/*****************************************************************************/
void ili932x_begin(void)
{
  //Serial.println("initializing ILI932x...");
    uint16_t a, d;
	uint8_t i = 0;

    while(i < sizeof(ILI932x_regValues) / sizeof(uint16_t)) {
      a = pgm_read_word(&ILI932x_regValues[i++]);
      d = pgm_read_word(&ILI932x_regValues[i++]);
      if(a == TFTLCD_DELAY) delay(d);
      else {
		  //Serial.print("writing to 0x"); Serial.print(a,HEX); Serial.print(" value: 0x"); Serial.println(d,HEX);
		  writeRegister16(a, d);
	  }
    }
	rotation = 0;
    ili932x_setRotation(rotation);
    //setAddrWindow(0, 0, TFTWIDTH-1, TFTHEIGHT-1); // done in setRotation()
}

/*****************************************************************************/
// Sets the LCD address window (and address counter, on 932X).
// Relevant to rect/screen fills and H/V lines.  Input coordinates are
// assumed pre-sorted (e.g. x2 >= x1).
/*****************************************************************************/
void ili932x_setAddrWindow(int x1, int y1, int x2, int y2)
{
    // Values passed are in current (possibly rotated) coordinate
    // system.  932X requires hardware-native coords regardless of
    // MADCTL, so rotate inputs as needed.  The address counter is
    // set to the top-left corner -- although fill operations can be
    // done in any direction, the current screen rotation is applied
    // because some users find it disconcerting when a fill does not
    // occur top-to-bottom.
    int x, y, t;
    switch(rotation) {
     default:
      x  = x1;
      y  = y1;
      break;
     case 1:
	  t  = y1;
      y1 = x1;
      if (y2>(TFTWIDTH-1)) { y2 = (TFTWIDTH-1); }
	  x1 = TFTWIDTH  - 1 - y2;
      y2 = x2;
      x2 = TFTWIDTH  - 1 - t;
      x  = x2;
      y  = y1;
      break;
     case 2:
      t  = x1;
      x1 = TFTWIDTH  - 1 - x2;
      x2 = TFTWIDTH  - 1 - t;
      t  = y1;
      y1 = TFTHEIGHT - 1 - y2;
      y2 = TFTHEIGHT - 1 - t;
      x  = x2;
      y  = y2;
      break;
     case 3:
      t  = x1;
      x1 = y1;
      y1 = TFTHEIGHT - 1 - x2;
      if (y2>(TFTWIDTH-1)) { y2 = (TFTWIDTH-1); }
	  x2 = y2;
      y2 = TFTHEIGHT - 1 - t;
      x  = x1;
      y  = y2;
      break;
    }
	//Serial.print("setAddrWindow: rot: "); Serial.print(rotation); Serial.print(", x1: "); Serial.print(x1); Serial.print(", y1: "); Serial.print(y1); Serial.print(", x2: "); Serial.print(x2); Serial.print(", y2: "); Serial.println(y2);
    writeRegister16(ILI932X_HOR_START_AD, x1); // Set window address
    writeRegister16(ILI932X_HOR_END_AD, x2);
    writeRegister16(ILI932X_VER_START_AD, y1);
    writeRegister16(ILI932X_VER_END_AD, y2);
    writeRegister16(ILI932X_GRAM_HOR_AD, x ); // Set address counter to top left
    writeRegister16(ILI932X_GRAM_VER_AD, y );
}

/*****************************************************************************/
void ili932x_fillScreen(uint16_t color)
{
    // For the 932X, a full-screen address window is already the default
    // state, just need to set the address pointer to the top-left corner.
    // Although we could fill in any direction, the code uses the current
    // screen rotation because some users find it disconcerting when a
    // fill does not occur top-to-bottom.
    uint16_t x, y;
    switch(rotation) {
      default: x = 0            ; y = 0            ; break;
      case 1 : x = TFTWIDTH  - 1; y = 0            ; break;
      case 2 : x = TFTWIDTH  - 1; y = TFTHEIGHT - 1; break;
      case 3 : x = 0            ; y = TFTHEIGHT - 1; break;
    }
    writeRegister16(ILI932X_GRAM_HOR_AD, x);
    writeRegister16(ILI932X_GRAM_VER_AD, y);
}

/*****************************************************************************/
void ili932x_drawPixel(int16_t x, int16_t y, uint16_t color)
{
    int16_t t;
    switch(rotation) {
     case 1:
      t = x;
      x = TFTWIDTH  - 1 - y;
      y = t;
      break;
     case 2:
      x = TFTWIDTH  - 1 - x;
      y = TFTHEIGHT - 1 - y;
      break;
     case 3:
      t = x;
      x = y;
      y = TFTHEIGHT - 1 - t;
      break;
    }
    writeRegister16(ILI932X_GRAM_HOR_AD, x);
    writeRegister16(ILI932X_GRAM_VER_AD, y);
    writeRegister16(ILI932X_RW_GRAM, color);
}

/*****************************************************************************/
void ili932x_setRotation(uint8_t rot)
{
    uint16_t t, x2 = 0, y2 = 0;
	rotation = rot;
    switch(rot) {
     default: t = 0x1030; x2 = TFTWIDTH-1; y2 = TFTHEIGHT-1; break;
     case 1 : t = 0x1028; x2 = TFTHEIGHT-1; y2 = TFTWIDTH-1; break;
     case 2 : t = 0x1000; x2 = TFTWIDTH-1; y2 = TFTHEIGHT-1; break;
     case 3 : t = 0x1018; x2 = TFTHEIGHT-1; y2 = TFTWIDTH-1; break;
    }
    writeRegister16(ILI932X_ENTRY_MOD, t ); // MADCTL
    // For 932X, init default full-screen address window:
    ili932x_setAddrWindow(0, 0, x2, y2);
}

/*****************************************************************************/
uint16_t ili932x_readPixel(int16_t x, int16_t y)
{
    int16_t t,r;
    switch(rotation) {
     case 1:
      t = x;
      x = TFTWIDTH  - 1 - y;
      y = t;
      break;
     case 2:
      x = TFTWIDTH  - 1 - x;
      y = TFTHEIGHT - 1 - y;
      break;
     case 3:
      t = x;
      x = y;
      y = TFTHEIGHT - 1 - t;
      break;
    }
    writeRegister16(ILI932X_GRAM_HOR_AD, x);
    writeRegister16(ILI932X_GRAM_VER_AD, y);
    // Inexplicable thing: sometimes pixel read has high/low bytes
    // reversed.  A second read fixes this.  Unsure of reason.  Have
    // tried adjusting timing in read8() etc. to no avail.
    for(uint8_t pass=0; pass<2; pass++) {
      r = readReg(ILI932X_RW_GRAM); // Read data from GRAM
    }
    return r;
}
