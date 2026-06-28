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
   2. GenesisAPI    — Genesis 数据接口适配层
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


# ==========================================================================
# 2. GenesisAPI — Genesis 数据接口适配层
# ==========================================================================

class GenesisAPI(object):
    """
    Genesis 2000 数据接口适配层

    优先使用 Genesis 内置 Python API 获取数据;
    当不在 Genesis 环境中运行时，自动降级为文件模式 (解析 .tgz / 目录)。

    典型 Genesis Python API 调用:
        import genesis
        genesis.open_job(job_path)
        genesis.get_steps(job)
        genesis.get_layers(step)
        genesis.get_entities(layer, entity_type='line|arc|poly|surface|pad')
    """

    def __init__(self):
        self.inside_genesis = False
        self.genesis_module = None
        self.job_path = ''
        self.steps = []
        self.layers = {}
        self._init_genesis()

    def _init_genesis(self):
        """检测是否运行在 Genesis 环境中"""
        try:
            import genesis
            self.genesis_module = genesis
            self.inside_genesis = True
        except ImportError:
            self.inside_genesis = False

    # -- Job 操作 ----------------------------------------------------------

    def open_job(self, job_path):
        """打开 Genesis Job"""
        self.job_path = job_path
        if self.inside_genesis:
            try:
                self.genesis_module.open_job(job_path)
                return True
            except Exception:
                return False
        else:
            return os.path.isdir(job_path) or os.path.isfile(job_path)

    def get_job_name(self):
        """获取当前 Job 名称"""
        if self.job_path:
            base = os.path.basename(self.job_path.rstrip('/\\'))
            if base.endswith('.tgz'):
                base = base[:-4]
            return base
        return 'UNKNOWN'

    # -- Step 操作 ---------------------------------------------------------

    def get_steps(self):
        """获取 Job 下所有 Step 列表"""
        if self.inside_genesis:
            try:
                self.steps = self.genesis_module.get_steps()
                return self.steps
            except Exception:
                pass

        # 降级: 从文件系统读取
        self.steps = self._scan_steps_fs()
        return self.steps

    def _scan_steps_fs(self):
        """从本地目录/压缩包扫描 Step 列表"""
        steps = []
        job_path = self.job_path
        if not job_path:
            return steps

        # 如果是 .tgz 压缩包
        if job_path.endswith('.tgz') and os.path.isfile(job_path):
            try:
                with tarfile.open(job_path, 'r:gz') as tf:
                    for member in tf.getmembers():
                        parts = member.name.split('/')
                        if len(parts) >= 2 and parts[0] not in steps:
                            if not parts[0].startswith('.'):
                                steps.append(parts[0])
            except Exception:
                pass
        elif os.path.isdir(job_path):
            # 本地目录
            try:
                for item in os.listdir(job_path):
                    full = os.path.join(job_path, item)
                    if os.path.isdir(full) and not item.startswith('.'):
                        steps.append(item)
            except Exception:
                pass

        self.steps = sorted(steps)
        return self.steps

    # -- Layer 操作 --------------------------------------------------------

    def get_layers(self, step_name):
        """获取指定 Step 下所有图层"""
        if not step_name:
            return []

        if self.inside_genesis:
            try:
                layers = self.genesis_module.get_layers(step_name)
                return layers
            except Exception:
                pass

        return self._scan_layers_fs(step_name)

    def _scan_layers_fs(self, step_name):
        """从本地文件系统扫描图层"""
        layers = []
        job_path = self.job_path
        if not job_path:
            return layers

        step_dir = os.path.join(job_path, step_name)

        # .tgz 模式
        if job_path.endswith('.tgz') and os.path.isfile(job_path):
            try:
                with tarfile.open(job_path, 'r:gz') as tf:
                    for member in tf.getmembers():
                        parts = member.name.split('/')
                        if (len(parts) >= 3 and parts[0] == step_name
                                and not parts[0].startswith('.')):
                            lname = parts[1]
                            if lname not in layers:
                                layers.append(lname)
            except Exception:
                pass
        elif os.path.isdir(step_dir):
            try:
                for item in os.listdir(step_dir):
                    full = os.path.join(step_dir, item)
                    if os.path.isdir(full) and not item.startswith('.'):
                        layers.append(item)
            except Exception:
                pass

        return sorted(layers)

    # -- 图形数据提取 ------------------------------------------------------

    def get_layer_data(self, step_name, layer_name, data_type='all'):
        """
        提取图层图形数据

        Args:
            step_name:  Step 名称
            layer_name: 图层名称
            data_type:  数据类型 'all'/'lines'/'pads'/'arcs'/'surfaces'/'drills'

        Returns:
            dict: {
                'lines':     [(x1,y1,x2,y2), ...],
                'circles':   [(cx,cy,radius), ...],
                'pads':      [(cx,cy,width,height,rotation), ...],
                'arcs':      [(cx,cy,radius,start_ang,end_ang), ...],
                'surfaces':  [ [(x,y),...], ... ],   # 多边形轮廓
                'drills':    [(cx,cy,diameter), ...],
            }
        """
        result = {
            'lines':     [],
            'circles':   [],
            'pads':      [],
            'arcs':      [],
            'surfaces':  [],
            'drills':    [],
        }

        if self.inside_genesis:
            try:
                return self._get_layer_data_genesis(step_name, layer_name,
                                                    data_type)
            except Exception:
                pass

        return self._get_layer_data_fs(step_name, layer_name, data_type)

    def _get_layer_data_genesis(self, step_name, layer_name, data_type):
        """通过 Genesis API 提取图形数据"""
        result = {
            'lines':     [],
            'circles':   [],
            'pads':      [],
            'arcs':      [],
            'surfaces':  [],
            'drills':    [],
        }
        try:
            g = self.genesis_module

            # 提取线段
            if data_type in ('all', 'lines'):
                lines = g.get_lines(step_name, layer_name)
                if lines:
                    for l in lines:
                        result['lines'].append(
                            (float(l.x1), float(l.y1),
                             float(l.x2), float(l.y2)))

            # 提取焊盘
            if data_type in ('all', 'pads'):
                pads = g.get_pads(step_name, layer_name)
                if pads:
                    for p in pads:
                        result['pads'].append(
                            (float(p.cx), float(p.cy),
                             float(p.width), float(p.height),
                             float(getattr(p, 'rotation', 0))))

            # 提取圆弧
            if data_type in ('all', 'arcs'):
                arcs = g.get_arcs(step_name, layer_name)
                if arcs:
                    for a in arcs:
                        result['arcs'].append(
                            (float(a.cx), float(a.cy),
                             float(a.radius),
                             float(a.start_angle),
                             float(a.end_angle)))

            # 提取表面 (多边形)
            if data_type in ('all', 'surfaces'):
                surfaces = g.get_surfaces(step_name, layer_name)
                if surfaces:
                    for s in surfaces:
                        pts = [(float(p.x), float(p.y)) for p in s.points]
                        result['surfaces'].append(pts)

            # 提取钻孔
            if data_type in ('all', 'drills'):
                drills = g.get_drills(step_name, layer_name)
                if drills:
                    for d in drills:
                        result['drills'].append(
                            (float(d.cx), float(d.cy), float(d.diameter)))

        except Exception:
            pass

        return result

    def _get_layer_data_fs(self, step_name, layer_name, data_type):
        """
        从本地文件系统提取图层数据 (主要为独立测试/演示用途)
        尝试解析 Genesis .tgz 内可能的文本/XML 格式数据
        """
        # 降级模式下返回空数据，由后续流程处理
        # 真正的数据提取需要通过 Genesis API 完成
        return {
            'lines':     [],
            'circles':   [],
            'pads':      [],
            'arcs':      [],
            'surfaces':  [],
            'drills':    [],
        }

    # -- 辅助: 判断图层类型 --------------------------------------------------

    def classify_layer(self, layer_name):
        """根据图层名称推断图层类型"""
        lower = layer_name.lower().replace('_', '').replace('-', '').replace(' ', '')
        for keyword, ltype in LAYER_TYPE_MAP.items():
            kw = keyword.replace('_', '').replace('-', '').replace(' ', '')
            if kw in lower:
                return ltype
        return 'COPPER'  # 默认当作信号层

    # -- 辅助: 单位转换 ------------------------------------------------------

    @staticmethod
    def mil_to_mm(val):
        """mil -> 毫米"""
        return float(val) * 0.0254

    @staticmethod
    def mil_to_inch(val):
        """mil -> 英寸"""
        return float(val) * 0.001

    @staticmethod
    def mm_to_mil(val):
        """毫米 -> mil"""
        return float(val) / 0.0254


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
    WIDTH  = 600
    HEIGHT = 580

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
        self.genesis  = GenesisAPI()
        self.dp       = DataProcessor(unit='mm')
        self.worker   = None  # 转换工作状态

        self._setup_root()
        self._setup_fonts()
        self._build_ui()
        self.root.mainloop()

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
        self.root.geometry(
            '+%d+%d' % ((sw - self.WIDTH)//2, (sh - self.HEIGHT)//2))

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

        # 滚动主区域
        main_canvas = tk.Canvas(self.root, bg=self.BG, highlightthickness=0,
                                height=self.HEIGHT - 90)
        main_canvas.pack(fill=tk.BOTH, expand=1)

        self.main_frame = tk.Frame(main_canvas, bg=self.BG)
        main_canvas.create_window((0, 0), window=self.main_frame,
                                  anchor=tk.NW, tags='main_frame')
        self.main_frame.bind('<Configure>',
                             lambda e: main_canvas.configure(
                                 scrollregion=main_canvas.bbox('all')))

        # Job 路径卡片
        self._card_job()

        # Step 选择卡片
        self._card_step()

        # 图层选择卡片
        self._card_layer()

        # 设置卡片 (单位/输出路径)
        self._card_settings()

        # 日志区域
        self._card_log()

        # 底部按钮
        self._build_footer()

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
                     bg=self.LIGHT_BG, bd=1)
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
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
        # 图层多选: Canvas + Checkbutton 列表
        self.layer_canvas = tk.Canvas(inner, bg=self.CARD_BG,
                                      height=120, highlightthickness=0)
        self.layer_canvas.pack(fill=tk.X, pady=(0, 2))

        self.layer_frame = tk.Frame(self.layer_canvas, bg=self.CARD_BG)
        self.layer_canvas.create_window((0, 0), window=self.layer_frame,
                                        anchor=tk.NW)

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

        # 输出路径
        of_ = tk.Frame(inner, bg=self.CARD_BG)
        of_.pack(fill=tk.X, pady=(2, 0))
        tk.Label(of_, text=u'输出:', font=self.FONT_NORMAL,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)
        self.var_output = tk.StringVar()
        tk.Entry(of_, textvariable=self.var_output,
                 font=self.FONT_MONO, relief=tk.FLAT,
                 bg=self.LIGHT_BG, bd=1).pack(side=tk.LEFT, fill=tk.X,
                                              expand=1, ipady=2, padx=4)
        self._btn(of_, u'...', self._on_output_browse, width=3).pack(
            side=tk.RIGHT)

        # DXF 版本 + 选项
        optf = tk.Frame(inner, bg=self.CARD_BG)
        optf.pack(fill=tk.X, pady=(4, 0))
        tk.Label(optf, text=u'DXF 版本:', font=self.FONT_SMALL,
                 bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)
        self.var_dxf_ver = tk.StringVar(value='R12')
        for v in ['R12', 'R14']:
            tk.Radiobutton(optf, text=v, variable=self.var_dxf_ver, value=v,
                           bg=self.CARD_BG, font=self.FONT_SMALL,
                           selectcolor=self.CARD_BG).pack(
                side=tk.LEFT, padx=(2, 8))

        self.var_split = tk.IntVar(value=0)
        tk.Checkbutton(optf, text=u'每层单独文件',
                       variable=self.var_split,
                       bg=self.CARD_BG, font=self.FONT_SMALL,
                       selectcolor=self.CARD_BG).pack(side=tk.RIGHT)

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
        foot = tk.Frame(self.root, bg=self.BG, height=32)
        foot.pack(fill=tk.X, padx=6, pady=(2, 6))
        foot.pack_propagate(0)

        self.status_label = tk.Label(foot, text=u'就绪',
                                     font=self.FONT_NORMAL,
                                     bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=2)

        tk.Button(foot, text=u'  退 出  ', command=self.root.quit,
                  bg=self.RED, fg='white', relief=tk.FLAT,
                  font=self.FONT_BOLD, cursor='hand2',
                  padx=14).pack(side=tk.RIGHT, padx=(3, 0), ipady=3)

        self.start_btn = tk.Button(foot, text=u'  ▶ 开始导出  ',
                                   command=self._on_export,
                                   bg=self.GREEN, fg='white', relief=tk.FLAT,
                                   font=self.FONT_BOLD, cursor='hand2',
                                   padx=16)
        self.start_btn.pack(side=tk.RIGHT, ipady=3)

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
        """选择 Job 路径 (.tgz 或 目录)"""
        p = filedialog.askdirectory(title=u'选择 Genesis Job 目录')
        if not p:
            p = filedialog.askopenfilename(
                title=u'选择 Genesis Job .tgz 文件',
                filetypes=[(u'TGZ 文件', '*.tgz'), (u'所有', '*.*')])
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
        ok = self.genesis.open_job(path)
        if not ok:
            messagebox.showerror(u'错误', u'无法打开 Job:\n' + path)
            return

        self._log(u'Job 名称: ' + self.genesis.get_job_name())
        self._on_step_refresh()

    def _on_step_refresh(self):
        """刷新 Step 列表"""
        steps = self.genesis.get_steps()
        self._log(u'发现 %d 个 Step' % len(steps))
        menu = self.step_menu['menu']
        menu.delete(0, tk.END)
        for s in steps:
            menu.add_command(
                label=s, command=lambda v=s: self._on_step_select(v))
        if steps:
            self.var_step.set(steps[0])
            self._on_step_select(steps[0])

    def _on_step_select(self, step_name):
        """选中 Step 后加载图层"""
        self.var_step.set(step_name)
        self._on_layer_refresh()

    def _on_layer_refresh(self):
        """刷新图层列表"""
        step = self.var_step.get().strip()
        if not step or step.startswith(u'('):
            return

        layers = self.genesis.get_layers(step)
        self._log(u'Step [%s] 发现 %d 个图层' % (step, len(layers)))

        # 清空旧的
        for w in self.layer_frame.winfo_children():
            w.destroy()
        self.layer_vars.clear()

        # 重建 checkbutton
        for lname in layers:
            var = tk.IntVar(value=1)
            self.layer_vars[lname] = var
            ltype = self.genesis.classify_layer(lname)
            color = DXF_LAYER_COLORS.get(ltype, 7)
            color_hex = ['#000000','#FF0000','#FFFF00','#00FF00',
                         '#00FFFF','#0000FF','#FF00FF','#FFFFFF'][color - 1]
            display = '%s  [%s]' % (lname, ltype)
            cb = tk.Checkbutton(self.layer_frame, text=display,
                                variable=var, bg=self.CARD_BG,
                                font=self.FONT_SMALL,
                                selectcolor=self.CARD_BG,
                                activebackground=self.CARD_BG,
                                fg=color_hex)
            cb.pack(anchor=tk.W)

        self.layer_frame.update_idletasks()
        self.layer_canvas.configure(
            scrollregion=self.layer_canvas.bbox('all'))

    def _on_select_all(self):
        for v in self.layer_vars.values():
            v.set(1)

    def _on_select_none(self):
        for v in self.layer_vars.values():
            v.set(0)

    def _on_output_browse(self):
        p = filedialog.askdirectory(title=u'选择 DXF 输出文件夹')
        if p:
            self.var_output.set(p)

    # -- 导出主流程 ---------------------------------------------------------

    def _on_export(self):
        """开始导出"""
        import threading

        # 禁用按钮
        self.start_btn.config(state=tk.DISABLED, text=u'  导出中...  ')

        self.root.update_idletasks()
        try:
            self._do_export()
        except Exception as e:
            self._log(u'!!! 导出异常: ' + str(e))
            traceback.print_exc()
            messagebox.showerror(u'导出失败', str(e))
        finally:
            self.start_btn.config(state=tk.NORMAL, text=u'  ▶ 开始导出  ')

    def _do_export(self):
        """执行导出流程"""
        # -- 1. 验证输入 --
        job_path = self.var_job.get().strip()
        step = self.var_step.get().strip()
        output_dir = self.var_output.get().strip()
        unit = self.var_unit.get()
        split = bool(self.var_split.get())

        if not job_path:
            raise Exception(u'请先加载 Job')
        if not step or step.startswith(u'('):
            raise Exception(u'请选择 Step')
        if not output_dir:
            raise Exception(u'请选择输出目录')

        selected_layers = [l for l, v in self.layer_vars.items() if v.get()]
        if not selected_layers:
            raise Exception(u'请至少选择一个图层')

        job_name = self.genesis.get_job_name()
        self._log(u'========== 开始导出 ==========')
        self._log(u'Job: %s | Step: %s | 单位: %s' % (job_name, step, unit))
        self._log(u'选中图层: %s' % (', '.join(selected_layers)))

        # 确保输出目录存在
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # -- 2. 逐层提取数据 并 生成 DXF --
        dp = DataProcessor(unit=unit)
        total_layers = len(selected_layers)
        exported_files = []

        for idx, layer_name in enumerate(selected_layers):
            self._log(u'处理图层 [%d/%d]: %s' %
                      (idx+1, total_layers, layer_name))

            # 提取 Genesis 图形数据
            layer_data = self.genesis.get_layer_data(step, layer_name)
            layer_type = self.genesis.classify_layer(layer_name)

            # 单位转换: Genesis 内部 mil -> 目标单位
            layer_data = dp.convert_layer_data(layer_data, 'mil', unit)

            # 数据预处理
            layer_data['lines'] = dp.filter_short_lines(
                layer_data['lines'])
            layer_data['lines'] = dp.deduplicate_lines(
                layer_data['lines'])
            layer_data['circles'] = dp.filter_small_circles(
                layer_data['circles'])
            layer_data['circles'] = dp.deduplicate_circles(
                layer_data['circles'])

            # 统计图形数量
            total_entities = (len(layer_data['lines']) +
                              len(layer_data['circles']) +
                              len(layer_data['pads']) +
                              len(layer_data['arcs']) +
                              len(layer_data['surfaces']) +
                              len(layer_data['drills']))

            self._log(u'  -> 图层类型: %s | 图形数: %d (线%d/圆%d/弧%d/面%d/钻%d)' %
                      (layer_type, total_entities,
                       len(layer_data['lines']),
                       len(layer_data['circles']),
                       len(layer_data['arcs']),
                       len(layer_data['surfaces']),
                       len(layer_data['drills'])))

            if total_entities == 0:
                self._log(u'  -> 图层无数据, 跳过')
                continue

            # 确定 DXF 文件名
            if split:
                dxf_name = '%s_%s_%s.dxf' % (job_name, step, layer_name)
                dxf_path = os.path.join(output_dir, dxf_name)
                self._write_single_layer_dxf(dxf_path, layer_data,
                                             layer_type, unit)
                exported_files.append(dxf_path)
                self._log(u'  -> 输出: %s' % dxf_name)
            else:
                # 合并模式: 收集所有层数据最后统一写入
                if '_merged_data' not in dir(self):
                    self._merged_layers = []
                    self._merged_output_dir = output_dir

                self._merged_layers.append({
                    'name': layer_name,
                    'type': layer_type,
                    'data': layer_data,
                })

            # 更新进度
            pct = (idx + 1) * 100 // total_layers
            self._update_progress(pct)

        # -- 3. 合并模式: 写入单文件多图层 DXF --
        if not split and hasattr(self, '_merged_layers') and self._merged_layers:
            dxf_name = '%s_%s.dxf' % (job_name, step)
            dxf_path = os.path.join(output_dir, dxf_name)
            self._write_merged_dxf(dxf_path, self._merged_layers, unit)
            exported_files.append(dxf_path)
            self._log(u'合并输出: %s' % dxf_name)

        # -- 4. 完成 --
        self._update_progress(100)
        self.status_label.config(text=u'导出完成', fg=self.GREEN)
        self._log(u'========== 导出完成 ==========')
        self._log(u'共导出 %d 个文件' % len(exported_files))

        msg = u'导出完成!\n\n共 %d 个 DXF 文件:\n' % len(exported_files)
        for f in exported_files:
            msg += u'  • ' + os.path.basename(f) + u'\n'
        msg += u'\n输出目录:\n' + output_dir

        messagebox.showinfo(u'导出完成', msg)

    def _write_single_layer_dxf(self, dxf_path, layer_data, layer_type, unit):
        """单图层 DXF 写入"""
        dxf = DxfWriter(dxf_path, unit=unit)

        # 确定目标 DXF 图层名
        dxf_layer = layer_type

        # 写入线段
        for x1, y1, x2, y2 in layer_data.get('lines', []):
            dxf.add_line(x1, y1, x2, y2, layer=dxf_layer)

        # 写入圆弧
        for cx, cy, r, sa, ea in layer_data.get('arcs', []):
            dxf.add_arc(cx, cy, r, sa, ea, layer=dxf_layer)

        # 写入圆 (焊盘)
        for cx, cy, r in layer_data.get('circles', []):
            dxf.add_circle(cx, cy, r, layer=dxf_layer)

        # 写入焊盘 (矩形焊盘 -> 多段线)
        for cx, cy, w, h, rot in layer_data.get('pads', []):
            hw, hh = w / 2.0, h / 2.0
            points = [
                (cx - hw, cy - hh),
                (cx + hw, cy - hh),
                (cx + hw, cy + hh),
                (cx - hw, cy + hh),
            ]
            # 简单旋转 (仅 0/90/180/270)
            if abs(rot - 90) < 0.01 or abs(rot - 270) < 0.01:
                points = [
                    (cx - hh, cy - hw),
                    (cx + hh, cy - hw),
                    (cx + hh, cy + hw),
                    (cx - hh, cy + hw),
                ]
            dxf.add_polyline(points, closed=True, layer=dxf_layer)

        # 写入多边形表面 (轮廓)
        for pts in layer_data.get('surfaces', []):
            if len(pts) >= 3:
                dxf.add_polyline(pts, closed=True, layer=dxf_layer)

        # 写入钻孔
        for dx, dy, dia in layer_data.get('drills', []):
            dxf.add_circle(dx, dy, dia / 2.0, layer='DRILL')
            dxf.add_point(dx, dy, layer='DRILL')

        dxf.save()

    def _write_merged_dxf(self, dxf_path, merged_layers, unit):
        """多图层合并 DXF 写入"""
        dxf = DxfWriter(dxf_path, unit=unit)

        for layer_info in merged_layers:
            lname = layer_info['name']
            ltype = layer_info['type']
            ldata = layer_info['data']
            dxf_layer = ltype + '_' + lname if lname != ltype else ltype

            for x1, y1, x2, y2 in ldata.get('lines', []):
                dxf.add_line(x1, y1, x2, y2, layer=dxf_layer)
            for cx, cy, r, sa, ea in ldata.get('arcs', []):
                dxf.add_arc(cx, cy, r, sa, ea, layer=dxf_layer)
            for cx, cy, r in ldata.get('circles', []):
                dxf.add_circle(cx, cy, r, layer=dxf_layer)
            for cx, cy, w, h, rot in ldata.get('pads', []):
                hw, hh = w / 2.0, h / 2.0
                pts = [(cx - hw, cy - hh), (cx + hw, cy - hh),
                       (cx + hw, cy + hh), (cx - hw, cy + hh)]
                dxf.add_polyline(pts, closed=True, layer=dxf_layer)
            for pts in ldata.get('surfaces', []):
                if len(pts) >= 3:
                    dxf.add_polyline(pts, closed=True, layer=dxf_layer)
            for dx, dy, dia in ldata.get('drills', []):
                dxf.add_circle(dx, dy, dia / 2.0, layer='DRILL')
                dxf.add_point(dx, dy, layer='DRILL')

        dxf.save()


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
    """批量命令行导出模式"""
    print('OutputDxf v%s - Genesis Batch Export' % VERSION)
    print(BRAND)

    args = sys.argv[1:]
    job_path = ''
    step = ''
    layers = []
    output_dir = ''
    unit = 'mm'

    i = 0
    while i < len(args):
        if args[i] in ('--job', '-j') and i+1 < len(args):
            job_path = args[i+1]; i += 2
        elif args[i] in ('--step', '-s') and i+1 < len(args):
            step = args[i+1]; i += 2
        elif args[i] in ('--layers', '-l') and i+1 < len(args):
            layers = args[i+1].split(','); i += 2
        elif args[i] in ('--output', '-o') and i+1 < len(args):
            output_dir = args[i+1]; i += 2
        elif args[i] in ('--unit', '-u') and i+1 < len(args):
            unit = args[i+1]; i += 2
        elif args[i] in ('--genesis', '--batch'):
            i += 1
        else:
            i += 1

    if not job_path or not output_dir:
        print('用法: main_dxf_export.py --genesis -j <job> -s <step> '
              '-l <layer1,layer2> -o <output> [-u mm|inch]')
        return

    try:
        g = GenesisAPI()
        g.open_job(job_path)

        if not step:
            steps = g.get_steps()
            if steps:
                step = steps[0]

        if not layers:
            layers = g.get_layers(step)

        dp = DataProcessor(unit=unit)
        job_name = g.get_job_name()
        dxf_name = '%s_%s.dxf' % (job_name, step)
        dxf_path = os.path.join(output_dir, dxf_name)

        dxf = DxfWriter(dxf_path, unit=unit)
        for layer_name in layers:
            ldata = g.get_layer_data(step, layer_name)
            ltype = g.classify_layer(layer_name)
            ldata = dp.convert_layer_data(ldata, 'mil', unit)

            for x1, y1, x2, y2 in ldata.get('lines', []):
                dxf.add_line(x1, y1, x2, y2, layer=ltype)
            for cx, cy, r in ldata.get('circles', []):
                dxf.add_circle(cx, cy, r, layer=ltype)

        dxf.save()
        print('Done: ' + dxf_path)
    except Exception as e:
        print('Error: ' + str(e))
        sys.exit(1)


if __name__ == '__main__':
    run_genesis()
