# GUI Correctness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the concrete GUI-thread-blocking, race, optimistic-state, and
offline-review-windowing bugs found in `ads1292-studio` by extending the
background-thread-plus-result-queue pattern (already used for CSV loading) to
Connect and Start/Stop, and by making offline CSV review process the full
recording instead of a truncated 10-second tail.

**Architecture:** No new modules and no restructuring of existing module
boundaries. Each blocking operation (`connect`, `start`, `stop`) gets a small
typed result dataclass and a `queue.Queue`, mirroring the existing
`CsvLoadResult`/`csv_load_results` pair exactly. `_tick()` (already polled via
`self.after(50, self._tick)`) drains the new queues alongside the existing
ones. Offline review stops routing through the bounded live-display deques
and instead builds plain numpy arrays from the full loaded recording, only
decimating what is handed to matplotlib for rendering.

**Tech Stack:** Python 3, pytest, numpy, scipy, matplotlib, tkinter (existing
stack — no new dependencies).

---

### Task 1: Add `connecting`/`starting`/`busy` to `GuiState`

**Files:**
- Modify: `src/ads1292_studio/app.py:85-106` (`GuiState`, `_gui_state`)
- Modify: `src/ads1292_studio/app.py:153-340` (`gui_control_states`, `gui_workflow_hint`, `gui_status_cards`)
- Test: `tests/test_gui_control_state.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_gui_control_state.py`:

```python
def test_gui_state_busy_is_true_for_connecting_starting_or_loading() -> None:
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, starting=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, loading_csv=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False).busy is False


def test_gui_control_states_disable_everything_while_connecting() -> None:
    state = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)

    states = gui_control_states(state=state)

    assert states["Connect"] == "disabled"
    assert states["Start"] == "disabled"
    assert states["Load CSV"] == "disabled"


def test_gui_control_states_disable_everything_while_starting() -> None:
    state = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    states = gui_control_states(state=state)

    assert states["Start"] == "disabled"
    assert states["Stop"] == "disabled"
    assert states["Load CSV"] == "disabled"


def test_gui_workflow_hint_explains_connecting_and_starting() -> None:
    connecting = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    starting = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    assert "Connecting" in gui_workflow_hint(state=connecting)
    assert "Starting" in gui_workflow_hint(state=starting)


def test_gui_status_cards_show_connecting_and_starting_acquisition_values() -> None:
    connecting = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    starting = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    connecting_cards = {card.label: card.value for card in gui_status_cards(state=connecting)}
    starting_cards = {card.label: card.value for card in gui_status_cards(state=starting)}

    assert connecting_cards["Acquisition"] == "connecting"
    assert starting_cards["Acquisition"] == "starting stream"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_gui_control_state.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'connecting'` (or similar) for the new tests; existing tests in the file still pass.

- [ ] **Step 3: Implement `GuiState` and `_gui_state` changes**

In `src/ads1292_studio/app.py`, replace the `GuiState` dataclass and `_gui_state` helper:

```python
@dataclass(frozen=True)
class GuiState:
    connected: bool
    streaming: bool
    has_data: bool
    has_recording_path: bool
    loading_csv: bool = False
    connecting: bool = False
    starting: bool = False

    @property
    def busy(self) -> bool:
        return self.loading_csv or self.connecting or self.starting

    @property
    def package_ready(self) -> bool:
        return self.has_data and self.has_recording_path and not self.busy
```

```python
def _gui_state(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    loading_csv: bool = False,
    connecting: bool = False,
    starting: bool = False,
) -> GuiState:
    if state is not None:
        return state
    return GuiState(
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        loading_csv=loading_csv,
        connecting=connecting,
        starting=starting,
    )
```

- [ ] **Step 4: Implement `gui_control_states` change**

Replace the `if current.loading_csv:` branch in `gui_control_states` with:

```python
    if current.busy:
        return {
            "Refresh": tk.DISABLED,
            "Connect": tk.DISABLED,
            "Start": tk.DISABLED,
            "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
            "Load CSV": tk.DISABLED,
            "Export Report": tk.DISABLED,
            "Export Package": tk.DISABLED,
            "Verify Package": tk.DISABLED,
            "Batch Compare": tk.DISABLED,
            "Session Index": tk.DISABLED,
        }
```

