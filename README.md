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

## 安装到 Codex

将本仓库目录复制或克隆到 Codex 的 Skill 目录，并保留目录名 `nuist-stem-lab-report`：

```powershell
git clone https://github.com/<你的用户名>/<你的仓库名>.git "$env:USERPROFILE\.codex\skills\nuist-stem-lab-report"
```

如果目标目录已经存在，先在该目录执行 `git pull`，或删除旧副本后重新克隆。安装后可以显式调用：

```text
$nuist-stem-lab-report
```

## 发布前检查

公开仓库前，请确认参考报告和模板已经去除姓名、学号、联系方式、账号、设备序列号、内部链接等个人或敏感信息，并确认你拥有公开这些课程资料、模板和实例的权限。生成的个人报告、PDF、临时文件和 Word 锁文件不应提交到仓库。

## 新增课程

新增课程时，先阅读 `references/new-course-integration.md`，再登记课程提示词、模板、实例来源和可借鉴范围。未登记课程可以使用 `references/general-stem-lab-prompt.md`，但当前教师规范始终优先。
