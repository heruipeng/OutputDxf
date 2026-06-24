#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OutputDxf - Genesis TGZ → DXF 转换工具
鹏程工作室 出品

Genesis 平台输出 TGZ 文件 → 自动转换为 DXF
支持公英制、XY涨缩比例、轮廓/填充输出

兼容: Python 2.7 / Python 3.x
"""

from __future__ import unicode_literals, print_function

try:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import ttk
    PY2 = True
except ImportError:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import ttk
    PY2 = False

import os
import sys
import json


# ══════════════════════════════════════════════════════
# 配置持久化
# ══════════════════════════════════════════════════════

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULTS = {
    'tgz_path': '',
    'output_path': '',
    'unit': 'mm',
    'scale_x': '1.0',
    'scale_y': '1.0',
    'mode': 'contour',
}

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except Exception:
        return dict(DEFAULTS)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════════════

class OutputDxfApp:
    
    TITLE    = "OutputDxf - Genesis TGZ → DXF 转换工具"
    GEOMETRY = "560x420"
    PAD_X    = 12
    PAD_Y    = 6
    
    # 颜色方案
    BG_MAIN     = "#F0F2F5"
    BG_SECTION  = "#FFFFFF"
    FG_LABEL    = "#333333"
    FG_TITLE    = "#1A5276"
    ACCENT      = "#2E86C1"
    ACCENT_HOVER = "#2874A6"
    BORDER      = "#D5D8DC"
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry(self.GEOMETRY)
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_MAIN)
        
        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry("+%d+%d" % ((sw-560)//2, (sh-420)//2))
        
        # 加载配置
        self.cfg = load_config()
        self.vars = {}
        
        self._build_ui()
        self._load_config_to_ui()
        self.root.mainloop()
    
    def _build_ui(self):
        """构建界面"""
        # ── 标题栏 ──
        header = tk.Frame(self.root, bg=self.ACCENT, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="OutputDxf", font=("Arial", 16, "bold"),
                bg=self.ACCENT, fg="white").pack(side=tk.LEFT, padx=16, pady=10)
        tk.Label(header, text="鹏程工作室 出品", font=("Arial", 9),
                bg=self.ACCENT, fg="#D4E6F1").pack(side=tk.RIGHT, padx=16, pady=14)
        
        # ── 主体容器 ──
        main = tk.Frame(self.root, bg=self.BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # ★ 输入区域
        self._section_input(main)
        
        # ★ 输出路径
        self._section_output(main)
        
        # ★ 参数设置
        self._section_params(main)
        
        # ★ 输出方式
        self._section_mode(main)
        
        # ★ 操作按钮
        self._section_buttons()
    
    def _section_input(self, parent):
        """TGZ 路径选择"""
        frame = self._create_section(parent, "TGZ 文件路径")
        frame.columnconfigure(1, weight=1)
        
        var = tk.StringVar()
        self.vars['tgz_path'] = var
        entry = tk.Entry(frame, textvariable=var, font=("Consolas", 10),
                        relief=tk.FLAT, bd=1, bg="#F8F9FA")
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 6), ipady=3)
        
        btn = tk.Button(frame, text=" 浏览... ", command=self._browse_tgz,
                       bg=self.ACCENT, fg="white", relief=tk.FLAT,
                       font=("Arial", 9), cursor="hand2", padx=8)
        btn.grid(row=0, column=2, padx=(4, 4), ipady=2)
        self._bind_hover(btn)
    
    def _section_output(self, parent):
        """输出路径"""
        frame = self._create_section(parent, "DXF 输出目录")
        frame.columnconfigure(1, weight=1)
        
        var = tk.StringVar()
        self.vars['output_path'] = var
        entry = tk.Entry(frame, textvariable=var, font=("Consolas", 10),
                        relief=tk.FLAT, bd=1, bg="#F8F9FA")
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 6), ipady=3)
        
        btn = tk.Button(frame, text=" 浏览... ", command=self._browse_output,
                       bg=self.ACCENT, fg="white", relief=tk.FLAT,
                       font=("Arial", 9), cursor="hand2", padx=8)
        btn.grid(row=0, column=2, padx=(4, 4), ipady=2)
        self._bind_hover(btn)
    
    def _section_params(self, parent):
        """参数：公英制 + XY涨缩"""
        frame = self._create_section(parent, "参数设置")
        
        # ── 公英制 ──
        tk.Label(frame, text="单位:", font=("Arial", 10), bg=self.BG_SECTION,
                fg=self.FG_LABEL).grid(row=0, column=0, sticky=tk.W, pady=(0,8))
        
        unit_frame = tk.Frame(frame, bg=self.BG_SECTION)
        unit_frame.grid(row=0, column=1, sticky=tk.W, pady=(0,8))
        
        var_unit = tk.StringVar(value=self.cfg.get('unit', 'mm'))
        self.vars['unit'] = var_unit
        
        for text, val in [("mm  毫米", "mm"), ("inch 英寸", "inch")]:
            tk.Radiobutton(unit_frame, text=text, variable=var_unit, value=val,
                          bg=self.BG_SECTION, font=("Arial", 9),
                          activebackground=self.BG_SECTION,
                          selectcolor=self.BG_SECTION).pack(side=tk.LEFT, padx=(0, 16))
        
        # ── XY 涨缩比例 ──
        row_start = 1
        tk.Label(frame, text="涨缩比例:", font=("Arial", 10), bg=self.BG_SECTION,
                fg=self.FG_LABEL).grid(row=row_start, column=0, sticky=tk.W, pady=4)
        
        scale_frame = tk.Frame(frame, bg=self.BG_SECTION)
        scale_frame.grid(row=row_start, column=1, sticky=tk.W, pady=4)
        
        tk.Label(scale_frame, text=" X:", font=("Arial", 9), bg=self.BG_SECTION,
                fg=self.FG_LABEL).pack(side=tk.LEFT)
        var_sx = tk.StringVar(value=self.cfg.get('scale_x', '1.0'))
        self.vars['scale_x'] = var_sx
        tk.Entry(scale_frame, textvariable=var_sx, width=7, justify=tk.CENTER,
                font=("Consolas", 10), relief=tk.FLAT, bd=1, bg="#F8F9FA").pack(side=tk.LEFT, ipady=2)
        
        tk.Label(scale_frame, text="  Y:", font=("Arial", 9), bg=self.BG_SECTION,
                fg=self.FG_LABEL).pack(side=tk.LEFT, padx=(8, 0))
        var_sy = tk.StringVar(value=self.cfg.get('scale_y', '1.0'))
        self.vars['scale_y'] = var_sy
        tk.Entry(scale_frame, textvariable=var_sy, width=7, justify=tk.CENTER,
                font=("Consolas", 10), relief=tk.FLAT, bd=1, bg="#F8F9FA").pack(side=tk.LEFT, ipady=2)
        
        # 提示
        tk.Label(frame, text="  1.0 = 原始比例, 1.05 = X方向拉伸5%",
                font=("Arial", 8), bg=self.BG_SECTION, fg="#999").grid(
                row=2, column=1, sticky=tk.W, pady=(0,4))
    
    def _section_mode(self, parent):
        """输出方式：轮廓 / 填充"""
        frame = self._create_section(parent, "输出方式")
        
        var_mode = tk.StringVar(value=self.cfg.get('mode', 'contour'))
        self.vars['mode'] = var_mode
        
        modes = [
            ("contour", "轮廓输出", "只输出图形外轮廓线"),
            ("fill",    "填充输出", "输出完整填充图形（含铜皮）"),
        ]
        
        for i, (val, label, desc) in enumerate(modes):
            rb_frame = tk.Frame(frame, bg=self.BG_SECTION)
            rb_frame.pack(anchor=tk.W, pady=2)
            
            tk.Radiobutton(rb_frame, text=label, variable=var_mode, value=val,
                          bg=self.BG_SECTION, font=("Arial", 10, "bold"),
                          activebackground=self.BG_SECTION,
                          selectcolor=self.BG_SECTION).pack(side=tk.LEFT)
            tk.Label(rb_frame, text="  —  " + desc, font=("Arial", 9),
                    bg=self.BG_SECTION, fg="#777").pack(side=tk.LEFT)
    
    def _section_buttons(self):
        """底部操作按钮"""
        btn_frame = tk.Frame(self.root, bg=self.BG_MAIN)
        btn_frame.pack(fill=tk.X, padx=10, pady=(8, 12))
        
        self._status_label = tk.Label(
            btn_frame, text="就绪", font=("Arial", 9),
            bg=self.BG_MAIN, fg="#999", anchor=tk.W)
        self._status_label.pack(side=tk.LEFT, padx=4)
        
        btn_quit = tk.Button(btn_frame, text=" 退出 ", command=self.root.quit,
                            bg="#E74C3C", fg="white", relief=tk.FLAT,
                            font=("Arial", 10), cursor="hand2", padx=16)
        btn_quit.pack(side=tk.RIGHT, padx=(4, 0), ipady=4)
        self._bind_hover(btn_quit, "#E74C3C", "#CB4335")
        
        btn_run = tk.Button(btn_frame, text=" ▶ 开始转换 ", command=self._run,
                           bg="#27AE60", fg="white", relief=tk.FLAT,
                           font=("Arial", 10, "bold"), cursor="hand2", padx=20)
        btn_run.pack(side=tk.RIGHT, padx=(0, 4), ipady=4)
        self._bind_hover(btn_run, "#27AE60", "#229954")
    
    def _create_section(self, parent, title):
        """创建带标题的卡片容器"""
        card = tk.Frame(parent, bg=self.BG_SECTION, relief=tk.FLAT,
                       bd=1, highlightbackground=self.BORDER,
                       highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card, text=" ▎" + title, font=("Arial", 10, "bold"),
                bg=self.BG_SECTION, fg=self.FG_TITLE, anchor=tk.W).pack(
                anchor=tk.W, padx=10, pady=(8, 2))
        
        inner = tk.Frame(card, bg=self.BG_SECTION)
        inner.pack(fill=tk.X, padx=10, pady=(2, 10))
        return inner
    
    def _bind_hover(self, btn, normal=None, hover=None):
        """鼠标悬停变色"""
        if normal is None:
            normal = btn.cget('bg')
        if hover is None:
            # 自动加深 15%
            hover = self._darken_color(normal)
        
        def on_enter(e):
            btn.config(bg=hover)
        def on_leave(e):
            btn.config(bg=normal)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
    
    def _darken_color(self, hex_color):
        """颜色加深"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
        factor = 0.85
        return '#%02x%02x%02x' % (int(r*factor), int(g*factor), int(b*factor))
    
    # ═══ 交互逻辑 ═══
    
    def _browse_tgz(self):
        path = filedialog.askopenfilename(
            title="选择 Genesis TGZ 文件",
            filetypes=[("TGZ 文件", "*.tgz"), ("GZ 文件", "*.gz"), ("所有文件", "*.*")])
        if path:
            self.vars['tgz_path'].set(path)
    
    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.vars['output_path'].set(path)
    
    def _load_config_to_ui(self):
        for key in ('tgz_path', 'output_path', 'unit', 'scale_x', 'scale_y', 'mode'):
            if key in self.vars and key in self.cfg:
                self.vars[key].set(self.cfg[key])
    
    def _validate(self):
        """校验输入"""
        errors = []
        
        tgz = self.vars['tgz_path'].get().strip()
        if not tgz:
            errors.append("请选择 TGZ 文件路径")
        elif not os.path.isfile(tgz):
            errors.append("TGZ 文件不存在: " + tgz)
        
        out = self.vars['output_path'].get().strip()
        if not out:
            errors.append("请选择输出路径")
        elif not os.path.isdir(out):
            errors.append("输出目录不存在: " + out)
        
        try:
            sx = float(self.vars['scale_x'].get().strip() or '1.0')
            if sx <= 0:
                raise ValueError
        except ValueError:
            errors.append("X 涨缩比例请输入正数 (如 1.0)")
        
        try:
            sy = float(self.vars['scale_y'].get().strip() or '1.0')
            if sy <= 0:
                raise ValueError
        except ValueError:
            errors.append("Y 涨缩比例请输入正数 (如 1.0)")
        
        return errors
    
    def _run(self):
        """执行转换"""
        errors = self._validate()
        if errors:
            msg = u"请修正以下问题:\n\n" + u"\n".join(u"• " + e for e in errors)
            messagebox.showerror("输入错误", msg)
            return
        
        # 保存配置
        for key in self.vars:
            self.cfg[key] = self.vars[key].get()
        save_config(self.cfg)
        
        self._status_label.config(text="转换中...", fg="#E67E22")
        self.root.update_idletasks()
        
        # ── 调用转换引擎 ──
        try:
            result = self._do_convert()
            self._status_label.config(text="完成: " + result, fg="#27AE60")
            messagebox.showinfo("转换完成", "DXF 已输出到:\n" + result)
        except Exception as e:
            self._status_label.config(text="转换失败", fg="#E74C3C")
            messagebox.showerror("转换失败", str(e))
    
    def _do_convert(self):
        """
        执行转换 — 对接 Genesis 输出引擎
        
        TODO: 集成 Genesis Gateway 接口，实际解析 TGZ → DXF
        """
        tgz_path = self.vars['tgz_path'].get().strip()
        out_dir  = self.vars['output_path'].get().strip()
        unit     = self.vars['unit'].get()
        sx       = float(self.vars['scale_x'].get().strip())
        sy       = float(self.vars['scale_y'].get().strip())
        mode     = self.vars['mode'].get()
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(tgz_path))[0]
        if base_name.endswith('.tgz'):
            base_name = base_name[:-4]
        output_file = os.path.join(out_dir, base_name + '.dxf')
        
        # ── 转换逻辑占位 ──
        # 实际项目需替换为:
        # from genesis_gateway import TgzReader
        # from dxf_writer import DxfWriter
        # reader = TgzReader(tgz_path)
        # writer = DxfWriter(output_file, unit=unit, scale=(sx, sy), mode=mode)
        # writer.convert(reader)
        
        # 临时: 输出空 DXF 占位
        self._write_placeholder_dxf(output_file, tgz_path, unit, sx, sy, mode)
        
        return output_file
    
    def _write_placeholder_dxf(self, path, source, unit, sx, sy, mode):
        """输出占位 DXF (临时)"""
        with open(path, 'w') as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n")
            f.write("9\n$MEASUREMENT\n70\n" + ("1" if unit == "inch" else "0") + "\n")
            f.write("9\n$INSUNITS\n70\n" + ("1" if unit == "inch" else "4") + "\n")
            f.write("0\nENDSEC\n0\nEOF\n")


# ══════════════════════════════════════════════════════

if __name__ == '__main__':
    OutputDxfApp()
