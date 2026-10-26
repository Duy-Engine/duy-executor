# 引擎重构档案：roman_to_int

## 流程（引擎重构链全程）
1. 感知：原件 `roman_to_int`（减法前缀规则）→ 骨架 = CHAR_VAL 子组件（码点→值 if 链）+ ROMAN_TO_INT 主组件（while 逐字符 + call 子组件 + 减法前缀分支）
2. refactor 命令 ×4（v1 ret 槽错 → v2 字符串手术不彻底 → v3 全局部槽 → v4 回执落写类步）——**--update 原地更新实证**（同 key 重发=段替换）
3. shadow 锚点验收：0/9（ret_value 恒 0）——**进行中**

## 判别矩阵（shadow 组件化判别）
| 判别件 | 结果 | 裁决 |
|---|---|---|
| W1：eval 局部槽 → write_mem val='$_t' | ret=7 ✓ | write_mem 局部槽 val 路径通 |
| W2：write_mem 字面 val='3.5' | ret=3.5 ✓ | remember 写入正常 |
| B1：str_cat + str_len → write_mem val='$_n' | ret=0.94921875 ✗ | **str_len 回执非长度** |
| B2：while 迭代 _i | 编译拒（判别件自身笔误 $i） | 待重跑 |

## 未查明（挂账）
`str_len concept='rm_in'` 回执 = **0.94921875**（两次独立组件同值·期望 3）——0.94921875 疑似
TEXT_MEM_VAL 权重值（write_text_mem 落库 val）——**嫌疑：str_len 的 out 写点或局部槽读点被
记忆权重链路覆盖**——下轮判别：str_len 单独隔离（无 write_mem）+ query result 概念直读。

## 引擎回执记录
- CHAR_VAL refactor：{written: 731, primitives: 30, gen: 10325}
- ROMAN_TO_INT v1-v4 refactor：{written: 1265-1375, primitives: 30→31, gen: 12447→15181}
- v4 shadow：{key: ROMAN_TO_INT, steps: 19, vops: [44,8,5,5,16,52,32,16,44,16,52,32,46,46,3,3], eff: 3, 装载 0 拒绝}
