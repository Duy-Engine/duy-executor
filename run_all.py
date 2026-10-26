#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 demos/*/ 下的全部用例。

新增一个演示只需两个文件（无需改代码）：

    demos/<name>/<name>.duy     重构件：一个 .duy 文件，内含唯一组件
    demos/<name>/cases.tsv      用例：输入 <TAB> 期望 <TAB> 来源
    demos/<name>/original/      原件存档（可选，不参与执行）

约定：
  · 组件唯一形参名为 `concept`（str），即 cases.tsv 第一列的输入
  · 结果写入记忆概念 `result`，执行器读它的文本与期望比对
"""
import glob
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from duy_exec import parse_program, run_file, DuyError  # noqa: E402

NULL = "\\N"
RESULT_CONCEPT = "result"
INPUT_PARAM = "concept"


def demo_dirs(only=None):
    dirs = sorted(d for d in glob.glob(os.path.join(BASE, "demos", "*")) if os.path.isdir(d))
    if only:
        dirs = [d for d in dirs if os.path.basename(d) == only]
        if not dirs:
            raise SystemExit("找不到演示目录：demos/%s" % only)
    return dirs


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


def run_demo(d):
    name = os.path.basename(d)
    duys = glob.glob(os.path.join(d, "*.duy"))
    if len(duys) != 1:
        raise SystemExit("demos/%s 需要恰好 1 个 .duy，实得 %d" % (name, len(duys)))
    duy = duys[0]
    prog = parse_program(open(duy, encoding="utf-8-sig").read())
    if len(prog) != 1:
        raise SystemExit("demos/%s 的 .duy 需恰好 1 个组件，实得 %d" % (name, len(prog)))
    key = next(iter(prog))
    cases = load_cases(os.path.join(d, "cases.tsv"))

    print("== %s（组件 %s，%d 条用例）" % (name, key, len(cases)))
    ok = fail = 0
    for inp, exp, ln in cases:
        try:
            _, m = run_file(duy, key, {INPUT_PARAM: inp})
            got = m.mem_text(RESULT_CONCEPT).decode("ascii", "replace")
        except DuyError as e:
            print("  ERROR  line %-3d %-16r %s" % (ln, inp, e))
            fail += 1
            continue
        good = got == exp
        print("  %-4s  %-16r -> %-16r" % ("OK" if good else "FAIL", inp, got)
              + ("" if good else "  expect %r" % exp))
        if good:
            ok += 1
        else:
            fail += 1
    return ok, fail


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dirs = demo_dirs(only)
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