Keep the rest of the function (the non-busy return dict) unchanged.

- [ ] **Step 5: Implement `gui_workflow_hint` change**

Replace the `if current.loading_csv:` line in `gui_workflow_hint` with:

```python
    if current.connecting:
        return "Connecting: probing the selected port."
    if current.starting:
        return "Starting stream: waiting for the device to confirm."
    if current.loading_csv:
        return "Loading CSV: keep the window open; review plots will update when parsing finishes."
```

- [ ] **Step 6: Implement `gui_status_cards` change**

Replace the existing `if current.loading_csv: ... elif current.streaming: ...` chain inside `gui_status_cards` with:

```python
    if current.connecting:
        acquisition_value = "connecting"
        acquisition_tone = "running"
    elif current.starting:
        acquisition_value = "starting stream"
        acquisition_tone = "running"
    elif current.loading_csv:
        acquisition_value = "loading CSV"
        acquisition_tone = "running"
    elif current.streaming:
        acquisition_value = "streaming"
        acquisition_tone = "running"
    elif current.connected:
        acquisition_value = "ready to start"
        acquisition_tone = "ready"
    else:
        acquisition_value = "idle"
        acquisition_tone = "neutral"
```

The `data = GuiStatusCard(...)` line right after stays unchanged — it already
keys off `current.loading_csv` only for the "Data" card, which is correct
(connecting/starting don't affect what's plotted).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_gui_control_state.py -v`
Expected: PASS, all tests including the 5 new ones.

- [ ] **Step 8: Run full suite and commit**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/app.py
git add src/ads1292_studio/app.py tests/test_gui_control_state.py
git commit -m "feat: add connecting and starting states to GuiState"
```

---

### Task 2: Non-blocking Connect

**Files:**
- Modify: `src/ads1292_studio/app.py:393-421` (`App.__init__`)
- Modify: `src/ads1292_studio/app.py:705-726` (`App.connect`)
- Modify: `src/ads1292_studio/app.py:1122-1139` (`App._tick`)
- Modify: `src/ads1292_studio/app.py:963-989` (`App._apply_control_states`)
- Test: `tests/test_workers.py` (new file, also used by Task 3/4)

- [ ] **Step 1: Write the failing test**

Create `tests/test_workers.py`:

```python
from __future__ import annotations

import queue

from ads1292_studio.app import ConnectResult


def test_connect_result_holds_success_detail() -> None:
    result = ConnectResult(port="/dev/fake", detail="firmware 1.0, ID 0x23")

    assert result.port == "/dev/fake"
    assert result.detail == "firmware 1.0, ID 0x23"
    assert result.error is None


def test_connect_result_holds_error() -> None:
    result = ConnectResult(port="/dev/fake", error="timed out")

    assert result.error == "timed out"
    assert result.detail is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_workers.py -v`
Expected: FAIL — `ImportError: cannot import name 'ConnectResult'`

- [ ] **Step 3: Add `ConnectResult` and the connect-results queue**

In `src/ads1292_studio/app.py`, add this dataclass next to `CsvLoadResult`:

```python
@dataclass(frozen=True)
class ConnectResult:
    port: str
    detail: str | None = None
    error: str | None = None
```

In `App.__init__`, after the existing `self.csv_load_results: queue.Queue[CsvLoadResult] = queue.Queue()` line, add:

```python
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
        self.is_connecting = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_workers.py -v`
Expected: PASS

- [ ] **Step 5: Rewrite `connect()` to run in a background thread**

Replace `App.connect()` entirely with:

```python
    def connect(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select an ADS1x9x serial port first.")
            return
        if self.is_connecting:
            self._log("Connect already in progress")
            return
        self.is_connecting = True
        self.connection_var.set("Connecting...")
        self._apply_control_states()
        threading.Thread(
            target=self._connect_in_background,
            args=(port,),
            daemon=True,
        ).start()

    def _connect_in_background(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
                try:
                    device_id = device.read_register(0x00)
                    detail = f"firmware {firmware}, ID 0x{device_id:02X}"
                except Exception:
                    detail = f"firmware {firmware}"
            self.connect_results.put(ConnectResult(port=port, detail=detail))
        except Exception as exc:
            self.connect_results.put(ConnectResult(port=port, error=str(exc)))

    def _drain_connect_results(self) -> None:
        while True:
            try:
                result = self.connect_results.get_nowait()
            except queue.Empty:
                return
            self._finish_connect(result)

    def _finish_connect(self, result: ConnectResult) -> None:
        self.is_connecting = False
        if result.error:
            self.connected_port = None
            self.connection_var.set("Connection failed")
            self._log(f"Connect failed for {result.port}: {result.error}")
            messagebox.showerror("Connection failed", result.error)
        else:
            self.connected_port = result.port
            self.connection_var.set(f"Connected: {result.detail}")
            self._log(f"Connected to {result.port}: {result.detail}")
        self._apply_control_states()
```

