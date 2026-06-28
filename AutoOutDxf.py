#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import re
import math
import time
from genClasses import Genesis
gen = Genesis()

tgz_path = ''
job = ''
step = ''
layer = ''
output_dir = ''
unit = ''
dxf_mode = ''

if len(sys.argv)>1:
    tgz_path = sys.argv[1]
    job = sys.argv[2]
    step = sys.argv[3]
    layer = sys.argv[4]
    output_dir = sys.argv[5]
    unit = sys.argv[6]
    dxf_mode = sys.argv[7]

    if ',' in step:
        step = step.split(',')
    else:
        step = [step]
    if ',' in layer:
        layer = layer.split(',')
    else:
        layer = [layer]


    gen.COM('')
else:
    pass



