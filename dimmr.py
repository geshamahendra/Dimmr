"""
Dimmr - Screen Dimmer for Windows
Scheduled overlay dimmer with system tray
"""

import tkinter as tk
import threading
import time
import json
import os
import sys
import ctypes
import ctypes.wintypes
from datetime import datetime
from PIL import Image, ImageDraw
import pystray

# ── Windows API ───────────────────────────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW  = 0x00000080
WS_EX_NOACTIVATE  = 0x08000000

user32 = ctypes.windll.user32

def _hwnd(win):
    return ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()

def make_click_through(win):
    hwnd  = _hwnd(win)
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE,
        style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    )

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.environ.get("APPDATA", "."), "Dimmr", "config.json")
DEFAULT_CONFIG = {
    "brightness": 80,
    "enabled": True,
    "schedules": [
        {"hour": 20, "minute": 0, "brightness": 50},
        {"hour": 7,  "minute": 0, "brightness": 100},
    ],
    "schedule_enabled": True,
    "autostart": False,
}

def load_config():
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def set_autostart(enabled: bool):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enabled:
            exe    = sys.executable
            script = os.path.abspath(__file__)
            winreg.SetValueEx(key, "Dimmr", 0, winreg.REG_SZ, f'"{exe}" "{script}"')
        else:
            try:
                winreg.DeleteValue(key, "Dimmr")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[autostart] {e}")

def get_monitors():
    try:
        from screeninfo import get_monitors as _gm
        return [(m.x, m.y, m.width, m.height) for m in _gm()]
    except Exception:
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return [(0, 0, w, h)]

# ── Overlay ───────────────────────────────────────────────────────────────────

class OverlayWindow:
    def __init__(self, root, x, y, width, height):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.configure(bg="black")
        self.win.geometry(f"{width}x{height}+{x}+{y}")
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        self.win.update_idletasks()
        self.win.update()
        make_click_through(self.win)

    def set_alpha(self, alpha: float):
        alpha = max(0.0, min(0.9, alpha))
        try:
            self.win.attributes("-alpha", alpha)
            self.win.update_idletasks()
        except Exception:
            pass

    def destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class OverlayManager:
    def __init__(self, root):
        self.root        = root
        self.overlays    = []
        self._brightness = 100
        self._enabled    = True
        self._rebuild()

    def _rebuild(self):
        for ov in self.overlays:
            ov.destroy()
        self.overlays.clear()
        for (x, y, w, h) in get_monitors():
            self.overlays.append(OverlayWindow(self.root, x, y, w, h))
        self._apply()

    def _apply(self):
        alpha = (1.0 - self._brightness / 100.0) * 0.9 if self._enabled else 0.0
        for ov in self.overlays:
            ov.set_alpha(alpha)

    def set_brightness(self, value: int):
        self._brightness = max(0, min(100, value))
        self._apply()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._apply()

    def refresh_monitors(self):
        self._rebuild()

# ── Tray icon image ───────────────────────────────────────────────────────────

def make_tray_icon(brightness: int) -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size-3, size-3], fill="#222222", outline="#888888", width=2)
    fill_h = int((size - 8) * brightness / 100)
    if fill_h > 0:
        draw.rectangle([4, size - 4 - fill_h, size - 5, size - 4], fill="#F5C518")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([2, 2, size-3, size-3], fill=255)
    img.putalpha(mask)
    return img

# ── Main app ──────────────────────────────────────────────────────────────────

