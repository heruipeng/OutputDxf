# OutputDxf

Genesis TGZ → DXF 转换工具 | 鹏程工作室 出品

## 功能

- Genesis 平台 TGZ 文件 → DXF 格式自动转换
- tkinter GUI 图形界面，操作简单直观
- 支持公英制（mm / inch）切换
- 支持 X / Y 方向独立涨缩比例
- 轮廓输出 / 填充输出 两种模式
- 配置自动记忆（config.json）

## 运行环境

- Python 2.7+ / Python 3.x
- 标准库 tkinter（Python 自带，无需额外安装）
- 操作系统：Windows, Linux 均可

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/heruipeng/OutputDxf.git
cd OutputDxf

# 运行
python main.py
```

## 界面说明

| 区域 | 说明 |
|------|------|
| TGZ 文件路径 | 点击「浏览」选择 Genesis 导出的 .tgz 文件 |
| DXF 输出目录 | 选择 DXF 文件的输出目录 |
| 单位 | 选择 mm（毫米）或 inch（英寸） |
| 涨缩比例 | X 方向和 Y 方向独立设置缩放系数（1.0 = 原始比例） |
| 输出方式 | 轮廓输出（仅图形边界线）/ 填充输出（完整铜面） |

## 项目结构

```
OutputDxf/
├── main.py              # 入口
├── output_dxf_gui.py    # GUI 界面（tkinter）
├── config.json          # 配置持久化（自动生成）
└── LICENSE              # MIT License
```

## 开发计划

- [x] GUI 界面框架
- [ ] Genesis TGZ 解析引擎（对接 Gateway 接口）
- [ ] DXF 写入引擎（轮廓/填充/标注）
- [ ] 批量转换支持
- [ ] 转换日志记录

---

鹏程工作室 — 2026
