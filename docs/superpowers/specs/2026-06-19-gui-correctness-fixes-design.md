# ADS1292 Studio: GUI Correctness Fixes — Design

## Context

The user reported the GUI feels unreliable ("设计很垃圾，很多bugs"). The codebase is
not actually elementary — it has 41 prior TDD phases (session packaging, quality
gates, protocol segments, session indexing) and 97 passing tests — but a direct
read of `app.py`, `workers.py`, and `device.py` turned up concrete concurrency and
state-management bugs that would produce exactly that impression. Separately, the
user asked us to verify the codebase against the ADS1292R datasheet; that
investigation (see `findings.md`, "Datasheet Cross-Check") confirmed the existing
CH1=respiration/CH2=ECG channel assignment rather than overturning it, and is
otherwise unrelated to the bugs below.

## Problems (evidence-based, not speculative)

1. **`connect()` blocks the GUI thread** (`app.py:705-726`). Opens the serial
   port, queries firmware, reads a register — all synchronously on the Tk main
   thread, with up to a ~2s internal deadline. The window freezes on every
   Connect press.
2. **`LiveWorker.stop()` blocks the GUI thread and races itself** (`workers.py:26-34`).
   It calls `device.close()` from the caller's (GUI) thread while the worker
   thread may simultaneously be blocked inside a serial `read()` on that same
   device, then does `thread.join(timeout=1.0)` synchronously from the GUI
   thread — a freeze of up to a second, longer if the race causes the worker
   to hang instead of exiting cleanly.
3. **`start()` declares "Streaming" optimistically** (`app.py:728-752`).
   `is_streaming = True` and the toolbar text update happen unconditionally
   right after launching the worker thread, before anything confirms the
   device actually opened or started streaming. If it fails, the only signal
   is a buried Log-tab line; the GUI is left showing "Streaming" with a dead
   plot and Stop enabled, indefinitely.
4. **Offline CSV review only ever shows/scores the last 10 seconds of a
   recording** (`app.py:1209-1221`, `_show_recording`). It routes loaded
   samples through the same `maxlen=5000` (10s at 500Hz) deques used for live
   display. For a 75s baseline/motion/recovery protocol recording, the Review
   tab and its quality numbers only reflect the final ~10s; baseline and
   motion are invisible. This predates the now-committed background-CSV-load
   diff; that diff made the *displayed metrics* consistent with the truncated
   plot, but did not fix the truncation itself.

## Design

### Connect: move off the GUI thread

Mirror the `CsvLoadResult` pattern already used for CSV loading:

- Add a `ConnectResult` (`port`, `detail: str | None`, `error: str | None`) and
  an `App.connect_results: queue.Queue[ConnectResult]`.
- `connect()` starts a daemon thread that does the open/firmware-query/register-read
  and puts a `ConnectResult`; it returns immediately without touching widgets.
- `_tick()` drains `connect_results` (alongside the existing sample/log/CSV
  queues) and applies the result: set `connected_port`/`connection_var` on
  success, show `messagebox.showerror` on failure, then `_apply_control_states()`.
- While a connect is in flight, disable Connect/Start (new `connecting` flag on
  `GuiState`, same shape as `loading_csv`) so a second click can't overlap it.

### Stop: don't block, don't race

- `LiveWorker.stop()` only sets `stop_event` and returns immediately — no
  `device.close()` call from the caller's thread, no `thread.join()` on the
  GUI thread.
- The worker thread closes its own device when its read loop notices
  `stop_event` and exits (the existing `with Ads1x9xDevice(port) as device:`
  block's `__exit__` already does this on the worker thread).
- Reduce the device read timeout (`Ads1x9xDevice.timeout`, currently 1.0s) to
  something like 0.2s so the loop actually notices `stop_event` promptly
  instead of potentially blocking for a full second per check.
- `App.stop()` sets a "stopping" flag and returns; the worker's existing
  `"Stopped"` log message (already posted in `_run()`'s `finally` block) is
  the confirmation — `_tick()` flips `is_streaming = False` and refreshes
  control states only once that confirmation is drained, rather than assuming
  success synchronously.

### Start: don't declare success before it happens

- Reuse the same confirmation-via-queue idea: immediately after
  `device.start_stream()` succeeds inside `_run()` (before entering the
  sample loop), the worker puts an explicit `StreamStartResult(ok=True)` (or
  `ok=False, error=...` from the `except Exception` branch around the
  open/start sequence) onto a new `App.stream_start_results` queue.
  `is_streaming` only flips to `True` in the GUI, and the toolbar text only
  updates, once `_tick()` drains an `ok=True` result. On `ok=False`, show
  `messagebox.showerror` and leave `is_streaming = False`/controls re-enabled,
  consistent with how `connect()`/`load_csv()` already report failures. This
  does not depend on whether samples actually arrive afterward — it only
  confirms the device accepted the start command.

### Offline review: show the full recording

- `_show_recording()` builds plain `numpy` arrays sized to the *full* loaded
  recording instead of routing through the capped live-display deques.
- Decimate only what gets handed to the matplotlib line objects when the full
  series is much larger than is useful to render (live deques/rolling window
  stay exactly as they are for real-time streaming — that part is correct as
  is). Quality/HR/contact/PQRST metrics always run on the full, undecimated
  sample array, so the displayed numbers and the visible plot describe the
  same data regardless of render resolution.
- This supersedes the metrics-windowing part of the now-committed background-
  CSV-load diff (`compute_quality_metrics(display_samples, ...)`); the
  background-thread loading mechanism itself is unaffected and stays as is.

### Channel/lead labels — deferred, narrow follow-up

`ADS1292R_ECG_SOURCE`, `ADS1292R_CHANNEL_LABELS`, and `ADS1292R_PLOT_LAYOUT_LABELS`
stay exactly as they are today. The datasheet cross-check confirmed
CH1=respiration/CH2=ECG is correct; the only open question is which exact
Einthoven lead CH2 represents, pending the user's electrode-disconnect test.
If that test calls for a label change, it is a small, isolated edit to those
three constants plus README/findings prose — not part of this implementation
plan unless/until the test result is in.

### Explicitly out of scope

- Adding a register-write command to `device.py`/the firmware protocol (the
  app can currently only read registers). No evidence this is needed yet;
  YAGNI until a concrete reason appears.
- Restructuring `app.py` into multiple files. It is over this project's own
  800-line guideline (1427 lines), but splitting it is a separate, larger,
  higher-risk effort the user has not asked for. Revisit only if it starts
  blocking the fixes above.

## Testing

Follow this project's existing TDD convention exactly (write a failing test,
implement, then full suite + `py_compile` + `git diff --check`), matching all
42 prior phases. For the threading fixes, test the queue-draining and
state-transition logic as plain functions/objects decoupled from a real Tk
mainloop (the same approach `gui_control_states`/`GuiState` already use),
since this project already found driving a live Tk widget in pytest unstable
on macOS (`progress.md`, Phase 33).

## Verification

After implementation: full pytest suite, `py_compile`, `git diff --check`,
then a smoke test — CLI commands against a real saved CSV at minimum, and an
attempt to launch the actual GUI to confirm Connect/Start/Stop no longer
freeze the window (manual confirmation from the user if a live Tk window
can't be driven from this environment).
