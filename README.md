# NUIST 理工科实验报告 Skill

这是一个面向南信大（NUIST）理工科课程实验报告的 Skill。它会根据用户提供的实验指导书、教师规范、原始数据、代码、截图和已有实例，选择合适的课程提示词、模板与参考材料，协助生成并检查 DOCX 和 PDF 报告。

## 安装 Skill

### 方法一：交给 Agent 安装（推荐）

1. 打开本仓库的 GitHub 页面，点击绿色的 **Code**，再点击 **Download ZIP**。
2. 将下载的 ZIP 文件提供给你的 Agent（**例如Codex、WorkBuddy、Zcode、Deepseek Harness等**），并发送下面的请求：

```text
请安装这个实验报告 Skill。请解压文件，读取 SKILL.md，并按照当前 Agent 的 Skill 目录规范完成安装；如果不支持自动安装，请告诉我应该复制到哪个目录。
```

3. 让 Agent 检查 `SKILL.md` 是否位于 Skill 文件夹的第一层，避免出现重复嵌套的文件夹。

这个 ZIP 包的核心内容是 `SKILL.md`、`references/` 和各课程目录，适合迁移到支持本地 Skill 的 Agent。不同 Agent 的安装目录、调用方式和文档生成能力可能不同；如果 Agent 不支持自动安装，请使用下面的网页复制方法。

## 新增课程
如果你有更多的改进建议or愿意无偿提供更多的课程实验报告，欢迎联系我：Yu_tai233@outlook.com。

新增课程时，先阅读 `references/new-course-integration.md`，再登记课程提示词、模板、实例来源和可借鉴范围。未登记课程可以使用 `references/general-stem-lab-prompt.md`，但当前教师规范始终优先。

## 特别鸣谢

感谢以下同学无偿提供了优质的实验报告：

🌹-**旺仔牛逼糖**  

🌹-**醋溜便当**  

🌹-**Stay Gold.**  

🌹-**鲁米**  

## 核心规则

教师提供的实验指导书、评分标准和格式要求优先于课程专属提示词；课程专属提示词优先于通用理工科提示词；模板和已有实例只用于补充未明确规定的写法与版式。

没有证据时不编造实验数据、运行结果、截图、调试过程或个人经历。缺失项及识图不确定性记在任务笔记并在过程/交付对话中告知，不默认写入正式 Word；空白模板或用户明确要求的草稿可保留占位符。无法确切区分指导书图和本次实测图时直接询问用户。

涉及实验图片时，按 `references/figure-evidence.md` 在任务目录建立 `图片证据笔记.md`，关联来源、条件、读数与实验内容；成稿后结合结构辅助检查和原图/最终页面复核验收。

## 目录结构

- `SKILL.md`：Skill 入口说明与工作流程
- `agents/openai.yaml`：Codex 界面元数据
- `references/`：通用规则、课程登记表、新课程接入要求和 DOCX/PDF 验收规则
- `scripts/`：只读图片结构辅助检查及测试（依赖 Python 和 Pillow；不能替代图面语义与逐页视觉检查）
- 各课程目录：课程专属提示词、Word 模板和经过整理的参考实例；电子设计自动化实验按 ADS、HFSS、Altium Designer 软件分类组织；独立的 EDA设计与仿真课程按 Multisim 仿真和 Altium 原理图/PCB 设计选择提示词中的对应分支与模板，材料来源见各课程的来源说明；电路分析实验另有仿真实验卡

## Star History

<a href="https://www.star-history.com/?repos=yutai233%2Fnuist-stem-lab-report-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=yutai233/nuist-stem-lab-report-skill&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=yutai233/nuist-stem-lab-report-skill&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=yutai233/nuist-stem-lab-report-skill&type=date&legend=top-left" />
 </picture>
</a>
