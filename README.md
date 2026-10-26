# duy-executor

[![test](https://github.com/Duy-Engine/duy-executor/actions/workflows/test.yml/badge.svg)](https://github.com/Duy-Engine/duy-executor/actions/workflows/test.yml)

独语（`.duy`）行式组件的**零依赖执行器**，以及一组「外部实现 → 重构件」的对照演示。

每个演示都取一份**公开的原件**，用**原作者写的判据**验证重构结果——判据不在本仓手里，也不需要信任作者本人。

## 演示

| 演示 | 原件 | 判据 | 结果 |
|---|---|---|---|
| [atbash](demos/atbash/) | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) `ciphers/atbash.py`（MIT） | 原作者 doctest ×2 + 边界 ×5 | **7/7** |

## 快速开始

```bash
python run_all.py               # 跑全部演示
python run_all.py atbash        # 只跑一个
python duy_exec.py demos/atbash/atbash.duy ATBASH concept=ABCDEFG    # 单条
```

CI 在 Python 3.9 / 3.12 两个版本上跑同一套用例（`.github/workflows/test.yml`）。

## 新增一个演示

三个文件，**不需要改代码**——`run_all.py` 自动发现 `demos/*/`：

```
demos/<name>/
├── <name>.duy     重构件：一个 .duy 文件，内含唯一组件
├── cases.tsv      用例：输入 <TAB> 期望 <TAB> 来源
└── original/      原件存档（可选，不参与执行）
```

约定三条：

1. 组件唯一形参名为 `concept`（`str` 类型），对应 `cases.tsv` 第一列的输入
2. 结果写入记忆概念 `result`
3. 每个演示目录恰好一个 `.duy`、一个组件

## 执行器支持范围

| 类 | 算子 |
|---|---|
| 计算 | `eval_expr` `cond` `prob` |
| 控制 | `if` `while` `stop` |
| 文本 | `str_cat` `str_slice` `str_find` `str_ord` `str_num` `str_chr` `str_eq` `str_len` |
| 变量 | `read_var` `write_var` |
| 记忆 | `write_mem` `scale_mem`（纯内存，不落盘） |

共 **18 个**。**不支持**（超出即报错并点名）：依赖运行环境的算子——`measure` / `mem_exec` / `attack` / `unit_foreach` / `seg_call` / `verify_lib` 等。

## 语义口径（与实现必须一致的五条）

写好 `.duy` 之前先看这五条，都是踩过的：

1. **取模 = `fmod`**，保被除数符号。Python 原生 `%` 是 floor 语义，直接照搬会错。
2. **`while` 是 do-while**：先跑 body 再判 `until`（`>0` 停）。**空/零边界必须前置守卫**，否则体至少跑一轮。
3. **文本是字节序列**，不是码点。内部一律 `bytes`。
4. **参数类型两种写法要归一化**：契约写 `s/n/a/e`，实际文件写 `str/num/expr/arr`。
5. **字段值的引号决定类型**：`val=10` 是数值，`val='10'` 是字符串（会写成文本记忆）。`n` 类字段必须写裸数字；`e` 类字段才是带引号的表达式。

## 边界

- **本执行器是独立实现，不是唯一实现**。用例全部通过只说明「它符合这些用例」，不等于「它与其它实现逐字节等价」——后者未做。
- **`prob` 是确定性替身**：用固定 `0.5` 阈值，不抽真随机。含 `prob` 的演示结果不代表真实随机行为。
- **`scale_mem` 回执语义未核对**，当前恒写 0，只验证不崩。

## 许可

本仓代码 MIT（见 [LICENSE](LICENSE)）。`demos/*/original/` 下的原件**各自保留其原始许可**，出处与许可全文见各演示的 `SOURCE.md`。
