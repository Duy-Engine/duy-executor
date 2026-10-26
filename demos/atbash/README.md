# atbash — Atbash 替换密码

## 原件

| 项 | 值 |
|---|---|
| 仓库 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) |
| 文件 | `ciphers/atbash.py` |
| commit | `bc8df6de3143b417c4d174200fd7edd0dbba4ce3`（2024-03-13） |
| 许可证 | MIT |
| 抓取日期 | 2026-10-26 |

原件为**逐字副本未作修改**，位于 `original/atbash.py`；版权与许可全文见 `original/SOURCE.md`。

判据不在本仓手里：`cases.tsv` 前两条**逐字来自原件 docstring**，该仓库有 CI 跑 `pytest --doctest-modules`。

## 重构件

`atbash.duy` 重构的是原件里的 `atbash_slow`（逐字符算术版），不含 `atbash`（查表版）与 `benchmark`。

```
A-Z: 155 - c      a-z: 219 - c      其余: 原样
```

独语没有分支表达式，所以三段偏移合成一句、**用乘法当布尔门**：

```
c + (155 - 2c)·((c≥65)·(c≤90)) + (219 - 2c)·((c≥97)·(c≤122))
```

三段互斥 ⇒ 每段要么贡献完整偏移、要么贡献 0。逐字符遍历靠 `while` + `str_slice` + `str_chr` 拼回。

## 用例

```bash
python run_all.py atbash
```

| 输入 | 期望 | 来源 |
|---|---|---|
| `ABCDEFG` | `ZYXWVUT` | 原件 doctest |
| `aW;;123BX` | `zD;;123YC` | 原件 doctest |
| `''` | `''` | 边界（do-while 守卫路径） |
| `a` | `z` | 边界：小写单字符 |
| `Z` | `A` | 边界：大写边界 |
| `@#1` | `@#1` | 边界：全非字母 |
| `AaZz` | `ZzAa` | 边界：大小写混合 |

7/7 通过。