- [ ] **Step 6: Drain the new queue from `_tick()`**

In `App._tick()`, change the first line from `self._drain_csv_load_results()` to:

```python
        self._drain_csv_load_results()
        self._drain_connect_results()
```

- [ ] **Step 7: Pass `connecting` into the shared `GuiState` in `_apply_control_states`**

In `App._apply_control_states()`, add `connecting=self.is_connecting` to the `GuiState(...)` construction, e.g.:

```python
        state = GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
        )
```

- [ ] **Step 8: Run full suite, syntax check, commit**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/app.py
git add src/ads1292_studio/app.py tests/test_workers.py
git commit -m "fix: connect to ads1292 device on a background thread"
```

---

### Task 3: Non-blocking, non-racing Stop

**Files:**
- Modify: `src/ads1292_studio/device.py:80-92` (`Ads1x9xDevice.__init__`)
- Modify: `src/ads1292_studio/workers.py:20-34` (`LiveWorker.start`, `LiveWorker.stop`)
- Test: `tests/test_device_parser.py`
- Test: `tests/test_workers.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_device_parser.py`:

```python
def test_device_default_timeout_is_short_enough_to_notice_stop_promptly() -> None:
    from ads1292_studio.device import Ads1x9xDevice

    device = Ads1x9xDevice("fake-port")

    assert device.timeout == 0.2
```

Add to `tests/test_workers.py`:

```python
from ads1292_studio.workers import LiveWorker


def test_live_worker_stop_only_sets_event_without_closing_device() -> None:
    worker = LiveWorker(queue.Queue(), queue.Queue())

    class FakeDevice:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    fake_device = FakeDevice()
    worker.device = fake_device

    worker.stop()

    assert worker.stop_event.is_set()
    assert fake_device.close_calls == 0
```

This uses the current two-argument `LiveWorker(sample_queue, log_queue)`
constructor, which still exists at this point in the plan — the third
`start_result_queue` argument is added in Task 4. Task 4 Step 1 replaces this
exact test's constructor call with the three-argument form once that
argument exists; that is expected and not a regression.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_device_parser.py tests/test_workers.py -v`
Expected: FAIL — only the timeout test fails (default is still `1.0`); the
`LiveWorker.stop()` test fails on `assert fake_device.close_calls == 0`
because the current implementation still calls `self.device.close()` from
`stop()`.

- [ ] **Step 3: Shrink the default device read timeout**

In `src/ads1292_studio/device.py`, change `Ads1x9xDevice.__init__`'s
`timeout: float = 1.0` parameter default to `timeout: float = 0.2`.

- [ ] **Step 4: Make `LiveWorker.stop()` non-blocking and non-racing**

In `src/ads1292_studio/workers.py`, replace `LiveWorker.start()` and
`LiveWorker.stop()` with:

```python
    def start(self, port: str, csv_path: Path | None) -> None:
        self._stop_and_wait()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(port, csv_path), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _stop_and_wait(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
```

This removes the `self.device.close()` call from the caller's thread
entirely — the worker thread closes its own device when its `with
Ads1x9xDevice(port) as device:` block exits after the read loop notices
`stop_event`. The public `stop()` (called from `App.stop()`, i.e. the Stop
button) now only sets the event and returns immediately; the blocking join
only happens inside `start()`'s defensive `_stop_and_wait()` call, which only
matters for the rare case of a stale worker still finishing up from a
previous session (the GUI already disables Start while streaming, so this
should not trigger from normal button use).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_device_parser.py tests/test_workers.py -v`
Expected: PASS (the `LiveWorker(queue.Queue(), queue.Queue())` two-argument
call from Step 1 will start failing again once Task 4 changes the
constructor signature — that's expected and fixed in Task 4 Step 1, which
rewrites this exact test to pass three queues).

- [ ] **Step 6: Run full suite, syntax check, commit**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/device.py src/ads1292_studio/workers.py
git add src/ads1292_studio/device.py src/ads1292_studio/workers.py tests/test_device_parser.py tests/test_workers.py
git commit -m "fix: stop ads1292 streaming without blocking or racing the gui thread"
```

