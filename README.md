# Dimmr 🌙
Screen dimmer untuk Windows — pengganti PangoBright dengan fitur jadwal otomatis.

## Cara kerja
Dimmr meletakkan **overlay hitam semi-transparan** di atas seluruh layar (persis seperti PangoBright), dengan tambahan:
- Jadwal otomatis berdasarkan jam
- Pengaturan kecerahan via tray icon
- Setting tersimpan otomatis
- Multi-monitor ready
- Autostart saat Windows nyala

## Instalasi

### 1. Install Python
Download dari https://python.org (centang "Add to PATH")

### 2. Install dependensi
Buka Command Prompt, jalankan:
```
pip install pystray pillow screeninfo
```

### 3. Jalankan
```
python dimmr.py
```
Ikon akan muncul di system tray (pojok kanan bawah taskbar).

## Penggunaan
- **Klik kanan** ikon tray → pilih level kecerahan
- **Edit jadwal** → atur jam berapa layar redup/terang otomatis
- **Autostart** → centang agar jalan otomatis saat Windows nyala

## Jadwal default
| Jam | Kecerahan |
|-----|-----------|
| 20:00 | 50% (redup) |
| 07:00 | 100% (normal) |

Jadwal bisa diubah lewat menu "Edit jadwal..."

## Config
Tersimpan di: `%APPDATA%\Dimmr\config.json`

## Compile jadi .exe (opsional)
```
pip install pyinstaller
pyinstaller --onefile --windowed --name Dimmr dimmr.py
```
Hasil `.exe` ada di folder `dist/`.
