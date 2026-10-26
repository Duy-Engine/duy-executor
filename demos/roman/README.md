# roman：roman_to_int 重构演示

- **原件**：[TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) `conversions/roman_numerals.py` 的 `roman_to_int`（MIT）——减法前缀规则（v[i] < v[i+1] ⇒ 加 v[i+1]-v[i] 并跳 2）
- **重构件**：`roman.duy`——while 逐字符 + 码点映射内联（I=1 V=5 X=10 L=50 C=100 D=500 M=1000）+ 哨兵 '0'（越界字符读零）
- **判据**：`cases.tsv` 9 条——前 5 条逐字来自原件 doctest（III/CLIV/MIX/MMD/MMMCMXCIX），后 4 条本仓边界

## 状态

9/9 通过（引擎 shadow 验收与本地执行器双端一致）。
