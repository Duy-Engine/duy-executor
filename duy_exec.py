#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duy_exec.py —— 独语（.duy）行式组件的零依赖 Python 执行器

定位：`.duy` 语言规范的独立参考实现——用一份可独立运行的实现，
      检验这套语法能否被另一份实现一致地复现。

语义口径（写组件前必读，逐条都是踩过的）：
  · 取模 = fmod（保被除数符号）；Python 原生 % 是 floor 语义 —— 不等价处必须显式模拟
  · 除法 = 浮点除（表达式域全 float，不截断）
  · 文本 = 字节序列（bytes），不是码点
  · while = do-while（先跑 body 再判 until，>0 停）

支持范围（壳能力子集）：
  计算  eval_expr / cond / prob
  控制  if / while / stop
  文本  str_cat / str_slice / str_find / str_ord / str_num / str_chr / str_eq / str_len
  变量  read_var / write_var
  记忆  write_mem / scale_mem（纯内存，不落盘）
不支持（装载期点名报错）：measure / mem_exec / attack / unit_foreach / seg_call / verify_lib …
"""

import sys
import os
import re
import math

# ---------------------------------------------------------------- 异常
class DuyError(Exception):
    pass


# ---------------------------------------------------------------- 词法
_FIELD = re.compile(r"(\w+)=('([^']*)'|(\S+))")


def parse_line(line):
    """一行步行 → (op, {field: ('str'|'num', value)})。裸值=数值，单引号值=字符串。"""
    m = re.match(r"([A-Za-z_]\w*)\s*(.*)$", line)
    if not m:
        raise DuyError("无法解析的行：" + line)
    op, rest = m.group(1), m.group(2)
    fields = {}
    for fm in _FIELD.finditer(rest):
        k = fm.group(1)
        if fm.group(3) is not None:
            fields[k] = ("str", fm.group(3))
        else:
            raw = fm.group(4)
            try:
                fields[k] = ("num", float(raw))
            except ValueError:
                fields[k] = ("str", raw)
    return op, fields


# ---------------------------------------------------------------- 结构
class Comp(object):
    def __init__(self, key):
        self.key = key
        self.scope = "per_unit"
        self.phase = None
        self.ret = None          # '_slot' / '$param' / None
        self.params = []         # [(name, type)]
        self.steps = []


def strip_comment(line):
    """剥离注释（# 到行尾）。引号内的 # 属于字面量，不是注释。"""
    quoted = False
    for i, ch in enumerate(line):
        if ch == "'":
            quoted = not quoted
        elif ch == "#" and not quoted:
            return line[:i]
    return line


def parse_program(text):
    """文本 → {key: Comp}。body_open/body_close 驱动嵌套栈，缩进无意义。"""
    comps = {}
    cur = None
    stack = None
    for raw in text.splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        if line.startswith("prim_key"):
            parts = line.split()
            if len(parts) < 2:
                raise DuyError("prim_key 缺名字")
            cur = Comp(parts[1])
            if cur.key in comps:
                raise DuyError("重复的 prim_key：%s（同名组件会互相覆盖，拒绝装载）" % cur.key)
            comps[cur.key] = cur
            stack = [cur.steps]
            continue
        if cur is None:
            raise DuyError("步行体出现在 prim_key 之前：" + line)
        if line.startswith("prim_scope"):
            cur.scope = line.split()[1]
            continue
        if line.startswith("prim_phase"):
            cur.phase = line.split()[1]
            continue
        if line.startswith("prim_ret"):
            cur.ret = line.split(None, 1)[1].strip()
            continue
        if line.startswith("prim_param"):
            parts = line.split()
            if len(parts) != 3:
                raise DuyError("prim_param 形态应为「名字 类型」：" + line)
            # 主版写全称（str/num/expr/arr），契约写单字母（s/n/a/e）——归一化
            t = {"str": "s", "num": "n", "expr": "e", "arr": "a"}.get(parts[2], parts[2])
            if t not in ("s", "n", "a", "e"):
                raise DuyError("未知参数类型 %r" % parts[2])
            cur.params.append((parts[1], t))
            continue
        if line == "body_open":
            if not stack[-1]:
                raise DuyError("body_open 前没有步")
            body = []
            stack[-1][-1]["body"] = body
            stack.append(body)
            continue
        if line == "body_close":
            if len(stack) == 1:
                raise DuyError("body_close 无对应 body_open")
            stack.pop()
            continue
        op, fields = parse_line(line)
        stack[-1].append({"op": op, "f": fields, "body": None})
    if stack is not None and len(stack) != 1:
        raise DuyError("body_open 未闭合")
    return comps


