# ADS1292 Studio — C++/Qt 完整移植设计

- 日期: 2026-06-24
- 状态: Draft accepted for review; implementation starts only after P-1 fixture spec is frozen
  （草案已接受评审；仅在 P-1 fixture spec 冻结后才开始写 C++）
- 性质: **完整重写**（不是 GUI 优化），目标是功能零缺失地把现有 Python 应用移植为原生 C++/Qt 应用

## 1. 目标与非目标

### 目标
- 把现有 ~17,585 行 Python / 70+ 模块的 ECG 采集·记录·复盘应用完整移植为 C++/Qt。
- 产出**独立原生二进制**（不依赖 Python/conda）。
- 满足三个动机：原生二进制分发、实时性能、嵌入式可移植。
- **现有任何功能都不能缺失**——以语义级兼容与对拍测试作为硬约束保证。
- 黑色主题 GUI（Qt Widgets + QSS）。

### 非目标
- 不移植遗留 Tk GUI（`app.py` 及相关）。
- 不移植 Python 专属运行时垫片（`matplotlib_runtime.py`、`macos_stderr.py`）。
- 不在本次引入新算法替换现有算法（Pan-Tompkins 等仅作后续显式 opt-in v2）。
- 不追求文件字节级一致（见兼容性契约）。
- 目标平台当前仅 macOS（Apple Silicon）；core 层保持可移植以备将来嵌入式，但本次不交付嵌入式构建。

## 2. 架构（分层，核心可移植）

```
ads1292-cpp/
├── core/         纯 C++17，零 Qt / 零系统 API。可单元测试、可嵌入式移植
│   ├── device/   ADS1x9x 帧解析、协议常量          ← device.py protocol.py
│   ├── model/    Sample / RawSample / StreamSample / ReviewResult / EventMarker
│   │                                               ← models.py events.py
│   ├── dsp/      butter/iirnotch 系数、filtfilt 零相位、find_peaks、HR、PQRST、
│   │             KissFFT 频谱、质量/SNR、lead-off、校准
│   │             ← signal_processing.py quality.py spectrum.py lead_off.py calibration.py
│   └── analysis/ 质量门控、分段、会话索引、批处理、报告数据模型
│                 ← quality_gate.py segments.py session_index.py batch.py report.py(数据部分)
├── io/           HDF5 / CSV / XLSX / hash / 磁盘空间（允许第三方库）
│                 ← csv_io.py h5_io.py h5_export.py xlsx_io.py recording_*.py hashing.py disk_space.py
├── qt_runtime/   QSerialPort / QThread / QSettings / 文件对话框 / 端口发现
│                 ← workers.py(串口部分) device.py(端口发现) preferences
├── gui/          Qt Widgets 黑色主题
│   ├── 主窗口 / 标签页 / 状态面板 / 侧栏表单 / 偏好对话框
│   │             ← ui_qt/main_window.py status_panel.py sidebar_forms.py preferences.py 等
│   ├── LiveScope（IWaveformPlot 接口 → QCustomPlot 后端）   ← ui_qt/live_scope.py
│   ├── 事件控制台 + SNR 条                                   ← ui_qt/event_console.py
│   └── 离线渲染（QPainter/QtCharts→PNG, QSvg）              ← plots.py review_render.py live_render.py
├── cli/          命令行工具，链接 core + io（支持无 GUI 采集）  ← cli.py
├── third_party/  kissfft / qcustomplot / qxlsx（vendored 单文件/小库）
└── tests/        Catch2 单元测试 + 黄金对拍资产
```

**分层依赖规则**：`gui → qt_runtime → io → core`，`cli → io → core`。core 不依赖任何上层。io 可依赖第三方库但不依赖 Qt（HDF5/XLSX 例外评估见下）。

> 注：XLSX 选用 QXlsx（依赖 QtGui/QtCore），因此 XLSX 写出归入 `qt_runtime/` 或独立 `io_qt/`，而非纯 `io/`。CSV/HDF5/hash 留在纯 `io/`。这样无 Qt 的 CLI 仍可做 CSV/HDF5，只有 XLSX 需要 Qt——与现有 Python 一致（XLSX 是次要导出格式）。

## 3. 技术栈选型（已确认）