---

### Task 4: Background-confirmed Start

**Files:**
- Modify: `src/ads1292_studio/models.py` (add `StreamStartResult`)
- Modify: `src/ads1292_studio/workers.py:12-18,36-73` (`LiveWorker.__init__`, `LiveWorker._run`)
- Modify: `src/ads1292_studio/app.py:393-421` (`App.__init__`)
- Modify: `src/ads1292_studio/app.py:728-758` (`App.start`, `App.stop`)
- Modify: `src/ads1292_studio/app.py:1122-1139` (`App._tick`)
- Modify: `src/ads1292_studio/app.py:963-989` (`App._apply_control_states`)
- Test: `tests/test_workers.py`

- [ ] **Step 1: Write the failing tests**

Replace the `test_live_worker_stop_only_sets_event_without_closing_device`
test's worker construction (and the import block) at the top of
`tests/test_workers.py` so the whole file reads:

```python
from __future__ import annotations

import queue

from ads1292_studio.app import ConnectResult
from ads1292_studio.models import StreamSample, StreamStartResult
from ads1292_studio.workers import LiveWorker
import ads1292_studio.workers as workers


def test_connect_result_holds_success_detail() -> None:
    result = ConnectResult(port="/dev/fake", detail="firmware 1.0, ID 0x23")

    assert result.port == "/dev/fake"
    assert result.detail == "firmware 1.0, ID 0x23"
    assert result.error is None


def test_connect_result_holds_error() -> None:
    result = ConnectResult(port="/dev/fake", error="timed out")

    assert result.error == "timed out"
    assert result.detail is None


def test_live_worker_stop_only_sets_event_without_closing_device() -> None:
    worker = LiveWorker(queue.Queue(), queue.Queue(), queue.Queue())

    class FakeDevice:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    fake_device = FakeDevice()
    worker.device = fake_device

    worker.stop()

    assert worker.stop_event.is_set()
    assert fake_device.close_calls == 0


class _FakeStreamingDevice:
    def __init__(self, port: str) -> None:
        self.port = port

    def __enter__(self) -> "_FakeStreamingDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        return None

    def stop_stream(self) -> None:
        return None

    def iter_stream_samples(self):
        for index in range(3):
            yield StreamSample(
                timestamp=float(index),
                ch1=index,
                ch2=index,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )


class _FakeFailingDevice:
    def __init__(self, port: str) -> None:
        self.port = port

    def __enter__(self) -> "_FakeFailingDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        raise RuntimeError("device not responding")


def test_live_worker_posts_success_result_when_stream_starts(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _FakeStreamingDevice)
    sample_queue: queue.Queue = queue.Queue()
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(sample_queue, queue.Queue(), start_queue)

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    worker.stop()
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result == StreamStartResult(ok=True)


def test_live_worker_posts_failure_result_when_start_stream_raises(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _FakeFailingDevice)
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(queue.Queue(), queue.Queue(), start_queue)

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result.ok is False
    assert "device not responding" in (result.error or "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_workers.py -v`
Expected: FAIL — `ImportError: cannot import name 'StreamStartResult'`

- [ ] **Step 3: Add `StreamStartResult` to `models.py`**

In `src/ads1292_studio/models.py`, add after the `AdsPort` dataclass:

```python
@dataclass(frozen=True)
class StreamStartResult:
    ok: bool
    error: str | None = None
```

- [ ] **Step 4: Run tests to verify the import works (other failures remain)**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_workers.py -v`
Expected: FAIL — `TypeError: __init__() takes 3 positional arguments but 4 were given` for the `LiveWorker(..., start_queue)` calls, since `LiveWorker.__init__` does not yet accept a third argument.

- [ ] **Step 5: Update `LiveWorker.__init__` and `_run`**

In `src/ads1292_studio/workers.py`, replace the imports and `LiveWorker`
class with:

```python
from __future__ import annotations

