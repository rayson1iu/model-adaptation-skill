#!/usr/bin/env python3
"""Maintain and serve a local, read-only model-adaptation dashboard."""

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import quote, unquote, urlsplit


STAGES = {
    "P0": [
        ("training", "训练", True),
        ("inference", "目标 GPU 推理", True),
        ("accuracy", "精度对齐", True),
        ("profiling", "端到端性能剖析", True),
    ],
    "P1": [
        ("inference", "目标 GPU 推理", True),
        ("accuracy", "参考 GPU 精度对齐", True),
        ("finetuning", "按需微调", False),
    ],
    "P2": [
        ("sources", "资料核对", True),
        ("assessment", "适配判断", True),
        ("report", "技术报告", True),
    ],
    "UNSPECIFIED": [
        ("preparation", "范围与准备", True),
        ("execution", "约定工作", True),
        ("handoff", "报告与交付", True),
    ],
}
ITEMS = {
    "P0": {
        "training": [
            ("plan", "冻结训练方案与完成条件"),
            ("data", "核对数据、权重与训练环境"),
            ("run", "执行约定训练并保存检查点"),
            ("evaluate", "核对训练指标与完成依据"),
        ],
        "inference": [
            ("device", "确认目标 GPU 与运行环境"),
            ("load", "加载模型及全部组件权重"),
            ("sample", "运行真实输入样例"),
            ("output", "检查输出结构与实际设备"),
        ],
        "accuracy": [
            ("baseline", "确认参考基线与冻结门槛"),
            ("inputs", "准备配对输入与比较条件"),
            ("compare", "计算逐样本与汇总误差"),
            ("review", "复核超门槛样本与判定"),
        ],
        "profiling": [
            ("boundary", "固定端到端测量边界"),
            ("timing", "采集正式时延、吞吐与显存数据"),
            ("trace", "独立采集 GPU trace"),
            ("analysis", "解释阶段耗时、热点与瓶颈"),
        ],
    },
    "P1": {
        "inference": [
            ("device", "确认目标 GPU 与运行环境"),
            ("load", "加载模型及全部组件权重"),
            ("sample", "运行真实输入样例"),
            ("output", "检查输出结构与实际设备"),
        ],
        "accuracy": [
            ("baseline", "确认参考 GPU 基线与门槛"),
            ("inputs", "准备配对输入与比较条件"),
            ("compare", "计算逐样本与汇总误差"),
            ("review", "复核超门槛样本与判定"),
        ],
        "finetuning": [
            ("decision", "判断本次是否需要微调"),
            ("plan", "确认数据、方案与完成条件"),
            ("run", "执行约定微调"),
            ("recheck", "复验推理、精度与任务指标"),
        ],
    },
    "P2": {
        "sources": [
            ("official", "核对官方仓库、论文与模型卡"),
            ("rights", "核对权重可用性与许可证"),
            ("runtime", "整理架构、依赖与推理入口"),
        ],
        "assessment": [
            ("compatibility", "评估目标平台兼容条件"),
            ("risks", "排序关键适配风险与资料缺口"),
            ("prerequisites", "列出进入 P1/P0 的前置条件"),
        ],
        "report": [
            ("recommendation", "写出收录建议与关键理由"),
            ("evidence", "核对来源、版本与判断依据"),
            ("deliver", "交付技术报告与下一步"),
        ],
    },
    "UNSPECIFIED": {
        "preparation": [("scope", "确认任务范围与已有资料"), ("plan", "明确本次交付与验收依据")],
        "execution": [("work", "执行约定工作"), ("check", "核对结果与证据")],
        "handoff": [("report", "整理报告与问题"), ("deliver", "交付产物与下一步")],
    },
}
PROCESS = {"pending", "running", "done", "blocked"}
ITEM_STATUS = {"pending", "running", "done", "blocked", "skipped"}
ACCEPTANCE = {"not_evaluated", "pass", "fail", "blocked", "not_applicable"}
ISSUE_STATUS = {"open", "in_progress", "resolved", "blocked"}
REPORT_STATUS = {"draft", "final"}
DATA_SUFFIXES = {".json", ".csv", ".tsv", ".md"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "dashboard.html"


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_state(path):
    with path.open(encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("schema_version") != 1:
        raise ValueError("Unsupported dashboard state schema")
    return state


def save_state(path, state):
    state["updated_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dashboard-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def workspace_path(state, given, must_exist=True):
    root = Path(state["workspace_root"]).resolve()
    candidate = Path(given)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Artifact must be inside the selected workspace")
    if must_exist and not candidate.is_file():
        raise ValueError(f"Artifact file does not exist: {candidate}")
    return str(candidate.relative_to(root))


def command_init(args):
    state_path = Path(args.state).expanduser().resolve()
    if state_path.exists():
        raise ValueError(f"Dashboard state already exists: {state_path}")
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace}")
    if not state_path.is_relative_to(workspace):
        raise ValueError("Dashboard state must be inside the selected workspace")
    state = {
        "schema_version": 1,
        "model": args.model,
        "level": args.level,
        "run_id": args.run_id,
        "workspace_root": str(workspace),
        "summary": "已建立看板，等待首个工作阶段更新。",
        "next_action": "核对任务范围与已有资料",
        "updated_at": now(),
        "stages": [
            {"id": key, "label": label, "required": required,
             "process": "pending", "acceptance": "not_evaluated", "note": "",
             "items": [
                 {"id": item_id, "label": item_label, "status": "pending", "note": "", "updated_at": None}
                 for item_id, item_label in ITEMS[args.level][key]
             ]}
            for key, label, required in STAGES[args.level]
        ],
        "issues": [],
        "reports": [],
    }
    save_state(state_path, state)
    print(state_path)


def command_stage(args):
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    stage = next((item for item in state["stages"] if item["id"] == args.id), None)
    if stage is None:
        raise ValueError(f"Unknown stage: {args.id}")
    process = args.process if args.process is not None else stage["process"]
    acceptance = args.acceptance if args.acceptance is not None else stage["acceptance"]
    if process in {"pending", "running"} and acceptance not in {"not_evaluated"}:
        raise ValueError("Pending or running stages cannot have a final acceptance result")
    if process == "blocked" and acceptance not in {"not_evaluated", "blocked"}:
        raise ValueError("A blocked stage cannot be marked passed or failed")
    if process == "done" and acceptance == "blocked":
        raise ValueError("Use process=blocked for blocked stages")
    if acceptance == "not_applicable" and stage["required"]:
        raise ValueError("Required stages cannot be marked not applicable")
    stage["process"] = process
    stage["acceptance"] = acceptance
    if args.note is not None:
        stage["note"] = args.note
    save_state(path, state)


def command_item(args):
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    stage = next((entry for entry in state["stages"] if entry["id"] == args.stage), None)
    if stage is None:
        raise ValueError(f"Unknown stage: {args.stage}")
    items = stage.setdefault("items", [])
    item = next((entry for entry in items if entry["id"] == args.id), None)
    if item is None:
        if not args.label:
            raise ValueError("A new work item needs --label")
        item = {"id": args.id, "label": args.label, "status": "pending", "note": "", "updated_at": None}
        items.append(item)
    elif args.label is not None:
        item["label"] = args.label
    if args.status is not None:
        item["status"] = args.status
    if args.note is not None:
        item["note"] = args.note
    item["updated_at"] = now()
    save_state(path, state)


def command_note(args):
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    if args.summary is not None:
        state["summary"] = args.summary
    if args.next_action is not None:
        state["next_action"] = args.next_action
    save_state(path, state)


def command_artifact(args, kind):
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    relative = workspace_path(state, args.path)
    if Path(relative).suffix.lower() not in {".md", ".pdf"}:
        raise ValueError("Only Markdown or PDF issue/report files can be linked")
    collection = state["issues" if kind == "issue" else "reports"]
    identifier = args.id
    entry = next((item for item in collection if item["id"] == identifier), None)
    if entry is None:
        entry = {"id": identifier}
        collection.append(entry)
    entry.update({"title": args.title, "status": args.status, "path": relative})
    if kind == "report":
        entry["kind"] = args.kind
    save_state(path, state)


def document_target(state, kind, identifier):
    collection = state["issues" if kind == "issue" else "reports"]
    entry = next((item for item in collection if item["id"] == identifier), None)
    if entry is None:
        raise ValueError("Document is not registered")
    relative = workspace_path(state, entry["path"])
    if Path(relative).suffix.lower() not in {".md", ".pdf"}:
        raise ValueError("Document type is not supported")
    return Path(state["workspace_root"], relative).resolve()


def linked_target(state, kind, identifier, relative, allowed):
    document = document_target(state, kind, identifier)
    if not relative or Path(relative).is_absolute():
        raise ValueError("Relative document link required")
    candidate = (document.parent / relative).resolve()
    root = Path(state["workspace_root"]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file() or candidate.suffix.lower() not in allowed:
        raise ValueError("Linked file is unavailable")
    return candidate


def read_measurements(state):
    relative = state.get("measurements_path")
    if not relative:
        return {"metrics": [], "charts": []}
    relative = workspace_path(state, relative)
    if Path(relative).suffix.lower() != ".json":
        raise ValueError("Measurement summary must be JSON")
    with Path(state["workspace_root"], relative).open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("metrics", []), list) or not isinstance(data.get("charts", []), list):
        raise ValueError("Measurement summary needs metrics and charts arrays")
    seen = set()
    for kind, entries in (("metric", data.get("metrics", [])), ("chart", data.get("charts", []))):
        if len(entries) > 30:
            raise ValueError("Too many dashboard measurements")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Measurement entry must be an object")
            identifier = entry.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen or len(identifier) > 80:
                raise ValueError("Measurement IDs must be unique nonempty strings")
            seen.add(identifier)
            if not isinstance(entry.get("label" if kind == "metric" else "title"), str):
                raise ValueError("Measurement needs a label or title")
            if not isinstance(entry.get("unit"), str):
                raise ValueError("Measurement needs a unit")
            source = entry.get("source")
            if not isinstance(source, str) or Path(workspace_path(state, source)).suffix.lower() not in DATA_SUFFIXES:
                raise ValueError("Measurement source must be an existing data or Markdown file")
            if kind == "metric":
                value = entry.get("value")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Metric value must be a finite number")
                status = entry.get("status", "diagnostic")
                if status not in {"pass", "fail", "diagnostic"}:
                    raise ValueError("Metric status must be pass, fail, or diagnostic")
                if status in {"pass", "fail"} and not entry.get("threshold"):
                    raise ValueError("Passing or failing metrics need an explicit threshold")
            else:
                if entry.get("type") not in {"line", "bar"}:
                    raise ValueError("Chart type must be line or bar")
                threshold = entry.get("threshold")
                if threshold is not None and (isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold)):
                    raise ValueError("Chart threshold must be a finite number")
                points = entry.get("points")
                limit = 40 if entry["type"] == "bar" else 600
                if not isinstance(points, list) or not points or len(points) > limit:
                    raise ValueError(f"{entry['type']} chart needs 1 to {limit} points")
                for point in points:
                    if not isinstance(point, dict) or not isinstance(point.get("label"), str):
                        raise ValueError("Chart point needs a label")
                    value = point.get("value")
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise ValueError("Chart point value must be finite")
    return {"metrics": data.get("metrics", []), "charts": data.get("charts", [])}


def command_measurements(args):
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    relative = workspace_path(state, args.file)
    previous = state.get("measurements_path")
    state["measurements_path"] = relative
    try:
        read_measurements(state)
    except (OSError, ValueError, json.JSONDecodeError):
        if previous is None:
            state.pop("measurements_path", None)
        else:
            state["measurements_path"] = previous
        raise
    save_state(path, state)


def public_state(state):
    root = Path(state["workspace_root"]).resolve()
    result = {key: value for key, value in state.items() if key != "workspace_root"}
    for kind, plural in (("issue", "issues"), ("report", "reports")):
        result[plural] = []
        for entry in state[plural]:
            item = dict(entry)
            try:
                target = (root / entry["path"]).resolve()
                if target.is_relative_to(root) and target.is_file():
                    item["url"] = f"/artifact/{kind}/{quote(entry['id'], safe='')}"
            except (KeyError, OSError):
                pass
            result[plural].append(item)
    try:
        measurements = read_measurements(state)
        for kind, plural in (("metric", "metrics"), ("chart", "charts")):
            result[plural] = []
            for entry in measurements[plural]:
                item = dict(entry)
                item["source_url"] = f"/evidence/{kind}/{quote(entry['id'], safe='')}"
                result[plural].append(item)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result["metrics"] = []
        result["charts"] = []
        result["measurement_error"] = str(error)
    return result


def command_serve(args):
    state_path = Path(args.state).expanduser().resolve()
    load_state(state_path)

    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, body, content_type, status=200, artifact=False):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if artifact:
                self.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlsplit(self.path).path
            if route in ("/", "/index.html"):
                self.send_bytes(TEMPLATE.read_bytes(), "text/html; charset=utf-8")
                return
            try:
                state = load_state(state_path)
            except (OSError, ValueError, json.JSONDecodeError):
                self.send_bytes(b"State unavailable", "text/plain; charset=utf-8", 503)
                return
            if route == "/api/state":
                body = json.dumps(public_state(state), ensure_ascii=False).encode("utf-8")
                self.send_bytes(body, "application/json; charset=utf-8")
                return
            parts = route.split("/")
            if len(parts) == 4 and parts[1] == "evidence" and parts[2] in ("metric", "chart"):
                try:
                    measurements = read_measurements(state)
                    collection = measurements["metrics" if parts[2] == "metric" else "charts"]
                    entry = next(item for item in collection if item["id"] == unquote(parts[3]))
                    target = Path(state["workspace_root"], workspace_path(state, entry["source"]))
                    self.send_bytes(target.read_bytes(), "text/plain; charset=utf-8", artifact=True)
                    return
                except (OSError, ValueError, StopIteration, json.JSONDecodeError):
                    pass
            if len(parts) == 4 and parts[1] == "artifact" and parts[2] in ("issue", "report"):
                try:
                    target = document_target(state, parts[2], unquote(parts[3]))
                    content_type = "application/pdf" if target.suffix.lower() == ".pdf" else "text/plain; charset=utf-8"
                    self.send_bytes(target.read_bytes(), content_type, artifact=target.suffix.lower() != ".pdf")
                    return
                except (OSError, ValueError):
                    pass
            if len(parts) == 5 and parts[1] in ("attachment", "resource") and parts[2] in ("issue", "report"):
                try:
                    identifier = unquote(parts[3])
                    relative = unquote(parts[4])
                    allowed = set(IMAGE_TYPES) if parts[1] == "attachment" else DATA_SUFFIXES | {".pdf"}
                    target = linked_target(state, parts[2], identifier, relative, allowed)
                    content_type = IMAGE_TYPES[target.suffix.lower()] if parts[1] == "attachment" else ("application/pdf" if target.suffix.lower() == ".pdf" else "text/plain; charset=utf-8")
                    self.send_bytes(target.read_bytes(), content_type, artifact=target.suffix.lower() != ".pdf")
                    return
                except (OSError, ValueError):
                    pass
            self.send_bytes(b"Not found", "text/plain; charset=utf-8", 404)

        def log_message(self, format_string, *arguments):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Local dashboard: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create dashboard state for one adaptation task")
    init.add_argument("--state", required=True)
    init.add_argument("--workspace", required=True)
    init.add_argument("--model", required=True)
    init.add_argument("--level", choices=STAGES, required=True)
    init.add_argument("--run-id", required=True)
    init.set_defaults(func=command_init)

    stage = sub.add_parser("stage", help="Update a workflow stage")
    stage.add_argument("--state", required=True)
    stage.add_argument("--id", required=True)
    stage.add_argument("--process", choices=sorted(PROCESS))
    stage.add_argument("--acceptance", choices=sorted(ACCEPTANCE))
    stage.add_argument("--note")
    stage.set_defaults(func=command_stage)

    item = sub.add_parser("item", help="Update or add one work item inside a stage")
    item.add_argument("--state", required=True)
    item.add_argument("--stage", required=True)
    item.add_argument("--id", required=True)
    item.add_argument("--label", help="Required when adding a project-specific item")
    item.add_argument("--status", choices=sorted(ITEM_STATUS))
    item.add_argument("--note")
    item.set_defaults(func=command_item)

    note = sub.add_parser("note", help="Update the current summary and next action")
    note.add_argument("--state", required=True)
    note.add_argument("--summary")
    note.add_argument("--next-action")
    note.set_defaults(func=command_note)

    measurements = sub.add_parser("measurements", help="Link a validated JSON summary of measured data")
    measurements.add_argument("--state", required=True)
    measurements.add_argument("--file", required=True)
    measurements.set_defaults(func=command_measurements)

    for name, kind in (("issue", "issue"), ("report", "report")):
        entry = sub.add_parser(name, help=f"Add or update a {kind} link")
        entry.add_argument("--state", required=True)
        entry.add_argument("--id", required=True)
        entry.add_argument("--title", required=True)
        entry.add_argument("--path", required=True)
        entry.add_argument("--status", choices=sorted(ISSUE_STATUS if kind == "issue" else REPORT_STATUS), required=True)
        if kind == "report":
            entry.add_argument("--kind", choices=("run", "research", "other"), required=True)
        entry.set_defaults(func=lambda args, selected=kind: command_artifact(args, selected))

    serve = sub.add_parser("serve", help="Serve the read-only dashboard on loopback")
    serve.add_argument("--state", required=True)
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=command_serve)
    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(2, f"dashboard: {error}\n")


if __name__ == "__main__":
    main()
