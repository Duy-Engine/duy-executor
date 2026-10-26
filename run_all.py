#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 demos/*/ 下的全部用例。

新增一个演示只需两个文件（无需改代码）：

    demos/<name>/<name>.duy     重构件：一个 .duy 文件，内含唯一组件
    demos/<name>/cases.tsv      用例：输入 <TAB> 期望 <TAB> 来源
    demos/<name>/original/      原件存档（可选，不参与执行）

约定：

  · cases.tsv 第一列是输入。单参数组件直接取用；多参数组件按空格分隔，
    依 prim_param 声明序绑定（num 转数值、str 原样）。
  · 结果写入记忆概念 `result`：有 text 比文本，有 val 比数值。
"""
import glob
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from duy_exec import parse_program, run_file, DuyError  # noqa: E402

NULL = "\\N"
RESULT_CONCEPT = "result"


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


def bind_args(comp, raw):
    """按 prim_param 声明序绑定输入。单参数直接取用，多参数按空格拆分。"""
    ps = comp.params
    if not ps:
        return {}
    if len(ps) == 1:
        nm, t = ps[0]
        return {nm: raw if t == "s" else float(raw)}
    parts = raw.split()
    if len(parts) != len(ps):
        raise DuyError("输入 %r 需要 %d 个参数，实得 %d" % (raw, len(ps), len(parts)))
    return {nm: (v if t == "s" else float(v)) for (nm, t), v in zip(ps, parts)}


def read_result(m):
    """读 result 概念：优先文本，其次数值。"""
    e = m.mem_get(RESULT_CONCEPT)
    if e is None:
        raise DuyError("组件未写 %s 概念（与「写了空」不同）" % RESULT_CONCEPT)
    if e.get("text") is not None:
        return e["text"].decode("utf-8", "replace")
    if e.get("val") is not None:
        v = e["val"]
        return ("%d" % int(v)) if v == int(v) else repr(v)
    raise DuyError("%s 概念既无文本也无数值" % RESULT_CONCEPT)


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
    comp = prog[key]
    cases = load_cases(os.path.join(d, "cases.tsv"))

    print("== %s（组件 %s，%d 条用例）" % (name, key, len(cases)))
    ok = fail = 0
    for inp, exp, ln in cases:
        try:
            _, m = run_file(duy, key, bind_args(comp, inp))
            got = read_result(m)
        except DuyError as e:
            print("  ERROR  line %-3d %-16r %s" % (ln, inp, e))
            fail += 1
            continue
        good = got == exp
        print("  %-4s  %-16r -> %-12r" % ("OK" if good else "FAIL", inp, got)
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
