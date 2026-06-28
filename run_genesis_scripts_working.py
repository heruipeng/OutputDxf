#!/usr/bin/env python
# -*- coding: utf-8 -*-
#@Author       :    Gfzhang
#@Mail         :    gfzhang@163.com
#@Date         :    2025/10/10
#@Revision     :    1.0.0
#@File         :    run_genesis_scripts_working.py
#@Software     :    PyCharm
#@Usefor       :    无界面启动Genesis并调用指定程序
#---------------------------------------------------------#
_header = {
    'description': '''无界面启动Genesis并调用指定程序'''
}

import sys,os
import logging

run_pid = os.getpid()
GENESIS_DIR = "C:/genesis"
GENESIS_EDIR = "C:/genesis/e97/get"
# --定义运行genesis的程序
RUN_GET_FILE = 'C:/tmp/run_get_%s.csh' % run_pid
# --定义Genesis执行另一程序的文件
RUN_PY_FILE = 'C:/tmp/run_main_py_%s.csh' % run_pid

# --主程式
def MAIN(param):
    # 优先从配置获取，缺失时回退到当前文件默认值
    genesis_edir = GENESIS_EDIR
    os.chdir(genesis_edir)
    # --封装启动文件
    write_run_get_tmp(param)
    # --封装启动后执行的程序
    write_run_script_tmp(param, '')
    # --台头提醒
    logging.info('    **************************')
    logging.info('    * 即将启动Genesis软件...  ')
    logging.info('    **************************\n\n')

    # 从配置获取临时启动脚本路径模板，缺失时回退到默认值
    run_get_file = RUN_GET_FILE
    # --执行主程序
    RUN_CSH(run_get_file)

    # --删除临时文件
    # cleanup_temp_files()
    return

# --无界面执行CSH程序
def RUN_CSH(csh_file):
    # --调用系统命令执行
    shell_id = os.system('csh %s' % csh_file)
    logging.info(f"ID: {shell_id}, run_pid: {run_pid}")
    return

# --封装启动Genesis的csh文件 (C:/tmp/ruN_gEt.csh)
def write_run_get_tmp(param):

    # 优先取配置，缺失时使用本文件中的默认常量
    genesis_dir = GENESIS_DIR
    genesis_edir = GENESIS_EDIR
    run_py_file = RUN_PY_FILE

    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    guid_script_path = (os.path.join(PROJECT_DIR, "import_tgz.csh")
                        .replace("\\", "/"))

    get_txt="""\
    #!c:/bin/csh
    
    setenv GENESIS_DIR {0}
    cd {1}
    
    # 启动Genesis并调用指定程序
    ./get.exe -x -s{2} {3}
    
    exit 0
    """.format(genesis_dir,genesis_edir,guid_script_path,' '.join(param))
    run_get_file = RUN_GET_FILE
    WRITE_FILE(get_txt, run_get_file)
    #判断get.exe文件是否存在
    if not os.path.isfile(os.path.join(genesis_edir, 'get.exe')):
        logging.error("get.exe文件不存在,exit...")
        return
    return

# --封装run的程序文件  (runpyFile)
def write_run_script_tmp(param, script_args=""):
    # 定义引导程序路径
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    guid_script_path = (os.path.join(PROJECT_DIR, "import_tgz.csh")
                        .replace("\\", "/"))

    genesis_dir = GENESIS_DIR
    genesis_edir = GENESIS_EDIR

    scripts_txt="""\
    #!c:/bin/csh
    
    # 设定环境变量
    setenv GENESIS_DIR {0}
    setenv GENESIS_EDIR {1}
    
    # 执行Python脚本
    csh "{2}" {3}
    
    exit 0
    """.format(genesis_dir, genesis_edir, guid_script_path, ' '.join(param))
    logging.info(f"引导程序路径: {guid_script_path}")
    run_py_file = RUN_PY_FILE
    WRITE_FILE(scripts_txt, run_py_file)
    return

def WRITE_FILE(text, tmp_f):
    # print(text)
    f=open(tmp_f,'w')
    f.write(text+'\n')
    f.close()
    return

def cleanup_temp_files():
    """清理临时文件"""
    run_get_file = RUN_GET_FILE
    run_py_file = RUN_PY_FILE
    temp_files = [run_get_file, run_py_file]
    for temp_file in temp_files:
        if os.path.isfile(temp_file):
            try:
                os.unlink(temp_file)
                logging.info(f"已删除临时文件: {temp_file}")
            except Exception as e:
                logging.error(f"删除临时文件失败 {temp_file}: {e}")

##################################################################
if __name__=="__main__":
    MAIN(sys.argv[1:])
