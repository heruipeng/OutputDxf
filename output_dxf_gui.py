#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OutputDxf - Genesis TGZ -> DXF è½¬æ¢å·¥å·
é¹ç¨å·¥ä½å®¤ åºå
å¼å®¹ Python 2.6+ / Python 3.x | çº¯ Tkinter (æ  ttk)

è®¾è®¡åå:
  - py2 ä¸ææ Tkinter ææ¬ç¨æ¾å¼ u"..." (unicode)
  - è·¯å¾æä½ä¿æå­èä¸²ï¼os.path åçå¤ç
  - æä»¶ IO ç¨ codecs.open æäºè¿å¶æ¨¡å¼
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

# Python 2.6: json åºå¼å®¹
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
# å·¥å·å½æ°
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _script_dir():
    """èæ¬æå¨ç®å½ (py2 â unicode, py3 â str)"""
    d = os.path.dirname(os.path.abspath(__file__))
    if PY == 2 and isinstance(d, bytes):
        return d.decode(sys.getfilesystemencoding())
    return d


def _join_path(*args):
    """å®å¨è·¯å¾æ¼æ¥ â py2 è¿åå­èä¸² (é¿å unicode/bytes æ··ç¨)"""
    # ç¡®ä¿ææ args æ¯ str/bytes (ä¸æ¯ unicode)
    parts = []
    for a in args:
        if PY == 2 and isinstance(a, unicode):
            a = a.encode(sys.getfilesystemencoding())
        parts.append(a)
    return os.path.join(*parts)


def _utf8_open_read(path):
    """utf-8 è¯»ææ¬"""
    if PY == 2:
        import codecs
        return codecs.open(path, 'r', encoding='utf-8')
    else:
        return open(path, 'r', encoding='utf-8')


