Embedding web assets for UNO R4 firmware

- Edit files under `arduino_r4_wifi/TUSS4470_arduino_r4/www/` directly (HTML/CSS/JS).
- Optionally minify the files (spectrogram.js -> spectrogram.min.js etc). I use VSCode Minify extension.
- Generate the C header with embedded strings:

```bash
cd TUSS4470_shield_002/arduino_r4_wifi/TUSS4470_arduino_r4
python3 tools/embed_assets.py
```

This writes `embedded_assets.h`. The firmware includes this header to serve pages.

If the header is missing, the build will fail when including `embedded_assets.h`.
