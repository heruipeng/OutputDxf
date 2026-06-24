#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OutputDxf - Genesis TGZ -> DXF \u8f6c\u6362\u5de5\u5177
\u9e4f\u7a0b\u5de5\u4f5c\u5ba4 \u51fa\u54c1
\u517c\u5bb9 Python 2.6+ / Python 3.x | \u7eaf Tkinter (\u65e0 ttk)

\u8bbe\u8ba1\u539f\u5219:
  - py2 \u4e0b\u6240\u6709 Tkinter \u6587\u672c\u7528\u663e\u5f0f u"..." (unicode)
  - \u8def\u5f84\u64cd\u4f5c\u4fdd\u6301\u5b57\u8282\u4e32\uff0cos.path \u539f\u751f\u5904\u7406
  - \u6587\u4ef6 IO \u7528 codecs.open \u6216\u4e8c\u8fdb\u5236\u6a21\u5f0f
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

# Python 2.6: json \u5e93\u517c\u5bb9
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


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# \u5de5\u5177\u51fd\u6570
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _script_dir():
    """\u811a\u672c\u6240\u5728\u76ee\u5f55 (py2 â unicode, py3 â str)"""
    d = os.path.dirname(os.path.abspath(__file__))
    if PY == 2 and isinstance(d, bytes):
        return d.decode(sys.getfilesystemencoding())
    return d


def _join_path(*args):
    """\u5b89\u5168\u8def\u5f84\u62fc\u63a5 â py2 \u8fd4\u56de\u5b57\u8282\u4e32 (\u907f\u514d unicode/bytes \u6df7\u7528)"""
    # \u786e\u4fdd\u6240\u6709 args \u662f str/bytes (\u4e0d\u662f unicode)
    parts = []
    for a in args:
        if PY == 2 and isinstance(a, unicode):
            a = a.encode(sys.getfilesystemencoding())
        parts.append(a)
    return os.path.join(*parts)


def _utf8_open_read(path):
    """utf-8 \u8bfb\u6587\u672c"""
    if PY == 2:
        import codecs
        return codecs.open(path, 'r', encoding='utf-8')
    else:
        return open(path, 'r', encoding='utf-8')


def _utf8_open_write(path):
    """utf-8 \u5199\u6587\u672c"""
    if PY == 2:
        import codecs
        return codecs.open(path, 'w', encoding='utf-8')
    else:
        return open(path, 'w', encoding='utf-8')


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# \u914d\u7f6e\u6301\u4e45\u5316
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

CONFIG_FILE = _join_path(_script_dir(), 'config.ini')

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
                with _utf8_open_read(CONFIG_FILE) as f:
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
            with _utf8_open_write(CONFIG_FILE) as f:
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
# \u5b57\u4f53\u517c\u5bb9: py2 Windows \u4e0b Arial \u65e0\u4e2d\u6587 â \u56de\u9000\u7cfb\u7edf CJK \u5b57\u4f53
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

if PY == 2 and sys.platform == 'win32':
    # \u68c0\u6d4b\u53ef\u7528\u4e2d\u6587\u5b57\u4f53 (\u6309\u4f18\u5148\u7ea7)
    _CJK_CANDIDATES = [
        'Microsoft YaHei',  # Win7+
        'SimSun',           # Win XP+
        'SimHei',
        'FangSong',
        'KaiTi',
    ]
    _CJK_FONT = 'Arial'  # \u9ed8\u8ba4

    def _detect_font():
        try:
            root = tk.Tk()
            available = set(root.tk.call('font', 'families'))
            root.destroy()
            for f in _CJK_CANDIDATES:
                if f in available:
                    return f
        except Exception:
            pass
        return 'Arial'

    _CJK_FONT = _detect_font()
    _FONT_NORMAL = (_CJK_FONT, 9)
    _FONT_BOLD   = (_CJK_FONT, 10, 'bold')
    _FONT_TITLE  = (_CJK_FONT, 15, 'bold')
    _FONT_SMALL  = (_CJK_FONT, 8)
    _FONT_MONO   = ('Courier New', 9)
    _FONT_MONO10 = ('Courier New', 10)
else:
    _CJK_FONT = None
    _FONT_NORMAL = ('Arial', 9)
    _FONT_BOLD   = ('Arial', 10, 'bold')
    _FONT_TITLE  = ('Arial', 15, 'bold')
    _FONT_SMALL  = ('Arial', 8)
    _FONT_MONO   = ('Courier', 9)
    _FONT_MONO10 = ('Courier', 10)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# \u4e3b\u7a97\u53e3
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