from pathlib import Path
import queue
import threading

from ads1292_studio.csv_io import CsvRecorder
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.models import StreamSample, StreamStartResult


class LiveWorker:
    def __init__(
        self,
        sample_queue: queue.Queue[StreamSample],
        log_queue: queue.Queue[str],
        start_result_queue: queue.Queue[StreamStartResult],
    ) -> None:
        self.sample_queue = sample_queue
        self.log_queue = log_queue
        self.start_result_queue = start_result_queue
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.device: Ads1x9xDevice | None = None

    def start(self, port: str, csv_path: Path | None) -> None:
        self._stop_and_wait()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(port, csv_path), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _stop_and_wait(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run(self, port: str, csv_path: Path | None) -> None:
        recorder_cm = CsvRecorder(csv_path) if csv_path else None
        recorder = None
        started = False
        try:
            if recorder_cm:
                recorder = recorder_cm.__enter__()
                self.log_queue.put(f"Saving CSV: {csv_path}")
            with Ads1x9xDevice(port) as device:
                self.device = device
                try:
                    self.log_queue.put(f"Firmware: {device.query_firmware()}")
                except Exception as exc:
                    self.log_queue.put(f"Firmware query failed: {exc}")
                device.start_stream()
                started = True
                self.start_result_queue.put(StreamStartResult(ok=True))
                self.log_queue.put("Streaming started")
                for sample in device.iter_stream_samples():
                    if self.stop_event.is_set():
                        break
                    self.sample_queue.put(sample)
                    if recorder is not None:
                        recorder.write(sample)
                try:
                    device.stop_stream()
                except Exception as exc:
                    self.log_queue.put(f"Stop stream warning: {exc}")
        except Exception as exc:
            if not started:
                self.start_result_queue.put(StreamStartResult(ok=False, error=str(exc)))
            self.log_queue.put(f"ERROR: {exc}")
        finally:
            if recorder_cm:
                try:
                    recorder_cm.__exit__(None, None, None)
                    rows = recorder_cm.rows_written
                    self.log_queue.put(f"CSV closed: {csv_path} ({rows} samples)")
                except Exception as exc:
                    self.log_queue.put(f"CSV close error: {exc}")
            self.device = None
            self.log_queue.put("Stopped")
```

Note `Ads1x9xDevice` is still imported at module level (so
`monkeypatch.setattr(workers, "Ads1x9xDevice", ...)` in the tests works) —
`_run` references the module-level name, not a re-imported local one.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_workers.py -v`
Expected: PASS, all 6 tests.

- [ ] **Step 7: Wire `App` to construct `LiveWorker` with the new queue and consume `StreamStartResult`**

In `App.__init__`, change:

```python
        self.worker = LiveWorker(self.samples, self.logs)
```

to:

```python
        self.stream_start_results: queue.Queue[StreamStartResult] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)
        self.is_starting = False
```

Add `StreamStartResult` to the existing
`from ads1292_studio.models import Recording, StreamSample` import line so it
reads:

```python
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
```

- [ ] **Step 8: Rewrite `App.start()` and `App.stop()`**

Replace both methods with:

```python
    def start(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select a port and press Connect first.")
            return
        if self.connected_port != port:
            messagebox.showerror("Not connected", "Press Connect before Start.")
            return
        self._clear_buffers()
        self.recording_path = None
        csv_path = None
        if self.save_var.get():
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            csv_path = Path("recordings") / f"{stamp}-ads1292-studio.csv"
            self.recording_path = csv_path
            write_metadata_json(csv_path.with_suffix(".json"), self._metadata())
            write_events_json(self._events_path(csv_path), self.event_markers)
            write_calibration_json(self._calibration_path(csv_path), self._calibration())
            write_protocol_json(self._protocol_path(csv_path), self._protocol())
            write_quality_gate_json(self._quality_gate_path(csv_path), self._quality_gate())
            self.path_var.set(f"CSV: {csv_path}")
        self.is_starting = True
        self.connection_var.set("Starting stream...")
        self.worker.start(port, csv_path)
        self._apply_control_states()

    def stop(self) -> None:
        self.worker.stop()
        self.is_streaming = False
        self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
        self._apply_control_states()

    def _drain_stream_start_results(self) -> None:
        while True:
            try:
                result = self.stream_start_results.get_nowait()
            except queue.Empty:
                return
            self._finish_stream_start(result)

    def _finish_stream_start(self, result: StreamStartResult) -> None:
        self.is_starting = False
        if result.ok:
            self.is_streaming = True
            self.connection_var.set("Streaming")
        else:
            self.is_streaming = False
            self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
            messagebox.showerror("Start failed", result.error or "Unknown error starting stream")
        self._apply_control_states()
```

- [ ] **Step 9: Drain the new queue from `_tick()`**

In `App._tick()`, add a third drain call so the top of the method reads:

```python
        self._drain_csv_load_results()
        self._drain_connect_results()
        self._drain_stream_start_results()
```

- [ ] **Step 10: Pass `starting` into the shared `GuiState`**

In `App._apply_control_states()`, add `starting=self.is_starting` to the
`GuiState(...)` construction so it reads:

```python
        state = GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
            starting=self.is_starting,
        )
```

- [ ] **Step 11: Run full suite, syntax check, commit**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/workers.py src/ads1292_studio/models.py
git add src/ads1292_studio/app.py src/ads1292_studio/workers.py src/ads1292_studio/models.py tests/test_workers.py
git commit -m "fix: do not report streaming until the device confirms it started"
```

---

### Task 5: Full-recording offline review with decimated plotting

**Files:**
- Modify: `src/ads1292_studio/plots.py` (add `decimate_for_plot`)
- Modify: `src/ads1292_studio/app.py:295-299` (remove `offline_display_samples`)
- Modify: `src/ads1292_studio/app.py:1209-1265` (`App._show_recording`)
- Modify: `src/ads1292_studio/app.py:1284-1307` (`App._quality_text`, `App._redraw_live` call site)
- Test: `tests/test_plots.py` (new file)
- Test: `tests/test_gui_control_state.py` (remove the now-obsolete `offline_display_samples` test)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plots.py`:

```python
from __future__ import annotations

import numpy as np

from ads1292_studio.plots import decimate_for_plot


def test_decimate_for_plot_returns_unchanged_arrays_when_within_budget() -> None:
    x = np.arange(10)
    y = np.arange(10, dtype=float)

    out_x, out_y = decimate_for_plot(x, y, max_points=20)

    assert list(out_x) == list(x)
    assert list(out_y) == list(y)


def test_decimate_for_plot_decimates_large_arrays_to_budget() -> None:
    x = np.arange(1000)
    y = np.arange(1000, dtype=float)

    out_x, out_y = decimate_for_plot(x, y, max_points=100)

    assert 0 < out_x.size <= 100
    assert out_x.size == out_y.size
    assert list(out_x) == [int(value) for value in out_y]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_plots.py -v`
Expected: FAIL — `ImportError: cannot import name 'decimate_for_plot'`

- [ ] **Step 3: Implement `decimate_for_plot`**

In `src/ads1292_studio/plots.py`, add:

```python
def decimate_for_plot(x, y, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)
    if y_arr.size <= max_points:
        return x_arr, y_arr
    step = int(np.ceil(y_arr.size / max_points))
    return x_arr[::step], y_arr[::step]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest tests/test_plots.py -v`
Expected: PASS

- [ ] **Step 5: Remove the now-superseded `offline_display_samples` helper and its test**

In `src/ads1292_studio/app.py`, delete the `offline_display_samples` function
(currently right before `gui_signal_quality_cards`):

```python
def offline_display_samples(samples: tuple[StreamSample, ...], max_points: int = MAX_POINTS) -> tuple[StreamSample, ...]:
    if len(samples) <= max_points:
        return samples
    return samples[-max_points:]
```

In `tests/test_gui_control_state.py`, delete the
`test_offline_display_samples_use_recent_window_without_discarding_loaded_source`
test (it tests the function being removed).

- [ ] **Step 6: Add the `decimate_for_plot` import to `app.py`**

Change the import line `from ads1292_studio.plots import robust_ylim` to:

```python
from ads1292_studio.plots import decimate_for_plot, robust_ylim
```

- [ ] **Step 7: Give `_quality_text` an explicit `status_values` parameter**

Replace `App._quality_text` with:

```python
    def _quality_text(
        self,
        source: str,
        valid_rr: int,
        samples: tuple[StreamSample, ...],
        status_values: tuple[int, ...],
        metrics=None,
    ) -> str:
        protocol = self._protocol()
        should_evaluate_protocol = bool(self.loaded_samples) or protocol_ready_for_live_quality(
            samples,
            protocol,
            SAMPLE_RATE_HZ,
        )
        return build_quality_text(
            samples=samples,
            status_values=status_values,
            source=source,
            selected_source=ADS1292R_ECG_SOURCE,
            valid_rr=valid_rr,
            protocol=protocol if should_evaluate_protocol else None,
            sample_rate_hz=SAMPLE_RATE_HZ,
            gate=self._quality_gate(),
            metrics=metrics,
        )
```

In `App._redraw_live`, update the call site from
`self._quality_text(source, hr.valid_rr_count, samples, metrics=metrics)` to:

```python
        self.quality_var.set(self._quality_text(source, hr.valid_rr_count, samples, tuple(self.status), metrics=metrics))
```

(This is a one-line change — `_redraw_live` keeps using the live rolling
`self.status` deque, which is correct for the live path.)

- [ ] **Step 8: Rewrite `App._show_recording` to use the full recording**

Replace the entire method with:

```python
    def _show_recording(self, samples: tuple[StreamSample, ...]) -> None:
        self._clear_signal_buffers()
        self.sample_index = 0
        full_ch1 = np.asarray([sample.ch1 for sample in samples], dtype=float)
        full_ch2 = np.asarray([sample.ch2 for sample in samples], dtype=float)
        full_status_ints = tuple(sample.lead_off_bits for sample in samples)
        ecg = self._display_signal(full_ch2)
        resp = self._display_signal(full_ch1)
        source = ADS1292R_ECG_SOURCE
        result = review_channels(full_ch1, full_ch2, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        x = np.arange(ecg.size)
        status_arr = np.asarray(full_status_ints, dtype=float)
        plot_x, plot_ecg = decimate_for_plot(x, ecg, MAX_POINTS)
        _, plot_resp = decimate_for_plot(x, resp, MAX_POINTS)
        _, plot_status = decimate_for_plot(x, status_arr, MAX_POINTS)
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        self.review_ecg_line.set_data(plot_x, plot_ecg)
        self.review_resp_line.set_data(plot_x, plot_resp)
        self.review_status_line.set_data(plot_x, plot_status)
        self.review_peak_line.set_data(list(result.peaks), ecg[list(result.peaks)] if result.peaks else [])
        self.ax_review_ecg.set_title(
            f"Offline ECG: {ecg_label} | "
            f"HR {result.heart_rate.median_bpm:.1f} bpm | peaks {len(result.peaks)}"
        )
        self.ax_review_resp.set_title(resp_label)
        self.ax_review_status.set_title(contact_label)
        for ax, values in ((self.ax_review_ecg, ecg), (self.ax_review_resp, resp)):
            ax.set_xlim(0, max(1, x[-1] if x.size else 1))
            ax.set_ylim(*robust_ylim(values))
        self.ax_review_status.set_xlim(0, max(1, x[-1] if x.size else 1))
        self.ax_review_status.set_ylim(-0.5, max(1.0, float(status_arr.max()) + 0.5 if status_arr.size else 1.0))
        self.review_canvas.draw_idle()
        self._draw_pqrst(ecg, result.peaks)
        self.metrics_var.set(
            f"samples {len(samples)} | duration {len(samples) / SAMPLE_RATE_HZ:.1f} s | source {ecg_label}"
        )
        self.quality_var.set(
            f"{self._quality_text(source, result.heart_rate.valid_rr_count, samples, full_status_ints, metrics=metrics)} | "
            f"QRS {'clear' if result.pqrst.qrs_clear else 'unclear'} | "
            f"P {'tentative' if result.pqrst.p_tentative else 'not reliable'} | "
            f"T {'tentative' if result.pqrst.t_tentative else 'not reliable'}"
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
                quality_label=metrics.quality_label,
                ecg_source=metrics.ecg_source,
                contact_ok_percent=metrics.contact_ok_percent,
                lead_off_bad_samples=metrics.lead_off_bad_samples,
                r_peaks=metrics.r_peaks,
                hr_median_bpm=metrics.hr_median_bpm,
                baseline_drift_counts=metrics.baseline_drift_counts,
                noise_rms_counts=metrics.noise_rms_counts,
                peak_to_peak_counts=metrics.peak_to_peak_counts,
            )
        )
```

Note this method no longer calls `self._ads1292r_display_channels()` or
`self._append_sample()` — it builds `full_ch1`/`full_ch2`/`full_status_ints`
directly from the full `samples` tuple, so the Review tab and its quality
numbers always describe the entire loaded recording regardless of length;
only the matplotlib line data is decimated when very large.

- [ ] **Step 9: Run full suite to verify everything passes**

Run: `cd ads1292-studio && PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q`
Expected: PASS, no failures, no `offline_display_samples` references left.

- [ ] **Step 10: Syntax check and commit**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/plots.py
git add src/ads1292_studio/app.py src/ads1292_studio/plots.py tests/test_plots.py tests/test_gui_control_state.py
git commit -m "fix: review full recordings instead of only the last 10 seconds"
```

---

### Task 6: Docs, full verification, and smoke test

**Files:**
- Modify: `task_plan.md`, `progress.md`, `findings.md`

- [ ] **Step 1: Run the full verification sequence**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m py_compile src/ads1292_studio/*.py
git diff --check
```

Expected: all tests pass, no syntax errors, no whitespace errors.

- [ ] **Step 2: Run CLI smoke tests against a real saved CSV**

Use whatever real recording exists under `recordings/` or `../record/ads1292/`
(see `README.md` for the exact path used historically). Run:

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m ads1292_studio.cli review <path-to-a-real-csv>
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m ads1292_studio.cli qc <path-to-a-real-csv>
```

Expected: both commands print `ecg_source=CH2` and a quality label, exit 0
(or exit 2 only if the gate genuinely fails on that recording — compare
against the historical smoke results in `progress.md`).

- [ ] **Step 3: Attempt a real GUI launch**

```bash
cd ads1292-studio
PYTHONPATH=src /opt/homebrew/Caskroom/miniconda/base/envs/sensor/bin/python -m ads1292_studio
```

This opens a real Tk window — confirm it launches without an immediate
traceback, then close it. If the environment cannot display a GUI window,
note that explicitly and ask the user to manually verify Connect/Start/Stop
no longer freeze the window, instead of claiming this step passed without
having actually observed it.

- [ ] **Step 4: Update project docs**

Add a `### Phase 43: GUI Correctness Fixes` section to `progress.md` (after
the existing Phase 42 entry) summarizing the Connect/Stop/Start threading
fixes and the offline-review windowing fix, with the same file-list style as
prior phases. Add a matching `### Phase 43: GUI Correctness Fixes` checklist
to `task_plan.md` and update `## Current Phase` to `Phase 43`. Add a findings
row to `findings.md`'s "Technical Decisions" table for the offline-review
full-recording decision.

