#!/usr/bin/env python3
"""Portable course tools. Python 3.9+, standard library only; no model API keys."""
import argparse
import csv
import functools
import hashlib
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata

SKILL = Path(__file__).resolve().parents[1]
VERSION = 1


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    """Replace a complete document atomically, never leave a partial catalog."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def normalize(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).replace("’", "'")).strip().lower()


def term_key(term):
    return normalize(term).strip(" .!?;:")


def parse_subtitles(text):
    """Parse SRT, VTT or one-dialogue-per-line TXT; retain cue timing."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    rows = []
    timed = "-->" in text
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if lines and re.match(r"^(WEBVTT|NOTE|STYLE|REGION)(\s|$)", lines[0]):
            continue
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timed and timing is None:
            continue
        body = lines[timing + 1:] if timing is not None else lines
        for line in body:
            clean = html.unescape(re.sub(r"<[^>]*>", "", line)).strip()
            if clean and not clean.isdigit():
                rows.append({"id": len(rows) + 1, "text": clean,
                             "timestamp": lines[timing].strip() if timing is not None else None})
    if not rows:
        raise ValueError("没有找到字幕对话。请提供 UTF-8 SRT、VTT 或逐行 TXT。")
    return rows


def prepare(input_path, output, source):
    p = Path(input_path)
    if p.stat().st_size > 10_000_000:
        raise ValueError("字幕文件超过 10 MB，请先按集拆分。")
    raw = p.read_text(encoding="utf-8-sig")
    result = {"schemaVersion": VERSION, "source": source,
              "sha256": hashlib.sha256(raw.encode()).hexdigest(), "lines": parse_subtitles(raw)}
    write_json(output, result)
    return {"lines": len(result["lines"]), "output": str(output)}


def string(obj, name, limit=2000):
    value = obj.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("字段缺失、为空或过长：" + name)
    return value.strip()


def validate(course, evidence):
    if not isinstance(course, dict) or course.get("schemaVersion") != VERSION:
        raise ValueError("课程 schemaVersion 必须是 1。")
    slug = string(course, "seriesId", 80)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("seriesId 仅接受小写字母、数字和连字符。")
    for name in ("season", "episode"):
        if type(course.get(name)) is not int or not 1 <= course[name] <= 999:
            raise ValueError(name + " 必须是 1–999 的整数。")
    for name in ("series", "title", "language", "source"):
        string(course, name)
    if course["source"] != evidence.get("source"):
        raise ValueError("课程来源必须与 prepare 的来源一致。")
    words = course.get("words")
    if not isinstance(words, list) or not 1 <= len(words) <= 100:
        raise ValueError("每集需要 1–100 个词条；不为凑数虚构词汇。")
    lines = {r["id"]: r["text"] for r in evidence["lines"]}
    keys = set()
    for word in words:
        if not isinstance(word, dict):
            raise ValueError("词条必须是对象。")
        for name in ("term", "meaning", "ipa", "sentence", "translation", "tip", "sourceForm"):
            string(word, name)
        key = term_key(word["term"])
        if key in keys:
            raise ValueError("本集存在重复词条：" + word["term"])
        keys.add(key)
        line = word.get("sourceLine")
        if type(line) is not int or line not in lines:
            raise ValueError("无效 sourceLine：" + word["term"])
        source_form = normalize(word["sourceForm"])
        source_text = normalize(lines[line])
        if not re.search(r"(?<!\w)" + re.escape(source_form) + r"(?!\w)", source_text):
            raise ValueError("来源行中找不到 sourceForm：" + word["term"])
        if len(source_form.split()) > 12:
            raise ValueError("sourceForm 应是短表达，不能存整段对话。")
        if normalize(word["sentence"]) == source_text:
            raise ValueError("sentence 应为原创练习句，不能复制来源整句。")
    return {"valid": True, "words": len(words), "note": "出现位置已核验；语境词义和 IPA 仍须 Agent 审校。"}


def public_course(course):
    result = {k: course[k] for k in ("schemaVersion", "seriesId", "series", "season", "episode", "title", "language", "source")}
    result["id"] = f'{course["seriesId"]}-s{course["season"]:02d}e{course["episode"]:02d}'
    result["words"] = []
    for w in course["words"]:
        row = {k: w[k] for k in ("term", "meaning", "ipa", "sentence", "translation", "tip")}
        row["key"] = term_key(w["term"])
        result["words"].append(row)
    return result


def annotate(courses):
    seen = {}
    for course in sorted(courses, key=lambda c: (c["seriesId"], c["season"], c["episode"])):
        for w in course["words"]:
            key = (course["seriesId"], w["key"])
            first = seen.setdefault(key, course["id"])
            w["firstEpisode"] = first
            w["review"] = first != course["id"]
    return courses


