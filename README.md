# duy-executor

[![test](https://github.com/Duy-Engine/duy-executor/actions/workflows/test.yml/badge.svg)](https://github.com/Duy-Engine/duy-executor/actions/workflows/test.yml)

`.duy` 行式组件执行器（Windows 单文件 `duy_mini.exe`），以及一组「外部实现 → 重构件」的对照演示。

每个演示都取一份**公开的原件**：锚点用例逐字来自原件 doctest，边界用例由本仓补充并在用例表里标注来源。

## 演示

| 演示 | 原件 | 判据 | 结果 |
|---|---|---|---|
| [atbash](demos/atbash/) | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) `ciphers/atbash.py`（MIT） | 上游 doctest ×2 + 本仓边界 ×5 | **7/7** |
| [roman](demos/roman/) | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) `conversions/roman_numerals.py`（MIT） | 上游 doctest ×5 + 本仓边界 ×4 | **9/9** |

## 快速开始

```bash
python run_all.py                                             # 跑全部演示判据
python run_all.py atbash                                      # 只跑一个
duy_mini.exe demos/atbash/atbash.duy ATBASH concept=ABCDEFG   # 单条（输出 JSON 回执）
```

CI 在 windows-latest 上跑同一套判据（`.github/workflows/test.yml`）。

## 约定

1. 组件唯一形参名为 `concept`（`str` 类型），对应 `cases.tsv` 第一列的输入
2. 结果写入记忆概念 `rt`：有 text 比文本，有 val 比数值
3. 空文本结果不落库：无该概念记忆且回执为 0，即空串
4. 文本按 UTF-8 字节处理（中文 3 字节/字），切片落在字节边界

## 新增一个演示

三个文件，**不需要改代码**——`run_all.py` 自动发现 `demos/*/`：

```
demos/<name>/
├── <name>.duy     重构件：一个 .duy 文件，内含唯一组件
├── cases.tsv      用例：输入 <TAB> 期望 <TAB> 来源
└── original/      原件存档（可选，不参与执行）
```

格式与边界语义的完整说明见 [`docs/format.md`](docs/format.md)。

## 边界

- 执行器以 **Windows x64 产物二进制**随仓发布，实现源码不在本仓。单条运行输出 JSON 回执（`ret_value` 与全部记忆副作用），判据判读规则见 `run_all.py`。
- 判据全部通过只说明「产物符合这些用例」。

## 许可

本仓代码 MIT（见 [LICENSE](LICENSE)）。`demos/*/original/` 下的原件**各自保留其原始许可**，出处与许可全文见各演示的 `SOURCE.md`。
