# 本地工作看板

仅在用户要求 `dashboard=on` 或明确要求网页进展时启用。工作坊看板列出可选模型；选中后，只加载该模型当前运行的“阶段 → 工作项”逐项进展、阶段流程状态与验收判定、ISSUE、报告和最近更新时间。有实测结果时可增加关键指标与图表；点击 ISSUE 或报告可在页面内阅读正文及其本地图片。真实结论与原始证据仍以项目文档和日志为准。不从“已执行命令数”推算虚假的完成百分比。

## 建立与查看

使用本 skill 的 `scripts/dashboard.py`，仅需 Python 标准库。workshop 根目录默认为 `/workshop`，用户另有指定时使用实际 workshop 根目录。`<workshop>/dashboard/` 用于看板自身的状态和索引；模型源码、测量摘要、报告、ISSUE 和原始数据保存在 `<workshop>/model_zoo/` 或 `<workshop>/repo/`。每个模型的每次运行维护一个独立状态文件，选择不冲突的模型目录名和 run ID：

```sh
skill_dir=/absolute/path/to/model-adaptation
workspace_dir=/workshop
model_dir=example-model
run_id=run-001
state_file="$workspace_dir/dashboard/models/$model_dir/runs/$run_id/dashboard.json"
python3 "$skill_dir/scripts/dashboard.py" init \
  --workshop "$workspace_dir" --state "$state_file" \
  --model '目标模型' --level P1 --run-id "$run_id"
python3 "$skill_dir/scripts/dashboard.py" serve --workshop "$workspace_dir" --port 8765
```

多模型分别执行 `init --workshop`，共用一个 `serve --workshop`。服务仅在 `dashboard/` 内发现看板自身的 `dashboard.json`；报告、ISSUE、图片、测量摘要和原始数据须来自 `model_zoo/` 或 `repo/`。看板只读取并引用这些现有产物，实际工作按项目规范正常写入 `model_zoo/` 和 `repo/`；不要把报告或原始证据复制到 `dashboard/`。侧栏按名称排序列出模型，同名模型默认展示最近更新的运行；点击模型或使用键盘切换，地址中的 `?model=` 保存运行标识。只加载所选运行的详情。顶部标签分别显示工作阶段、模型数据与相关文档；切换模型时保留当前标签，没有实测数据时指标卡片显示“—”。此前的 `init --workspace`、`serve --state` 和 `serve --workspace` 保留供已有状态使用；旧状态需显式重新登记到 `dashboard/` 才会出现在新 workshop 模式中，避免自动迁移历史记录。

若旧看板把测量摘要保存在 `dashboard/`，将该摘要迁入对应模型的 `repo/` 或 `model_zoo/` 后，用 `measurements --state ... --file ...` 重新登记；源数据、报告和旧索引按项目要求保留。界面不自动发现新文档，Agent 应在产物落盘后登记或更新索引。

在可持续运行的终端会话中启动服务，记录进程与端口，然后继续适配工作；向用户提供脚本打印的 `http://127.0.0.1:8765/` 地址。服务只绑定本机回环地址，页面每 5 秒读取一次状态；不部署到外网。服务需要保持运行才能自动刷新，任务结束后可停止；状态 JSON 保留，之后可重新启动查看。端口占用时选其他空闲端口。不要把凭据、完整命令、原始日志或私人数据复制进看板状态。

## 工作中更新

看板只显示已经落盘的事实。开始或结束一个工作项、发生阻塞、保存 ISSUE 或报告时及时更新；长时间运行的工作项在实际出现检查点或明确状态变化时更新。已有文档是事实来源，不因看板建立重复记录。以下示例沿用上面的 `skill_dir` 和 `state_file`，所指 ISSUE 与报告须先实际保存：

```sh
python3 "$skill_dir/scripts/dashboard.py" stage --state "$state_file" \
  --id inference --process running --note '已开始目标 GPU 真实输入推理'
python3 "$skill_dir/scripts/dashboard.py" item --state "$state_file" \
  --stage inference --id load --status done --note '模型与组件权重加载完成'
python3 "$skill_dir/scripts/dashboard.py" item --state "$state_file" \
  --stage inference --id sample --status running --note '正在运行真实输入样例'
python3 "$skill_dir/scripts/dashboard.py" note --state "$state_file" \
  --summary '推理已跑通，正在对齐参考 GPU 精度' --next-action '检查逐样本误差'
python3 "$skill_dir/scripts/dashboard.py" issue --state "$state_file" \
  --id ISSUE-001 --title '两组样本误差超门槛' --status open \
  --path repo/model/docs/issues/ISSUE-001.md
python3 "$skill_dir/scripts/dashboard.py" report --state "$state_file" \
  --id current-report --title '本次运行报告' --kind run --status draft \
  --path repo/model/reports/runs/run-001/run-report.md
```