# ---------------------------------------------------------------- 表达式
_TOK = re.compile(r"\s*(\d+\.?\d*(?:[eE][-+]?\d+)?|\$?[A-Za-z_]\w*|>=|<=|==|!=|[-+*/%^(),<>])")


def tokenize_expr(src):
    out = []
    pos = 0
    while pos < len(src):
        m = _TOK.match(src, pos)
        if not m:
            if src[pos].isspace():
                pos += 1
                continue
            raise DuyError("表达式非法字符 %r in %r" % (src[pos], src))
        out.append(m.group(1))
        pos = m.end()
    return out


FUNCS = {
    "min": lambda a: min(a),
    "max": lambda a: max(a),
    "neg": lambda a: -a[0],
    "sqrt": lambda a: math.sqrt(a[0]) if a[0] >= 0 else 0.0,
    "abs": lambda a: abs(a[0]),
    "exp": lambda a: math.exp(a[0]),
    "log": lambda a: math.log(a[0]) if a[0] > 0 else 0.0,
    "sin": lambda a: math.sin(a[0]),
    "cos": lambda a: math.cos(a[0]),
    "floor": lambda a: math.floor(a[0]),
}


class ExprEval(object):
    """递归下降。返回 float。取模用 fmod（C 语义），除法用浮点除。"""

    def __init__(self, src, lookup):
        self.toks = tokenize_expr(src)
        self.i = 0
        self.lookup = lookup

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, want=None):
        t = self.peek()
        if t is None:
            raise DuyError("表达式意外结束")
        if want is not None and t != want:
            raise DuyError("表达式期望 %r 实得 %r" % (want, t))
        self.i += 1
        return t

    def run(self):
        v = self.cmp()
        if self.i != len(self.toks):
            raise DuyError("表达式多余 token：%r" % (self.toks[self.i:],))
        return v

    def cmp(self):
        v = self.add()
        while self.peek() in (">", "<", ">=", "<=", "==", "!="):
            op = self.eat()
            r = self.add()
            if op == ">":
                v = 1.0 if v > r else 0.0
            elif op == "<":
                v = 1.0 if v < r else 0.0
            elif op == ">=":
                v = 1.0 if v >= r else 0.0
            elif op == "<=":
                v = 1.0 if v <= r else 0.0
            elif op == "==":
                v = 1.0 if v == r else 0.0
            else:
                v = 1.0 if v != r else 0.0
        return v

    def add(self):
        v = self.mul()
        while self.peek() in ("+", "-"):
            op = self.eat()
            r = self.mul()
            v = v + r if op == "+" else v - r
        return v

    def mul(self):
        v = self.unary()
        while self.peek() in ("*", "/", "%"):
            op = self.eat()
            r = self.unary()
            if op == "*":
                v = v * r
            elif op == "/":
                v = (v / r) if r != 0 else 0.0          # 浮点除，不截断
            else:
                v = math.fmod(v, r) if r != 0 else 0.0  # ★ fmod，非 Python 的 floor %
        return v

    def unary(self):
        if self.peek() == "-":
            self.eat()
            return -self.unary()
        if self.peek() == "+":
            self.eat()
            return self.unary()
        return self.power()

    def power(self):
        v = self.atom()
        if self.peek() == "^":
            self.eat()
            r = self.unary()   # 右结合
            v = v ** r
        return v

    def atom(self):
        t = self.eat()
        if t == "(":
            v = self.cmp()
            self.eat(")")
            return v
        if re.match(r"^\d", t):
            return float(t)
        if t in FUNCS:
            self.eat("(")
            args = []
            if self.peek() != ")":
                args.append(self.cmp())
                while self.peek() == ",":
                    self.eat(",")
                    args.append(self.cmp())
            self.eat(")")
            return float(FUNCS[t](args))
        return self.lookup(t)


