// IMPORTANT: LIBRARY MUST BE SPECIFICALLY CONFIGURED FOR EITHER TFT SHIELD
// OR BREAKOUT BOARD USAGE.  SEE RELEVANT COMMENTS IN Adafruit_TFTLCD.h

// Graphics library by ladyada/adafruit with init code from Rossum
// MIT license


#include "Adafruit_TFTLCD_8bit_STM32.h"
//#include "pin_magic.h"

#include "ili9341.h"


/*****************************************************************************/
void ili9341_begin(void)
{
    writeRegister8(ILI9341_SOFTRESET, 0);
    delay(50);
    writeRegister8(ILI9341_DISPLAYOFF, 0);

    writeRegister8(ILI9341_POWERCONTROL1, 0x23);
    writeRegister8(ILI9341_POWERCONTROL2, 0x10);
    writeRegister16(ILI9341_VCOMCONTROL1, 0x2B2B);
    writeRegister8(ILI9341_VCOMCONTROL2, 0xC0);
    writeRegister8(ILI9341_MEMCONTROL, ILI9341_MADCTL_MY | ILI9341_MADCTL_BGR);
    writeRegister8(ILI9341_PIXELFORMAT, 0x55);
    writeRegister16(ILI9341_FRAMECONTROL, 0x001B);
    
    writeRegister8(ILI9341_ENTRYMODE, 0x07);
    /* writeRegister32(ILI9341_DISPLAYFUNC, 0x0A822700);*/

    writeRegister8(ILI9341_SLEEPOUT, 0);
    delay(120);
    writeRegister8(ILI9341_DISPLAYON, 0);
    ili9341_setAddrWindow(0, 0, TFTWIDTH-1, TFTHEIGHT-1);
}

/*****************************************************************************/
// Sets the LCD address window (and address counter, on 932X).
// Relevant to rect/screen fills and H/V lines.  Input coordinates are
// assumed pre-sorted (e.g. x2 >= x1).
/*****************************************************************************/
void ili9341_setAddrWindow(int x1, int y1, int x2, int y2)
{
    uint32_t t;

    t = x1;
    t <<= 16;
    t |= x2;
    writeRegister32(ILI9341_COLADDRSET, t);  // HX8357D uses same registers!
    t = y1;
    t <<= 16;
    t |= y2;
    writeRegister32(ILI9341_PAGEADDRSET, t); // HX8357D uses same registers!
}

/*****************************************************************************/
void ili9341_fillScreen(uint16_t color)
{
}

/*****************************************************************************/
void ili9341_drawPixel(int16_t x, int16_t y, uint16_t color)
{
}

/*****************************************************************************/
void ili9341_setRotation(uint8_t x)
{
}

/*****************************************************************************/
uint16_t ili9341_readPixel(int16_t x, int16_t y)
{
}