`init` 按级别预置工作项，以下 ID 可直接用于 `item --stage ... --id ...`；它们用于显示进展，不自动增加项目验收要求。项目有不同流程时，可用 `item --stage <阶段ID> --id <新ID> --label '工作项名称' --status pending` 增补。旧状态文件没有工作项时也可这样逐项补充。

| 级别 | 阶段 ID | 预置工作项 ID（顺序即页面顺序） |
| --- | --- | --- |
| P0 | `training` | `plan`、`data`、`run`、`evaluate` |
| P0/P1 | `inference` | `device`、`load`、`sample`、`output` |
| P0/P1 | `accuracy` | `baseline`、`inputs`、`compare`、`review` |
| P0 | `profiling` | `boundary`、`timing`、`trace`、`analysis` |
| P1 | `finetuning` | `decision`、`plan`、`run`、`recheck` |
| P2 | `sources` | `official`、`rights`、`runtime` |
| P2 | `assessment` | `compatibility`、`risks`、`prerequisites` |
| P2 | `report` | `recommendation`、`evidence`、`deliver` |

工作项状态用 `pending/running/done/blocked/skipped`；`skipped` 仅表示本次不适用，并说明原因。阶段流程状态另用 `pending/running/done/blocked`，验收判定另用 `not_evaluated/pass/fail/blocked/not_applicable`。例如某项 `done` 只表示该项工作已结束；`stage --process done --acceptance fail` 表示整个阶段执行完但验收失败。P1 微调不需要时，把决策项记为 `done`，其余确实不适用的项记为 `skipped`，阶段记为 `done/not_applicable` 并写明依据。预置项可根据项目现行流程改名或标为不适用，不能因为页面项目数增加就扩大适配范围。命令的 `issue` 与 `report` 只接受工作区内已存在的文件，重复 ID 会更新其当前状态与路径。

## 实测指标与图表

模型数据页通过完整指标表展示全部已登记指标及未测的预设项，列出实测值、单位、参考值、门槛、判定、测量条件和来源。表格与卡片使用同一份数据，额外的项目指标也会列入；窄屏可横向滚动查看所有列。空值显示“—”，数值零按实际值显示。

卡片用于概览，完整表格按下列类别展开，每行附有口径说明。预设位置不代表所有模型都必须测量该项；任务成功率、困惑度、token 指标等只在模型和任务适用时登记。P2 没有本次实测时保留空值。

| 类别 | 预设指标 ID |
| --- | --- |
| 推理时延 | `latency_mean`、`latency_p50`、`latency_p90`、`latency_p95`、`latency_p99`、`latency_min`、`latency_max`、`latency_std`、`cold_start_latency`、`model_compute_latency`、`preprocess_latency`、`transfer_latency`、`postprocess_latency` |
| 吞吐 | `throughput`、`time_to_first_token`、`time_per_output_token` |
| 资源占用 | `peak_memory`（allocated）、`reserved_memory`、`device_memory`、`host_rss`、`gpu_utilization` |
| 数值对齐 | `max_error`、`mean_abs_error`、`rmse`、`max_rel_error`、`mean_rel_error`、`cosine_similarity`、`alignment_pass_rate`、`nonfinite_count` |
| 任务效果 | `accuracy`、`task_success_rate`、`perplexity` |
| 测量覆盖 | `sample_count`、`inference_iterations`、`inference_failure_count` |
| P0 训练验证 | `training_loss`、`gradient_norm`、`parameter_update_norm`、`optimizer_updates`、`training_step_latency`、`training_throughput`、`training_peak_memory`、`gradient_nonfinite_count` |

用指标 `id` 对应预设行；也接受 `max_abs_error`、`peak_memory_mb`、`task_accuracy` 这些已有同义 ID。优先按 ID 识别具体指标，未匹配 ID 时可用同名 `slot` 关联行；只有 `slot=accuracy` 等宽泛信息时，不将其推断为最大误差等不同指标。其他指标列在“项目扩展”中。最多登记 100 项指标及 30 个图表；同一指标的多配置结果使用独立 ID，写明配置条件，不覆盖另一配置的数据。

