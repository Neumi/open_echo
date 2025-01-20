#ifndef _HX8347G_H_
#define _HX8347G_H_


// Register names
#define HX8347G_COLADDRSTART_HI    0x02
#define HX8347G_COLADDRSTART_LO    0x03
#define HX8347G_COLADDREND_HI      0x04
#define HX8347G_COLADDREND_LO      0x05
#define HX8347G_ROWADDRSTART_HI    0x06
#define HX8347G_ROWADDRSTART_LO    0x07
#define HX8347G_ROWADDREND_HI      0x08
#define HX8347G_ROWADDREND_LO      0x09
#define HX8347G_MEMACCESS          0x16


/*****************************************************************************/
extern void hx8347g_setLR(void);
extern void hx8347g_begin(void);
extern void hx8347g_setAddrWindow(int x1, int y1, int x2, int y2);
extern void hx8347g_fillScreen(uint16_t color);
extern void hx8347g_drawPixel(int16_t x, int16_t y, uint16_t color);
extern void hx8347g_setRotation(uint8_t x);
extern uint16_t hx8347g_readPixel(int16_t x, int16_t y);


#endif
