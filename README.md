# NUIST 理工科实验报告 Skill

这是一个面向南信大（NUIST）理工科课程实验报告的 Codex Skill。它会根据用户提供的实验指导书、教师规范、原始数据、代码、截图和已有实例，选择合适的课程提示词、模板与参考材料，协助生成并检查 DOCX 和 PDF 报告。

## 核心规则

教师提供的实验指导书、评分标准和格式要求优先于课程专属提示词；课程专属提示词优先于通用理工科提示词；模板和已有实例只用于补充未明确规定的写法与版式。

没有证据时不编造实验数据、运行结果、截图、调试过程或个人经历。缺失信息应标记为待补充或待核对，并在生成报告前询问会影响结果的关键问题。

## 目录结构

- `SKILL.md`：Skill 入口说明与工作流程
- `agents/openai.yaml`：Codex 界面元数据
- `references/`：通用规则、课程登记表、新课程接入要求和 DOCX/PDF 验收规则
- 各课程目录：课程专属提示词、Word 模板和经过整理的参考实例

## 安装 Skill

### 方法一：下载 ZIP 后交给 Agent 安装（推荐）

1. 打开本仓库的 GitHub 页面，点击绿色的 **Code**，再点击 **Download ZIP**。
2. 将下载的 ZIP 文件提供给你的 Agent（**例如Codex、WorkBuddy、Zcode等**），并发送下面的请求：

```text
请安装这个实验报告 Skill。请解压文件，读取 SKILL.md，并按照当前 Agent 的 Skill 目录规范完成安装；如果不支持自动安装，请告诉我应该复制到哪个目录。
```

3. 让 Agent 检查 `SKILL.md` 是否位于 Skill 文件夹的第一层，避免出现重复嵌套的文件夹。

这个 ZIP 包的核心内容是 `SKILL.md`、`references/` 和各课程目录，适合迁移到支持本地 Skill 的 Agent。不同 Agent 的安装目录、调用方式和文档生成能力可能不同；如果 Agent 不支持自动安装，请使用下面的网页复制方法。

### 方法二：网页下载后手动复制（不需要 Git）

1. 解压下载的 ZIP 文件。
2. 将解压出的文件夹重命名为 `nuist-stem-lab-report`。
3. 在 Windows 文件资源管理器的地址栏输入 `%USERPROFILE%\.codex\skills` 并打开。没有这个文件夹时可以手动创建。
4. 将 `nuist-stem-lab-report` 文件夹复制到这个目录中。

安装后应当满足下面的结构，不能多套一层文件夹：

```text
C:\Users\你的用户名\.codex\skills\nuist-stem-lab-report\SKILL.md
```

在 Codex 中打开新的对话，输入下面的调用名即可测试：

```text
$nuist-stem-lab-report
```

### 方法三：Git 命令行

熟悉 Git 的用户可以直接执行：

```powershell
git clone https://github.com/Yutai233/NUIST-stem-lab-report-skill.git "$env:USERPROFILE\.codex\skills\nuist-stem-lab-report"
```

已有安装目录时，进入该目录执行 `git pull` 即可更新。

## 新增课程
如果你有更多的改进建议or愿意无偿提供更多的课程实验报告，欢迎联系我：Yu_tai233@outlook.com。

新增课程时，先阅读 `references/new-course-integration.md`，再登记课程提示词、模板、实例来源和可借鉴范围。未登记课程可以使用 `references/general-stem-lab-prompt.md`，但当前教师规范始终优先。