- [ ] **Step 5: Final commit and push**

```bash
cd ads1292-studio
git add task_plan.md progress.md findings.md
git commit -m "docs: log phase 43 gui correctness fixes"
git push origin main
```

---

## Self-Review Notes

- **Spec coverage:** Task 2 covers the Connect fix, Task 3+4 cover the
  Stop/Start fixes (split because Stop's fix is a pure deletion/simplification
  while Start's fix needs a new result type — keeping them separate keeps each
  task's diff focused), Task 5 covers the offline-review windowing fix, Task 1
  is the shared `GuiState` prerequisite all of them need, Task 6 covers the
  spec's verification requirements. The channel-label item is explicitly
  deferred in the spec itself and has no task here, matching that decision.
- **Type consistency checked:** `StreamStartResult` is defined once in
  `models.py` (Task 4) and used with the same field names (`ok`, `error`)
  everywhere it appears later in Task 4. `_quality_text`'s new
  `status_values` parameter (Task 5) is threaded through both of its call
  sites (`_redraw_live` and `_show_recording`) with matching types
  (`tuple[int, ...]`). `decimate_for_plot`'s signature (Task 5) is used
  identically at all three call sites inside `_show_recording`.
- **No placeholders:** every step above has complete, runnable code — no
  "add error handling" or "similar to Task N" shortcuts.
