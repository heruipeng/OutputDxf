#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OutputDxf - Genesis TGZ -> DXF è½¬æ¢å·¥å·
é¹ç¨å·¥ä½å®¤ åºå
å¼å®¹ Python 2.6+ / Python 3.x | çº¯ Tkinter (æ é ttk)
"""

from __future__ import print_function

try:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    PY = 2
except ImportError:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    PY = 3

import os
import sys

# å¼å®¹ Python 2.6 æ  json åº
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

# Python 2.6 æ  OrderedDict â ç¨åç½® dict (2.7+ æåº)
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# å·¥å·å½æ°
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _script_dir():
    d = os.path.dirname(os.path.abspath(__file__))
    if PY == 2 and isinstance(d, bytes):
        return d.decode(sys.getfilesystemencoding())
    return d


def _join_path(*args):
    parts = []
    for a in args:
        if PY == 2 and isinstance(a, unicode):
            a = a.encode(sys.getfilesystemencoding())
        parts.append(a)
    return os.path.join(*parts)


def _utf8_open(path, mode):
    if PY == 2:
        import codecs
        return codecs.open(path, mode, encoding='utf-8')
    return open(path, mode, encoding='utf-8')


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# éç½®æä¹å
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

CONFIG_FILE = _join_path(_script_dir(), 'config.ini')

DEFAULTS = OrderedDict([
    ('tgz_path',    ''),
    ('output_path', ''),
    ('unit',        'mm'),
    ('scale_x',     '1.0'),
    ('scale_y',     '1.0'),
    ('mode',        'contour'),
])


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.isfile(CONFIG_FILE):
        try:
            if HAS_JSON:
                with _utf8_open(CONFIG_FILE, 'r') as f:
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
            with _utf8_open(CONFIG_FILE, 'w') as f:
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


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# Windows + Python 2 å­ä½å¼å®¹
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

if PY == 2 and sys.platform == 'win32':
    _CJK_CANDIDATES = [
        u'Microsoft YaHei',
        u'SimSun',
        u'SimHei',
        u'FangSong',
        u'KaiTi',
    ]
    def _detect_cjk_font():
        try:
            r = tk.Tk()
            avail = set(r.tk.call('font', 'families'))
            r.destroy()
            for f in _CJK_CANDIDATES:
                if f in avail:
                    return f
        except Exception:
            pass
        return u'Arial'

    _CJK_FONT     = _detect_cjk_font()
    _FONT_NORMAL  = (_CJK_FONT, 9)
    _FONT_BOLD    = (_CJK_FONT, 10, 'bold')
    _FONT_TITLE   = (_CJK_FONT, 15, 'bold')
    _FONT_SMALL   = (_CJK_FONT, 8)
    _FONT_MONO    = ('Courier New', 9)
    _FONT_MONO10  = ('Courier New', 10)
else:
    _FONT_NORMAL  = ('Arial', 9)
    _FONT_BOLD    = ('Arial', 10, 'bold')
    _FONT_TITLE   = ('Arial', 15, 'bold')
    _FONT_SMALL   = ('Arial', 8)
    _FONT_MONO    = ('Courier', 9)
    _FONT_MONO10  = ('Courier', 10)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# ä¸»çªå£
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

class OutputDxfApp:
    TITLE  = 'OutputDxf - Genesis TGZ -> DXF'
    WIDTH  = 540
    HEIGHT = 440

    BG       = '#F0F2F5'
    CARD_BG  = '#FFFFFF'
    FG       = '#333333'
    TITLE_FG = '#1A5276'
    ACCENT   = '#2E86C1'
    GREEN    = '#27AE60'
    RED      = '#E74C3C'
    ORANGE   = '#E67E22'
    GRAY     = '#999999'
    BORDER   = '#D5D8DC'

    def __init__(self):
        if PY == 2:
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

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(
            '+%d+%d' % ((sw - self.WIDTH) // 2, (sh - self.HEIGHT) // 2))

        self.cfg  = load_config()
        self.vars = {}
        self._build()
        self._load_cfg()
        self.root.mainloop()

    # ââ UI æå»º ââ

    def _build(self):
        header = tk.Frame(self.root, bg=self.ACCENT, height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(0)

        tk.Label(header, text=u'OutputDxf', font=_FONT_TITLE,
                 bg=self.ACCENT, fg='white').pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(header, text=u'é¹ç¨å·¥ä½å®¤ åºå', font=_FONT_SMALL,
                 bg=self.ACCENT, fg='#D4E6F1').pack(side=tk.RIGHT, padx=14, pady=14)

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=1, padx=8, pady=(8, 0))
        self._card_tgz(body)
        self._card_output(body)
        self._card_params(body)
        self._card_mode(body)
        self._buttons()

    # ââ å¡ç ââ

    def _card(self, parent, title):
        card = tk.Frame(parent, bg=self.CARD_BG, relief=tk.FLAT, bd=1,
                        highlightbackground=self.BORDER, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(card, text=u' â' + title, font=_FONT_BOLD,
                 bg=self.CARD_BG, fg=self.TITLE_FG, anchor=tk.W).pack(
            anchor=tk.W, padx=8, pady=(6, 1))
        inner = tk.Frame(card, bg=self.CARD_BG)
        inner.pack(fill=tk.X, padx=8, pady=(1, 8))
        return inner

    def _btn(self, parent, cmd):
        btn = tk.Button(parent, text=u'...', command=cmd,
                        bg=self.ACCENT, fg='white', relief=tk.FLAT,
                        font=_FONT_NORMAL, cursor='hand2', width=3, height=1)
        btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#2471A3'))
        btn.bind('<Leave>', lambda e, b=btn: b.config(bg=self.ACCENT))
        return btn

    # ââ TGZ è·¯å¾ ââ

    def _card_tgz(self, parent):
        inner = self._card(parent, u'TGZ æä»¶è·¯å¾')
        v = tk.StringVar(); self.vars['tgz_path'] = v
        e = tk.Entry(inner, textvariable=v, font=_FONT_MONO,
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._btn(inner, self._on_tgz).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ è¾åºè·¯å¾ ââ

    def _card_output(self, parent):
        inner = self._card(parent, u'DXF è¾åºç®å½')
        v = tk.StringVar(); self.vars['output_path'] = v
        e = tk.Entry(inner, textvariable=v, font=_FONT_MONO,
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._btn(inner, self._on_out).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ åæ° ââ

    def _card_params(self, parent):
        inner = self._card(parent, u'åæ°è®¾ç½®')

        uf = tk.Frame(inner, bg=self.CARD_BG)
        uf.pack(anchor=tk.W, pady=(0, 4))
        tk.Label(uf, text=u'åä½:', font=_FONT_BOLD,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        uv = tk.StringVar(value=self.cfg.get('unit', 'mm'))
        self.vars['unit'] = uv
        for t, val in [(u'mm  æ¯«ç±³', 'mm'), (u'inch è±å¯¸', 'inch')]:
            tk.Radiobutton(uf, text=t, variable=uv, value=val,
                           bg=self.CARD_BG, font=_FONT_NORMAL,
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT, padx=(2, 12))

        sf = tk.Frame(inner, bg=self.CARD_BG)
        sf.pack(anchor=tk.W)
        tk.Label(sf, text=u'æ¶¨ç¼©:', font=_FONT_BOLD,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        tk.Label(sf, text=u' X=', font=_FONT_NORMAL,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(6, 0))
        svx = tk.StringVar(value=self.cfg.get('scale_x', '1.0'))
        self.vars['scale_x'] = svx
        tk.Entry(sf, textvariable=svx, width=6, justify=tk.CENTER,
                 font=_FONT_MONO10, relief=tk.FLAT, bd=1,
                 bg='#F8F9FA').pack(side=tk.LEFT, ipady=2)

        tk.Label(sf, text=u'  Y=', font=_FONT_NORMAL,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(8, 0))
        svy = tk.StringVar(value=self.cfg.get('scale_y', '1.0'))
        self.vars['scale_y'] = svy
        tk.Entry(sf, textvariable=svy, width=6, justify=tk.CENTER,
                 font=_FONT_MONO10, relief=tk.FLAT, bd=1,
                 bg='#F8F9FA').pack(side=tk.LEFT, ipady=2)

        tk.Label(inner, text=u' 1.0 = åå§, 1.05 = Xæ¹åæä¼¸5%',
                 font=_FONT_SMALL, bg=self.CARD_BG, fg=self.GRAY).pack(
            anchor=tk.W, pady=(3, 0))

    # ââ è¾åºæ¹å¼ ââ

    def _card_mode(self, parent):
        inner = self._card(parent, u'è¾åºæ¹å¼')
        mv = tk.StringVar(value=self.cfg.get('mode', 'contour'))
        self.vars['mode'] = mv

        modes = [
            ('contour', u'è½®å»è¾åº', u'åªè¾åºå¾å½¢å¤è½®å»çº¿'),
            ('fill',    u'å¡«åè¾åº', u'è¾åºå®æ´å¡«åï¼å«éé¢ï¼'),
        ]
        for val, label, desc in modes:
            rf = tk.Frame(inner, bg=self.CARD_BG)
            rf.pack(anchor=tk.W, pady=1)
            tk.Radiobutton(rf, text=label, variable=mv, value=val,
                           bg=self.CARD_BG, font=_FONT_BOLD,
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT)
            tk.Label(rf, text=u' â ' + desc, font=_FONT_SMALL,
                     bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)

    # ââ æé® ââ

    def _buttons(self):
        bf = tk.Frame(self.root, bg=self.BG)
        bf.pack(fill=tk.X, padx=8, pady=(6, 10))

        self.status = tk.Label(bf, text=u'å°±ç»ª', font=_FONT_NORMAL,
                               bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status.pack(side=tk.LEFT, padx=2)

        q = tk.Button(bf, text=u' éåº ', command=self.root.quit,
                      bg=self.RED, fg='white', relief=tk.FLAT,
                      font=_FONT_BOLD, cursor='hand2', padx=14)
        q.pack(side=tk.RIGHT, padx=(3, 0), ipady=4)
        q.bind('<Enter>', lambda e: q.config(bg='#CB4335'))
        q.bind('<Leave>', lambda e: q.config(bg=self.RED))

        r = tk.Button(bf, text=u' â¶ å¼å§è½¬æ¢ ', command=self._run,
                      bg=self.GREEN, fg='white', relief=tk.FLAT,
                      font=_FONT_BOLD, cursor='hand2', padx=16)
        r.pack(side=tk.RIGHT, padx=(0, 3), ipady=4)
        r.bind('<Enter>', lambda e: r.config(bg='#229954'))
        r.bind('<Leave>', lambda e: r.config(bg=self.GREEN))

    # ââ äº¤äº ââ

    def _on_tgz(self):
        p = filedialog.askopenfilename(
            title=u'éæ© Genesis TGZ æä»¶',
            filetypes=[(u'TGZ æä»¶', '*.tgz'), (u'GZ æä»¶', '*.gz'),
                       (u'ææ', '*.*')])
        if p:
            self.vars['tgz_path'].set(p)

    def _on_out(self):
        p = filedialog.askdirectory(title=u'éæ©è¾åºç®å½')
        if p:
            self.vars['output_path'].set(p)

    def _load_cfg(self):
        for k in DEFAULTS:
            if k in self.vars and k in self.cfg:
                self.vars[k].set(self.cfg[k])

    def _validate(self):
        err = []
        tgz = self.vars['tgz_path'].get().strip()
        if not tgz:
            err.append(u'è¯·éæ© TGZ æä»¶')
        elif not os.path.isfile(tgz):
            err.append(u'TGZ æä»¶ä¸å­å¨')

        out = self.vars['output_path'].get().strip()
        if not out:
            err.append(u'è¯·éæ©è¾åºç®å½')
        elif not os.path.isdir(out):
            err.append(u'è¾åºç®å½ä¸å­å¨')

        for axis in ('scale_x', 'scale_y'):
            try:
                v = float(self.vars[axis].get().strip() or '1.0')
                if v <= 0:
                    raise ValueError
            except ValueError:
                err.append(axis.replace('scale_', '') + u' æ¶¨ç¼©è¯·è¾å¥æ­£æ°')
        return err

    def _run(self):
        errs = self._validate()
        if errs:
            msg = u'è¯·ä¿®æ­£:\n\n' + u'\n'.join(u'  * ' + e for e in errs)
            messagebox.showerror(u'è¾å¥éè¯¯', msg)
            return

        for k in self.vars:
            self.cfg[k] = self.vars[k].get()
        save_config(self.cfg)

        self.status.config(text=u'è½¬æ¢ä¸­...', fg=self.ORANGE)
        self.root.update_idletasks()

        try:
            out = self._convert()
            self.status.config(text=u'å®æ: ' + out, fg=self.GREEN)
            messagebox.showinfo(u'è½¬æ¢å®æ', 'DXF:\n' + out)
        except Exception as ex:
            self.status.config(text=u'å¤±è´¥', fg=self.RED)
            messagebox.showerror(u'è½¬æ¢å¤±è´¥', str(ex))

    def _convert(self):
        tgz    = self.vars['tgz_path'].get().strip()
        outdir = self.vars['output_path'].get().strip()
        unit   = self.vars['unit'].get()
        sx     = float(self.vars['scale_x'].get().strip())
        sy     = float(self.vars['scale_y'].get().strip())
        mode   = self.vars['mode'].get()

        base = os.path.splitext(os.path.basename(tgz))[0]
        if base.endswith('.tgz'):
            base = base[:-4]
        outfile = _join_path(outdir, base + '.dxf')

        self._dummy_dxf(outfile, unit)
        return outfile

    def _dummy_dxf(self, path, unit):
        m = '1' if unit == 'inch' else '0'
        u = '1' if unit == 'inch' else '4'
        with _utf8_open(path, 'w') as f:
            f.write(
                '0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n'
                '9\n$MEASUREMENT\n70\n' + m + '\n'
                '9\n$INSUNITS\n70\n' + u + '\n'
                '0\nENDSEC\n0\nEOF\n')


if __name__ == '__main__':
    OutputDxfApp()