# ---------------------------------------------------------------- 机器
class Machine(object):
    """槽 = 局部寄存器（float 或 bytes）；vars = 跨原语变量表；mem = 记忆（type,concept）"""

    def __init__(self, trace=False):
        self.slots = {}
        self.vars = {}
        self.mem = {}
        self.params = {}     # name -> (type, value)
        self.trace = trace

    # --- 值存取 ---
    def get_slot(self, name):
        if name in self.slots:
            return self.slots[name]
        if name in self.vars:
            return self.vars[name]
        raise DuyError("未初始化的槽：%s" % name)

    def set_slot(self, name, v):
        if name.startswith("$"):
            name = name[1:]
        self.slots[name] = v

    def lookup(self, tok):
        """表达式内的符号解析。$str 参数 → 其值当变量名再查。"""
        if tok.startswith("$"):
            nm = tok[1:]
            if nm not in self.params:
                raise DuyError("未声明的形参：%s" % tok)
            ptype, pval = self.params[nm]
            if ptype == "e":
                return float(ExprEval(str(pval), self.lookup).run())
            if ptype == "n":
                return float(pval)
            # str 参数：值当变量名/槽名读当前值
            key = str(pval)
            if key in self.vars:
                return float(self.vars[key])
            if key in self.slots:
                return float(self.slots[key])
            raise DuyError("str 参数 %s 的值 %r 既不是变量也不是槽" % (tok, key))
        if tok.startswith("_"):
            return float(self.get_slot(tok))
        if tok in self.slots:
            return float(self.slots[tok])
        if tok in self.vars:
            return float(self.vars[tok])
        raise DuyError("表达式引用了未知符号：%s" % tok)

    # --- 字段 ---
    def fraw(self, st, key):
        f = st["f"].get(key)
        return None if f is None else f[1]

    def fstr(self, st, key, default=None):
        f = st["f"].get(key)
        if f is None:
            return default
        return f[1] if f[0] == "str" else str(f[1])

    def fnum(self, st, key, default=None):
        f = st["f"].get(key)
        if f is None:
            return default
        return f[1]

    def fexpr(self, st, key, default=0.0):
        """字段当表达式求值。'$param'(expr 型) → 求参数内容；否则求文本。"""
        f = st["f"].get(key)
        if f is None:
            return default
        if f[0] == "num":
            return float(f[1])
        src = f[1].strip()
        if not src:
            return default
        if re.match(r"^\$[A-Za-z_]\w*$", src):
            nm = src[1:]
            if nm in self.params and self.params[nm][0] == "e":
                return float(ExprEval(str(self.params[nm][1]), self.lookup).run())
        return float(ExprEval(src, self.lookup).run())

    # --- 记忆 ---
    def mem_get(self, concept, mtype=None):
        for (t, c), e in self.mem.items():
            if c == concept and (mtype is None or t == mtype):
                return e
        return None

    def mem_text(self, concept):
        e = self.mem_get(concept)
        if e is None or e.get("text") is None:
            return b""
        return e["text"]

    def has_concept(self, concept):
        """概念是否存在（用于区分「写了空」与「从未写」）。"""
        return any(c == concept for (_t, c) in self.mem)

    def mem_set(self, concept, mtype="text", val=None, text=None, decay=0.5):
        self.mem[(mtype, concept)] = {"val": val, "text": text, "decay": decay}

    # --- 执行 ---
    def run_comp(self, comp, args):
        self.slots = {}
        self.vars = {}
        self.params = {}
        for idx, (nm, ptype) in enumerate(comp.params):
            if nm in args:
                v = args[nm]
            else:
                raise DuyError("组件 %s 缺少参数 %s" % (comp.key, nm))
            if ptype in ("n", "e"):
                self.params[nm] = (ptype, float(v) if ptype == "n" else str(v))
            else:
                self.params[nm] = (ptype, v)
        sig = self.run_steps(comp.steps)
        if sig == "end":
            return None
        if comp.ret is None:
            return None
        nm = comp.ret[1:] if comp.ret.startswith("$") else comp.ret
        if nm in self.slots:
            return self.slots[nm]
        if nm in self.params:
            return self.params[nm][1]
        return None

    def run_steps(self, steps):
        for st in steps:
            sig = self.run_step(st)
            if sig:
                return sig
        return None

    def run_step(self, st):
        op = st["op"]
        if self.trace:
            sys.stderr.write("  [step] %s %s\n" % (op, st["f"]))
        fn = getattr(self, "op_" + op, None)
        if fn is None:
            raise DuyError(
                "算子 %r 不在本执行器支持范围（壳能力子集之外）" % op)
        return fn(st)

    # --- 计算 ---
    def op_eval_expr(self, st):
        v = self.fexpr(st, "src", 0.0)
        if not math.isfinite(v):
            v = self.fexpr(st, "fallback", 0.0)
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, v)
        return None

    def op_cond(self, st):
        src = self.fstr(st, "src")
        if not src:              # 空 = 恒真
            return None
        v = float(ExprEval(src, self.lookup).run())
        return None if v > 0 else "end"

    def op_prob(self, st):
        src = self.fstr(st, "src")
        if not src:
            return None
        v = float(ExprEval(src, self.lookup).run())
        # 恒定抽一次 RNG；执行器用确定性 0.5 简化（差分测试时需喂同一随机源）
        return None if v > 0.5 else "end"

    def op_read_var(self, st):
        nm = self.fstr(st, "name")
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, self.vars.get(nm, 0.0))
        return None

    def op_write_var(self, st):
        nm = self.fstr(st, "name")
        frm = self.fstr(st, "from")
        v = self.get_slot(frm) if frm else 0.0
        self.vars[nm] = v
        return None

    def op_write_mem(self, st):
        mtype = self.fstr(st, "type", "text")
        concept = self.fstr(st, "concept")
        decay = self.fexpr(st, "decay", 0.5)
        f = st["f"].get("val")
        text = None
        val = None
        if f is None:
            val = 0.0
        elif f[0] == "num":
            val = float(f[1])
        else:
            nm = f[1]
            if nm == "":
                text = b""                      # 空字面量 → 空文本记忆
            else:
                key = nm[1:] if nm.startswith("$") else nm
                if key in self.params:
                    ptype, pval = self.params[key]
                    if isinstance(pval, (bytes, bytearray)):
                        text = bytes(pval)
                    elif ptype == "s":
                        text = str(pval).encode("utf-8", "replace")
                    else:
                        val = float(pval)
                elif key in self.slots:
                    sv = self.slots[key]
                    if isinstance(sv, (bytes, bytearray)):
                        text = bytes(sv)
                    else:
                        val = float(sv)
                else:
                    text = nm.encode("utf-8", "replace")
        self.mem_set(concept, mtype, val=val, text=text, decay=decay)
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, val if text is None else float(len(text)))
        return None

    def op_scale_mem(self, st):
        concepts = self.fstr(st, "concepts") or ""
        ratio = self.fexpr(st, "ratio", 1.0)
        for (t, c), e in self.mem.items():
            if c in concepts.split(","):
                if e.get("val") is not None:
                    e["val"] = e["val"] * ratio
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, 0.0)
        return None

    # --- 文本 ---
    def op_str_len(self, st):
        concept = self.fstr(st, "concept")
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(len(self.mem_text(concept))))
        return None

    def op_str_slice(self, st):
        fc = self.fstr(st, "from_concept")
        if fc is not None:
            hay = self.mem_text(fc)
        else:
            a = self.fstr(st, "a")
            hay = a.encode("utf-8") if a is not None else b""
        start = int(self.fexpr(st, "start", 0.0))
        ln = int(self.fexpr(st, "len", 0.0))
        piece = hay[start:start + ln] if ln >= 0 else b""
        ro = self.fstr(st, "ro")
        oc = self.fstr(st, "out_concept")
        if oc:
            self.mem_set(oc, "text", text=piece)
        if ro:
            self.set_slot(ro, piece)
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(len(piece)))
        return None

    def op_str_find(self, st):
        fc = self.fstr(st, "from_concept")
        fc2 = self.fstr(st, "ra")
        hay = self.mem_text(fc) if fc else (self.get_slot(fc2) if fc2 else b"")
        needle = self.fstr(st, "rb")
        if needle is None:
            a = self.fstr(st, "a")
            needle = a.encode("utf-8") if a is not None else b""
        else:
            needle = self.get_slot(needle)
        if not isinstance(hay, (bytes, bytearray)):
            hay = str(hay).encode("utf-8")
        if not isinstance(needle, (bytes, bytearray)):
            needle = str(needle).encode("utf-8")
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(hay.find(bytes(needle))))
        return None

    def op_str_ord(self, st):
        fc = self.fstr(st, "from_concept")
        a = self.fstr(st, "a")
        data = self.mem_text(fc) if fc else (a.encode("utf-8") if a is not None else b"")
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(data[0]) if data else 0.0)
        return None

    def op_str_chr(self, st):
        n = int(self.fexpr(st, "n", 0.0))
        if n < 0 or n > 255:
            n = 0            # 超界归 0（不是取模）
        ch = bytes([n])
        ro = self.fstr(st, "ro")
        oc = self.fstr(st, "out_concept")
        if oc:
            self.mem_set(oc, "text", text=ch)
        if ro:
            self.set_slot(ro, ch)
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(n))
        return None

    def op_str_num(self, st):
        n = self.fexpr(st, "n", 0.0)
        prefix = self.fstr(st, "prefix") or ""
        s = prefix + ("%d" % int(n) if n == int(n) else "%.6g" % n)
        oc = self.fstr(st, "out_concept")
        if oc:
            self.mem_set(oc, "text", text=s.encode("utf-8"))
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(len(s)))
        return None

    def _lit_or_param(self, st, key):
        """字面量或 $str 参数 → bytes。str 参数取数据值，其余按字面。"""
        lit = self.fstr(st, key)
        if lit is None:
            return b""
        if lit.startswith("$"):
            nm = lit[1:]
            if nm in self.params and self.params[nm][0] == "s":
                return str(self.params[nm][1]).encode("utf-8", "replace")
            raise DuyError("字段 %s 引用了非 str 形参 %r" % (key, lit))
        return lit.encode("utf-8", "replace")

    def op_str_cat(self, st):
        parts = []
        for lit_key, src_key in (("a", "from_a"), ("b", "from_b")):
            src = self.fstr(st, src_key)
            if src:                       # 记忆取指源：非空覆盖同侧字面
                parts.append(self.mem_text(src))
            else:
                parts.append(self._lit_or_param(st, lit_key))
        joined = b"".join(bytes(p) if not isinstance(p, bytes) else p for p in parts)
        oc = self.fstr(st, "out_concept")
        if oc:
            self.mem_set(oc, "text", text=joined)
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, float(len(joined)))
        return None

    def op_str_eq(self, st):
        """左 = ra 槽 | from_concept 记忆；右 = a 字面或 $str 参数（与其它文本算子一致）。"""
        ra = self.fstr(st, "ra")
        fc = self.fstr(st, "from_concept")
        if ra:
            v = self.get_slot(ra)
            if not isinstance(v, (bytes, bytearray)):
                raise DuyError("str_eq 的 ra 槽 %r 不是文本（是数值）" % ra)
            left = bytes(v)
        elif fc:
            left = self.mem_text(fc)
        else:
            raise DuyError("str_eq 需要 ra（槽）或 from_concept（记忆）作左操作数")
        right = self._lit_or_param(st, "a")
        out = self.fstr(st, "out")
        if out:
            self.set_slot(out, 1.0 if left == right else 0.0)
        return None

    # --- 控制 ---
    def op_if(self, st):
        c = self.fexpr(st, "cond", 0.0)
        if c > 0:
            sig = self.run_steps(st["body"] or [])
            if sig == "end":
                return "end"
            if sig == "stop":
                return "stop"
        return None

    def op_while(self, st):
        body = st["body"] or []
        if not body:
            raise DuyError("while 的 body 为空")
        guard = 0
        while True:
            sig = self.run_steps(body)
            if sig == "end":
                return "end"
            if sig == "stop":
                return None
            guard += 1
            if guard > 100000:
                raise DuyError("while 轮数护栏触发（>100000）")
            until = self.fexpr(st, "until", 0.0)
            if until > 0:
                return None

    def op_stop(self, st):
        return "stop"


# ---------------------------------------------------------------- CLI
def run_file(path, comp_key, args, trace=False):
    with open(path, "rb") as f:
        text = f.read().decode("utf-8", "replace").lstrip("\ufeff")
    comps = parse_program(text)
    if comp_key not in comps:
        raise DuyError("组件 %r 不在 %s（现有：%s）"
                       % (comp_key, path, ", ".join(sorted(comps))))
    m = Machine(trace=trace)
    return m.run_comp(comps[comp_key], args), m


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(
            "用法: duy_exec.py <file.duy> <COMPONENT> [k=v ...]\n")
        return 2
    path, key = argv[1], argv[2]
    args = {}
    for kv in argv[3:]:
        k, _, v = kv.partition("=")
        try:
            args[k] = float(v)
        except ValueError:
            args[k] = v
    try:
        ret, m = run_file(path, key, args, trace=("-v" in os.environ.get("DUY_TRACE", "")))
    except DuyError as e:
        sys.stderr.write("DUY ERROR: %s\n" % e)
        return 1
    if isinstance(ret, bytes):
        print(ret.decode("utf-8", "replace"))
    elif ret is None:
        print("")
    else:
        print(("%d" % int(ret)) if float(ret) == int(ret) else repr(ret))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