有真实测量结果时，在模型的 `repo/` 或 `model_zoo/` 目录内准备小型 JSON 摘要，然后用 `measurements` 命令将其路径登记到看板索引。看板每次刷新都重新读取该文件。页面预设推理延迟、显存占用、模型精度/误差和吞吐量卡片，P0 增加训练损失；未测项显示“—”，不增加验收要求。指标可用 `slot` 指定 `latency`、`memory`、`accuracy`、`throughput` 或 `training_loss`，多种口径时只将明确匹配的一项显示在预设卡片，其余另行显示。JSON 中每个指标和图都必须指向这些目录内已存在的原始数据或报告文件（`.json`、`.csv`、`.tsv`、`.md`），不要写入无来源的估计值。图表支持折线图 `line`（最多 600 点）和柱状图 `bar`（最多 40 点）；长序列可从原始数据生成有说明的抽样摘要，原始文件仍保留。

按本次任务选少量有判断价值的数据：P1 常见的是目标 GPU 推理结果、逐样本精度误差与参考 GPU 对比；P0 可再展示训练曲线、端到端时延/吞吐、显存和剖析热点。P2 仅调研，不展示仿佛本次实测的指标；引用上游公开指标应放在技术报告并标出来源与原条件。

以下数值与路径仅示范字段，均为虚构，实际工作中必须改为本次实测值与真实来源：

```json
{
  "metrics": [
    {
      "id": "latency_p50", "label": "端到端时延 p50", "value": 42.5,
      "unit": "ms", "context": "batch=1，20 次有效运行",
      "reference": "参考 GPU 51.3 ms", "threshold": "≤ 50 ms",
      "status": "pass", "source": "repo/model/reports/runs/run-001/latency.csv"
    }
  ],
  "charts": [
    {
      "id": "sample_error", "title": "逐样本最大绝对误差", "type": "bar",
      "unit": "误差", "threshold": 0.01, "threshold_label": "验收门槛",
      "caption": "两组样本超过事前冻结的门槛。",
      "source": "repo/model/reports/runs/run-001/error.csv",
      "points": [{"label": "样本 1", "value": 0.004}, {"label": "样本 2", "value": 0.018}]
    }
  ]
}
```

```sh
python3 "$skill_dir/scripts/dashboard.py" measurements --state "$state_file" \
  --file "$workspace_dir/repo/$model_dir/reports/runs/$run_id/dashboard-measurements.json"
```

`status=pass/fail` 只能依据已有门槛判定；尚无门槛的诊断值用 `diagnostic`。在指标中写清单位、样本范围、比较条件和门槛（适用时）；图表可用数值 `threshold` 绘制门槛线，标题、单位与图注应使读者能直接理解发现。更新 JSON 后页面自动显示新数据，但 Agent 仍应同步报告和阶段状态，避免看板与正式结论不一致。

图表也可直接读取 `source` 指向的 CSV、TSV 或 JSON 数据：例如 CSV 有 `sample,error` 两列时，用 `"data": {"label_column": "sample", "value_column": "error"}` 代替 `points`。JSON 使用对象数组，若数组位于顶层对象字段，可再指定 `"array_key"`。每次刷新重新读取来源；缺列、非数字或超出点数上限会提示错误。单个来源文件上限 5 MB；较大数据应准备有来源说明的小型摘要。原有内嵌 `points` 格式继续支持。

## 页面内查看产物

ISSUE 和报告登记后，点击标题会在页面内打开 Markdown 正文；其中的标题、列表、表格、代码块及相对路径图片可阅读。PDF 报告提供新标签打开或下载入口，避免在不支持内嵌 PDF 的浏览器里出现空白预览。图片可使用 PNG、JPEG、WebP、GIF 或 SVG，链接应相对于文档位置；其他相对文档/数据链接会以新标签打开。只提供已登记、仍在工作区内的内容，原始 HTML 不作为可执行页面渲染。

保存新 ISSUE 或报告后立即登记其标题、状态与文件路径；只登记工作区内实际存在的 Markdown 或 PDF 文档。文件移动或状态改变时更新相应条目；看板链接只打开已登记且仍在工作区内的文件。P2 只登记技术报告，不为了填充页面创建 ISSUE 或实验记录。最终回复仍提供主要产物的直接路径，看板不能代替报告交付。

页面若在进行中状态超过 10 分钟没有更新，会提示状态可能过期。看板服务停止、Agent 被中断或产物路径失效时，不把旧显示当作正在执行的证明；恢复工作前先核对真实进程、日志和文档，再更新看板。
