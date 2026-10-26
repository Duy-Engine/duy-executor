#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 demos/*/ 全部判据（执行器 = duy_mini.exe，Windows x64 产物）。

新增一个演示只需两个文件（无需改代码）：

    demos/<name>/<name>.duy     重构件：一个 .duy 文件，内含唯一组件
    demos/<name>/cases.tsv      用例：输入 <TAB> 期望 <TAB> 来源
    demos/<name>/original/      原件存档（可选，不参与执行）

约定：

  · 组件唯一形参名为 concept（str 类型），cases.tsv 第一列即其输入。
  · 结果写入记忆概念 `rt`：有 text 比文本，有 val 比数值。
  · 空文本结果不落库 ⇒ 无该概念记忆且回执为 0，即空串。
"""
import glob
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(BASE, "duy_mini.exe")
NULL = "\\N"
RESULT_CONCEPT = "rt"


def component_key(duy):
    with open(duy, encoding="utf-8-sig") as f:
        for line in f:
            if line.startswith("prim_key"):
                return line.split()[1]
    raise SystemExit("%s 缺 prim_key" % duy)


def load_cases(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for ln, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise SystemExit("%s 第 %d 行字段不足（需 输入<TAB>期望）" % (path, ln))
            inp, exp = parts[0], parts[1]
            rows.append(("" if inp == NULL else inp, "" if exp == NULL else exp, ln))
    return rows


def read_result(out):
    """产物口径判读：有 text 比文本，有 val 比数值；无文本记忆且回执 0 = 空文本结果。"""
    for m in out["mem"]:
        if m.get("concept") == RESULT_CONCEPT and m.get("text"):
            return m["text"]
    if out.get("ret_has"):
        v = out["ret_value"]
        if v == 0:
            return ""
        return "%d" % int(v) if v == int(v) else repr(v)
    raise SystemExit("结果缺失：无 %s 记忆且无回执" % RESULT_CONCEPT)


def run_demo(d):
    name = os.path.basename(d)
    duys = glob.glob(os.path.join(d, "*.duy"))
    if len(duys) != 1:
        raise SystemExit("demos/%s 需要恰好 1 个 .duy，实得 %d" % (name, len(duys)))
    duy = duys[0]
    key = component_key(duy)
    cases = load_cases(os.path.join(d, "cases.tsv"))

    print("== %s（组件 %s，%d 条用例）" % (name, key, len(cases)))
    ok = fail = 0
    for inp, exp, ln in cases:
        r = subprocess.run([EXE, duy, key, "concept=" + inp], capture_output=True)
        if r.returncode != 0:
            print("  ERROR  line %-3d %-16r %s"
                  % (ln, inp, r.stderr.decode("utf-8", "replace").strip()))
            fail += 1
            continue
        got = read_result(json.loads(r.stdout.decode("utf-8")))
        good = got == exp
        print("  %-4s  %-16r -> %-12r" % ("OK" if good else "FAIL", inp, got)
              + ("" if good else "  expect %r" % exp))
        ok, fail = ok + good, fail + (not good)
    return ok, fail


def main():
    if not os.path.isfile(EXE):
        raise SystemExit("找不到 duy_mini.exe（Windows x64 执行器产物，应在本仓根目录）")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dirs = sorted(d for d in glob.glob(os.path.join(BASE, "demos", "*")) if os.path.isdir(d))
    if only:
        dirs = [d for d in dirs if os.path.basename(d) == only]
        if not dirs:
            raise SystemExit("找不到演示目录：demos/%s" % only)
    if not dirs:
        raise SystemExit("demos/ 下没有演示")
    total_ok = total_fail = 0
    for d in dirs:
        ok, fail = run_demo(d)
        total_ok += ok
        total_fail += fail
        print()
    print("%d/%d passed  (%d 个演示)" % (total_ok, total_ok + total_fail, len(dirs)))
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
