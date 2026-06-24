#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OutputDxf - Genesis TGZ → DXF 转换工具
鹏程工作室 出品
兼容 Python 2.6+ / Python 3.x | 纯 Tkinter (无需 ttk)
"""

from __future__ import unicode_literals, print_function

try:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    PY = 2
except ImportError:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    PY = 3

import os, sys

# Python 2.6 没有 json → 用 ConfigParser 替代
try:
    import json
    HAS_JSON = True
except ImportError:
    HAS_JSON = False

if not HAS_JSON:
    try:
        from ConfigParser import ConfigParser
    except ImportError:
        from configparser import ConfigParser


# ══════════════════════════════════════════════════════
# 配置持久化 (兼容 py2.6)

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'config.ini')
if PY == 2:
    CONFIG_FILE = CONFIG_FILE.decode('utf-8')

DEFAULTS = {
    'tgz_path': '',
    'output_path': '',
    'unit': 'mm',
    'scale_x': '1.0',
    'scale_y': '1.0',
    'mode': 'contour',
}


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.isfile(CONFIG_FILE):
        try:
            if HAS_JSON:
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.loads(f.read())
                    cfg.update(loaded)
            else:
                cp = ConfigParser()
                cp.read(CONFIG_FILE)
                if cp.has_section('settings'):
                    for k in DEFAULTS:
                        if cp.has_option('settings', k):
                            cfg[k] = cp.get('settings', k)
        except Exception:
            pass
    return cfg


def save_config(cfg):
    try:
        if HAS_JSON:
            with open(CONFIG_FILE, 'w') as f:
                f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
        else:
            cp = ConfigParser()
            cp.add_section('settings')
            for k, v in cfg.items():
                cp.set('settings', k, v)
            with open(CONFIG_FILE, 'w') as f:
                cp.write(f)
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# 主窗口 (纯 Tkinter, 无 ttk)
# ══════════════════════════════════════════════════════

class OutputDxfApp:
    TITLE    = "OutputDxf - Genesis TGZ -> DXF"
    WIDTH    = 540
    HEIGHT   = 440
    PAD_X, PAD_Y = 10, 5

    BG       = "#F0F2F5"
    CARD_BG  = "#FFFFFF"
    FG       = "#333333"
    TITLE_FG = "#1A5276"
    ACCENT   = "#2E86C1"
    GREEN    = "#27AE60"
    RED      = "#E74C3C"
    ORANGE   = "#E67E22"
    GRAY     = "#999999"
    BORDER   = "#D5D8DC"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry("%dx%d" % (self.WIDTH, self.HEIGHT))
        self.root.resizable(0, 0)
        self.root.configure(bg=self.BG)

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(
            "+%d+%d" % ((sw - self.WIDTH) // 2, (sh - self.HEIGHT) // 2))

        self.cfg = load_config()
        self.vars = {}
        self._build()
        self._load_cfg()
        self.root.mainloop()

    # ── UI 构建 ──

    def _build(self):
        # 标题栏
        header = tk.Frame(self.root, bg=self.ACCENT, height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(0)
        tk.Label(header, text="OutputDxf", font=("Arial", 15, "bold"),
                 bg=self.ACCENT, fg="white").pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(header, text="鹏程工作室 出品", font=("Arial", 8),
                 bg=self.ACCENT, fg="#D4E6F1").pack(side=tk.RIGHT, padx=14, pady=14)

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=1, padx=8, pady=(8, 0))

        self._card_tgz(body)
        self._card_output(body)
        self._card_params(body)
        self._card_mode(body)
        self._buttons()

    # ── 卡片组件 ──

    def _card(self, parent, title):
        card = tk.Frame(parent, bg=self.CARD_BG, relief=tk.FLAT, bd=1,
                        highlightbackground=self.BORDER, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(card, text=" ▎" + title, font=("Arial", 10, "bold"),
                 bg=self.CARD_BG, fg=self.TITLE_FG, anchor=tk.W).pack(
            anchor=tk.W, padx=8, pady=(6, 1))
        inner = tk.Frame(card, bg=self.CARD_BG)
        inner.pack(fill=tk.X, padx=8, pady=(1, 8))
        return inner

    def _browse_btn(self, parent, cmd):
        btn = tk.Button(parent, text="...", command=cmd,
                        bg=self.ACCENT, fg="white", relief=tk.FLAT,
                        font=("Arial", 9, "bold"), cursor="hand2",
                        width=3, height=1)
        self._hover(btn, self.ACCENT, "#2471A3")
        return btn

    def _hover(self, btn, n, h):
        btn.bind("<Enter>", lambda e: btn.config(bg=h))
        btn.bind("<Leave>", lambda e: btn.config(bg=n))

    # ── TGZ 路径 ──

    def _card_tgz(self, parent):
        inner = self._card(parent, "TGZ 文件路径")
        v = tk.StringVar(); self.vars['tgz_path'] = v
        e = tk.Entry(inner, textvariable=v, font=("Courier", 9),
                     relief=tk.FLAT, bd=1, bg="#F8F9FA")
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_tgz).pack(side=tk.RIGHT, padx=(4, 0))

    # ── 输出路径 ──

    def _card_output(self, parent):
        inner = self._card(parent, "DXF 输出目录")
        v = tk.StringVar(); self.vars['output_path'] = v
        e = tk.Entry(inner, textvariable=v, font=("Courier", 9),
                     relief=tk.FLAT, bd=1, bg="#F8F9FA")
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_out).pack(side=tk.RIGHT, padx=(4, 0))

    # ── 参数 ──

    def _card_params(self, parent):
        inner = self._card(parent, "参数设置")

        # 单位
        uf = tk.Frame(inner, bg=self.CARD_BG)
        uf.pack(anchor=tk.W, pady=(0, 4))
        tk.Label(uf, text="单位:", font=("Arial", 10),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        uv = tk.StringVar(value=self.cfg.get('unit', 'mm'))
        self.vars['unit'] = uv
        for t, val in [("mm  毫米", "mm"), ("inch 英寸", "inch")]:
            tk.Radiobutton(uf, text=t, variable=uv, value=val,
                           bg=self.CARD_BG, font=("Arial", 9),
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT, padx=(2, 12))

        # 涨缩
        sf = tk.Frame(inner, bg=self.CARD_BG)
        sf.pack(anchor=tk.W)
        tk.Label(sf, text="涨缩:", font=("Arial", 10),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        tk.Label(sf, text=" X=", font=("Arial", 9),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(6, 0))
        svx = tk.StringVar(value=self.cfg.get('scale_x', '1.0'))
        self.vars['scale_x'] = svx
        tk.Entry(sf, textvariable=svx, width=6, justify=tk.CENTER,
                 font=("Courier", 10), relief=tk.FLAT, bd=1,
                 bg="#F8F9FA").pack(side=tk.LEFT, ipady=2)

        tk.Label(sf, text="  Y=", font=("Arial", 9),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(8, 0))
        svy = tk.StringVar(value=self.cfg.get('scale_y', '1.0'))
        self.vars['scale_y'] = svy
        tk.Entry(sf, textvariable=svy, width=6, justify=tk.CENTER,
                 font=("Courier", 10), relief=tk.FLAT, bd=1,
                 bg="#F8F9FA").pack(side=tk.LEFT, ipady=2)

        tk.Label(inner, text=" 1.0 = 原始  1.05 = X方向拉伸5%",
                 font=("Arial", 8), bg=self.CARD_BG, fg=self.GRAY).pack(
            anchor=tk.W, pady=(3, 0))

    # ── 输出方式 ──

    def _card_mode(self, parent):
        inner = self._card(parent, "输出方式")

        mv = tk.StringVar(value=self.cfg.get('mode', 'contour'))
        self.vars['mode'] = mv

        modes = [
            ("contour", "轮廓输出", "只输出图形外轮廓线"),
            ("fill", "填充输出", "输出完整填充（含铜面）"),
        ]
        for val, label, desc in modes:
            rf = tk.Frame(inner, bg=self.CARD_BG)
            rf.pack(anchor=tk.W, pady=1)
            tk.Radiobutton(rf, text=label, variable=mv, value=val,
                           bg=self.CARD_BG, font=("Arial", 10, "bold"),
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT)
            tk.Label(rf, text=" — " + desc, font=("Arial", 8),
                     bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)

    # ── 底部按钮 ──

    def _buttons(self):
        bf = tk.Frame(self.root, bg=self.BG)
        bf.pack(fill=tk.X, padx=8, pady=(6, 10))

        self.status = tk.Label(bf, text="就绪", font=("Arial", 9),
                               bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status.pack(side=tk.LEFT, padx=2)

        q = tk.Button(bf, text=" 退出 ", command=self.root.quit,
                      bg=self.RED, fg="white", relief=tk.FLAT,
                      font=("Arial", 10), cursor="hand2", padx=14)
        q.pack(side=tk.RIGHT, padx=(3, 0), ipady=4)
        self._hover(q, self.RED, "#CB4335")

        r = tk.Button(bf, text=" ▶ 开始转换 ", command=self._run,
                      bg=self.GREEN, fg="white", relief=tk.FLAT,
                      font=("Arial", 10, "bold"), cursor="hand2", padx=16)
        r.pack(side=tk.RIGHT, padx=(0, 3), ipady=4)
        self._hover(r, self.GREEN, "#229954")

    # ── 交互 ──

    def _on_tgz(self):
        p = filedialog.askopenfilename(
            title="选择 Genesis TGZ 文件",
            filetypes=[("TGZ 文件", "*.tgz"), ("GZ 文件", "*.gz"),
                       ("所有", "*.*")])
        if p:
            self.vars['tgz_path'].set(p)

    def _on_out(self):
        p = filedialog.askdirectory(title="选择输出目录")
        if p:
            self.vars['output_path'].set(p)

    def _load_cfg(self):
        for k in ('tgz_path', 'output_path', 'unit',
                  'scale_x', 'scale_y', 'mode'):
            if k in self.vars and k in self.cfg:
                self.vars[k].set(self.cfg[k])

    def _validate(self):
        err = []
        tgz = self.vars['tgz_path'].get().strip()
        if not tgz:
            err.append("请选择 TGZ 文件")
        elif not os.path.isfile(tgz):
            err.append("TGZ 文件不存在")

        out = self.vars['output_path'].get().strip()
        if not out:
            err.append("请选择输出目录")
        elif not os.path.isdir(out):
            err.append("输出目录不存在")

        for axis in ('scale_x', 'scale_y'):
            try:
                v = float(self.vars[axis].get().strip() or '1.0')
                if v <= 0:
                    raise ValueError
            except ValueError:
                err.append(axis.replace('scale_', '') + " 涨缩请输入正数")
        return err

    def _run(self):
        errs = self._validate()
        if errs:
            msg = "请修正:\n\n" + "\n".join("  * " + e for e in errs)
            messagebox.showerror("输入错误", msg)
            return

        for k in self.vars:
            self.cfg[k] = self.vars[k].get()
        save_config(self.cfg)

        self.status.config(text="转换中...", fg=self.ORANGE)
        self.root.update_idletasks()

        try:
            out = self._convert()
            self.status.config(text="完成: " + out, fg=self.GREEN)
            messagebox.showinfo("转换完成", "DXF:\n" + out)
        except Exception as ex:
            self.status.config(text="失败", fg=self.RED)
            messagebox.showerror("转换失败", str(ex))

    def _convert(self):
        """转换引擎占位 — 对接 Genesis Gateway + DXF Writer"""
        tgz   = self.vars['tgz_path'].get().strip()
        outdir = self.vars['output_path'].get().strip()
        unit  = self.vars['unit'].get()
        sx    = float(self.vars['scale_x'].get().strip())
        sy    = float(self.vars['scale_y'].get().strip())
        mode  = self.vars['mode'].get()

        base = os.path.splitext(os.path.basename(tgz))[0]
        if base.endswith('.tgz'):
            base = base[:-4]
        outfile = os.path.join(outdir, base + '.dxf')

        # TODO: 替换为 Genesis Gateway + DXF Writer
        self._dummy_dxf(outfile, tgz, unit, sx, sy, mode)
        return outfile

    def _dummy_dxf(self, path, src, unit, sx, sy, mode):
        ins = "1" if unit == "inch" else "4"
        with open(path, 'w') as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n")
            f.write("9\n$MEASUREMENT\n70\n%s\n" % ("1" if unit == "inch" else "0"))
            f.write("9\n$INSUNITS\n70\n%s\n" % ins)
            f.write("0\nENDSEC\n0\nEOF\n")


if __name__ == '__main__':
    OutputDxfApp()
