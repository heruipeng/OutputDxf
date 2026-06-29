#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
 main_dxf_export.py  —  GENESIS 2000 自动导出 DXF 工具
=============================================================================
 运行环境 : Python 2.7 / 3.x  |  纯 Tkinter GUI  |  无第三方依赖
 兼容    : Windows Genesis / Linux
 调用方式 : python main_dxf_export.py
=============================================================================
"""

from __future__ import print_function, unicode_literals, division

import sys
import os
import subprocess

# ---- Tkinter 检测 (Python 2/3 兼容) -------------------------------------
TK_IMPORT_ERROR = None
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import font as tkFont
    from tkinter import scrolledtext
except ImportError:
    try:
        import Tkinter as tk
        import tkFileDialog as filedialog
        import tkMessageBox as messagebox
        import tkFont
        import ScrolledText as scrolledtext
    except ImportError as e:
        TK_IMPORT_ERROR = e

if TK_IMPORT_ERROR:
    sys.stderr.write('\n[OutputDxf] tkinter/Tkinter 未安装, 无法启动 GUI。\n')
    sys.stderr.write('  修复方法:\n')
    if sys.platform == 'win32':
        sys.stderr.write('  1. 重装 Python 3, 勾选 tcl/tk and IDLE\n')
        sys.stderr.write('  2. Genesis 自带 Python 2 已含 Tkinter, 确保环境正确\n')
    else:
        sys.stderr.write('  sudo apt install python3-tk\n')
    sys.stderr.write('  详情: %s\n\n' % TK_IMPORT_ERROR)
    sys.exit(1)

import re
import math
import time
import traceback
import tarfile
import tempfile
import shutil
import fnmatch
import json
from collections import OrderedDict

# configparser: Python 2 叫 ConfigParser
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# ==========================================================================
# 全局常量
# ==========================================================================
VERSION = '2.0.0'

# Genesis 常见图层名称映射
LAYER_TYPE_MAP = {
    # 外形/轮廓
    'board_outline': 'OUTLINE',
    'profile':       'OUTLINE',
    'rout':          'OUTLINE',
    'outline':       'OUTLINE',
    '外形':          'OUTLINE',
    '轮廓':          'OUTLINE',
    # 钻孔
    'drill':      'DRILL',
    'drl':        'DRILL',
    'npth':       'DRILL',
    'pth':        'DRILL',
    '钻孔':       'DRILL',
    # 信号层 (顶层)
    'top':        'COPPER',
    'gtl':        'COPPER',
    'layer1':     'COPPER',
    'comp':       'COPPER',
    # 信号层 (底层)
    'bottom':     'COPPER',
    'gbl':        'COPPER',
    'sold':       'COPPER',
    # 阻焊
    'soldermask_top':    'MASK',
    'soldermask_bot':    'MASK',
    'gts':               'MASK',
    'gbs':               'MASK',
    'sm':                'MASK',
    '阻焊':              'MASK',
    # 丝印
    'silkscreen_top':    'SILK',
    'silkscreen_bot':    'SILK',
    'gto':               'SILK',
    'gbo':               'SILK',
    '丝印':              'SILK',
    # 钢网
    'paste_top':    'PASTE',
    'paste_bot':    'PASTE',
    'gtp':          'PASTE',
    'gbp':          'PASTE',
}

# DXF 图层颜色 (AutoCAD 标准色号)
DXF_LAYER_COLORS = {
    'OUTLINE':  1,   # 红色
    'COPPER':   7,   # 白色/黑色
    'DRILL':    3,   # 绿色
    'MASK':     4,   # 青色
    'SILK':     5,   # 蓝色
    'PASTE':    6,   # 品红
    'ROUT':     2,   # 黄色
    'TEXT':     7,   # 白色
}
# ==========================================================================
# 2. JobAdapter — TGZ 解压 & Step/Layer 扫描
# ==========================================================================

class JobAdapter(object):
    """TGZ 加载 / 解压 / Step扫描 / Layer扫描 (纯文件模式)"""

    def __init__(self):
        self.job_path = ''
        self.extracted_dir = ''

    def load(self, job_path):
        self.job_path = job_path
        self.extracted_dir = ''
        if not os.path.isdir(job_path) and not os.path.isfile(job_path):
            return False
        if self._is_tgz():
            extracted = self._extract_tgz()
            if not extracted:
                return False
        return True

    def job_name(self):
        if self.job_path:
            base = os.path.basename(self.job_path.rstrip('/\\'))
            if base.endswith('.tar.gz'):
                base = base[:-7]
            elif base.endswith('.tgz'):
                base = base[:-4]
            return base
        return 'UNKNOWN'

    def _is_tgz(self):
        lp = self.job_path.lower()
        return (lp.endswith('.tgz') or lp.endswith('.tar.gz')) \
               and os.path.isfile(self.job_path)

    def _extract_tgz(self):
        if not self._is_tgz():
            return self.job_path
        name = self.job_name()
        if sys.platform == 'win32':
            tmp_root = os.path.join('C:', os.sep, 'tmp')
        else:
            tmp_root = os.path.join(os.sep, 'tmp')
        self.extracted_dir = os.path.join(tmp_root, name)
        marker = os.path.join(self.extracted_dir, '.extracted')
        if os.path.isdir(self.extracted_dir) and os.path.isfile(marker):
            try:
                with open(marker, 'r') as f:
                    if f.read().strip() == self.job_path:
                        return self.extracted_dir
            except Exception:
                pass
        if os.path.isdir(self.extracted_dir):
            try:
                shutil.rmtree(self.extracted_dir)
            except Exception:
                pass
        if not os.path.isdir(self.extracted_dir):
            os.makedirs(self.extracted_dir)
        try:
            with tarfile.open(self.job_path, 'r:gz') as tf:
                tf.extractall(self.extracted_dir)
            with open(marker, 'w') as f:
                f.write(self.job_path)
        except Exception:
            return None
        return self.extracted_dir

    def find_steps_dir(self, root_dir):
        direct = os.path.join(root_dir, 'steps')
        if os.path.isdir(direct):
            return direct
        try:
            for item in os.listdir(root_dir):
                candidate = os.path.join(root_dir, item, 'steps')
                if os.path.isdir(candidate):
                    return candidate
        except Exception:
            pass
        return root_dir

    def scan_steps(self):
        steps = []
        if not self.job_path:
            return steps
        if self._is_tgz():
            extracted = self._extract_tgz()
            if not extracted:
                try:
                    with tarfile.open(self.job_path, 'r:gz') as tf:
                        for m in tf.getmembers():
                            parts = m.name.split('/')
                            if len(parts) >= 2 and parts[0] not in steps:
                                if not parts[0].startswith('.'):
                                    steps.append(parts[0])
                except Exception:
                    pass
                return sorted(steps)
            steps_dir = self.find_steps_dir(extracted)
            try:
                for item in os.listdir(steps_dir):
                    full = os.path.join(steps_dir, item)
                    if os.path.isdir(full) and not item.startswith('.'):
                        steps.append(item)
            except Exception:
                pass
        elif os.path.isdir(self.job_path):
            steps_dir = self.find_steps_dir(self.job_path)
            try:
                for item in os.listdir(steps_dir):
                    full = os.path.join(steps_dir, item)
                    if os.path.isdir(full) and not item.startswith('.'):
                        steps.append(item)
            except Exception:
                pass
        return sorted(steps)

    def scan_layers(self, step_name):
        layers = []
        if not self.job_path or not step_name:
            return layers
        if self._is_tgz():
            extracted = self.extracted_dir or self._extract_tgz()
            if extracted:
                steps_dir = self.find_steps_dir(extracted)
                step_dir = os.path.join(steps_dir, step_name)
                for c in [os.path.join(step_dir, 'layers'), step_dir]:
                    if os.path.isdir(c):
                        try:
                            for item in os.listdir(c):
                                full = os.path.join(c, item)
                                if os.path.isdir(full) and not item.startswith('.'):
                                    layers.append(item)
                        except Exception:
                            pass
                        if layers:
                            break
        elif os.path.isdir(self.job_path):
            steps_dir = self.find_steps_dir(self.job_path)
            step_dir = os.path.join(steps_dir, step_name)
            for c in [os.path.join(step_dir, 'layers'), step_dir]:
                if os.path.isdir(c):
                    try:
                        for item in os.listdir(c):
                            full = os.path.join(c, item)
                            if os.path.isdir(full) and not item.startswith('.'):
                                layers.append(item)
                    except Exception:
                        pass
                    if layers:
                        break
        return sorted(layers)

    @staticmethod
    def classify_layer(layer_name):
        """根据图层名称推断图层类型"""
        lower = layer_name.lower().replace('_', '').replace('-', '').replace(' ', '')
        for keyword, ltype in LAYER_TYPE_MAP.items():
            kw = keyword.replace('_', '').replace('-', '').replace(' ', '')
            if kw in lower:
                return ltype
        return 'COPPER'

# ==========================================================================
# 4. DxfExportApp — Tkinter GUI 主界面 (Python 2.7 兼容)
# ==========================================================================

class DxfExportApp(object):
    TITLE  = 'OutputDxf - Genesis DXF Export v' + VERSION
    WIDTH  = 660
    HEIGHT = 730

    # 配色
    BG        = '#EAECEE'
    CARD_BG   = '#FFFFFF'
    FG        = '#2C3E50'
    ACCENT    = '#2980B9'
    GREEN     = '#27AE60'
    RED       = '#C0392B'
    ORANGE    = '#E67E22'
    GRAY      = '#7F8C8D'
    LIGHT_BG  = '#F8F9FA'
    BORDER    = '#BDC3C7'

    def __init__(self):
        self.job = JobAdapter()
        self.worker   = None  # 转换工作状态
        self.cfg = self._load_cfg()

        self._setup_root()
        self._setup_fonts()
        self._build_ui()
        self.genesis_ver = ''
        self.genesis_dir = ''
        self.xmanager_dir = ''

        # 加载配置
        self._apply_cfg_defaults()

        self.root.mainloop()

    # -- 配置文件 -----------------------------------------------------------

    @staticmethod
    def _cfg_path():
        """配置文件路径: 优先同目录, 降级当前工作目录"""
        candidates = []
        try:
            candidates.append(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'outputdxf.cfg'))
        except Exception:
            pass
        candidates.append(os.path.join(os.getcwd(), 'outputdxf.cfg'))
        for p in candidates:
            if os.path.isfile(p):
                return p
        return candidates[0]  # 返回同目录路径 (供后续写入参考)

    @staticmethod
    def _load_cfg():
        """从配置文件加载参数"""
        cfg = {}
        cfg_path = DxfExportApp._cfg_path()
        print('[OutputDxf] _load_cfg 搜索: ' + cfg_path)
        print('[OutputDxf] 文件存在: ' + str(os.path.isfile(cfg_path)))
        if not os.path.isfile(cfg_path):
            print('[OutputDxf] 配置文件未找到, 使用默认设置')
            return cfg
        print('[OutputDxf] 已找到配置文件, 开始解析')
        try:
            parser = configparser.ConfigParser()
            # 强制 UTF-8 读取, 避免 Windows gbk 编码报错
            if sys.version_info[0] >= 3:
                parser.read(cfg_path, encoding='utf-8')
            else:
                parser.read(cfg_path)
            sections = parser.sections()
            print('[OutputDxf] 解析到节: ' + str(sections))
            for section in sections:
                cfg[section] = {}
                for k, v in parser.items(section):
                    cfg[section][k] = v
                    print('[OutputDxf]   [%s] %s = %s' % (section, k, v))
        except Exception:
            pass
        print('[OutputDxf] cfg keys: ' + str(list(cfg.keys())))
        return cfg

    def _apply_cfg_defaults(self):
        """应用配置文件默认值到界面"""
        if not self.cfg:
            return  # 未找到配置文件, 静默跳过

        print('[OutputDxf] 已加载配置: ' + self._cfg_path())

        if 'paths' in self.cfg:
            p = self.cfg['paths'].get('output_path', '').strip()
            if p:
                self.var_output.set(p)
                print('[OutputDxf] 输出路径已设置: ' + p)

            self.genesis_ver = self.cfg['paths'].get('genesis_ver', '').strip()
            if os.path.isdir(self.genesis_ver) is False:
                self._log(u'genesis安装版本异常:%s' % self.genesis_ver)
            self.genesis_dir = self.cfg['paths'].get('genesis_dir', '').strip()
            if os.path.isdir(self.genesis_dir) is False:
                self._log(u'genesis安装路径异常:%s' % self.genesis_dir)
            self.xmanager_dir = self.cfg['paths'].get('xmanager_dir', '').strip()
            if os.path.isdir(self.xmanager_dir) is False:
                self._log(u'genesis xmanager路径异常:%s' % self.xmanager_dir)
        if 'layers' in self.cfg:
            # 存储预选图层列表, 等 Job 加载后调用
            self._cfg_layers = [
                x.strip() for x in self.cfg['layers'].get('dxf', '*').split(';')
                if x.strip()
            ]
        else:
            self._cfg_layers = ['*']
        if 'steps' in self.cfg:
            self._cfg_steps = [
                x.strip() for x in self.cfg['steps'].get('step', '').split(';')
                if x.strip()
            ]
        else:
            self._cfg_steps = []

    # -- 窗口初始化 ---------------------------------------------------------

    def _setup_root(self):
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry('%dx%d' % (self.WIDTH, self.HEIGHT))
        self.root.resizable(0, 0)
        self.root.configure(bg=self.BG)

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.WIDTH) // 2
        y = max(0, (sh - self.HEIGHT) // 2)
        self.root.geometry('+%d+%d' % (x, y))

    def _setup_fonts(self):
        """自适应字体"""
        is_win = sys.platform == 'win32'
        if is_win:
            cjk = 'Arial'
            try:
                r = tk.Tk()
                avail = set(r.tk.call('font', 'families'))
                r.destroy()
                for f in ['Microsoft YaHei', 'SimSun', 'SimHei']:
                    if f in avail:
                        cjk = f
                        break
            except Exception:
                pass
        else:
            cjk = 'Arial'

        try:
            self.FONT_TITLE  = tkFont.Font(family=cjk, size=14, weight='bold')
            self.FONT_NORMAL = tkFont.Font(family=cjk, size=9)
            self.FONT_BOLD   = tkFont.Font(family=cjk, size=9, weight='bold')
            self.FONT_SMALL  = tkFont.Font(family=cjk, size=8)
            self.FONT_MONO   = tkFont.Font(family='Courier', size=9)
            self.FONT_LOG    = tkFont.Font(family='Courier', size=8)
        except Exception:
            self.FONT_TITLE  = (cjk, 14, 'bold')
            self.FONT_NORMAL = (cjk, 9)
            self.FONT_BOLD   = (cjk, 9, 'bold')
            self.FONT_SMALL  = (cjk, 8)
            self.FONT_MONO   = ('Courier', 9)
            self.FONT_LOG    = ('Courier', 8)

    # -- UI 构建 ------------------------------------------------------------

    def _build_ui(self):
        # 标题栏
        self._build_header()

        # 底部按钮 (先 pack, 确保不被挤出)
        self._build_footer()

        # 滚动主区域 (填充剩余空间)
        main_canvas = tk.Canvas(self.root, bg=self.BG, highlightthickness=0)
        main_scroll = tk.Scrollbar(self.root, orient=tk.VERTICAL,
                                   command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_scroll.set)
        main_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        self.main_frame = tk.Frame(main_canvas, bg=self.BG)
        self._main_canvas_id = main_canvas.create_window(
            (0, 0), window=self.main_frame, anchor=tk.NW, tags='main_frame')
        self.main_frame.bind('<Configure>',
                             lambda e: main_canvas.configure(
                                 scrollregion=main_canvas.bbox('all')))

        # canvas 宽度跟随
        def _resize_main_canvas(event):
            main_canvas.itemconfig(self._main_canvas_id, width=event.width)
        main_canvas.bind('<Configure>', _resize_main_canvas)

        # 主区域鼠标滚轮
        main_canvas.bind('<Enter>',
                         lambda e: self._bind_canvas_scroll(main_canvas, e))
        main_canvas.bind('<Leave>',
                         lambda e: self._unbind_canvas_scroll(main_canvas, e))

        # Job 路径卡片
        self._card_job()

        # Step 选择卡片
        self._card_step()

        # 图层选择卡片
        self._card_layer()

        # DXF 输出路径卡片
        self._card_output_path()

        # 设置卡片 (单位/版本/选项)
        self._card_settings()

        # 日志区域
        self._card_log()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=self.ACCENT, height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(0)
        tk.Label(hdr, text=u'  OutputDxf',
                 font=self.FONT_TITLE, bg=self.ACCENT, fg='white').pack(
            side=tk.LEFT, padx=10, pady=6)

    # -- 卡片基类 -----------------------------------------------------------

    def _card(self, parent, title, pady=(0, 4)):
        card = tk.Frame(parent, bg=self.CARD_BG, relief=tk.FLAT, bd=1,
                        highlightbackground=self.BORDER, highlightthickness=1)
        card.pack(fill=tk.X, padx=6, pady=pady)
        tk.Label(card, text=u'  ' + title, font=self.FONT_BOLD,
                 bg=self.CARD_BG, fg=self.ACCENT, anchor=tk.W).pack(
            anchor=tk.W, padx=4, pady=(4, 0))
        inner = tk.Frame(card, bg=self.CARD_BG)
        inner.pack(fill=tk.X, padx=6, pady=(2, 6))
        return inner

    def _btn(self, parent, text, command, bg=None, width=4):
        bg = bg or self.ACCENT
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg='white', relief=tk.FLAT,
                        font=self.FONT_NORMAL, cursor='hand2',
                        width=width, height=1)
        btn.bind('<Enter>', lambda e, b=btn, c=bg:
                 b.config(bg=self._darken(c)))
        btn.bind('<Leave>', lambda e, b=btn, c=bg:
                 b.config(bg=c))
        return btn

    @staticmethod
    def _darken(hex_color):
        """颜色加深"""
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r, g, b = max(0, r-30), max(0, g-30), max(0, b-30)
        return '#%02X%02X%02X' % (r, g, b)

    # -- Job 路径卡片 -------------------------------------------------------

    def _card_job(self):
        inner = self._card(self.main_frame, u'Job 路径')
        self.var_job = tk.StringVar()
        e = tk.Entry(inner, textvariable=self.var_job,
                     font=self.FONT_MONO, relief=tk.FLAT,
                     bg=self.LIGHT_BG, fg=self.FG, bd=1)
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=5)
        self._btn(inner, u'浏览', self._on_job_browse).pack(
            side=tk.RIGHT, padx=(3, 0))
        self._btn(inner, u'加载', self._on_job_load,
                  bg=self.GREEN).pack(side=tk.RIGHT, padx=2)

    # -- Step 选择卡片 ------------------------------------------------------

    def _card_step(self):
        inner = self._card(self.main_frame, u'Step 选择')
        self.var_step = tk.StringVar()
        self.step_menu = tk.OptionMenu(inner, self.var_step, u'(请先加载Job)')
        self.step_menu.config(font=self.FONT_NORMAL, bg=self.LIGHT_BG,
                              relief=tk.FLAT, width=20)
        self.step_menu.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(inner, text=u'刷新:', font=self.FONT_SMALL,
                 bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)
        self._btn(inner, u'↻', self._on_step_refresh,
                  width=2).pack(side=tk.LEFT, padx=2)

    # -- 图层选择卡片 -------------------------------------------------------

    def _card_layer(self):
        inner = self._card(self.main_frame, u'图层选择')

        # 当前 Step 信息条
        self.layer_info = tk.Label(inner, text=u'  (未选择 Step)',
                                   font=self.FONT_SMALL, bg=self.CARD_BG,
                                   fg=self.GRAY, anchor=tk.W)
        self.layer_info.pack(fill=tk.X, padx=2, pady=(0, 4))

        # 图层多选区域 — 固定 260px, 微灰底色
        tree_frame = tk.Frame(inner, bg='#F2F4F4', height=80, bd=1,
                              relief=tk.SUNKEN)
        tree_frame.pack(fill=tk.X, pady=(0, 2))
        tree_frame.pack_propagate(0)

        self.layer_canvas = tk.Canvas(tree_frame, bg='#F2F4F4',
                                      highlightthickness=0)
        layer_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                    command=self.layer_canvas.yview)
        self.layer_canvas.configure(yscrollcommand=layer_scroll.set)
        layer_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.layer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        self.layer_frame = tk.Frame(self.layer_canvas, bg='#F2F4F4')
        self._layer_canvas_id = self.layer_canvas.create_window(
            (0, 0), window=self.layer_frame, anchor=tk.NW, tags='layer_frame')

        # 绑定滚轮滚动
        self.layer_canvas.bind('<Enter>', self._bind_layer_scroll)
        self.layer_canvas.bind('<Leave>', self._unbind_layer_scroll)

        # 控制按钮
        ctrl = tk.Frame(inner, bg=self.CARD_BG)
        ctrl.pack(fill=tk.X)
        self._btn(ctrl, u'全选', self._on_select_all,
                  bg=self.ACCENT, width=6).pack(side=tk.LEFT, padx=(0, 3))
        self._btn(ctrl, u'全不选', self._on_select_none,
                  bg=self.GRAY, width=6).pack(side=tk.LEFT, padx=(0, 3))
        self._btn(ctrl, u'刷新', self._on_layer_refresh,
                  bg=self.ACCENT, width=6).pack(side=tk.LEFT)

        self.layer_vars = {}   # {layer_name: tk.IntVar}

        # canvas frame 大小变化时自动更新内部窗口宽度
        def _resize_layer_canvas(event):
            self.layer_canvas.itemconfig(self._layer_canvas_id, width=event.width)
        self.layer_canvas.bind('<Configure>', _resize_layer_canvas)

    def _bind_layer_scroll(self, _event):
        self._bind_canvas_scroll(self.layer_canvas, _event)

    def _unbind_layer_scroll(self, _event):
        self._unbind_canvas_scroll(self.layer_canvas, _event)

    def _bind_canvas_scroll(self, canvas, _event):
        if sys.platform == 'win32':
            canvas.bind_all('<MouseWheel>',
                            lambda e: self._on_canvas_mousewheel(canvas, e))
        else:
            canvas.bind_all('<Button-4>',
                            lambda e: self._on_canvas_mousewheel(canvas, e))
            canvas.bind_all('<Button-5>',
                            lambda e: self._on_canvas_mousewheel(canvas, e))

    def _unbind_canvas_scroll(self, canvas, _event):
        if sys.platform == 'win32':
            canvas.unbind_all('<MouseWheel>')
        else:
            canvas.unbind_all('<Button-4>')
            canvas.unbind_all('<Button-5>')

    def _on_layer_mousewheel(self, event):
        self._on_canvas_mousewheel(self.layer_canvas, event)

    @staticmethod
    def _on_canvas_mousewheel(canvas, event):
        if sys.platform == 'win32':
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        elif event.num == 4:
            canvas.yview_scroll(-1, 'units')
        elif event.num == 5:
            canvas.yview_scroll(1, 'units')

    # -- 设置卡片 -----------------------------------------------------------

    # -- 输出路径卡片 (独立) ----------------------------------------------

    def _card_output_path(self):
        inner = self._card(self.main_frame, u'DXF 输出路径')
        row = tk.Frame(inner, bg=self.CARD_BG)
        row.pack(fill=tk.X)
        self.var_output = tk.StringVar()
        tk.Entry(row, textvariable=self.var_output,
                 font=self.FONT_MONO, relief=tk.FLAT,
                 bg=self.LIGHT_BG, fg=self.FG,
                 bd=1).pack(side=tk.LEFT, fill=tk.X,
                            expand=1, ipady=5)
        self._btn(row, u'浏览', self._on_output_browse,
                  bg=self.ACCENT, width=5).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Label(inner, text=u' 导出文件自动携带 Job名+Step名+图层名',
                 font=self.FONT_SMALL, bg=self.CARD_BG, fg=self.GRAY).pack(
            anchor=tk.W, pady=(3, 0))

    # -- 设置卡片 -----------------------------------------------------------

    def _card_settings(self):
        inner = self._card(self.main_frame, u'导出设置')

        # 单位
        uf = tk.Frame(inner, bg=self.CARD_BG)
        uf.pack(anchor=tk.W, pady=(0, 2))
        tk.Label(uf, text=u'单位:', font=self.FONT_NORMAL,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)
        self.var_unit = tk.StringVar(value='mm')
        for txt, val in [(u'  mm 毫米 ', 'mm'), (u'  inch 英寸 ', 'inch')]:
            tk.Radiobutton(uf, text=txt, variable=self.var_unit, value=val,
                           bg=self.CARD_BG, font=self.FONT_NORMAL,
                           selectcolor=self.CARD_BG).pack(
                side=tk.LEFT, padx=(2, 8))

        # DXF 模式
        optf = tk.Frame(inner, bg=self.CARD_BG)
        optf.pack(fill=tk.X, pady=(4, 0))
        tk.Label(optf, text=u'DXF 模式:', font=self.FONT_SMALL,
                 bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)
        self.var_dxf_mode = tk.StringVar(value='yes')
        for txt, val in [(u'  轮廓  ', 'yes'), (u'  实体  ', 'no')]:
            tk.Radiobutton(optf, text=txt, variable=self.var_dxf_mode, value=val,
                           bg=self.CARD_BG, font=self.FONT_SMALL,
                           selectcolor=self.CARD_BG).pack(
                side=tk.LEFT, padx=(2, 8))

    # -- 日志卡片 -----------------------------------------------------------

    def _card_log(self):
        inner = self._card(self.main_frame, u'操作日志')

        # ScrolledText (Python 2.7 无 ttk.ScrolledText, 自己实现)
        log_frame = tk.Frame(inner, bg=self.CARD_BG)
        log_frame.pack(fill=tk.BOTH, expand=1)

        self.log_text = tk.Text(log_frame, height=6, font=self.FONT_LOG,
                                bg='#1C2833', fg='#ABEBC6', relief=tk.FLAT,
                                bd=1, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # 进度条 (Canvas 模拟)
        self.progress_canvas = tk.Canvas(inner, bg='#D5D8DC',
                                         height=14, highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, pady=(3, 0))
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 14, fill=self.GREEN, outline='')

    def _build_footer(self):
        """底部操作栏 — 状态 + 导出 + 退出"""
        foot = tk.Frame(self.root, bg=self.BG, height=44)
        foot.pack(fill=tk.X, padx=8, pady=(4, 8), side=tk.BOTTOM)
        foot.pack_propagate(0)

        self.status_label = tk.Label(foot, text=u'就绪',
                                     font=self.FONT_NORMAL,
                                     bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=4)

        tk.Button(foot, text=u'  退 出  ', command=self.root.quit,
                  bg=self.RED, fg='white', relief=tk.FLAT,
                  font=self.FONT_BOLD, cursor='hand2',
                  padx=20, pady=2).pack(side=tk.RIGHT, padx=(6, 0), ipady=4)

        self.start_btn = tk.Button(foot, text=u'  ▶ 开始导出  ',
                                   command=self._on_export,
                                   bg=self.GREEN, fg='white', relief=tk.FLAT,
                                   font=self.FONT_BOLD, cursor='hand2',
                                   padx=24, pady=2)
        self.start_btn.pack(side=tk.RIGHT, ipady=4)

    # -- 交互逻辑 -----------------------------------------------------------

    def _log(self, msg):
        """日志输出"""
        self.log_text.config(state=tk.NORMAL)
        ts = time.strftime('%H:%M:%S')
        self.log_text.insert(tk.END, '[%s] %s\n' % (ts, msg))
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _update_progress(self, pct):
        """更新进度条 0-100"""
        w = float(self.progress_canvas.winfo_width())
        self.progress_canvas.coords(self.progress_bar, 0, 0,
                                    w * pct / 100.0, 14)
        self.status_label.config(
            text=u'导出中... %d%%' % int(pct),
            fg=self.ORANGE)
        self.root.update_idletasks()

    def _on_job_browse(self):
        """选择 Job 路径 (.tgz 优先, 目录备选)"""
        # 优先弹出文件选择器 —— Genesis Job 最常见格式为 .tgz
        p = filedialog.askopenfilename(
            title=u'选择 Genesis Job .tgz 文件',
            filetypes=[(u'TGZ 压缩包', '*.tgz;*.tar.gz'),
                       (u'TGZ 文件', '*.tgz'),
                       (u'所有文件', '*.*')])
        if not p:
            # 文件选择取消 → 可以选择目录
            p = filedialog.askdirectory(title=u'或选择 Genesis Job 目录')
        if p:
            self.var_job.set(p)

    def _on_job_load(self):
        """加载 Job"""
        path = self.var_job.get().strip()
        if not path:
            messagebox.showwarning(u'提示', u'请先输入或选择 Job 路径')
            return
        if not (os.path.isfile(path) or os.path.isdir(path)):
            messagebox.showerror(u'错误', u'Job 路径不存在:\n' + path)
            return

        self._log(u'加载 Job: ' + path)
        ok = self.job.load(path)
        if not ok:
            messagebox.showerror(u'错误', u'无法打开 Job:\n' + path)
            return

        job_name = self.job.job_name()
        self._log(u'Job 名称: ' + job_name)
        if self.job.extracted_dir:
            self._log(u'解压至: ' + self.job.extracted_dir)
        self._on_step_refresh()

    def _on_step_refresh(self):
        """刷新 Step 列表, 优先匹配配置文件中的 step"""
        steps = self.job.scan_steps()
        self._log(u'发现 %d 个 Step' % len(steps))
        menu = self.step_menu['menu']
        menu.delete(0, tk.END)
        for s in steps:
            menu.add_command(
                label=s, command=lambda v=s: self._on_step_select(v))

        if not steps:
            return

        # 配置匹配: 从 _cfg_steps 中找第一个存在的
        matched = None
        for cfg_step in self._cfg_steps:
            cfg_lower = cfg_step.lower()
            for s in steps:
                if s.lower() == cfg_lower:
                    matched = s
                    break
            if matched:
                break

        default_step = matched or steps[0]
        self.var_step.set(default_step)
        self._on_step_select(default_step)

    def _on_step_select(self, step_name):
        """选中 Step 后加载图层"""
        self.var_step.set(step_name)
        self._on_layer_refresh()

    def _on_layer_refresh(self):
        """刷新图层列表"""
        step = self.var_step.get().strip()
        if not step or step.startswith(u'('):
            return

        layers = self.job.scan_layers(step)
        self._log(u'Step [%s] 发现 %d 个图层' % (step, len(layers)))

        # 清空旧的
        for w in self.layer_frame.winfo_children():
            w.destroy()
        self.layer_vars.clear()

        # 重建 checkbutton (按配置过滤)
        for lname in layers:
            # 配置文件图层过滤: 非 * 时只显示匹配的图层
            if self._cfg_layers and self._cfg_layers != ['*']:
                matched = False
                for cfg_layer in self._cfg_layers:
                    if lname.lower() == cfg_layer.lower():
                        matched = True
                        break
                if not matched:
                    continue  # 不匹配的图层不显示

            var = tk.IntVar(value=1)  # 显示的图层默认选中
            var.trace('w', lambda *_a: self._update_layer_count())
            self.layer_vars[lname] = var
            ltype = self.job.classify_layer(lname)
            color = DXF_LAYER_COLORS.get(ltype, 7)
            color_hex = ['#000000','#FF0000','#FFFF00','#00FF00',
                         '#00FFFF','#0000FF','#FF00FF','#FFFFFF'][color - 1]
            display = '%s  [%s]' % (lname, ltype)
            cb = tk.Checkbutton(self.layer_frame, text=display,
                                variable=var, bg='#F2F4F4',
                                font=self.FONT_SMALL,
                                selectcolor='#F2F4F4',
                                activebackground='#EAECEE',
                                fg=color_hex)
            cb.pack(anchor=tk.W)

        self.layer_frame.update_idletasks()
        self.layer_canvas.config(
            scrollregion=(0, 0, self.layer_frame.winfo_reqwidth(),
                          self.layer_frame.winfo_reqheight()))
        self._update_layer_count()  # 更新信息条 (含过滤后计数)

    def _update_layer_count(self):
        """更新图层选中计数"""
        total = len(self.layer_vars)
        selected = sum(1 for v in self.layer_vars.values() if v.get())
        self.layer_info.config(
            text=u'  Step: %s  |  共 %d 层  |  已选: %d' % (
                self.var_step.get().strip(), total, selected))

    def _on_select_all(self):
        for v in self.layer_vars.values():
            v.set(1)
        self._update_layer_count()

    def _on_select_none(self):
        for v in self.layer_vars.values():
            v.set(0)
        self._update_layer_count()

    def _on_output_browse(self):
        p = filedialog.askdirectory(title=u'选择 DXF 输出文件夹')
        if p:
            self.var_output.set(p)

    # -- 导出主流程 ---------------------------------------------------------

    def _on_export(self):
        """导出按钮 — 校验参数后占位提示 (后续自行添加导出逻辑)"""
        # 校验输入
        job_path = self.var_job.get().strip()
        job = job_path.split('/')[-1].replace('.tgz','')
        step = self.var_step.get().strip()
        output_dir = self.var_output.get().strip()
        unit = self.var_unit.get()
        dxf_mode = self.var_dxf_mode.get()

        if not job_path:
            messagebox.showwarning(u'提示', u'请先加载 Job')
            return
        if not step or step.startswith(u'('):
            messagebox.showwarning(u'提示', u'请选择 Step')
            return
        if not output_dir:
            messagebox.showwarning(u'提示', u'请选择输出目录')
            return

        selected_layers = [l for l, v in self.layer_vars.items() if v.get()]
        if not selected_layers:
            messagebox.showwarning(u'提示', u'请至少选择一个图层')
            return

        mode_text = u'轮廓' if dxf_mode == 'yes' else u'实体'
        output_dir = output_dir + '/' + job
        if os.path.exists(output_dir) is False:
            os.makedirs(output_dir)
        # 参数汇总
        self._log(u'========== 导出参数确认 ==========')
        self._log(u'Job:     %s' % job_path)
        self._log(u'Step:    %s' % step)
        self._log(u'单位:    %s' % unit)
        self._log(u'输出:    %s' % output_dir)
        self._log(u'模式:    %s' % mode_text)
        self._log(u'图层:    %s' % (', '.join(selected_layers)))
        self._log(u'=====================================')

        # messagebox.showinfo(u'准备就绪',
        #     u'参数校验通过!\n\n'
        #     u'选中 %d 个图层\n'
        #     u'DXF 模式: %s\n'
        #     u'输出目录: %s\n\n'
        #     u'导出逻辑待后续添加 (在 get_layer_data() 中对接 Genesis API)。' %
        #     (len(selected_layers), dxf_mode, output_dir))

        # self.status_label.config(text=u'就绪 (导出逻辑待添加)', fg=self.GRAY)
        self._load_job_info(job_path,job,step,','.join(selected_layers),output_dir,unit,dxf_mode)

    def _load_job_info(self,tgz_path,job,step,layers,output_dir,unit,dxf_mode):
        """启动 Genesis 批处理 — 写临时 csh 脚本并调用 get.exe"""
        self._log(','.join([tgz_path,job,step,layers,output_dir,unit,dxf_mode]))

        genesis_dir = self.genesis_dir
        genesis_edir = genesis_dir + f'/e{self.genesis_ver}/get'
        xmanager_exe = genesis_dir + '/Xmanager139/XMANAGER.exe'
        project_dir = os.path.dirname(os.path.abspath(__file__))
        # guid_script = os.path.join(project_dir, 'import_tgz.csh').replace('\\', '/')
        guid_script = os.path.join(os.getcwd(), 'import_tgz.csh').replace('\\', '/')
        run_pid = os.getpid()
        run_get_file = 'C:/tmp/run_get_%s.csh' % run_pid

        self._kill_xmanager()

        # 启动 XMANAGER
        if os.path.isfile(xmanager_exe):
            subprocess.Popen(xmanager_exe, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print('[OutputDxf] XMANAGER 已启动')

        # 检查 Genesis 目录
        if not os.path.isdir(genesis_edir):
            print('[OutputDxf] Genesis 目录异常: %s' % genesis_edir)
            messagebox.showerror(u'错误', u'Genesis 安装目录不存在:\n%s' % genesis_edir)
            return
        if not os.path.isfile(os.path.join(genesis_edir, 'get.exe')):
            print('[OutputDxf] get.exe 不存在')
            messagebox.showerror(u'错误', u'get.exe 未找到')
            return

        # 写入 csh 启动脚本
        params = [tgz_path, job, step, layers, output_dir, unit, dxf_mode]
        csh_content = (
            '#!/c:/bin/csh\n'
            'setenv GENESIS_DIR %s\n'
            'cd %s\n'
            './get.exe -x -s%s %s\n'
            'exit 0\n'
        ) % (genesis_dir, genesis_edir, guid_script, ' '.join(params))

        with open(run_get_file, 'w') as f:
            f.write(csh_content + '\n')
        print('[OutputDxf] 启动脚本: %s' % run_get_file)

        # 执行 csh
        os.chdir(genesis_edir)
        print('[OutputDxf] 启动 Genesis ...')
        os.system('csh %s' % run_get_file)
        print('[OutputDxf] Genesis 已退出')
        messagebox.showinfo(u'提示', u'转换完成')

    @staticmethod
    def _kill_xmanager():
        """关闭 XMANAGER.exe 进程 (大小写不敏感匹配)"""
        try:
            if sys.platform != 'win32':
                return
            # 全量 tasklist, 不用 /fi 过滤 (避免大小写漏掉)
            p = subprocess.Popen('tasklist /fo csv', shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate()
            if isinstance(out, bytes):
                out = out.decode('gbk', errors='replace')
            # print('[OutputDxf] tasklist 输出 (前200字):\n' + out[:200])

            killed = False
            for line in out.split('\n'):
                if 'xmanager' not in line.lower():
                    continue
                # CSV 格式: "映像名称","PID","会话名",...
                parts = line.split(',')
                if not parts:
                    continue
                proc_name = parts[0].strip('"').strip()
                if not proc_name or 'xmanager' not in proc_name.lower():
                    continue
                print('[OutputDxf] 发现进程: %s' % proc_name)
                # taskkill /f /t
                subprocess.call('taskkill /f /t /im "%s"' % proc_name, shell=True)
                print('[OutputDxf] 已 kill: %s' % proc_name)
                killed = True

            if not killed:
                print('[OutputDxf] 未找到 xmanager 进程, 无需关闭')
        except Exception:
            pass




# ==========================================================================
# 5. 独立运行 / Genesis 调用入口
# ==========================================================================

def run_standalone():
    """独立 GUI 模式"""
    DxfExportApp()


def run_genesis():
    """
    Genesis 内部命令行调用模式
    用法: gen_cmd main_dxf_export.py --genesis job_path step layer output unit
    """
    args = sys.argv[1:]
    if '--genesis' in args or '--batch' in args:
        _batch_export()
    else:
        run_standalone()


def _batch_export():
    """批量命令行导出模式 (待后续添加导出逻辑)"""
    print('OutputDxf v%s - DXF Export' % VERSION)
    print('批量导出逻辑待后续添加 (在 get_layer_data() 中对接 Genesis API)。')
    print('请使用 GUI 模式: python main_dxf_export.py')


if __name__ == '__main__':
    run_genesis()
