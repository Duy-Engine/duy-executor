# 原件来源与许可

## 来源

| 项 | 值 |
|---|---|
| 仓库 | **TheAlgorithms/Python** |
| 仓库地址 | https://github.com/TheAlgorithms/Python |
| 维护方 | TheAlgorithms（组织）与社区贡献者 |
| 文件 | `conversions/roman_numerals.py` |
| 分支 | `master` |
| 文件最后变更 commit | `351805cd69a90486bf935e95cb675814609029b6`（2026-09-16，仅改 `int_to_roman` 越界校验） |
| 抓取日期 | 2026-10-26 |
| 许可证 | MIT |
| 仓库星标 | 约 225,500（2026-10-26 查得） |

## 使用范围

- `roman_numerals.py` 是**逐字副本，未作任何修改**。副本已含 2026-09-16 上游加入的 `int_to_roman` 越界校验，与上游 `master` 当前文本逐行一致（行尾差异由本仓 `.gitattributes` 的 `eol=lf` 归一）。
- 用途：重构前后对照 + 判据来源。本仓只重构 `roman_to_int`；前五条判据逐字来自其 docstring 锚点（LeetCode No. 13：III/CLIV/MIX/MMD/MMMCMXCIX），上游 CI 跑 `pytest --doctest-modules`。
- 本仓不对原件作任何修改声明或改进主张；原件的正确性由原作者与其 CI 负责。

## 版权与许可（MIT 全文）

```
## MIT License

Copyright (c) 2016-2022 TheAlgorithms and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
