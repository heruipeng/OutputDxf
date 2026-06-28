#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
 main_dxf_export.py  —  GENESIS 2000 自动导出 DXF 工具
 鹏程工作室 出品
=============================================================================
 运行环境 : Python 2.7  |  纯 Tkinter GUI  |  无第三方依赖
 兼容    : Windows Genesis / Linux Genesis
 调用方式 : python main_dxf_export.py          (独立启动)
           gen_cmd main_dxf_export.py          (Genesis 命令行调用)
           Genesis 菜单一键启动 (配合 .scr 注册脚本)
=============================================================================
 模块划分:
   1. DxfWriter     — 纯文本 DXF R12/R14 写入模块
   2. JobAdapter    — Genesis 数据接口适配层
   3. DataProcessor — 图形数据预处理 (过滤/去重/优化)
   4. DxfExportApp  — Tkinter GUI 主界面
=============================================================================
"""

from __future__ import print_function, unicode_literals, division

import sys
import os
import re
import math
import time
import traceback
import tarfile
import tempfile
import shutil
import fnmatch

# ==========================================================================
# Python 2.7 Tkinter 兼容
# ==========================================================================
try:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import tkFont
    import ScrolledText as scrolledtext
    PY_VERSION = 2
except ImportError:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import font as tkFont
    from tkinter import scrolledtext
    PY_VERSION = 3

# OrderedDict — Python 2.7 内置
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

# json — Python 2.6+ 内置; 2.6 无则回退 ConfigParser
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

# ==========================================================================
# 全局常量
# ==========================================================================
VERSION = '2.0.0'
BRAND   = u'鹏程工作室 出品'

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
# 1. DxfWriter — 纯文本 DXF R12 写入模块
# ==========================================================================

class DxfWriter(object):
    """纯文本生成标准 DXF R12 文件，无需任何第三方 CAD 库"""

    def __init__(self, filepath, unit='mm', precision=4):
        """
        Args:
            filepath:  输出 .dxf 文件路径
            unit:      'mm' 毫米 / 'inch' 英寸
            precision: 坐标小数位数
        """
        self.fp = None
        self.filepath = filepath
        self.unit = unit
        self.precision = precision
        self._entities = []
        self._current_layer = '0'
        self._layers_used = set(['0'])

    # -- 坐标格式化 --------------------------------------------------------

    def _fmt(self, val, default=0.0):
        """格式化数值为 DXF 组码精度字符串"""
        v = float(val) if val is not None else float(default)
        return ('{:.' + str(self.precision) + 'f}').format(v)

    # -- DXF 基础结构 ------------------------------------------------------

    def _write_header(self):
        """写入 DXF HEADER 段"""
        f = self.fp
        # 单位: 4=mm, 1=inch
        insunits = '4' if self.unit == 'mm' else '1'
        measurement = '1' if self.unit == 'mm' else '0'
        f.write('0\nSECTION\n2\nHEADER\n')
        f.write('9\n$ACADVER\n1\nAC1009\n')              # R12 版本
        f.write('9\n$INSBASE\n10\n0.0\n20\n0.0\n30\n0.0\n')
        f.write('9\n$EXTMIN\n10\n0.0\n20\n0.0\n30\n0.0\n')
        f.write('9\n$EXTMAX\n10\n100.0\n20\n100.0\n30\n0.0\n')
        f.write('9\n$LIMMIN\n10\n0.0\n20\n0.0\n')
        f.write('9\n$LIMMAX\n10\n100.0\n20\n100.0\n')
        f.write('9\n$MEASUREMENT\n70\n' + measurement + '\n')
        f.write('9\n$INSUNITS\n70\n' + insunits + '\n')
        f.write('9\n$LUNITS\n70\n2\n')
        f.write('9\n$LUPREC\n70\n' + str(self.precision) + '\n')
        f.write('0\nENDSEC\n')

    def _write_tables(self):
        """写入 TABLES 段 (图层表 + 线型表)"""
        f = self.fp
        f.write('0\nSECTION\n2\nTABLES\n')

        # -- 线型表 LTYPE --
        f.write('0\nTABLE\n2\nLTYPE\n70\n3\n')   # 3 种线型
        # CONTINUOUS (默认)
        f.write('0\nLTYPE\n2\nCONTINUOUS\n70\n0\n3\nSolid line\n'
                '72\n65\n73\n0\n40\n0.0\n')
        # DASHED
        f.write('0\nLTYPE\n2\nDASHED\n70\n0\n3\nDashed __ __\n'
                '72\n65\n73\n2\n40\n0.6\n49\n0.4\n49\n-0.2\n')
        # CENTER
        f.write('0\nLTYPE\n2\nCENTER\n70\n0\n3\nCenter ____ _ ____\n'
                '72\n65\n73\n4\n40\n2.0\n49\n1.25\n49\n-0.25\n49\n0.25\n49\n-0.25\n')
        f.write('0\nENDTAB\n')

        # -- 图层表 LAYER --
        f.write('0\nTABLE\n2\nLAYER\n70\n' +
                str(len(self._layers_used) + 1) + '\n')
        # 默认图层 0
        f.write('0\nLAYER\n2\n0\n70\n0\n62\n7\n6\nCONTINUOUS\n')

        # 所有使用的图层
        for lname in sorted(self._layers_used):
            if lname == '0':
                continue
            color = DXF_LAYER_COLORS.get(lname, 7)
            f.write('0\nLAYER\n2\n' + lname + '\n70\n0\n62\n' +
                    str(color) + '\n6\nCONTINUOUS\n')

        f.write('0\nENDTAB\n')
        f.write('0\nENDSEC\n')

    def _write_entities_start(self):
        """开始 ENTITIES 段"""
        self.fp.write('0\nSECTION\n2\nENTITIES\n')

    def _write_entities_end(self):
        """结束 ENTITIES 段 + EOF"""
        self.fp.write('0\nENDSEC\n0\nEOF\n')

    # -- 几何实体方法 ------------------------------------------------------

    def add_line(self, x1, y1, x2, y2, layer='0'):
        """添加线段"""
        self._layers_used.add(layer)
        self._entities.append(('LINE', {
            'layer': layer,
            'x1':    self._fmt(x1),
            'y1':    self._fmt(y1),
            'x2':    self._fmt(x2),
            'y2':    self._fmt(y2),
        }))

    def add_circle(self, cx, cy, radius, layer='0'):
        """添加圆"""
        self._layers_used.add(layer)
        self._entities.append(('CIRCLE', {
            'layer':  layer,
            'cx':     self._fmt(cx),
            'cy':     self._fmt(cy),
            'radius': self._fmt(radius),
        }))

    def add_arc(self, cx, cy, radius, angle_start, angle_end, layer='0'):
        """添加圆弧 (角度制, 0° = 3点钟方向)"""
        self._layers_used.add(layer)
        self._entities.append(('ARC', {
            'layer':       layer,
            'cx':          self._fmt(cx),
            'cy':          self._fmt(cy),
            'radius':      self._fmt(radius),
            'angle_start': self._fmt(angle_start),
            'angle_end':   self._fmt(angle_end),
        }))

    def add_polyline(self, points, closed=True, layer='0'):
        """添加多段线 (R12 POLYLINE + VERTEX)
        Args:
            points: [(x1,y1), (x2,y2), ...] 顶点列表
            closed: 是否闭合
        """
        if len(points) < 2:
            return
        self._layers_used.add(layer)
        self._entities.append(('POLYLINE', {
            'layer':  layer,
            'closed': 1 if closed else 0,
            'points': [(self._fmt(p[0]), self._fmt(p[1])) for p in points],
        }))

    def add_text(self, x, y, text, height=2.5, layer='0', rotation=0.0):
        """添加单行文字"""
        self._layers_used.add(layer)
        self._entities.append(('TEXT', {
            'layer':    layer,
            'x':        self._fmt(x),
            'y':        self._fmt(y),
            'text':     text,
            'height':   self._fmt(height),
            'rotation': self._fmt(rotation),
        }))

    def add_point(self, x, y, layer='0'):
        """添加点 (钻孔中心标记)"""
        self._layers_used.add(layer)
        self._entities.append(('POINT', {
            'layer': layer,
            'x':     self._fmt(x),
            'y':     self._fmt(y),
        }))

    # -- 写入实体到文件 ----------------------------------------------------

    def _flush_entities(self):
        """将所有缓存实体写入 DXF 文件"""
        f = self.fp
        for etype, data in self._entities:
            layer = data['layer']
            if etype == 'LINE':
                f.write('0\nLINE\n8\n' + layer + '\n'
                        '10\n' + data['x1'] + '\n20\n' + data['y1'] + '\n30\n0.0\n'
                        '11\n' + data['x2'] + '\n21\n' + data['y2'] + '\n31\n0.0\n')
            elif etype == 'CIRCLE':
                f.write('0\nCIRCLE\n8\n' + layer + '\n'
                        '10\n' + data['cx'] + '\n20\n' + data['cy'] + '\n30\n0.0\n'
                        '40\n' + data['radius'] + '\n')
            elif etype == 'ARC':
                f.write('0\nARC\n8\n' + layer + '\n'
                        '10\n' + data['cx'] + '\n20\n' + data['cy'] + '\n30\n0.0\n'
                        '40\n' + data['radius'] + '\n'
                        '50\n' + data['angle_start'] + '\n'
                        '51\n' + data['angle_end'] + '\n')
            elif etype == 'POLYLINE':
                f.write('0\nPOLYLINE\n8\n' + layer + '\n66\n1\n'
                        '70\n' + str(data['closed']) + '\n')
                for px, py in data['points']:
                    f.write('0\nVERTEX\n8\n' + layer + '\n'
                            '10\n' + px + '\n20\n' + py + '\n30\n0.0\n')
                f.write('0\nSEQEND\n')
            elif etype == 'TEXT':
                f.write('0\nTEXT\n8\n' + layer + '\n'
                        '10\n' + data['x'] + '\n20\n' + data['y'] + '\n30\n0.0\n'
                        '40\n' + data['height'] + '\n'
                        '1\n' + data['text'] + '\n'
                        '50\n' + data['rotation'] + '\n')
            elif etype == 'POINT':
                f.write('0\nPOINT\n8\n' + layer + '\n'
                        '10\n' + data['x'] + '\n20\n' + data['y'] + '\n30\n0.0\n')

    def save(self):
        """保存 DXF 文件"""
        out_dir = os.path.dirname(self.filepath)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        self.fp = open(self.filepath, 'w')
        try:
            self._write_header()
            self._write_tables()
            self._write_entities_start()
            self._flush_entities()
            self._write_entities_end()
        finally:
            self.fp.close()

        return self.filepath


# -*- coding: utf-8 -*-
# auto-generated replacement block

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
# 3. DataProcessor — 图形数据预处理
# ==========================================================================
class DataProcessor(object):
    """图形数据预处理: 过滤、去重、优化"""

    def __init__(self, unit='mm', min_segment_len=0.01, tolerance=0.001):
        """
        Args:
            unit:            'mm' / 'inch'
            min_segment_len: 最小线段长度 (小于此值的线段将被过滤)
            tolerance:       容差 (用于去重判断)
        """
        self.unit = unit
        self.min_segment_len = min_segment_len
        self.tolerance = tolerance
        if unit == 'inch':
            self.min_segment_len = min_segment_len / 25.4
            self.tolerance = tolerance / 25.4

    def filter_short_lines(self, lines):
        """过滤过短的线段"""
        result = []
        for x1, y1, x2, y2 in lines:
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            if length >= self.min_segment_len:
                result.append((x1, y1, x2, y2))
        return result

    def filter_small_circles(self, circles, min_radius=0.05):
        """过滤过小的圆 (钻头残留碎屑)"""
        result = []
        for cx, cy, radius in circles:
            if abs(radius) >= min_radius:
                result.append((cx, cy, abs(radius)))
        return result

    def deduplicate_lines(self, lines):
        """线段去重 (方向无关)"""
        seen = set()
        result = []
        for x1, y1, x2, y2 in lines:
            # 标准化端点顺序
            if (x1 > x2) or (abs(x1 - x2) < self.tolerance and y1 > y2):
                key = (round(x2 / self.tolerance) * self.tolerance,
                       round(y2 / self.tolerance) * self.tolerance,
                       round(x1 / self.tolerance) * self.tolerance,
                       round(y1 / self.tolerance) * self.tolerance)
            else:
                key = (round(x1 / self.tolerance) * self.tolerance,
                       round(y1 / self.tolerance) * self.tolerance,
                       round(x2 / self.tolerance) * self.tolerance,
                       round(y2 / self.tolerance) * self.tolerance)
            if key not in seen:
                seen.add(key)
                result.append((x1, y1, x2, y2))
        return result

    def deduplicate_circles(self, circles):
        """圆去重 (同圆心、同半径)"""
        seen = set()
        result = []
        for cx, cy, radius in circles:
            key = (round(cx / self.tolerance) * self.tolerance,
                   round(cy / self.tolerance) * self.tolerance,
                   round(radius / self.tolerance) * self.tolerance)
            if key not in seen:
                seen.add(key)
                result.append((cx, cy, radius))
        return result

    def close_polygon(self, points):
        """确保多边形闭合 (首尾相连)"""
        if len(points) < 3:
            return points
        first = points[0]
        last = points[-1]
        dx = first[0] - last[0]
        dy = first[1] - last[1]
        if math.sqrt(dx * dx + dy * dy) > self.tolerance:
            return points + [first]
        return points

    def convert_units(self, value, from_unit, to_unit):
        """单位转换"""
        if from_unit == to_unit:
            return value
        if from_unit == 'mil' and to_unit == 'mm':
            return value * 0.0254
        if from_unit == 'mil' and to_unit == 'inch':
            return value * 0.001
        if from_unit == 'mm' and to_unit == 'mil':
            return value / 0.0254
        if from_unit == 'mm' and to_unit == 'inch':
            return value / 25.4
        if from_unit == 'inch' and to_unit == 'mm':
            return value * 25.4
        if from_unit == 'inch' and to_unit == 'mil':
            return value * 1000.0
        return value

    def convert_layer_data(self, layer_data, from_unit, to_unit):
        """对整个图层数据进行单位转换"""
        factor = self.convert_units(1.0, from_unit, to_unit)
        result = {'lines': [], 'circles': [], 'pads': [],
                  'arcs': [], 'surfaces': [], 'drills': []}

        for item in layer_data.get('lines', []):
            result['lines'].append(tuple(v * factor for v in item))

        for item in layer_data.get('circles', []):
            result['circles'].append(tuple(v * factor for v in item))

        for item in layer_data.get('pads', []):
            result['pads'].append(tuple(v * factor for v in item))

        for item in layer_data.get('arcs', []):
            cx, cy, r, sa, ea = item
            result['arcs'].append((cx * factor, cy * factor,
                                   r * factor, sa, ea))

        for item in layer_data.get('surfaces', []):
            result['surfaces'].append(
                [(x * factor, y * factor) for x, y in item])

        for item in layer_data.get('drills', []):
            result['drills'].append(tuple(v * factor for v in item))

        return result


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
        self.dp       = DataProcessor(unit='mm')
        self.worker   = None  # 转换工作状态
        self.cfg = self._load_cfg()

        self._setup_root()
        self._setup_fonts()
        self._build_ui()

        # 加载配置
        self._apply_cfg_defaults()

        self.root.mainloop()

    # -- 配置文件 -----------------------------------------------------------

    @staticmethod
    def _cfg_path():
        """配置文件路径: 同目录下 outputdxf.cfg (Python 2.7 中文路径兼容)"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Python 2.7: 如果路径含中文, __file__ 可能是字节串, 需要显式转 unicode
            if isinstance(script_dir, bytes):
                script_dir = script_dir.decode(sys.getfilesystemencoding())
            return os.path.join(script_dir, u'outputdxf.cfg')
        except Exception:
            # 降级: 用当前工作目录
            return os.path.join(os.getcwdu() if hasattr(os, 'getcwdu') else os.getcwd(),
                                u'outputdxf.cfg')

    @staticmethod
    def _load_cfg():
        """读取配置文件 (Python 2.7 中文路径兼容)"""
        cfg = {}
        cfg_path = DxfExportApp._cfg_path()
        if not os.path.isfile(cfg_path):
            return cfg
        try:
            import ConfigParser as cp
        except ImportError:
            import configparser as cp
        try:
            parser = cp.ConfigParser()
            # Python 2.7: ConfigParser.read() 对 unicode 路径兼容性差,
            # 用 open + readfp 绕过
            if PY_VERSION == 2 and isinstance(cfg_path, unicode):
                with open(cfg_path, 'r') as fh:
                    parser.readfp(fh)
            else:
                parser.read(cfg_path)
            for section in parser.sections():
                cfg[section] = {}
                for k, v in parser.items(section):
                    cfg[section][k] = v
        except Exception:
            pass
        return cfg

    def _apply_cfg_defaults(self):
        """应用配置文件默认值到界面"""
        if 'paths' in self.cfg:
            p = self.cfg['paths'].get('output_path', '').strip()
            if p:
                self.var_output.set(p)
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
        if PY_VERSION == 2:
            try:
                self.root = tk.Tk()
                self.root.tk.eval('encoding system utf-8')
            except Exception:
                self.root = tk.Tk()
        else:
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
        if PY_VERSION == 2 and is_win:
            # Windows Python 2 — 检测中文字体
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
        tk.Label(hdr, text=u'Genesis DXF 自动导出 ' + BRAND,
                 font=self.FONT_SMALL, bg=self.ACCENT, fg='#AED6F1').pack(
            side=tk.RIGHT, padx=10, pady=12)

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
        self.var_dxf_mode = tk.StringVar(value='outline')
        for txt, val in [(u'  轮廓  ', 'outline'), (u'  实体  ', 'solid')]:
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

        mode_text = u'轮廓' if dxf_mode == 'outline' else u'实体'

        # 参数汇总
        self._log(u'========== 导出参数确认 ==========')
        self._log(u'Job:     %s' % job_path)
        self._log(u'Step:    %s' % step)
        self._log(u'单位:    %s' % ('毫米' if unit == 'mm' else '英寸'))
        self._log(u'输出:    %s' % output_dir)
        self._log(u'模式:    %s' % mode_text)
        self._log(u'图层:    %s' % (', '.join(selected_layers)))
        self._log(u'=====================================')

        messagebox.showinfo(u'准备就绪',
            u'参数校验通过!\n\n'
            u'选中 %d 个图层\n'
            u'DXF 模式: %s\n'
            u'输出目录: %s\n\n'
            u'导出逻辑待后续添加 (在 get_layer_data() 中对接 Genesis API)。' %
            (len(selected_layers), mode_text, output_dir))

        self.status_label.config(text=u'就绪 (导出逻辑待添加)', fg=self.GRAY)


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
    print(BRAND)
    print('批量导出逻辑待后续添加 (在 get_layer_data() 中对接 Genesis API)。')
    print('请使用 GUI 模式: python main_dxf_export.py')


if __name__ == '__main__':
    run_genesis()