| 关注点 | 选择 | 理由 |
|---|---|---|
| GUI 框架 | Qt Widgets (Qt 6.11.1, Homebrew) | 匹配现有 Widgets 风格；仪器类桌面首选；QSS 黑主题简单 |
| 实时绘图 | QCustomPlot（**临时后端**，经 `IWaveformPlot` 抽象） | 功能最接近 pyqtgraph；QPainter 光栅渲染（**非** GPU/VBO）。仅用于内部评估；外部分发前须完成许可证审查 |
| DSP | 手写 + KissFFT | 最少依赖、嵌入式可移植；filtfilt/find_peaks 须黄金对拍 |
| 串口 | QSerialPort (qtserialport 已装) | Qt 原生 |
| 并发 | QThread | Qt 原生，匹配现有 worker 模型 |
| HDF5 | HDF5 官方 C API（薄 RAII 封装；`brew install hdf5`） | 数据格式必须兼容现有文件 |
| XLSX | QXlsx（vendored） | Qt 原生、轻量 |
| 构建 | CMake（可选 Ninja） | 多目标、跨平台基础 |
| 测试 | Catch2 | 头文件库，易 vendored |

### 绘图后端抽象（GPL 保险）
定义 `IWaveformPlot` 接口（`appendSamples / setTimeWindow / setYRange / setAutoscale / overlayEvents / setPaperSpeed / clear`）。GUI 只依赖接口。**QCustomPlot 仅作临时后端用于内部评估，不是默认长期路线**；任何外部分发前必须完成许可证审查，必要时切换 QtCharts / 自绘后端——届时只改此抽象层，不动 GUI。若将来设备连同软件交付外部即构成 GPL 意义上的分发，GPL 义务会被激活。

## 4. 兼容性契约（防止功能丢失的硬约束）

| 格式 | 兼容级别 | 不要求 |
|---|---|---|
| CSV (live/raw) | 列顺序 + 列名 + 数值格式化兼容（接近文本级） | — |
| HDF5 | schema + datasets + attrs + per-array hashes 兼容 | 字节一致（chunk/压缩/属性顺序/库版本可不同） |
| XLSX | sheet 名 + 单元格值兼容 | 字节一致（zip 内时间戳/XML 顺序/rel id 可不同） |
| DSP 输出 | 数值容差兼容（filtfilt/find_peaks/FFT/质量指标逐项对拍） | 浮点 bit 一致 |
| 报告 (HTML/PNG) | 内容/回归快照兼容 | 像素级一致（除非必要） |

**关键实现风险点**：
- `scipy.signal.filtfilt` 默认 `padtype='odd'`、`padlen=3*max(len(a),len(b))`、用 `lfilter_zi` 设初始条件。短 ECG 窗口边界效应显著，必须逐样本对拍，不能凭"原理等价"。
- `scipy.signal.butter(2, ...)` 与 `iirnotch(w0, Q)` 的系数生成需复刻（双线性变换 + 预畸变），系数级对拍。
- R 波检测是 `scipy.signal.find_peaks`（配 `butter(2)` 带通预滤波），**非 Pan-Tompkins**。须 1:1 port find_peaks 的 distance/height/prominence 语义。

## 5. 对拍黄金测试策略

参考实现（`sensor` conda 环境）可运行，用它冻结"黄金输出"作为测试资产。C++ 实现对相同输入须在容差内匹配。现有 **697 个 Python 测试**逐个评估翻译为 Catch2（工作量大，是本项目主要成本之一）。

