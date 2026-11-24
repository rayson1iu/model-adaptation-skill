# 模型适配与验证 · model-adaptation-skill

为 GPU 模型适配、验证和技术调研提供方向与方法的中文 Agent Skill。

用 `level=P0|P1|P2` 指定工作深度。具体工具、步骤、目录和记录方式沿用项目规范，并按任务选择。

## 能做什么

- **环境与设备适配**：识别驱动、框架和依赖的兼容性问题，按需隔离环境。
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

### 通过 level 指定适配深度

| 参数 | 工作范围 |
| --- | --- |
| `level=P0` | 训练 + 推理 + 精度对齐 + 端到端性能剖析 |
| `level=P1` | 推理跑通 + 与参考 GPU 精度对齐，视情况微调 |
| `level=P2` | 调研收录，仅输出技术报告，不执行模型实验 |

直接在 Codex 的请求中填写参数与任务信息，例如：

```text
$model-adaptation level=P1
模型：OpenVLA-OFT
工作区：/workspace/openvla
目标平台：待适配 GPU
参考 GPU：项目指定的基线 GPU
```

```text
$model-adaptation level=P0
模型：目标模型
训练方案、数据、精度门槛和端到端测量范围：按当前项目验收规范执行
```

```text
$model-adaptation level=P2
模型：待调研模型
目标平台：待评估 GPU
仅输出技术报告，给出收录建议、适配风险及升级到 P1/P0 的前置条件。
```

在发给助手的请求中指定 `level`，也可写 `level=p1` 或“级别为 P1”。

开工时从项目已有资料确认模型、目标平台和验收依据。P0 可先找训练入口和代表性样本，P1 可先确认参考 GPU 基线。[分级执行与交付](skills/model-adaptation/references/levels.md)

P0 默认做短程训练链路验证，检查真实样本的前向、反向和实际参数更新，不默认要求完整训练或收敛；项目另有明确要求时按其范围执行。P1 根据证据与条件决定是否需要微调，不用微调掩盖精度对齐失败。P2 不安装依赖、下载权重或运行模型，仅交付注明来源和证据缺口的技术报告。详见 [分级执行与交付](skills/model-adaptation/references/levels.md)。

未指定 `level` 时按请求中的范围工作。已有基线、脚本和文档可以复用。

### 自然语言指定范围

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

调用时说清希望解决的问题即可，项目中已有的模型、环境和验收信息可以直接引用。

## 仓库结构

```text
skills/model-adaptation/
├── SKILL.md                      技能入口与适用范围
├── agents/openai.yaml            Codex 界面元数据
├── references/
│   ├── environment.md            环境、目录与跨平台对照
│   ├── levels.md                 P0/P1/P2 分级执行与交付
│   ├── validation.md             数值、性能及按需训练验证
│   └── issues-and-handoff.md     问题记录与成果交接
└── assets/
    ├── experiment-profile.md     实验配置模板
    ├── issue.md                  问题记录模板
    └── work-log.md               工作日志模板
```

从 [技能入口](skills/model-adaptation/SKILL.md) 选择适用的方法。模板可按任务取用，也可沿用项目已有格式。

## 安装参考

[OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills) 介绍技能格式、本地发现目录及安装方式。

## 许可证

本项目采用 [MIT License](LICENSE)，允许使用、修改与再分发，需保留版权及许可声明。
