// IMPORTANT: LIBRARY MUST BE SPECIFICALLY CONFIGURED FOR EITHER TFT SHIELD
// OR BREAKOUT BOARD USAGE.  SEE RELEVANT COMMENTS IN Adafruit_TFTLCD.h

// Graphics library by ladyada/adafruit with init code from Rossum
// MIT license


#include "Adafruit_TFTLCD_8bit_STM32.h"
//#include "pin_magic.h"

#include "hx8357x.h"

/*****************************************************************************/
static const uint8_t HX8357D_regValues[] PROGMEM = {
  HX8357_SWRESET, 0,
  HX8357D_SETC, 3, 0xFF, 0x83, 0x57,
  TFTLCD_DELAY, 250,
  HX8357_SETRGB, 4, 0x00, 0x00, 0x06, 0x06,
  HX8357D_SETCOM, 1, 0x25,  // -1.52V
  HX8357_SETOSC, 1, 0x68,  // Normal mode 70Hz, Idle mode 55 Hz
  HX8357_SETPANEL, 1, 0x05,  // BGR, Gate direction swapped
  HX8357_SETPWR1, 6, 0x00, 0x15, 0x1C, 0x1C, 0x83, 0xAA,
  HX8357D_SETSTBA, 6, 0x50, 0x50, 0x01, 0x3C, 0x1E, 0x08,
  // MEME GAMMA HERE
  HX8357D_SETCYC, 7, 0x02, 0x40, 0x00, 0x2A, 0x2A, 0x0D, 0x78,
  HX8357_COLMOD, 1, 0x55,
  HX8357_MADCTL, 1, 0xC0,
  HX8357_TEON, 1, 0x00,
  HX8357_TEARLINE, 2, 0x00, 0x02,
  HX8357_SLPOUT, 0,
  TFTLCD_DELAY, 150,
  HX8357_DISPON, 0, 
  TFTLCD_DELAY, 50,
};

/*****************************************************************************/
void hx8357x_begin(void)
{
    uint8_t i = 0;
    //CS_ACTIVE;
     while(i < sizeof(HX8357D_regValues)) {
      uint8_t r = pgm_read_byte(&HX8357D_regValues[i++]);
      uint8_t len = pgm_read_byte(&HX8357D_regValues[i++]);
      if(r == TFTLCD_DELAY) {
		delay(len);
      } else {
		//Serial.print("Register $"); Serial.print(r, HEX);
		//Serial.print(" datalen "); Serial.println(len);

		CS_ACTIVE;
		CD_COMMAND;
		write8(r);
		CD_DATA;
		for (uint8_t d=0; d<len; d++) {
		  uint8_t x = pgm_read_byte(&HX8357D_regValues[i++]);
		  write8(x);
		}
		CS_IDLE;

      }
    }
}

/*****************************************************************************/
// Sets the LCD address window (and address counter, on 932X).
// Relevant to rect/screen fills and H/V lines.  Input coordinates are
// assumed pre-sorted (e.g. x2 >= x1).
/*****************************************************************************/
void hx8357x_setAddrWindow(int x1, int y1, int x2, int y2)
{
}

/*****************************************************************************/
void hx8357x_fillScreen(uint16_t color)
{
}

/*****************************************************************************/
void hx8357x_drawPixel(int16_t x, int16_t y, uint16_t color)
{
}

/*****************************************************************************/
void hx8357x_setRotation(uint8_t x)
{
}

/*****************************************************************************/
uint16_t hx8357x_readPixel(int16_t x, int16_t y)
{
}
