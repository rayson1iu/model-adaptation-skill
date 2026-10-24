# 模型适配与验证 · model-adaptation-skill

面向模型环境配置、GPU 与厂商框架适配、推理验证、数值对齐、性能测量和适配问题排查的中文 Agent Skill。

将适配过程整理为可复现的操作、真实证据和有边界的结论，支持新增模型、已有适配修复和历史报告复核。

## 能做什么

- **环境与设备适配**：检查依赖、镜像、驱动和框架，按模型隔离环境。
- **分层验证**：从设备与算子检查到模型推理；训练、恢复和任务效果仅在任务需要时验证。
- **数值与性能验证**：明确基线、比较条件、计时边界和验收门槛。
- **问题排查与交接**：保留失败证据，区分事实与假设，输出报告、问题记录和工作日志。

这是指导 AI 助手执行工作的文档型 skill，安装本 skill 无需额外 Python 包。运行实际模型时，仍需按目标项目准备硬件、框架、权重、数据及访问权限。

## 安装

### 方式一：在 Codex 中安装

在支持 `$skill-installer` 的 Codex 会话中发送：

```text
使用 $skill-installer，从这个 GitHub 目录安装 model-adaptation：
https://github.com/rayson1iu/model-adaptation-skill/tree/main/skills/model-adaptation
```

安装后在下一轮对话中调用；若未出现，重新启动 Codex。

### 方式二：手动安装（macOS / Linux）

需要 Git。在终端中执行以下命令，将技能安装到用户级目录 `~/.agents/skills/model-adaptation`：

```sh
(
  set -eu
  skill_dir="$HOME/.agents/skills/model-adaptation"
  if [ -e "$skill_dir" ] || [ -L "$skill_dir" ]; then
    echo "目标已存在，请先检查：$skill_dir" >&2
    exit 1
  fi
  download_dir="$(mktemp -d)"
  trap 'rm -rf "$download_dir"' EXIT
  git clone --depth 1 https://github.com/rayson1iu/model-adaptation-skill.git "$download_dir/repository"
  mkdir -p "$HOME/.agents/skills"
  cp -R "$download_dir/repository/skills/model-adaptation" "$skill_dir"
  echo "已安装：$skill_dir"
)
```

若仅希望某个项目使用，将完整的 `skills/model-adaptation/` 目录复制到该项目的 `.agents/skills/model-adaptation/`，确保其中直接包含 `SKILL.md`。

本 skill 使用 `SKILL.md` 格式。其他支持此格式的 AI 助手可按各自的技能目录规则安装；`agents/openai.yaml` 提供 Codex 的界面元数据。

## 使用

安装后，在 Codex 中明确调用：

```text
使用 $model-adaptation，在当前项目中完成目标模型的 GPU 推理适配。
先检查现有项目规范和环境，只做推理兼容性验证，保存实际命令、日志、结果和问题清单。
```

其他示例：

```text
使用 $model-adaptation，比较 reference 与 candidate 的数值结果。
先确认权重、输入、精度、后端和验收门槛，输出可复核的对齐报告。
```

```text
使用 $model-adaptation，复核现有适配报告与原始日志。
不启动新实验，列出结论依据、证据缺口和下一步。
```

请给出模型、工作区、目标平台、任务范围和已有验收条件。项目现行规范与用户明确要求优先，skill 不会将推理验证自动扩展成完整训练或跨服务器实验。

## 仓库结构

```text
skills/model-adaptation/
├── SKILL.md                      技能入口与适用范围
├── agents/openai.yaml            Codex 界面元数据
├── references/
│   ├── environment.md            环境、目录与跨平台对照
│   ├── validation.md             数值、性能及按需训练验证
│   └── issues-and-handoff.md     问题记录与成果交接
└── assets/
    ├── experiment-profile.md     实验配置模板
    ├── run-report.md             运行报告模板
    ├── issue.md                  问题记录模板
    └── work-log.md               工作日志模板
```

阅读 [技能入口](skills/model-adaptation/SKILL.md) 了解完整流程。模板用于填写真实结果，也可与项目已有的等价文档合并。

## 安装参考

[OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills) 介绍技能格式、本地发现目录及安装方式。

## 许可证

本项目采用 [MIT License](LICENSE)，允许使用、修改与再分发，需保留版权及许可声明。
