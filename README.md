# Dimmr — Scheduled Screen Dimmer for Windows

**Dimmr** is a lightweight, open-source utility designed to dim your Windows screen(s) based on a custom time schedule. Unlike the default Windows Night Light which only filters blue light, Dimmr applies a true dimming overlay across multiple monitors, making it perfect for night owls, developers, and anyone working in low-light environments.

---

### 🌟 Key Features

*   **Smart Scheduled Dimming:** Automatically checks the system time upon Windows startup or user login and immediately applies the correct scheduled brightness level.
*   **Multi-Monitor Support:** Seamlessly spans and dims all connected screens and desktop displays.
*   **System Tray Integration:** Runs quietly in the background with a quick-access right-click tray menu.
*   **Toggleable Notifications:** Displays Windows toast notifications whenever the brightness changes (can be turned on/off easily via the tray menu).
*   **Resource Efficient:** Built using Python, Tkinter, and native Windows APIs to ensure minimal CPU and RAM usage.

---

### 🚀 How to Use

#### Option 1: Use the Pre-compiled Executable (Easiest)
If you just want to run the program without installing Python:
1. Go to the **Releases** section (or the `dist/` folder) and download `Dimmr.exe`.
2. Double-click `Dimmr.exe` to launch it. It will sit quietly in your system tray (bottom-right corner).

**To make it run automatically at Windows startup:**
1. Right-click `Dimmr.exe` and select **Show more options** -> **Create shortcut**.
2. Press `Win + R` on your keyboard to open the Run dialog box.
3. Type `shell:startup` and hit **Enter** (this opens your Windows Startup folder).
4. Cut and paste the newly created **Dimmr shortcut** into this folder. Done!

#### Option 2: Running from Source Code
1. Clone this repository or download the source code files.
2. Open your terminal/command prompt and install the required dependencies:
```bash
   pip install pystray pillow screeninfo pyinstaller