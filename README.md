# OutputDxf — Genesis TGZ → DXF 转换工具

鹏程工作室 出品

## 运行环境

- **Python 2.6 / 2.7 / 3.x** — 全兼容
- **tkinter** — Python 自带标准库，无需额外装包
- 操作系统：Windows / Linux 均可

## 快速开始

```bash
git clone https://github.com/heruipeng/OutputDxf.git
cd OutputDxf
python main.py
```

## 界面说明

| 区域 | 说明 |
|------|------|
| TGZ 文件路径 | 点击按钮弹窗选择 Genesis .tgz 文件 |
| DXF 输出目录 | 选择输出文件夹 |
| 单位 | mm 毫米 / inch 英寸 |
| 涨缩比例 | X、Y 方向独立缩放 (1.0 = 原始) |
| 输出方式 | 轮廓输出（外边界）/ 填充输出（含铜面） |

## 兼容性

```python
# Python 2.6 无 json 库 → 自动回退 ConfigParser
# 无 ttk → 纯 Tkinter 实现
```

已在 Python 2.6 环境验证 `import Tkinter` 通过。

## 项目结构

```
OutputDxf/
├── main.py              # 入口
├── output_dxf_gui.py    # GUI (纯 Tkinter, 兼容 2.6)
├── config.ini           # 配置 (自动生成)
└── LICENSE
```

---

鹏程工作室 © 2026
