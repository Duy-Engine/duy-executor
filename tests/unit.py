#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行器单元测试：逐算子最小用例 + 词法 + 表达式 + 错误路径。

零依赖，不需要 pytest。运行：

    python tests/unit.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from duy_exec import parse_program, Machine, DuyError  # noqa: E402

HEADER = "prim_key T\nprim_scope per_unit\nprim_ret _r\nprim_param concept str\n"

TESTS = []


def case(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def run(body, args=None):
    """跑一段步行体，返回 (ret, machine)。"""
    prog = parse_program(HEADER + body)
    m = Machine()
    ret = m.run_comp(prog["T"], args or {"concept": "x"})
    return ret, m


def run_expect_error(body, args=None):
    try:
        run(body, args)
    except DuyError as e:
        return str(e)
    raise AssertionError("期望抛 DuyError，但没有")


# ---------------------------------------------------------------- 计算
@case("eval_expr：优先级 1+2*3")
def _():
    ret, _ = run("eval_expr src='1+2*3' out='_r'")
    assert ret == 7.0, ret


@case("eval_expr：min/max 嵌套")
def _():
    ret, _ = run("eval_expr src='min(max(0,3),2)' out='_r'")
    assert ret == 2.0, ret


@case("eval_expr：比较返回 1/0")
def _():
    ret, _ = run("eval_expr src='(3>2)*10' out='_r'")
    assert ret == 10.0, ret


@case("eval_expr：取模是 fmod（-7%3 = -1）")
def _():
    ret, _ = run("eval_expr src='-7%3' out='_r'")
    assert ret == -1.0, ret


@case("eval_expr：空 src 归零")
def _():
    ret, _ = run("eval_expr src='' out='_r'")
    assert ret == 0.0, ret


@case("cond：0 中止本序列")
def _():
    ret, _ = run("cond src='0'\neval_expr src='9' out='_r'")
    assert ret is None, ret


@case("cond：非 0 继续")
def _():
    ret, _ = run("cond src='1'\neval_expr src='9' out='_r'")
    assert ret == 9.0, ret


@case("prob：>0.5 继续（确定性替身）")
def _():
    ret, _ = run("prob src='1'\neval_expr src='9' out='_r'")
    assert ret == 9.0, ret


@case("prob：<=0.5 中止")
def _():
    ret, _ = run("prob src='0.1'\neval_expr src='9' out='_r'")
    assert ret is None, ret


# ---------------------------------------------------------------- 控制
@case("if：条件假不执行体")
def _():
    ret, m = run("if cond='0'\nbody_open\neval_expr src='5' out='_r'\nbody_close\n"
                 "eval_expr src='7' out='_r'")
    assert ret == 7.0, ret


@case("if：条件真执行体")
def _():
    ret, _ = run("if cond='1'\nbody_open\neval_expr src='5' out='_r'\nbody_close")
    assert ret == 5.0, ret


@case("while：do-while 至少跑一轮")
def _():
    # until 恒真 ⇒ 先跑一轮体再退出
    ret, _ = run("eval_expr src='0' out='_i'\n"
                 "while until='1'\nbody_open\neval_expr src='_i+1' out='_i'\nbody_close\n"
                 "eval_expr src='_i' out='_r'")
    assert ret == 1.0, ret


@case("while：until 生效，跑满 3 轮")
def _():
    ret, _ = run("eval_expr src='0' out='_i'\n"
                 "while until='_i>=3'\nbody_open\neval_expr src='_i+1' out='_i'\nbody_close\n"
                 "eval_expr src='_i' out='_r'")
    assert ret == 3.0, ret


@case("stop：提前退出循环")
def _():
    ret, _ = run("eval_expr src='0' out='_i'\n"
                 "while until='0'\nbody_open\n"
                 "eval_expr src='_i+1' out='_i'\n"
                 "if cond='_i>=2'\nbody_open\nstop\nbody_close\n"
                 "body_close\neval_expr src='_i' out='_r'")
    assert ret == 2.0, ret


# ---------------------------------------------------------------- 文本
@case("str_cat：引号内的 # 不是注释")
def _():
    m = Machine()
    ret, m = run("str_cat a='a#b' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"a#b", m.mem_text("r")


@case("str_cat：行尾注释仍被剥离")
def _():
    ret, m = run("str_cat a='x' out_concept='r' out='_r'   # 尾注")
    assert m.mem_text("r") == b"x", m.mem_text("r")


@case("str_cat：记忆作 a，字面作 b")
def _():
    ret, m = run("str_cat a='ab' out_concept='r' out='_r'\n"
                 "str_cat b='cd' from_a='r' out_concept='r2' out='_r'")
    assert m.mem_text("r2") == b"abcd", m.mem_text("r2")


@case("str_cat：非 ASCII 走 UTF-8 字节")
def _():
    ret, m = run("str_cat a='$concept' out_concept='r' out='_r'", {"concept": "中文"})
    assert m.mem_text("r") == "中文".encode("utf-8"), m.mem_text("r")
    assert ret == 6.0, ret


@case("str_slice：运行期 start/len")
def _():
    ret, m = run("str_cat a='abcdef' out_concept='h'\n"
                 "str_slice from_concept='h' start='1' len='3' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"bcd", m.mem_text("r")


@case("str_slice：负 start 返回空")
def _():
    ret, m = run("str_cat a='abcdef' out_concept='h'\n"
                 "str_slice from_concept='h' start='-2' len='3' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"", m.mem_text("r")


@case("str_slice：len 超界截断")
def _():
    ret, m = run("str_cat a='ab' out_concept='h'\n"
                 "str_slice from_concept='h' start='1' len='99' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"b", m.mem_text("r")


@case("str_find：命中返回位置")
def _():
    ret, _ = run("str_cat a='abcdef' out_concept='h'\n"
                 "str_find from_concept='h' a='cd' out='_r'")
    assert ret == 2.0, ret


@case("str_find：未命中返回 -1")
def _():
    ret, _ = run("str_cat a='abc' out_concept='h'\n"
                 "str_find from_concept='h' a='zz' out='_r'")
    assert ret == -1.0, ret


@case("str_ord：首字节 ASCII")
def _():
    ret, _ = run("str_cat a='A' out_concept='h'\nstr_ord from_concept='h' out='_r'")
    assert ret == 65.0, ret


@case("str_ord：空串返回 0")
def _():
    ret, _ = run("str_cat a='' out_concept='h'\nstr_ord from_concept='h' out='_r'")
    assert ret == 0.0, ret


@case("str_chr：码 → 字符")
def _():
    ret, m = run("str_chr n='66' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"B", m.mem_text("r")


@case("str_chr：超 255 截断为 0")
def _():
    ret, m = run("str_chr n='300' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"\x00", m.mem_text("r")


@case("str_num：整数不带小数点")
def _():
    ret, m = run("str_num n='42' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"42", m.mem_text("r")


@case("str_num：非整数走 %.6g")
def _():
    ret, m = run("str_num n='1.5' out_concept='r' out='_r'")
    assert m.mem_text("r") == b"1.5", m.mem_text("r")


@case("str_eq：ra 槽 vs 字面")
def _():
    ret, _ = run("str_slice a='ab' start='0' len='2' ro='_t'\n"
                 "str_eq ra='_t' a='ab' out='_r'")
    assert ret == 1.0, ret


@case("str_eq：from_concept vs 字面")
def _():
    ret, _ = run("str_cat a='abc' out_concept='h'\n"
                 "str_eq from_concept='h' a='abc' out='_r'")
    assert ret == 1.0, ret


@case("str_eq：缺左操作数报错")
def _():
    e = run_expect_error("str_eq a='x' out='_r'")
    assert "from_concept" in e, e


@case("str_len：按字节计长（中文 3 字节/字）")
def _():
    ret, _ = run("str_cat a='$concept' out_concept='h'\nstr_len concept='h' out='_r'",
                 {"concept": "中"})
    assert ret == 3.0, ret


# ---------------------------------------------------------------- 变量与记忆
@case("write_var / read_var：往返")
def _():
    ret, _ = run("eval_expr src='7' out='_v'\nwrite_var name='x' from='_v'\n"
                 "read_var name='x' out='_y'\neval_expr src='_y*2' out='_r'")
    assert ret == 14.0, ret


@case("read_var：未赋值变量读 0")
def _():
    ret, _ = run("read_var name='nope' out='_r'")
    assert ret == 0.0, ret


@case("write_mem：数值记忆，回执为实落值")
def _():
    ret, _ = run("write_mem type='knowledge' concept='k' val=10 decay=1 out='_r'")
    assert ret == 10.0, ret


@case("write_mem：val='10' 是字符串（写文本记忆）")
def _():
    ret, m = run("write_mem type='text' concept='k' val='10' out='_r'")
    assert m.mem_text("k") == b"10", m.mem_text("k")


@case("scale_mem：不崩，回执 0")
def _():
    ret, _ = run("write_mem type='knowledge' concept='k' val=10 decay=1 out='_a'\n"
                 "scale_mem concepts='k' ratio=0.5 out='_r'")
    assert ret == 0.0, ret


# ---------------------------------------------------------------- 词法与错误
@case("词法：重复 prim_key 报错")
def _():
    src = HEADER + "prim_key T\nprim_scope per_unit\n"
    try:
        parse_program(src)
    except DuyError as e:
        assert "重复" in str(e), e
        return
    raise AssertionError("重复 prim_key 未报错")


@case("错误：未知算子点名")
def _():
    e = run_expect_error("measure x=1")
    assert "measure" in e, e


@case("错误：body_open 未闭合")
def _():
    try:
        parse_program(HEADER + "if cond='1'\nbody_open\neval_expr src='1' out='_r'")
    except DuyError as e:
        assert "未闭合" in str(e), e
        return
    raise AssertionError("未闭合 body 未报错")


def main():
    ok = fail = 0
    for name, fn in TESTS:
        try:
            fn()
            ok += 1
            print("  OK    %s" % name)
        except AssertionError as e:
            fail += 1
            print("  FAIL  %s\n        %s" % (name, e))
        except Exception as e:  # noqa: BLE001
            fail += 1
            print("  ERROR %s\n        %r" % (name, e))
    print("\n%d/%d passed  (%d 条单测)" % (ok, ok + fail, len(TESTS)))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
