# 原生 AC/TRAN 执行器

入口：[run_multisim_native.py](../scripts/run_multisim_native.py)，宿主源码：[NativeSolve.cs](../scripts/NativeSolve.cs)。用于已生成并核对拓扑的工程；不生成电路，不决定课程参数，也不把进程退出成功判为物理验收通过。

依赖 Windows、可用的 Multisim COM、Python 3 和 x86 .NET Framework C# 编译器。Python 只需标准库，位数不限；COM 在 x86 STA 宿主运行。编译器从 `WINDIR` 定位，可用 `--compiler` 指定。无需安装 pywin32/MCP，不修改 COM 注册。编译输出位于本轮结果的 `_host/`。

## 输入契约

任务级构建器写入 JSON 清单。文件路径相对清单目录解析，也接受绝对路径。以下为字段说明，数值必须从本次任务确定：

| 字段 | 类型/含义 |
|---|---|
| `analysis.frequency_hz` | 正数，单频 AC 分析频率 |
| `analysis.duration_s` | 正数，瞬态总时长 |
| `analysis.sample_rate_hz` | 正数，输出请求采样率 |
| `analysis.sample_count` | 正整数，输出请求点数 |
| `analysis.output_timeout_s` | 正数，每个输出的限时等待 |
| `outputs` | 可省略以读取所有枚举输出；指定时是实际输出名的非空、不重复字符串数组 |
| `cases` | 非空工况数组 |
| `cases[].name` | 唯一目录名，字母/数字开头，后续可含下划线和短横线；不能是 Windows 保留名 |
| `cases[].binary` | 输入工程路径，须已生成且经过结构/拓扑核对 |
| `cases[].sha256` | 生成文件的真实 SHA-256，运行前后检查 |

工况条目可保留本次物理验收所需参数与来源，执行器原样写入结果清单。各工况共用本轮分析配置；分析设置不同则拆成不同批次。频率参数只决定 AC 分析频率，不修改工程内瞬态源；输出请求也不代替求解器步长设置，两者由任务级生成器同步。

在任务工作目录调用，路径按实际位置替换：

```powershell
python <Skill目录>/simulation/scripts/run_multisim_native.py --cases cases.json --outdir outputs/run-new --timeout-s <本次每工况秒数>
```

`--timeout-s` 为整个工况宿主的墙钟上限，包含连接、打开、分析及保存，须覆盖本次工作量。所有数值均显式传入，执行器没有课程默认频率/时长。输出目录必须不存在；可从任意工作目录调用。

## 产物与后续验收

每工况保存：

- `native_netlist.txt`：原生网表，供任务级拓扑比对。
- `ac.json`：每输出 `[frequency, real, imaginary]`。
- `transient.json`：每输出的 `[[time, value], ...]`。
- `execution.json`：软件版本、枚举/选择的输出、分析请求、方法标识、数组形状、时间范围及错误。
- `verified.ms14`、`native_schematic.png`：原生保存工程和图纸导出。
- `execution.log`、`host.log`：动作和宿主日志。

根目录 `run_manifest.json` 记录输入/脚本指纹、实际参数、时间、退出状态及输出指纹。`native_execution=PASS` 仅证明接口执行、有限数值、预期数组形状、时间递增、保存及输入未变；`physical_validation` 和 `reproduction` 初始为 UNVERIFIED。`complete` 仅指本批次原生执行完成，不能当实验整体通过。

任务验收器继续检查时间窗覆盖、精度、单位、源幅值约定、探针方向、KCL/KVL、理论或跨分析一致性，将公式、容差和证据写入独立验收报告。再以 `verified.ms14` 和其新 SHA-256 建立重开清单，调用同一执行器到另一新目录并比对结果；只能声明实际完成的复现等级。

## 失败行为与支持范围

输入指纹不符、非法参数或输出目录已存在时拒绝运行。编译/求解/输出/保存失败即停批次，未到达工况保持 UNVERIFIED，不自动重试。超时只结束本次创建的宿主，不结束 Multisim；其状态需确认后才可开展下一批。

已验证接口为单频 AC 与 TRAN，不能由此推断 OP/DC/扫频或任意器件可用。COM API 和模型行为按本机版本做最小闭环；包含 Forth/动画的工程可能需要独立适配。固定模型、交互模型、GUI 面板证据分别验收。