def add_course(course, evidence, library, replace=False):
    validate(course, evidence)
    root = Path(library)
    if not (root / "index.html").exists():
        raise ValueError("请先 init 建立独立课程库。")
    target = root / "catalog.json"
    catalog = read_json(target)
    item = public_course(course)
    exists = any(c["id"] == item["id"] for c in catalog["courses"])
    if exists and not replace:
        raise ValueError("课程已经存在；只有明确更新时才使用 --replace。")
    catalog["courses"] = [c for c in catalog["courses"] if c["id"] != item["id"]] + [item]
    annotate(catalog["courses"])
    write_json(target, catalog)
    return {"course": item["id"], "words": len(item["words"]), "library": str(root)}


def init_library(library, demo=False):
    root = Path(library)
    if root.exists() and any(root.iterdir()):
        raise ValueError("目标目录非空；请选择新目录，避免影响已有网站。")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL / "assets" / "web", root, dirs_exist_ok=True)
    write_json(root / "catalog.json", {"schemaVersion": VERSION, "courses": []})
    if demo:
        sample = SKILL / "assets" / "demo"
        evidence = {"source": "Original demo by Series English Agent contributors",
                    "lines": parse_subtitles((sample / "dialogue.srt").read_text(encoding="utf-8"))}
        for path in sorted(sample.glob("lesson-*.json")):
            add_course(read_json(path), evidence, root)
    return {"library": str(root.resolve()), "demo": demo}


def export_course(library, course_id, output):
    courses = read_json(Path(library) / "catalog.json")["courses"]
    course = next((c for c in courses if c["id"] == course_id), None)
    if course is None:
        raise ValueError("课程不存在。")
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / (course_id + ".csv")).open("w", encoding="utf-8", newline="") as f:
        f.write("#separator:Comma\n#html:false\n#notetype:Basic\n#columns:Front,Back\n")
        writer = csv.writer(f)
        for w in course["words"]:
            writer.writerow([w["sentence"], f'{w["translation"]}（{w["term"]}：{w["meaning"]} /{w["ipa"]}/）'])
    notes = ["# " + course["series"] + " · " + course["title"], "", "来源标识：" + course["source"], "", "例句均为原创练习句。", ""]
    for w in course["words"]:
        notes.extend(["## " + w["term"], f'/{w["ipa"]}/ · {w["meaning"]}', "", w["sentence"], w["translation"], "", w["tip"], ""])
    (dest / (course_id + ".md")).write_text("\n".join(notes), encoding="utf-8")
    return {"output": str(dest)}


def review(library, progress_path):
    progress = read_json(progress_path)
    if progress.get("schemaVersion") != VERSION or not isinstance(progress.get("records"), dict):
        raise ValueError("不是有效的学习记录导出文件。")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).timestamp() * 1000
    result = []
    for c in read_json(Path(library) / "catalog.json")["courses"]:
        for w in c["words"]:
            state = progress["records"].get(c["id"] + "::" + w["key"], {})
            if state.get("status") == "review" or (type(state.get("due")) in (int, float) and state["due"] <= now):
                result.append({"course": c["id"], "term": w["term"], "meaning": w["meaning"], "sentence": w["sentence"], "status": state.get("status")})
    return {"dueCount": len(result), "words": result}


class LocalHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--library", required=True); p.add_argument("--demo", action="store_true")
    p = sub.add_parser("prepare"); p.add_argument("input"); p.add_argument("--output", required=True); p.add_argument("--source", required=True)
    for name in ("validate", "add"):
        p = sub.add_parser(name); p.add_argument("course"); p.add_argument("--evidence", required=True)
        if name == "add":
            p.add_argument("--library", required=True); p.add_argument("--replace", action="store_true")
    p = sub.add_parser("serve"); p.add_argument("--library", required=True); p.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("export"); p.add_argument("course_id"); p.add_argument("--library", required=True); p.add_argument("--output", required=True)
    p = sub.add_parser("review"); p.add_argument("progress"); p.add_argument("--library", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init": result = init_library(args.library, args.demo)
        elif args.command == "prepare": result = prepare(args.input, args.output, args.source)
        elif args.command == "validate": result = validate(read_json(args.course), read_json(args.evidence))
        elif args.command == "add": result = add_course(read_json(args.course), read_json(args.evidence), args.library, args.replace)
        elif args.command == "export": result = export_course(args.library, args.course_id, args.output)
        elif args.command == "review": result = review(args.library, args.progress)
        else:
            root = Path(args.library).resolve()
            if not (root / "catalog.json").exists(): raise ValueError("课程库不存在，请先 init。")
            handler = functools.partial(LocalHandler, directory=str(root))
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                print(f"学习网站：http://127.0.0.1:{args.port}/（Ctrl+C 停止）", flush=True)
                server.serve_forever()
            return
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as e:
        print("错误：" + str(e), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
