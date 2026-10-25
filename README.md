# 模型适配与验证 · model-adaptation-skill

面向模型环境配置、GPU 与厂商框架适配、推理验证、数值对齐、性能测量和适配问题排查的中文 Agent Skill。

将适配过程整理为可复现的操作、真实证据和有边界的结论，支持通过 `level=P0|P1|P2` 指定适配深度，也支持新增模型、已有适配修复和历史报告复核。

## 能做什么

- **环境与设备适配**：检查依赖、镜像、驱动和框架，按模型隔离环境。
- **分层验证**：从设备与算子检查到模型推理；训练、恢复和任务效果仅在任务需要时验证。
- **数值与性能验证**：明确基线、比较条件、计时边界和验收门槛。
- **问题排查与交接**：保留失败证据，区分事实与假设，输出报告、问题记录和工作日志。

这是指导 AI 助手执行工作的文档型 skill，安装本 skill 无需额外 Python 包。运行实际模型时，仍需按目标项目准备硬件、框架、权重、数据及访问权限。

报告面向需要理解结果和作出决定的人：先写结论与关键指标，必要时用真实数据绘制误差、训练或性能图表；详细命令、环境和原始日志放在附录或证据链接中。失败和关键限制仍需如实说明，避免在正文反复堆砌一般性免责声明。P0/P1 使用[运行报告模板](skills/model-adaptation/assets/run-report.md)，P2 使用[技术调研报告模板](skills/model-adaptation/assets/research-report.md)；[报告示例](skills/model-adaptation/references/report-examples.md)展示建议收录、暂缓收录和 P1 未通过的写法。

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

`level` 是本 skill 解释的输入约定，不是终端命令或 Codex 原生 CLI 参数。也可写“级别：P1”，小写 `p1` 按 P1 处理。不支持的值或互相冲突的级别会在执行受影响的工作前要求澄清。

希望工作过程中查看网页进展时，在请求中加 `dashboard=on` 或写“开启本地看板”。Agent 会逐项更新本机只读页面，展开每个阶段的工作项、流程状态和验收判定；有实测结果时显示附来源的指标和图表，Markdown ISSUE 与报告可在页面内阅读，PDF 提供打开或下载入口。页面自动刷新；看板没有显示 Agent 内部思考或自动探测真实进程的能力。详见[本地工作看板](skills/model-adaptation/references/dashboard.md)。

有条件时一并提供目标 GPU、参考 GPU 或已有基线、权重与真实输入、验收门槛及产物位置；P0 的长时训练还应说明已有训练方案、完成条件和资源额度。Skill 会先读取项目已有资料，不要求重复填写；[开工前的最小依据](skills/model-adaptation/references/levels.md#开工前的最小依据)说明缺项时可以先推进哪些工作。

P0 按约定训练方案执行，单步训练不代表训练验收完成。P1 根据证据与条件决定是否需要微调，不用微调掩盖精度对齐失败。P2 不安装依赖、下载权重或运行模型，仅交付注明来源和证据缺口的技术报告。详见 [分级执行与交付](skills/model-adaptation/references/levels.md)。

未指定 `level` 时继续按自然语言限定范围，不默认执行 P0。缺少必需条件或阶段失败时如实标记未完成，不自动降级或宣称完成；用户明确裁剪必需阶段时按裁剪范围执行，并在报告中说明。

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

请给出模型、工作区、目标平台、任务范围和已有验收条件。项目现行规范与用户明确要求优先，skill 不会将推理验证自动扩展成完整训练或跨服务器实验。

## 仓库结构

```text
skills/model-adaptation/
├── SKILL.md                      技能入口与适用范围
├── agents/openai.yaml            Codex 界面元数据
├── references/
│   ├── environment.md            环境、目录与跨平台对照
│   ├── levels.md                 P0/P1/P2 分级执行与交付
│   ├── validation.md             数值、性能及按需训练验证
│   ├── issues-and-handoff.md     问题记录与成果交接
│   ├── report-examples.md        虚构示例，展示报告结论写法
│   └── dashboard.md              可选本地工作看板
├── scripts/dashboard.py          看板状态与本机只读服务
└── assets/
    ├── experiment-profile.md     实验配置模板
    ├── run-report.md             运行报告模板
    ├── research-report.md        P2 技术调研报告模板
    ├── dashboard.html            看板页面
    ├── issue.md                  问题记录模板
    └── work-log.md               工作日志模板
```

阅读 [技能入口](skills/model-adaptation/SKILL.md) 了解完整流程。模板用于填写真实结果，也可与项目已有的等价文档合并。

## 安装参考

[OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills) 介绍技能格式、本地发现目录及安装方式。

## 许可证

本项目采用 [MIT License](LICENSE)，允许使用、修改与再分发，需保留版权及许可声明。
