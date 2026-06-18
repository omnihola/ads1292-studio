from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
import numpy as np

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.models import StreamSample
from ads1292_studio.plots import robust_ylim
from ads1292_studio.report import export_review_report
from ads1292_studio.signal_processing import (
    bandpass,
    choose_ecg_channel,
    detect_r_peaks,
    heart_rate_summary,
    pqrst_review,
    review_channels,
)
from ads1292_studio.workers import LiveWorker


MAX_POINTS = 5000
VISIBLE_SECONDS = 8.0
SAMPLE_RATE_HZ = 500.0


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ADS1292 Studio")
        self.geometry("1320x860")

        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs)
        self.connected_port: str | None = None
        self.recording_path: Path | None = None
        self.loaded_samples: tuple[StreamSample, ...] = tuple()

        self.sample_index = 0
        self.ch1: deque[float] = deque(maxlen=MAX_POINTS)
        self.ch2: deque[float] = deque(maxlen=MAX_POINTS)
        self.status: deque[int] = deque(maxlen=MAX_POINTS)
        self.indices: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_hr: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_rr: deque[int] = deque(maxlen=MAX_POINTS)

        self._build_ui()
        self.refresh_ports()
        self.after(50, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Port").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(toolbar, textvariable=self.port_var, width=34)
        self.port_combo.pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_ports).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Connect", command=self.connect).pack(side=tk.LEFT, padx=(12, 4))
        self.start_button = ttk.Button(toolbar, text="Start", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Stop", command=self.stop).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Load CSV", command=self.load_csv).pack(side=tk.LEFT, padx=(12, 4))
        ttk.Button(toolbar, text="Export Report", command=self.export_report).pack(side=tk.LEFT, padx=4)

        self.save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Save CSV", variable=self.save_var).pack(side=tk.LEFT, padx=8)
        self.autoscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto scale", variable=self.autoscale_var).pack(side=tk.LEFT, padx=4)
        self.filter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Filter", variable=self.filter_var).pack(side=tk.LEFT, padx=4)
        ttk.Label(toolbar, text="ECG source").pack(side=tk.LEFT, padx=(12, 2))
        self.source_var = tk.StringVar(value="Auto")
        ttk.Combobox(
            toolbar,
            textvariable=self.source_var,
            values=["Auto", "CH1", "CH2"],
            state="readonly",
            width=7,
        ).pack(side=tk.LEFT)

        self.connection_var = tk.StringVar(value="Not connected")
        ttk.Label(toolbar, textvariable=self.connection_var).pack(side=tk.RIGHT)

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        side = ttk.Frame(body, padding=10, width=260)
        body.add(side, weight=0)
        main = ttk.Frame(body)
        body.add(main, weight=1)

        self.metrics_var = tk.StringVar(value="No session")
        self.quality_var = tk.StringVar(value="Quality: --")
        self.path_var = tk.StringVar(value="CSV: --")
        for label, var in (
            ("Session", self.metrics_var),
            ("Quality", self.quality_var),
            ("Storage", self.path_var),
        ):
            ttk.Label(side, text=label, font=("", 12, "bold")).pack(anchor=tk.W, pady=(8, 2))
            ttk.Label(side, textvariable=var, wraplength=230, justify=tk.LEFT).pack(anchor=tk.W)

        ttk.Label(side, text="Notes", font=("", 12, "bold")).pack(anchor=tk.W, pady=(14, 2))
        ttk.Label(
            side,
            text="Research use only. Use battery power for body-contact testing.",
            wraplength=230,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.live_tab = ttk.Frame(self.notebook)
        self.review_tab = ttk.Frame(self.notebook)
        self.pqrst_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.live_tab, text="Live")
        self.notebook.add(self.review_tab, text="Review")
        self.notebook.add(self.pqrst_tab, text="PQRST")
        self.notebook.add(self.log_tab, text="Log")

        self._build_live_plot()
        self._build_review_plot()
        self._build_pqrst_plot()
        self.log_text = tk.Text(self.log_tab, height=12)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_live_plot(self) -> None:
        fig = Figure(figsize=(10, 7), dpi=100)
        self.ax_live_ecg = fig.add_subplot(311)
        self.ax_live_other = fig.add_subplot(312, sharex=self.ax_live_ecg)
        self.ax_live_status = fig.add_subplot(313, sharex=self.ax_live_ecg)
        self.ax_live_status.set_xlabel("Time (s)")
        self.live_ecg_line, = self.ax_live_ecg.plot([], [], lw=1.0)
        self.live_peak_line, = self.ax_live_ecg.plot([], [], "r.", ms=5)
        self.live_other_line, = self.ax_live_other.plot([], [], lw=0.8)
        self.live_status_line, = self.ax_live_status.plot([], [], lw=0.8, drawstyle="steps-post")
        self.live_canvas = FigureCanvasTkAgg(fig, master=self.live_tab)
        self.live_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_review_plot(self) -> None:
        fig = Figure(figsize=(10, 7), dpi=100)
        self.ax_review_ecg = fig.add_subplot(211)
        self.ax_review_other = fig.add_subplot(212, sharex=self.ax_review_ecg)
        self.ax_review_other.set_xlabel("Samples")
        self.review_ecg_line, = self.ax_review_ecg.plot([], [], lw=0.9)
        self.review_peak_line, = self.ax_review_ecg.plot([], [], "r.", ms=5)
        self.review_other_line, = self.ax_review_other.plot([], [], lw=0.8)
        self.review_canvas = FigureCanvasTkAgg(fig, master=self.review_tab)
        self.review_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_pqrst_plot(self) -> None:
        fig = Figure(figsize=(10, 6), dpi=100)
        self.ax_pqrst = fig.add_subplot(111)
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        self.pqrst_canvas = FigureCanvasTkAgg(fig, master=self.pqrst_tab)
        self.pqrst_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def refresh_ports(self) -> None:
        ports = list_ads_ports()
        values = [port.device for port in ports]
        if not values:
            guess = find_ads_port()
            values = [guess] if guess else []
        self.port_combo["values"] = values
        if values and not self.port_var.get():
            self.port_var.set(values[0])
        if not values:
            self.connection_var.set("No ADS1x9x port")

    def connect(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select an ADS1x9x serial port first.")
            return
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
                try:
                    device_id = device.read_register(0x00)
                    detail = f"firmware {firmware}, ID 0x{device_id:02X}"
                except Exception:
                    detail = f"firmware {firmware}"
            self.connected_port = port
            self.connection_var.set(f"Connected: {detail}")
            self._log(f"Connected to {port}: {detail}")
        except Exception as exc:
            self.connected_port = None
            self.connection_var.set("Connection failed")
            messagebox.showerror("Connection failed", str(exc))

    def start(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select a port and press Connect first.")
            return
        if self.connected_port != port:
            messagebox.showerror("Not connected", "Press Connect before Start.")
            return
        self._clear_buffers()
        csv_path = None
        if self.save_var.get():
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            csv_path = Path("recordings") / f"{stamp}-ads1292-studio.csv"
            self.recording_path = csv_path
            self.path_var.set(f"CSV: {csv_path}")
        self.worker.start(port, csv_path)
        self.start_button.configure(state=tk.DISABLED)
        self.connection_var.set("Streaming")

    def stop(self) -> None:
        self.worker.stop()
        self.start_button.configure(state=tk.NORMAL)
        self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Load ADS1292 CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            recording = read_recording_csv(Path(path))
            self.loaded_samples = recording.samples
            self._show_recording(recording.samples)
            self.path_var.set(f"CSV: {path}")
            self._log(f"Loaded {path}")
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))

    def export_report(self) -> None:
        if self.loaded_samples:
            samples = self.loaded_samples
        elif self.ch1 and self.ch2:
            samples = tuple(
                StreamSample(
                    timestamp=index / SAMPLE_RATE_HZ,
                    ch1=int(ch1),
                    ch2=int(ch2),
                    board_heart_rate=0,
                    board_respiration_rate=0,
                    status_byte=int(status),
                )
                for index, (ch1, ch2, status) in enumerate(zip(self.ch1, self.ch2, self.status))
            )
        else:
            messagebox.showerror("No data", "Load a CSV or record data before exporting a report.")
            return
        out_dir = filedialog.askdirectory(title="Choose report output folder")
        if not out_dir:
            return
        try:
            export = export_review_report(
                samples=samples,
                out_dir=Path(out_dir),
                title="ADS1292 Studio Review",
                sample_rate_hz=SAMPLE_RATE_HZ,
                source=self.source_var.get(),
            )
            self._log(f"Exported report: {export.html_path}")
            messagebox.showinfo("Report exported", f"Saved report:\n{export.html_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _clear_buffers(self) -> None:
        self.sample_index = 0
        self.loaded_samples = tuple()
        for buffer in (self.ch1, self.ch2, self.status, self.indices, self.board_hr, self.board_rr):
            buffer.clear()

    def _tick(self) -> None:
        latest = None
        while True:
            try:
                latest = self.samples.get_nowait()
            except queue.Empty:
                break
            self._append_sample(latest)
        if latest is not None:
            self._redraw_live()
        while True:
            try:
                self._log(self.logs.get_nowait())
            except queue.Empty:
                break
        self.after(50, self._tick)

    def _append_sample(self, sample: StreamSample) -> None:
        self.indices.append(self.sample_index)
        self.sample_index += 1
        self.ch1.append(sample.ch1)
        self.ch2.append(sample.ch2)
        self.status.append(sample.lead_off_bits)
        self.board_hr.append(sample.board_heart_rate)
        self.board_rr.append(sample.board_respiration_rate)

    def _selected_channels(self) -> tuple[str, np.ndarray, np.ndarray]:
        ch1 = np.asarray(self.ch1, dtype=float)
        ch2 = np.asarray(self.ch2, dtype=float)
        choice = choose_ecg_channel(ch1, ch2, SAMPLE_RATE_HZ, self.source_var.get())
        if choice.channel == "CH2":
            return "CH2", ch2, ch1
        return "CH1", ch1, ch2

    def _display_signal(self, values: np.ndarray) -> np.ndarray:
        if not self.filter_var.get():
            return values
        return bandpass(values, SAMPLE_RATE_HZ)

    def _redraw_live(self) -> None:
        if not self.indices:
            return
        source, ecg_raw, other_raw = self._selected_channels()
        ecg = self._display_signal(ecg_raw)
        other = self._display_signal(other_raw)
        x = np.asarray(self.indices, dtype=float) / SAMPLE_RATE_HZ
        left = max(0.0, x[-1] - VISIBLE_SECONDS)
        right = max(VISIBLE_SECONDS, x[-1])
        visible = (x >= left) & (x <= right)
        peaks = detect_r_peaks(ecg[visible], SAMPLE_RATE_HZ)
        peaks_x = x[visible][list(peaks)] if peaks else []
        peaks_y = ecg[visible][list(peaks)] if peaks else []

        self.live_ecg_line.set_data(x, ecg)
        self.live_peak_line.set_data(peaks_x, peaks_y)
        self.live_other_line.set_data(x, other)
        self.live_status_line.set_data(x, list(self.status))
        for ax in (self.ax_live_ecg, self.ax_live_other, self.ax_live_status):
            ax.set_xlim(left, right)
        if self.autoscale_var.get():
            self.ax_live_ecg.set_ylim(*robust_ylim(ecg[visible]))
            self.ax_live_other.set_ylim(*robust_ylim(other[visible]))
            self.ax_live_status.set_ylim(-0.5, max(1.0, max(self.status or [0]) + 0.5))
        hr = heart_rate_summary(peaks, SAMPLE_RATE_HZ)
        self.ax_live_ecg.set_title(f"ECG display: {source} | R peaks {len(peaks)}")
        self.ax_live_other.set_title("Other channel")
        self.ax_live_status.set_title("Lead-off bits")
        self.metrics_var.set(
            f"samples {self.sample_index} | duration {x[-1]:.1f} s | source {source} | HR {hr.median_bpm:.0f} bpm"
        )
        self.quality_var.set(self._quality_text(source, hr.valid_rr_count))
        self.live_canvas.draw_idle()

    def _show_recording(self, samples: tuple[StreamSample, ...]) -> None:
        self._clear_buffers()
        for sample in samples:
            self._append_sample(sample)
        source, ecg_raw, other_raw = self._selected_channels()
        ecg = self._display_signal(ecg_raw)
        other = self._display_signal(other_raw)
        raw_ch1 = np.asarray(self.ch1, dtype=float)
        raw_ch2 = np.asarray(self.ch2, dtype=float)
        result = review_channels(raw_ch1, raw_ch2, SAMPLE_RATE_HZ, self.source_var.get())
        x = np.arange(ecg.size)
        self.review_ecg_line.set_data(x, ecg)
        self.review_other_line.set_data(x, other)
        self.review_peak_line.set_data(list(result.peaks), ecg[list(result.peaks)] if result.peaks else [])
        self.ax_review_ecg.set_title(
            f"Offline ECG: {source} | HR {result.heart_rate.median_bpm:.1f} bpm | peaks {len(result.peaks)}"
        )
        self.ax_review_other.set_title("Other channel")
        for ax, values in ((self.ax_review_ecg, ecg), (self.ax_review_other, other)):
            ax.set_xlim(0, max(1, x[-1] if x.size else 1))
            ax.set_ylim(*robust_ylim(values))
        self.review_canvas.draw_idle()
        self._draw_pqrst(ecg, result.peaks)
        self.metrics_var.set(
            f"samples {len(samples)} | duration {len(samples) / SAMPLE_RATE_HZ:.1f} s | source {source}"
        )
        self.quality_var.set(
            f"QRS {'clear' if result.pqrst.qrs_clear else 'unclear'} | "
            f"P {'tentative' if result.pqrst.p_tentative else 'not reliable'} | "
            f"T {'tentative' if result.pqrst.t_tentative else 'not reliable'}"
        )

    def _draw_pqrst(self, ecg: np.ndarray, peaks: tuple[int, ...]) -> None:
        review = pqrst_review(ecg, peaks, SAMPLE_RATE_HZ)
        self.ax_pqrst.clear()
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        if review.average_beat:
            self.ax_pqrst.plot(review.time_ms, review.average_beat, lw=2.0, label="average beat")
            self.ax_pqrst.axvline(0, color="r", linestyle="--", lw=1, label="R")
            self.ax_pqrst.axvspan(-220, -80, color="green", alpha=0.08, label="P search")
            self.ax_pqrst.axvspan(120, 380, color="orange", alpha=0.08, label="T search")
            self.ax_pqrst.legend(loc="upper right")
        self.ax_pqrst.set_title(
            f"PQRST review: QRS={review.qrs_clear}, P tentative={review.p_tentative}, "
            f"T tentative={review.t_tentative}, beats={review.beats_used}"
        )
        self.ax_pqrst.grid(True, alpha=0.25)
        self.pqrst_canvas.draw_idle()

    def _quality_text(self, source: str, valid_rr: int) -> str:
        lead_bad = sum(1 for value in self.status if value != 0)
        contact = "OK" if lead_bad == 0 else f"{lead_bad} bad samples"
        rhythm = "detecting" if valid_rr < 2 else "R peaks detected"
        return f"Contact {contact} | {rhythm} | source {source}"

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n")
        self.log_text.see(tk.END)

    def _close(self) -> None:
        self.stop()
        self.destroy()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
