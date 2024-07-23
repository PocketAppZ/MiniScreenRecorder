import platform
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import datetime
import webbrowser
import time
from configparser import ConfigParser
from screeninfo import get_monitors
from PIL import ImageGrab
from AreaSelector import AreaSelector


class ScreenRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Screen Recorder")
        root.resizable(0, 0)

        self.config = ConfigParser()
        self.config_file = 'config.ini'
        self.load_config()
        
        self.language = self.config.get('Settings', 'language', fallback='en')
        self.load_translation()

        self.set_theme(self.config.get('Settings', 'theme', fallback='dark'))

        self.audio_devices = self.get_audio_devices()
        self.monitors = self.get_monitors()

        self.set_icon()
        
        self.init_ui()

        self.create_output_folder()
        self.recording_process = None
        self.running = False
        self.elapsed_time = 0
        self.record_area = None
        self.area_selector = AreaSelector(root)

    def load_translation(self):
        translations_folder = 'translations'
        translation_file = os.path.join(translations_folder, f'{self.language}.ini')
        self.translation = ConfigParser()
        with open(translation_file, 'r', encoding='utf-8') as file:
            self.translation.read_file(file)
            
        for key in self.translation['Settings']:
            self.translation['Settings'][key] = self.translation['Settings'][key].replace('\\n', '\n')
    
    def t(self, key):
        return self.translation.get('Settings', key, fallback=key)

    def set_icon(self):
        if platform.system() == 'Windows':
            self.root.iconbitmap('video.ico')
        elif platform.system() == 'Linux':
            self.icon = tk.PhotoImage(file='video.png')
            self.root.iconphoto(True, self.icon)
    
    def set_dark_theme(self):
        self.root.tk_setPalette(background="#2e2e2e", foreground="white", activeBackground="#1e1e1e", activeForeground="white")

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TLabel", background="#2e2e2e", foreground="white")
        style.configure("TCombobox", fieldbackground="#1e1e1e", background="#2e2e2e", foreground="white")
        style.map("TCombobox", fieldbackground=[('readonly', '#1e1e1e')])
        style.configure("TButton", background="#1e1e1e", foreground="white")
        style.map("TButton", background=[('active', '#3e3e3e')], foreground=[('active', 'white')])

    def set_light_theme(self):
        self.root.tk_setPalette(background="#f0f0f0", foreground="black", activeBackground="#d0d0d0", activeForeground="black")

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TLabel", background="#f0f0f0", foreground="black")
        style.configure("TCombobox", fieldbackground="#d0d0d0", background="#f0f0f0", foreground="black")
        style.map("TCombobox", fieldbackground=[('readonly', '#d0d0d0')])
        style.configure("TButton", background="#d0d0d0", foreground="black")
        style.map("TButton", background=[('active', '#c0c0c0')], foreground=[('active', 'black')])

    def set_theme(self, theme):
        if theme == "dark":
            self.set_dark_theme()
        elif theme == "light":
            self.set_light_theme()

    def init_ui(self):
        self.language_label = ttk.Label(self.root, text=self.t("Language") + ":")
        self.language_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.language_combo = ttk.Combobox(self.root, values=["English", "Español", "中文(简体)", "Italiano", "Français"], width=25)
        self.language_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        if self.language == 'en':
            self.language_combo.current(0)
        elif self.language == 'es':
            self.language_combo.current(1)
        elif self.language == 'zh':
            self.language_combo.current(2)
        elif self.language == 'it':
            self.language_combo.current(3)
        elif self.language == "fr":
            self.language_combo.current(4)
        self.language_combo.config(state="readonly")
        self.language_combo.bind("<<ComboboxSelected>>", self.change_language)

        self.theme_label = ttk.Label(self.root, text=self.t("theme") + ":")
        self.theme_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.theme_combo = ttk.Combobox(self.root, values=["Dark", "Light"], width=25)
        self.theme_combo.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.theme_combo.current(0 if self.config.get('Settings', 'theme', fallback='dark') == 'dark' else 1)
        self.theme_combo.config(state="readonly")
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        self.monitor_label = ttk.Label(self.root, text=self.t("monitor") + ":")
        self.monitor_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.monitor_combo = ttk.Combobox(self.root, values=[f"Monitor {i+1}: {monitor.name}" for i, monitor in enumerate(self.monitors)], width=25)
        self.monitor_combo.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.monitor_combo.current(0)
        self.monitor_combo.config(state="readonly")
        self.monitor_combo.bind("<<ComboboxSelected>>", self.save_config)

        self.fps_label = ttk.Label(self.root, text=self.t("framerate") + ":")
        self.fps_label.grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.fps_combo = ttk.Combobox(self.root, values=["30", "60"], width=25)
        self.fps_combo.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.fps_combo.current(self.config.getint('Settings', 'fps'))
        self.fps_combo.config(state="readonly")
        self.fps_combo.bind("<<ComboboxSelected>>", self.save_config)
        
        self.bitrate_label = ttk.Label(self.root, text=self.t("bitrate") + ":")
        self.bitrate_label.grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.bitrate_combo = ttk.Combobox(self.root, values=["2000k", "4000k", "6000k", "8000k", "10000k", "12000k", "14000k", "20000k"], width=25)
        self.bitrate_combo.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.bitrate_combo.current(self.config.getint('Settings', 'bitrate'))
        self.bitrate_combo.config(state="readonly")
        self.bitrate_combo.bind("<<ComboboxSelected>>", self.save_config)

        self.codec_label = ttk.Label(self.root, text=self.t("video_codec") + ":")
        self.codec_label.grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.codec_combo = ttk.Combobox(self.root, values=["libx264", "libx265"], width=25)
        self.codec_combo.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.codec_combo.current(self.config.getint('Settings', 'codec'))
        self.codec_combo.config(state="readonly")
        self.codec_combo.bind("<<ComboboxSelected>>", self.save_config)
        
        self.format_label = ttk.Label(self.root, text=self.t("output_format") + ":")
        self.format_label.grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.format_combo = ttk.Combobox(self.root, values=["mp4", "mkv"], width=25)
        self.format_combo.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.format_combo.current(self.config.getint('Settings', 'format'))
        self.format_combo.config(state="readonly")
        self.format_combo.bind("<<ComboboxSelected>>", self.save_config)
        
        self.audio_label = ttk.Label(self.root, text=self.t("audio_device") + ":")
        self.audio_label.grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.audio_combo = ttk.Combobox(self.root, values=self.audio_devices, width=25)
        self.audio_combo.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        self.audio_combo.current(self.config.getint('Settings', 'audio'))
        self.audio_combo.config(state="readonly")
        self.audio_combo.bind("<<ComboboxSelected>>", self.save_config)

        if self.audio_devices:
            self.audio_combo.current(0)
        else:
            messagebox.showerror(self.t("error"), self.t("error_no_audio_devices"))

        self.volume_label = ttk.Label(self.root, text=self.t("volume") + ":")
        self.volume_label.grid(row=8, column=0, padx=10, pady=5, sticky="e")
        self.volume_scale = ttk.Scale(self.root, from_=0, to=100, orient=tk.HORIZONTAL)
        self.volume_scale.set(100)
        self.volume_scale.grid(row=8, column=1, padx=10, pady=5, sticky="w")

        self.start_btn = ttk.Button(self.root, text=self.t("start_recording"), command=self.start_recording)
        self.start_btn.grid(row=9, column=0, columnspan=2, pady=2)
        
        self.stop_btn = ttk.Button(self.root, text=self.t("stop_recording"), command=self.stop_recording)
        self.stop_btn.grid(row=10, column=0, columnspan=2, pady=2)
        self.stop_btn.config(state=tk.DISABLED)

        self.open_folder_btn = ttk.Button(self.root, text=self.t("open_output_folder"), command=self.open_output_folder)
        self.open_folder_btn.grid(row=11, column=0, columnspan=2, pady=2)

        self.select_area_btn = ttk.Button(self.root, text=self.t("select_recording_area"), command=self.select_area)
        self.select_area_btn.grid(row=12, column=0, columnspan=2, pady=2)

        self.timer_label = ttk.Label(self.root, text="00:00:00")
        self.timer_label.grid(row=13, column=0, columnspan=2, pady=10)
        self.timer_label.config(font=("Arial", 13))

        self.info_btn = ttk.Button(self.root, text=self.t("about"), command=self.show_info)
        self.info_btn.grid(row=14, column=0, columnspan=2, pady=2)

        self.status_label = ttk.Label(self.root, text=self.t("status_ready"))
        self.status_label.grid(row=15, column=0, columnspan=2, pady=5)
        self.status_label.config(font=("Arial", 10))

    def create_output_folder(self):
        self.output_folder = os.path.join(os.getcwd(), "OutputFiles")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def get_audio_devices(self):
        if platform.system() == 'Windows':
            cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            lines = result.stderr.splitlines()
            devices = []
            for line in lines:
                if "audio" in line:
                    parts = line.split("\"")
                    if len(parts) > 1:
                        devices.append(parts[1])
            return devices
        elif platform.system() == 'Linux':
            cmd = ["pactl", "list", "sources"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            lines = result.stdout.splitlines()
            devices = []
            for line in lines:
                if "Name:" in line:
                    parts = line.split()
                    if len(parts) > 1:
                        devices.append(parts[1])
            return devices

    def get_monitors(self):
        return get_monitors()

    def select_area(self):
        self.area_selector.select_area(self.set_record_area)

    def set_record_area(self, record_area):
        self.record_area = record_area
        if self.record_area:
            self.preview_record_area()

    def preview_record_area(self):
        x1, y1, x2, y2 = self.record_area
        width = x2 - x1
        height = y2 - y1
        preview_window = tk.Toplevel(self.root)
        preview_window.geometry(f"{width}x{height}+{x1}+{y1}")
        preview_window.overrideredirect(True)
        preview_window.attributes('-alpha', 0.3)
        preview_canvas = tk.Canvas(preview_window, width=width, height=height)
        preview_canvas.pack()
        preview_canvas.create_rectangle(0, 0, width, height, outline='red', width=2)
        preview_window.after(2000, preview_window.destroy) 

    def start_recording(self):
        video_name = f"Video.{datetime.datetime.now().strftime('%m-%d-%Y.%H.%M.%S')}.{self.format_combo.get()}"
        self.video_path = os.path.join(self.output_folder, video_name)
        
        fps = int(self.fps_combo.get())
        bitrate = self.bitrate_combo.get()
        codec = self.codec_combo.get()
        audio_device = self.audio_combo.get()
        volume = self.volume_scale.get()

        monitor_index = self.monitor_combo.current()
        monitor = self.monitors[monitor_index]

        if self.record_area:
            x1, y1, x2, y2 = self.record_area
            width = x2 - x1
            height = y2 - y1
            if width <= 0 or height <= 0:
                messagebox.showerror(self.t("error"), self.t("error_invalid_area"))
                return
            width -= width % 2
            height -= height % 2
            if width <= 0 or height <= 0:
                messagebox.showerror(self.t("error"), self.t("error_adjusted_area"))
                return

        if platform.system() == 'Windows':
            if self.record_area:
                ffmpeg_args = [
                    "ffmpeg",
                    "-f", "gdigrab",
                    "-framerate", str(fps),
                    "-offset_x", str(x1 + monitor.x),
                    "-offset_y", str(y1 + monitor.y),
                    "-video_size", f"{width}x{height}",
                    "-i", "desktop",
                    "-f", "dshow",
                    "-i", f"audio={audio_device}",
                    "-filter:a", f"volume={volume/100}",
                    "-c:v", codec,
                    "-b:v", bitrate,
                    "-pix_fmt", "yuv420p",
                    self.video_path
                ]
            else:
                ffmpeg_args = [
                    "ffmpeg",
                    "-f", "gdigrab",
                    "-framerate", str(fps),
                    "-offset_x", str(monitor.x),
                    "-offset_y", str(monitor.y),
                    "-video_size", f"{monitor.width}x{monitor.height}",
                    "-i", "desktop",
                    "-f", "dshow",
                    "-i", f"audio={audio_device}",
                    "-filter:a", f"volume={volume/100}",
                    "-c:v", codec,
                    "-b:v", bitrate,
                    "-pix_fmt", "yuv420p",
                    self.video_path
                ]
            creationflags = subprocess.CREATE_NO_WINDOW
        elif platform.system() == 'Linux':
            if self.record_area:
                ffmpeg_args = [
                    "ffmpeg",
                    "-f", "x11grab",
                    "-framerate", str(fps),
                    "-video_size", f"{width}x{height}",
                    "-i", f"{os.getenv('DISPLAY')}+{x1+monitor.x},{y1+monitor.y}",
                    "-f", "pulse",
                    "-i", audio_device,
                    "-filter:a", f"volume={volume/100}",
                    "-c:v", codec,
                    "-b:v", bitrate,
                    "-pix_fmt", "yuv420p",
                    self.video_path
                ]
            else:
                ffmpeg_args = [
                    "ffmpeg",
                    "-f", "x11grab",
                    "-framerate", str(fps),
                    "-video_size", f"{monitor.width}x{monitor.height}",
                    "-i", f"{os.getenv('DISPLAY')}+{monitor.x},{monitor.y}",
                    "-f", "pulse",
                    "-i", audio_device,
                    "-filter:a", f"volume={volume/100}",
                    "-c:v", codec,
                    "-b:v", bitrate,
                    "-pix_fmt", "yuv420p",
                    self.video_path
                ]
            creationflags = 0 
        
        try:
            self.recording_process = subprocess.Popen(ffmpeg_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                                      stderr=subprocess.PIPE, universal_newlines=True, creationflags=creationflags)
        except Exception as e:
            messagebox.showerror(self.t("error"), self.t("error_start_recording").format(error=str(e)))
            self.status_label.config(text="Status: Error")
            return

        self.toggle_widgets(state=tk.DISABLED)
        self.status_label.config(text=self.t("status_recording"))

        self.start_timer()

        threading.Thread(target=self.read_ffmpeg_output, daemon=True).start()

    def read_ffmpeg_output(self):
        if self.recording_process:
            try:
                for stdout_line in iter(self.recording_process.stderr.readline, ""):
                    print(stdout_line)
            except Exception as e:
                print(f"Error reading ffmpeg output: {e}")
            finally:
                if self.recording_process and self.recording_process.stderr:
                    self.recording_process.stderr.close()

    def stop_recording(self):
        if self.recording_process:
            if os.name == 'nt':  # Windows
                self.recording_process.communicate(input='q')
            else: 
                try:
                    self.recording_process.terminate()
                    self.recording_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.recording_process.kill()
                finally:
                    if self.recording_process.stdin:
                        self.recording_process.stdin.close()
                    if self.recording_process.stdout:
                        self.recording_process.stdout.close()
                    if self.recording_process.stderr:
                        self.recording_process.stderr.close()
            
            self.recording_process.wait()
            self.recording_process = None

            self.toggle_widgets(state=tk.NORMAL)
            self.stop_timer()
            self.status_label.config(text=self.t("status_ready"))

            self.record_area = None

    def toggle_widgets(self, state):
        if state == tk.DISABLED:
            self.monitor_combo.config(state=state)
            self.fps_combo.config(state=state)
            self.bitrate_combo.config(state=state)
            self.codec_combo.config(state=state)
            self.format_combo.config(state=state)
            self.audio_combo.config(state=state)
            self.volume_scale.config(state=state)
            self.select_area_btn.config(state=state)
            self.language_combo.config(state=state)
            self.theme_combo.config(state=state)
        else:
            self.monitor_combo.config(state="readonly")
            self.fps_combo.config(state="readonly")
            self.bitrate_combo.config(state="readonly")
            self.codec_combo.config(state="readonly")
            self.format_combo.config(state="readonly")
            self.audio_combo.config(state="readonly")
            self.volume_scale.config(state=tk.NORMAL)
            self.select_area_btn.config(state=tk.NORMAL)
            self.language_combo.config(state="readonly")
            self.theme_combo.config(state="readonly")

        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if state == tk.DISABLED else tk.DISABLED)

    def open_output_folder(self):
        webbrowser.open(self.output_folder)

    def start_timer(self):
        self.running = True
        self.elapsed_time = 0
        self.update_timer()

    def stop_timer(self):
        self.running = False
        self.timer_label.config(text="00:00:00", foreground="white")

    def update_timer(self):
        if self.running:
            self.elapsed_time += 1
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(self.elapsed_time))
            self.timer_label.config(text=elapsed_time_str, foreground="red")
            self.root.after(1000, self.update_timer)

    def show_info(self):
        info_window = tk.Toplevel(self.root)
        info_window.title(self.t("about"))
        info_window.geometry("350x250")
        info_window.resizable(0, 0)

        text = self.t("version_info")
        
        ttk.Label(info_window, text=text, justify=tk.LEFT).pack(pady=10, padx=10)

    def change_language(self, event=None):
        selected_language = self.language_combo.get()
        if selected_language == 'English':
            self.language = 'en'
        elif selected_language == 'Español':
            self.language = 'es'
        elif selected_language == '中文(简体)':
            self.language = 'zh'
        elif selected_language == 'Italiano':
            self.language = 'it'
        elif selected_language == 'Français':
            self.language = 'fr'
        self.load_translation()
        self.save_config()
        self.reload_ui()

    def change_theme(self, event=None):
        theme = self.theme_combo.get().lower()
        self.set_theme(theme)
        self.save_config()

    def save_config(self, event=None):
        self.config['Settings'] = {
            'language': self.language,
            'theme': self.theme_combo.get().lower(),
            'monitor': self.monitor_combo.current(),
            'fps': self.fps_combo.current(),
            'bitrate': self.bitrate_combo.current(),
            'codec': self.codec_combo.current(),
            'format': self.format_combo.current(),
            'audio': self.audio_combo.current()
        }
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['Settings'] = {
                'language': 'en',
                'theme': 'dark',
                'monitor': 0,
                'fps': 1,
                'bitrate': 1,
                'codec': 0,
                'format': 0,
                'audio': 0
            }
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)

    def reload_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.init_ui()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenRecorderApp(root)
    root.mainloop()
