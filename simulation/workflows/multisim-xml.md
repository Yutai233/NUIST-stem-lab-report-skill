# Multisim XML 对象与连接规则

仅在离线生成/修改工程时读取。以下来自已核对的 schema 67 原生对象，不是其他版本的完整格式规范。新版本、层次电路、多单元器件先用本机样例确认，不将单 sheet 的修复脚本当作通用编辑器。

## 容器与工具

`.ms14` 不是 ZIP：头为 `MSMCompressedElectronicsWorkbenchXML`，其后含解压长度和分块 PKWare DCL 数据。复用已验证编解码器，不为当前任务重写压缩算法。

已使用 [electronics-workbench-decoder](https://github.com/cinderblock/electronics-workbench-decoder) 的 `ewd`/`ewe`；固定实际版本并记录许可证。命令参数以所用版本的帮助为准：

```powershell
ewd input.ms14
ewe --output generated.ms14 input.ms14.xml
```

输入使用任务副本，输出使用新路径。回编码二进制不必逐字节相同，但再解码的关键数据和属性必须一致，最终仍由 Multisim 打开并求解。

可参考 [multisim-mcp](https://github.com/yxy050208/multisim-mcp) 的模板提取和有限构建代码；使用前固定提交、检查实现与许可。不把其器件覆盖声明当本机验收结果，也不要求安装完整 MCP。

## 必须同步的关系

| 对象 | 核对内容 |
|---|---|
| 逻辑组件与图形 | `CiID` 是逻辑对象，`ID` 是图形对象；`CiComponent@SymCompID` 与图形的组件反指一致 |
| 引脚与节点 | `CiPort/Nodes` ↔ `CiNode/Ports`，按所属电路和实例解析，不能只按名称合并 |
| 原生引脚注册 | `ComponentPins`、`CSCH_CAPVirtualComponentPin` 与实际组件/引脚/网络一致 |
| 实例及网络信息 | `TreeInstanceProxy`、网络标签、GUID、Ground modifier 等随模板关系同步 |
| 导线 | `CIITLinkComp` 的 `Node`、`Connect1/Connect2`、`ConnectList` 和连接点 owner 一致 |
| 仪器 | 符号与 `InstrumentsData/CSourceSymbolCollectNode` 实例状态一致，模式及端子连接正确 |
| 模型与参数 | 保留合法 `Model`/库引用；同步 `CiaParamList parameters/doubles`、单位及显示值 |

新增对象可以分配新 ID，但不能编造器件库标识。ID 是否允许重复取决于作用域和对象类别；不同动画层使用同一 PortID 不等于重复逻辑引脚。

## 导线端点是电气对象

`Points` 只表示绘图折线。几何重合不会自动建立原生连接；即使 XML 的逻辑节点名称一致，原生网表也可能把它们拆开。

遍历全部线端，既查三岔/四岔，也查只有两条线相接的纯线端：每个端点必须有模板要求的合法 owner、反向关联和一致网络。不要只按“分支数≥3”创建连接点。

按 ConnectList 连接分量检查同网连通与跨网误接；按器件引脚检查源到负载的闭合回路。电流表串联、电压表并联、瓦特表两条测量通路及正负端分别核对。断态开关有限泄漏和仪表负担属于模型，不能为了理想答案删除。

构建器验证至少覆盖一个断网负例和一个跨网误接负例。正式结论来自原生网表逐引脚核对及运行数据，不来自预览图。

## 参数、文本和模型

- `parameters` 与 `doubles` 可能不同时存在；按已核对模板的参数索引更新并回读，不能对所有器件统一假定索引含义。显示标签不是求解参数。
- 解析/序列化必须保留属性内 CR/LF/TAB。多行 SPICE/Forth 可能存于 XML 属性，普通解析器会归一化空白，导致注释吞掉语句。使用保留属性空白的解析器，做语义与往返检查。
- 单位遵循当前原生字段及模型的语法，不把显示单位与 SPICE 后缀混用。
- 初始化脚本可能在运行时改写静态参数。修改模板表达式、移除 Forth 或固定控制源是任务级模型变更，保存修改前后内容并交叉核验 AC/TRAN。某个灯泡模板的占位符修复不能推广到全部灯。
- 仪器里的历史显示缓存不是本次数据；原生求解输出与面板显示分别取证。

## 图面核对与保存

坐标变换按层累计：`x'=x*M00+y*M10+M20`，`y'=x*M01+y*M11+M21`。符号、引脚、文字、导线都可能有子变换，避免重复平移。

交叉线是否画实心点依据真实连接对象，不依据相交坐标或同名网络。报告图只按可见器件、测量链和走线对照；裁切、遮挡及版本差异应标明。XML 渲染图不是原生截图。

生成后原生打开、导出网表、求解和 SaveAs。重开时对比参数、网络及测量结果；保存前结构合法不能替代保存后验证。
