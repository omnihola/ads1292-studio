from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ads1292_studio.gui_specs import scrollbar_chrome_spec, scrollable_frame_spec


def _mousewheel_units(event: tk.Event) -> int:
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    delta = int(getattr(event, "delta", 0))
    if delta == 0:
        return 0
    return -1 if delta > 0 else 1


def _widget_exists(widget: tk.Widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def _unbind_mousewheel_events(widget: tk.Widget) -> None:
    for sequence in ScrollableFrame._mousewheel_events:
        try:
            widget.unbind_all(sequence)
        except tk.TclError:
            pass


class ScrollableFrame:
    _mousewheel_events = ("<MouseWheel>", "<Button-4>", "<Button-5>")
    _instances: list["ScrollableFrame"] = []
    _active_frame: "ScrollableFrame | None" = None
    _global_mousewheel_bound = False
    _global_mousewheel_widget: tk.Widget | None = None

    def __init__(self, parent: tk.Widget, width: int = 280) -> None:
        scrollbar_spec = scrollbar_chrome_spec()
        frame_spec = scrollable_frame_spec()
        self.frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(
            self.frame,
            width=width,
            bg=str(frame_spec["canvas_background"]),
            highlightthickness=int(frame_spec["highlightthickness"]),
            borderwidth=int(frame_spec["borderwidth"]),
            relief=str(frame_spec["relief"]),
        )
        self.scrollbar = ttk.Scrollbar(
            self.frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
            style=str(scrollbar_spec["vertical"]),
        )
        self.content = ttk.Frame(self.canvas, padding=int(frame_spec["content_padding"]))
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_content_width)
        self.canvas.bind("<Enter>", self._activate_mousewheel)
        self.content.bind("<Enter>", self._activate_mousewheel)
        self.canvas.bind("<Leave>", self._deactivate_mousewheel)
        self.frame.bind("<Destroy>", self._forget_instance, add="+")
        ScrollableFrame._instances.append(self)
        self._bind_global_mousewheel()

    def _bind_global_mousewheel(self) -> None:
        widget = ScrollableFrame._global_mousewheel_widget
        if ScrollableFrame._global_mousewheel_bound and widget is not None and _widget_exists(widget):
            return
        for sequence in ScrollableFrame._mousewheel_events:
            self.canvas.bind_all(sequence, self._dispatch_mousewheel)
        ScrollableFrame._global_mousewheel_bound = True
        ScrollableFrame._global_mousewheel_widget = self.canvas

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _activate_mousewheel(self, _event: tk.Event) -> None:
        ScrollableFrame._active_frame = self

    def _deactivate_mousewheel(self, event: tk.Event) -> None:
        if ScrollableFrame._active_frame is self and not self._contains_pointer(event):
            ScrollableFrame._active_frame = None

    def _forget_instance(self, event: tk.Event) -> None:
        if event.widget is not self.frame:
            return
        ScrollableFrame._instances = [instance for instance in ScrollableFrame._instances if instance is not self]
        if ScrollableFrame._active_frame is self:
            ScrollableFrame._active_frame = None
        if ScrollableFrame._global_mousewheel_widget is self.canvas:
            self._rebind_global_mousewheel()

    def _rebind_global_mousewheel(self) -> None:
        _unbind_mousewheel_events(self.canvas)
        ScrollableFrame._global_mousewheel_bound = False
        ScrollableFrame._global_mousewheel_widget = None
        if ScrollableFrame._instances:
            ScrollableFrame._instances[0]._bind_global_mousewheel()

    def _dispatch_mousewheel(self, event: tk.Event) -> None:
        target = self._mousewheel_target(event)
        if target is None:
            return
        target._scroll_mousewheel(event)

    def _mousewheel_target(self, event: tk.Event) -> "ScrollableFrame | None":
        active = ScrollableFrame._active_frame
        if active is not None and active._contains_pointer(event):
            return active
        return next((instance for instance in ScrollableFrame._instances if instance._contains_pointer(event)), None)

    def _scroll_mousewheel(self, event: tk.Event) -> None:
        units = _mousewheel_units(event)
        if units:
            self.canvas.yview_scroll(units, "units")

    def _contains_pointer(self, event: tk.Event) -> bool:
        x = int(getattr(event, "x_root", self.canvas.winfo_pointerx()))
        y = int(getattr(event, "y_root", self.canvas.winfo_pointery()))
        left = self.frame.winfo_rootx()
        top = self.frame.winfo_rooty()
        right = left + self.frame.winfo_width()
        bottom = top + self.frame.winfo_height()
        return left <= x <= right and top <= y <= bottom