def _utf8_open_write(path):
    """utf-8 åææ¬"""
    if PY == 2:
        import codecs
        return codecs.open(path, 'w', encoding='utf-8')
    else:
        return open(path, 'w', encoding='utf-8')


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# éç½®æä¹å
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
# ä¸»çªå£
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
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry('%dx%d' % (self.WIDTH, self.HEIGHT))
        self.root.resizable(0, 0)
        self.root.configure(bg=self.BG)

        # å±ä¸­
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
        tk.Label(header, text=u'OutputDxf', font=('Arial', 15, 'bold'),
                 bg=self.ACCENT, fg='white').pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(header, text=u'é¹ç¨å·¥ä½å®¤ åºå', font=('Arial', 8),
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
        tk.Label(card, text=u' â' + title, font=('Arial', 10, 'bold'),
                 bg=self.CARD_BG, fg=self.TITLE_FG, anchor=tk.W).pack(
            anchor=tk.W, padx=8, pady=(6, 1))
        inner = tk.Frame(card, bg=self.CARD_BG)
        inner.pack(fill=tk.X, padx=8, pady=(1, 8))
        return inner

    def _browse_btn(self, parent, cmd):
        btn = tk.Button(parent, text=u'...', command=cmd,
                        bg=self.ACCENT, fg='white', relief=tk.FLAT,
                        font=('Arial', 9, 'bold'), cursor='hand2',
                        width=3, height=1)
        self._hover(btn, self.ACCENT, '#2471A3')
        return btn

    def _hover(self, btn, n, h):
        btn.bind('<Enter>', lambda e: btn.config(bg=h))
        btn.bind('<Leave>', lambda e: btn.config(bg=n))

    # ââ TGZ è·¯å¾ ââ

    def _card_tgz(self, parent):
        inner = self._card(parent, u'TGZ æä»¶è·¯å¾')
        v = tk.StringVar(); self.vars['tgz_path'] = v
        e = tk.Entry(inner, textvariable=v, font=('Courier', 9),
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_tgz).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ è¾åºè·¯å¾ ââ

    def _card_output(self, parent):
        inner = self._card(parent, u'DXF è¾åºç®å½')
        v = tk.StringVar(); self.vars['output_path'] = v
        e = tk.Entry(inner, textvariable=v, font=('Courier', 9),
                     relief=tk.FLAT, bd=1, bg='#F8F9FA')
        e.pack(side=tk.LEFT, fill=tk.X, expand=1, ipady=3)
        self._browse_btn(inner, self._on_out).pack(side=tk.RIGHT, padx=(4, 0))

    # ââ åæ° ââ

    def _card_params(self, parent):
        inner = self._card(parent, u'åæ°è®¾ç½®')

        uf = tk.Frame(inner, bg=self.CARD_BG)
        uf.pack(anchor=tk.W, pady=(0, 4))
        tk.Label(uf, text=u'åä½:', font=('Arial', 10),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        uv = tk.StringVar(value=self.cfg.get('unit', 'mm'))
        self.vars['unit'] = uv
        for t, val in [(u'mm  æ¯«ç±³', 'mm'), (u'inch è±å¯¸', 'inch')]:
            tk.Radiobutton(uf, text=t, variable=uv, value=val,
                           bg=self.CARD_BG, font=('Arial', 9),
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT, padx=(2, 12))

        sf = tk.Frame(inner, bg=self.CARD_BG)
        sf.pack(anchor=tk.W)
        tk.Label(sf, text=u'æ¶¨ç¼©:', font=('Arial', 10),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT)

        tk.Label(sf, text=u' X=', font=('Arial', 9),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(6, 0))
        svx = tk.StringVar(value=self.cfg.get('scale_x', '1.0'))
        self.vars['scale_x'] = svx
        tk.Entry(sf, textvariable=svx, width=6, justify=tk.CENTER,
                 font=('Courier', 10), relief=tk.FLAT, bd=1,
                 bg='#F8F9FA').pack(side=tk.LEFT, ipady=2)

        tk.Label(sf, text=u'  Y=', font=('Arial', 9),
                 bg=self.CARD_BG, fg=self.FG).pack(side=tk.LEFT, padx=(8, 0))
        svy = tk.StringVar(value=self.cfg.get('scale_y', '1.0'))
        self.vars['scale_y'] = svy
        tk.Entry(sf, textvariable=svy, width=6, justify=tk.CENTER,
                 font=('Courier', 10), relief=tk.FLAT, bd=1,
                 bg='#F8F9FA').pack(side=tk.LEFT, ipady=2)

        tk.Label(inner, text=u' 1.0 = åå§, 1.05 = Xæ¹åæä¼¸5%',
                 font=('Arial', 8), bg=self.CARD_BG, fg=self.GRAY).pack(
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
                           bg=self.CARD_BG, font=('Arial', 10, 'bold'),
                           selectcolor=self.CARD_BG).pack(side=tk.LEFT)
            tk.Label(rf, text=u' â ' + desc, font=('Arial', 8),
                     bg=self.CARD_BG, fg=self.GRAY).pack(side=tk.LEFT)

    # ââ åºé¨æé® ââ

    def _buttons(self):
        bf = tk.Frame(self.root, bg=self.BG)
        bf.pack(fill=tk.X, padx=8, pady=(6, 10))

        self.status = tk.Label(bf, text=u'å°±ç»ª', font=('Arial', 9),
                               bg=self.BG, fg=self.GRAY, anchor=tk.W)
        self.status.pack(side=tk.LEFT, padx=2)

        q = tk.Button(bf, text=u' éåº ', command=self.root.quit,
                      bg=self.RED, fg='white', relief=tk.FLAT,
                      font=('Arial', 10), cursor='hand2', padx=14)
        q.pack(side=tk.RIGHT, padx=(3, 0), ipady=4)
        self._hover(q, self.RED, '#CB4335')

        r = tk.Button(bf, text=u' â¶ å¼å§è½¬æ¢ ', command=self._run,
                      bg=self.GREEN, fg='white', relief=tk.FLAT,
                      font=('Arial', 10, 'bold'), cursor='hand2', padx=16)
        r.pack(side=tk.RIGHT, padx=(0, 3), ipady=4)
        self._hover(r, self.GREEN, '#229954')

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
        for k in ('tgz_path', 'output_path', 'unit',
                  'scale_x', 'scale_y', 'mode'):
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
        """è½¬æ¢å¼æå ä½ â å¯¹æ¥ Genesis Gateway + DXF Writer"""
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

        # TODO: æ¿æ¢ä¸º Genesis Gateway + DXF Writer
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