class DimmrApp:
    def __init__(self):
        self.config = load_config()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Dimmr")

        self.overlay_mgr = OverlayManager(self.root)
        self.overlay_mgr.set_brightness(self.config["brightness"])
        self.overlay_mgr.set_enabled(self.config["enabled"])

        self._tray = None
        self._build_tray()

        threading.Thread(target=self._schedule_loop, daemon=True).start()
        self.root.after(100, self._tk_loop)
        self.root.mainloop()

    # ── Tray ─────────────────────────────────────────────────────────────────

    def _build_tray(self):

        def make_brightness_action(v):
            def action(icon, item):
                self._set_brightness(v)
            return action

        def make_brightness_check(v):
            def checked(item):
                return self.config["brightness"] == v
            return checked

        def brightness_item(label, value):
            return pystray.MenuItem(
                label,
                make_brightness_action(value),
                checked=make_brightness_check(value),
                radio=True,
            )

        def toggle_enabled(icon, item):
            self.config["enabled"] = not self.config["enabled"]
            self.overlay_mgr.set_enabled(self.config["enabled"])
            save_config(self.config)

        def toggle_schedule(icon, item):
            self.config["schedule_enabled"] = not self.config["schedule_enabled"]
            save_config(self.config)

        def toggle_autostart(icon, item):
            self.config["autostart"] = not self.config["autostart"]
            set_autostart(self.config["autostart"])
            save_config(self.config)

        def open_editor(icon, item):
            self.root.after(0, self._open_schedule_editor)

        def refresh_mon(icon, item):
            self.root.after(0, self.overlay_mgr.refresh_monitors)

        def quit_app(icon, item):
            self.overlay_mgr.set_enabled(False)
            icon.stop()
            self.root.after(0, self.root.quit)

        menu = pystray.Menu(
            pystray.MenuItem("Enabled", toggle_enabled,
                             checked=lambda item: self.config["enabled"],
                             default=True),
            pystray.Menu.SEPARATOR,
            brightness_item("100% — Full brightness", 100),
            brightness_item("80%", 80),
            brightness_item("60%", 60),
            brightness_item("50%", 50),
            brightness_item("40%", 40),
            brightness_item("20% — Very dim", 20),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Auto schedule", toggle_schedule,
                             checked=lambda item: self.config["schedule_enabled"]),
            pystray.MenuItem("Edit schedule...", open_editor),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run at Windows startup", toggle_autostart,
                             checked=lambda item: self.config["autostart"]),
            pystray.MenuItem("Refresh monitors", refresh_mon),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        )

        icon_img = make_tray_icon(self.config["brightness"])
        if self._tray:
            self._tray.stop()
        self._tray = pystray.Icon("Dimmr", icon_img, "Dimmr", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    # ── Brightness ────────────────────────────────────────────────────────────

    def _set_brightness(self, value: int):
        self.config["brightness"] = value
        self.overlay_mgr.set_brightness(value)
        save_config(self.config)
        if self._tray:
            self._tray.icon = make_tray_icon(value)

    # ── Schedule loop ─────────────────────────────────────────────────────────

    def _schedule_loop(self):
        last_triggered = None
        while True:
            time.sleep(20)
            if not self.config.get("schedule_enabled"):
                continue
            now = datetime.now()
            key = (now.hour, now.minute)
            if key == last_triggered:
                continue
            for sched in self.config.get("schedules", []):
                if (sched["hour"], sched["minute"]) == key:
                    last_triggered = key
                    self.root.after(0, lambda b=sched["brightness"]: self._set_brightness(b))
                    break

    # ── Schedule editor ───────────────────────────────────────────────────────

    def _open_schedule_editor(self):
        win = tk.Toplevel(self.root)
        win.title("Schedule Editor — Dimmr")
        win.geometry("500x460")          # lebih besar
        win.resizable(False, False)
        win.configure(bg="#1e1e1e")
        win.attributes("-topmost", True)
        win.lift()
        win.focus_force()

        fg, bg, bg2, accent = "#f0f0f0", "#1e1e1e", "#2d2d2d", "#F5C518"

        tk.Label(win, text="Brightness Schedule", font=("Segoe UI", 14, "bold"),
                 bg=bg, fg=accent).pack(pady=(20, 4))
        tk.Label(win, text="Set the time and brightness level for each schedule entry.",
                 font=("Segoe UI", 10), bg=bg, fg="#aaaaaa").pack(pady=(0, 16))

        frame = tk.Frame(win, bg=bg)
        frame.pack(fill="both", expand=True, padx=30)

        schedules = [s.copy() for s in self.config.get("schedules", [])]
        rows = []

        def render_rows():
            for w in frame.winfo_children():
                w.destroy()
            rows.clear()
            headers = ["Hour", "Minute", "Brightness (%)", ""]
            col_widths = [8, 8, 14, 4]
            for col, (label, _) in enumerate(zip(headers, col_widths)):
                tk.Label(frame, text=label, bg=bg, fg="#aaaaaa",
                         font=("Segoe UI", 10, "bold")).grid(
                             row=0, column=col, padx=10, pady=(0, 8), sticky="w")

            for i, s in enumerate(schedules):
                h_var = tk.StringVar(value=str(s["hour"]).zfill(2))
                m_var = tk.StringVar(value=str(s["minute"]).zfill(2))
                b_var = tk.StringVar(value=str(s["brightness"]))
                for col, (var, w) in enumerate(zip([h_var, m_var, b_var], [8, 8, 14])):
                    tk.Entry(frame, textvariable=var, width=w,
                             bg=bg2, fg=fg, insertbackground=fg,
                             relief="flat", font=("Segoe UI", 11), justify="center"
                             ).grid(row=i+1, column=col, padx=10, pady=5, ipady=4)

                def del_row(idx=i):
                    schedules.pop(idx)
                    render_rows()

                tk.Button(frame, text="✕", command=del_row,
                          bg="#c0392b", fg="white", relief="flat",
                          font=("Segoe UI", 10), padx=6, pady=2
                          ).grid(row=i+1, column=3, padx=6)
                rows.append((h_var, m_var, b_var))

        render_rows()

        def add_row():
            schedules.append({"hour": 0, "minute": 0, "brightness": 80})
            render_rows()

        def save():
            new_scheds = []
            for h_var, m_var, b_var in rows:
                try:
                    new_scheds.append({
                        "hour":       int(h_var.get()) % 24,
                        "minute":     int(m_var.get()) % 60,
                        "brightness": max(0, min(100, int(b_var.get()))),
                    })
                except ValueError:
                    pass
            self.config["schedules"] = sorted(
                new_scheds, key=lambda x: (x["hour"], x["minute"]))
            save_config(self.config)
            win.destroy()

        btn_frame = tk.Frame(win, bg=bg)
        btn_frame.pack(pady=16)
        tk.Button(btn_frame, text="+ Add entry", command=add_row,
                  bg=bg2, fg=fg, relief="flat", font=("Segoe UI", 10),
                  padx=14, pady=6).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Save", command=save,
                  bg=accent, fg="#111111", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=24, pady=6).pack(side="left", padx=8)

    # ── Tkinter heartbeat ─────────────────────────────────────────────────────

    def _tk_loop(self):
        self.root.after(100, self._tk_loop)


if __name__ == "__main__":
    DimmrApp()