class OutputDxfApp:
    TITLE    = 'OutputDxf - Genesis TGZ -> DXF'
    WIDTH    = 540
    HEIGHT   = 440

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
        # â py2 Windows Tcl \u7f16\u7801\u4fee\u590d: \u4e0d\u52a0\u8fd9\u884c\u4e2d\u6587\u53ef\u80fd\u4ecd\u4e71\u7801
        if PY == 2:
            try:
                self.root = tk.Tk()
                # \u5c1d\u8bd5\u8bbe\u7f6e Tcl \u7f16\u7801\u4e3a utf-8
                self.root.tk.eval('encoding system utf-8')
            except Exception:
                self.root = tk.Tk()
        else:
            self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry('%dx%d' % (self.WIDTH, self.HEIGHT))
        self.root.resizable(0, 0)
        self.root.configure(bg=self.BG)

        # \u5c45\u4e2d
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(
            '+%d+%d' % ((sw - self.WIDTH) // 2, (sh - self.HEIGHT) // 2))

        self.cfg = load_config()
        self.vars = {}
        self._build()
        self._load_cfg()
        self.root.mainloop()

    # ââ UI ââ

    def _build(self):
        header = tk.Frame(self.root, bg=self.ACCENT, height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(0)
        tk.Label(header, text=u'OutputDxf', font=_FONT_TITLE,
                 bg=self.ACCENT, fg='white').pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(header, text=u'\u9e4f\u7a0b\u5de5\u4f5c\u5ba4 \u51fa\u54c1', font=_FONT_SMALL,
                 bg=self.ACCENT, fg='#D4E6F1').pack(side=tk.RIGHT, padx=14, pady=14)

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=1, padx=8, pady=(8, 0))
        self._card_tgz(body)
        self._card_output(body)
        self._card_params(body)
        self._card_mode(body)
        self._buttons()

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

    def _browse_btn(self, parent, cmd):
        btn = tk.Button(parent, text=u'...', command=cmd,
                        bg=self.ACCENT, fg='white', relief=tk.FLAT,
                        font=_FONT_NORMAL, cursor='hand2',
                        width=3, height=1)
        self._hover(btn, self.ACCENT, '#2471A3')
        return btn

    def _hover(self, btn, n, h):
        btn.bind('<Enter>', lambda e: btn.config(bg=h))
        btn.bind('<Leave>', lambda e: btn.config(bg=n))

    # ââ TGZ \u8def\u5f84 ââ

    def _card_tgz(self, parent):
        inner = self._card(parent, u'TGZ \u6587\u4ef6\u8def\u5f84')
        v = tk.StringVar(); self.vars['tgz_path'] = v
        e = tk.Entry(inner, textvariable=v, font=_FONT_MONO,
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_tgz).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ \u8f93\u51fa\u8def\u5f84 ââ

    def _card_output(self, parent):
        inner = self._card(parent, u'DXF \u8f93\u51fa\u76ee\u5f55')
        v = tk.StringVar(); self.vars['output_path'] = v
        e = tk.Entry(inner, textvariable=v, font=_FONT_MONO,
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_out).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ \u53c2\u6570 ââ

    def _card_params(self, parent):
        inner = self._card(parent, u'\u53c2\u6570\u8bbe\u7f6e')

        uf = tk.Frame(inner, bg=self.CARD_BG)
        uf.pack(anchor=tk.W, pady=(0, 4))
        tk.Label(uf, text=u'\u5355\u4f4d:', font=_FONT_BOLD,
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        uv = tk.StringVar(value=self.cfg.get('unit', 'mm'))
        self.vars['unit'] = uv
        for t, val in [(u'mm  \u6beb\u7c73', 'mm'), (u'inch \u82f1\u5bf8', 'inch')]:
            tk.Radiobutton(uf, text=t, variable=uv, value=val,
                           bg=self.CARD_BG, font=_FONT_NORMAL,
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT, padx=(2, 12))

        sf = tk.Frame(inner, bg=self.CARD_BG)
        sf.pack(anchor=tk.W)
        tk.Label(sf, text=u'\u6da8\u7f29:', font=_FONT_BOLD,
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

        tk.Label(inner, text=u' 1.0 = \u539f\u59cb, 1.05 = X\u65b9\u5411\u62c9\u4f385%',
                 font=_FONT_SMALL, bg=self.CARD_BG, fg=self.GRAY).pack(
            anchor=tk.W, pady=(3, 0))

    # ââ \u8f93\u51fa\u65b9\u5f0f ââ

    def _card_mode(self, parent):
        inner = self._card(parent, u'\u8f93\u51fa\u65b9\u5f0f')

        mv = tk.StringVar(value=self.cfg.get('mode', 'contour'))
        self.vars['mode'] = mv

        modes = [
            ('contour', u'\u8f6e\u5ed3\u8f93\u51fa', u'\u53ea\u8f93\u51fa\u56fe\u5f62\u5916\u8f6e\u5ed3\u7ebf'),
            ('fill',    u'\u586b\u5145\u8f93\u51fa', u'\u8f93\u51fa\u5b8c\u6574\u586b\u5145\uff08\u542b\u94dc\u9762\uff09'),
        ]
        for val, label, desc in modes:
            rf = tk.Frame(inner, bg=self.CARD_BG)
            rf.pack(anchor=tk.W, pady=1)
            tk.Radiobutton(rf, text=label, variable=mv, value=val,
                           bg=self.CARD_BG, font=_FONT_BOLD,
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT)
            tk.Label(rf, text=u' â ' + desc, font=_FONT_SMALL,
                     bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)

    # ââ \u5e95\u90e8\u6309\u94ae ââ

    def _buttons(self):
        bf = tk.Frame(self.root, bg=self.BG)
        bf.pack(fill=tk.X, padx=8, pady=(6, 10))

        self.status = tk.Label(bf, text=u'\u5c31\u7eea', font=_FONT_NORMAL,
                               bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status.pack(side=tk.LEFT, padx=2)

        q = tk.Button(bf, text=u' \u9000\u51fa ', command=self.root.quit,
                      bg=self.RED, fg='white', relief=tk.FLAT,
                      font=_FONT_BOLD, cursor='hand2', padx=14)
        q.pack(side=tk.RIGHT, padx=(3, 0), ipady=4)
        self._hover(q, self.RED, '#CB4335')

        r = tk.Button(bf, text=u' â¶ \u5f00\u59cb\u8f6c\u6362 ', command=self._run,
                      bg=self.GREEN, fg='white', relief=tk.FLAT,
                      font=_FONT_BOLD, cursor='hand2', padx=16)
        r.pack(side=tk.RIGHT, padx=(0, 3), ipady=4)
        self._hover(r, self.GREEN, '#229954')

    # ââ \u4ea4\u4e92 ââ

    def _on_tgz(self):
        p = filedialog.askopenfilename(
            title=u'\u9009\u62e9 Genesis TGZ \u6587\u4ef6',
            filetypes=[(u'TGZ \u6587\u4ef6', '*.tgz'), (u'GZ \u6587\u4ef6', '*.gz'),
                       (u'\u6240\u6709', '*.*')])
        if p:
            self.vars['tgz_path'].set(p)

    def _on_out(self):
        p = filedialog.askdirectory(title=u'\u9009\u62e9\u8f93\u51fa\u76ee\u5f55')
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
            err.append(u'\u8bf7\u9009\u62e9 TGZ \u6587\u4ef6')
        elif not os.path.isfile(tgz):
            err.append(u'TGZ \u6587\u4ef6\u4e0d\u5b58\u5728')

        out = self.vars['output_path'].get().strip()
        if not out:
            err.append(u'\u8bf7\u9009\u62e9\u8f93\u51fa\u76ee\u5f55')
        elif not os.path.isdir(out):
            err.append(u'\u8f93\u51fa\u76ee\u5f55\u4e0d\u5b58\u5728')

        for axis in ('scale_x', 'scale_y'):
            try:
                v = float(self.vars[axis].get().strip() or '1.0')
                if v <= 0:
                    raise ValueError
            except ValueError:
                err.append(axis.replace('scale_', '') + u' \u6da8\u7f29\u8bf7\u8f93\u5165\u6b63\u6570')
        return err

    def _run(self):
        errs = self._validate()
        if errs:
            msg = u'\u8bf7\u4fee\u6b63:\n\n' + u'\n'.join(u'  * ' + e for e in errs)
            messagebox.showerror(u'\u8f93\u5165\u9519\u8bef', msg)
            return

        for k in self.vars:
            self.cfg[k] = self.vars[k].get()
        save_config(self.cfg)

        self.status.config(text=u'\u8f6c\u6362\u4e2d...', fg=self.ORANGE)
        self.root.update_idletasks()

        try:
            out = self._convert()
            self.status.config(text=u'\u5b8c\u6210: ' + out, fg=self.GREEN)
            messagebox.showinfo(u'\u8f6c\u6362\u5b8c\u6210', 'DXF:\n' + out)
        except Exception as ex:
            self.status.config(text=u'\u5931\u8d25', fg=self.RED)
            messagebox.showerror(u'\u8f6c\u6362\u5931\u8d25', str(ex))

    def _convert(self):
        """\u8f6c\u6362\u5f15\u64ce\u5360\u4f4d â \u5bf9\u63a5 Genesis Gateway + DXF Writer"""
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

        # TODO: \u66ff\u6362\u4e3a Genesis Gateway + DXF Writer
        self._dummy_dxf(outfile, tgz, unit, sx, sy, mode)
        return outfile

    def _dummy_dxf(self, path, src, unit, sx, sy, mode):
        m = '1' if unit == 'inch' else '0'
        i = '1' if unit == 'inch' else '4'
        with _utf8_open_write(path) as f:
            f.write(
                '0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n'
                '9\n$MEASUREMENT\n70\n' + m + '\n'
                '9\n$INSUNITS\n70\n' + i + '\n'
                '0\nENDSEC\n0\nEOF\n')


if __name__ == '__main__':
    OutputDxfApp()