## 6. 阶段计划（每阶段可独立运行验证）

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| **P-1** | Golden fixtures + compatibility spec（**先于任何 C++**） | 见 §6.1 资产清单全部冻结入库 |
| **P0** | CMake skeleton（core/io/qt_runtime/gui/cli 五目标）+ Catch2 + CI + 空 Qt 黑窗口 | 编译通过；弹出黑色主窗口；CI 跑空测试套件绿 |
| **P1** | core/model + device parser + event model | parse_stream_payload / parse_acquire_payload / 序列化(JSON·CSV) / lead-off bits / malformed·timeout·bad-trailer 全部对拍 Python |
| **P2** | CSV(live/raw) + HDF5 + recording_bundle 读写兼容（不丢数据优先） | C++ 写文件可被 Python 读、Python 文件可被 C++ 读；schema/datasets/attrs/hashes 对拍；**bundle 往返**：metadata / events / calibration / acquisition / protocol / quality_gate / processing 七类语义往返一致 |
| **P3** | 采集 worker：先 simulator（确定性样本流），后真实 QSerialPort | simulator 流→样本入队→CSV journal 落盘；真实板连通后 live/raw 两模式采集 |
| **P4** | Live GUI：status 面板 + event console + waveform（**仅原始波形**，无 SNR） | 连 simulator/真板→实时波形可见→录制 CSV→事件标注 |
| **P5** | DSP：filters / R peaks / HR / **lightweight 实时 SNR 条** / spectrum / PQRST（含显示滤波回填 P4） | 全部数值对拍 Python；SNR 条 + HP/Notch/LP/QRS 显示滤波接入 Live GUI |
| **P6** | Review tabs + Info + Event Log + 事件叠加 | 加载 CSV/HDF5 记录→复盘/PQRST/频谱/Info 标签页对拍 review fixture |
| **P7** | package / index / batch / report / CLI parity | CLI 各命令行为与 Python 对齐；报告内容回归快照兼容 |
| **P8** | 原生分发打包：macOS `.app` bundle / `macdeployqt` / codesign / notarization / `.dmg` 或 Homebrew | 双击即用的独立 app；GPL 许可证审查在此阶段前完成（决定绘图后端去留） |

**P4/P5 依赖说明**：Live GUI 显示滤波（HP/Notch/LP/QRS）是因果实时 IIR，lightweight SNR 是窗口 RMS 派生指标，二者都依赖 DSP 且都需对拍 Python。因此 P4 只保证**原始波形 + status + 事件标注**可见；SNR 条与所有显示滤波统一在 P5 落地、对拍后回填 P4 界面。这样所有数值对拍工作集中在 P5，P4 不出现任何先于其对拍基准的 DSP 计算。

**首个正式实现范围 = P-1 + P0 + P1。** 之后每阶段各自走 spec→plan→实现循环。

### 6.1 P-1 黄金资产清单（须冻结）
- stream frame parser fixtures（含正常帧）
- raw acquire frame fixtures
- live CSV fixture
- raw CSV fixture
- HDF5 fixture
- XLSX semantic fixture（sheet 名 + 单元格值）
- ECG review fixture
- R peak / HR / SNR / spectrum golden output
- known bad frames / timeout / bad trailer 边界用例
- filtfilt / butter / iirnotch 系数与滤波输出 golden（含短窗口边界）

**每批 fixture 必须附带 oracle 溯源 manifest（`oracle.json`），冻结 Python 参考版本：**
- `oracle_repo_commit`（生成 fixture 时 Python 仓库的 commit hash）
- `python_version`
- `numpy_version` / `scipy_version` / `h5py_version`（以及 openpyxl/PySide6 如涉及）
- `sample_rate_hz`
- `fixture_generation_command`（可复现的生成命令）
- `platform`（OS / arch）

无溯源 manifest 的 fixture 不得入库。Python oracle 后续若变更，须重新生成 fixture 并更新 manifest，C++ 对拍永远指向已冻结的版本。

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| filtfilt 边界行为难复刻 | P-1 冻结短窗口 golden；P5 逐样本对拍，必要时实现 scipy 同款 padding |
| find_peaks 语义偏差 | port distance/height/prominence/plateau 完整语义；review fixture 对拍峰索引 |
| HDF5 库版本/属性顺序差异 | 兼容契约定为 schema+attrs+hash 级，不追字节一致 |
| 697 测试翻译量大 | 按阶段翻译，仅翻译对应阶段模块的测试；硬件相关测试用 simulator |
| QCustomPlot GPL（未来分发） | IWaveformPlot 抽象层隔离，后端可换 |
| 嵌入式移植未来需求 | core/io(非XLSX) 严守零 Qt；qt_runtime/gui 可整体替换 |

## 8. 开放项（实现期细化，不阻塞批准）
- HDF5 RAII 封装是否独立成 `io/h5/` 子库。
- Catch2 vs GoogleTest 最终定（暂定 Catch2，头文件库更易 vendored）。
- CI 形态（本地 pre-commit 脚本 vs GitHub Actions）。
- report 的 PNG 渲染用 QtCharts 还是纯 QPainter（P7 再定）。
- P8 打包：codesign/notarization 需 Apple Developer 账号与签名身份（外部依赖，需提前确认是否具备；仅内部不分发则可跳过签名）。
- 绘图后端长期路线：QCustomPlot 仅临时；P8 分发审查前须决定是否切换 QtCharts/自绘以规避 GPL。
