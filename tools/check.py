#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - 环境检测');
30 9 * * * check.py
"""

import os
from qbit import QB
from queue import Queue
from threading import Thread
from clouddrive2 import CD2

from _Config import nas_mount_root_path
from __notify_template import notify_template
from __notifier import wecom_app
from __logger import Log
from __alist import Alist


def log_writer(log_queue, logger):
    while True:
        try:
            log_entry = log_queue.get(block=True)
            if log_entry is None:
                break
            logger.info(log_entry)
            print(log_entry)
        except Exception as e:
            if str(e) != 'Empty':
                raise


def check_connect(logger):
    logger = logger
    item = {}
    digest_content = ""
    try:
        c = CD2()
        logger.put("CD2 登录正常！")
        if c.mounted and os.listdir(nas_mount_root_path):
            logger.put("CD2 挂载正常！")
            cds = 0
            item['CD2 挂载'] = f"正常"
        else:
            logger.put("CD2 挂载错误！")
            cds = 1
            item['CD2 挂载'] = f"错误"
        digest_content += f"CD2 挂载：{item['CD2 挂载']}\n"
    except Exception as e:
        logger.put(f"CD2 登录失败！{e}")
        cds = 2
        item['CD2 登录'] = f"失败"
        digest_content += f"CD2 登录：{item['CD2 登录']}\n"


    try:
        q = QB(logger)
        logger.put("QB 登录正常！")
        qbs = 0
        item['QB 登录'] = f"正常"
        digest_content += f"QB 登录：{item['QB 登录']}\n"
    except Exception as e:
        logger.put(f"QB 连接失败！{e}")
        qbs = 1
        item['QB 连接'] = f"失败"
        digest_content += f"QB 连接：{item['QB 连接']}\n"


    try:
        a = Alist()
        logger.put("Alist 登录正常！")
        if a.ismount:
            logger.put("Alist 挂载正常！")
            als = 0
            item['Alist 挂载'] = f"正常"
        else:
            logger.put("Alist 挂载失效！")
            als = 1
            item['Alist 挂载'] = f"失效"
        digest_content += f"Alist 挂载：{item['Alist 挂载']}\n"
    except Exception as e:
        logger.put(f"Alist 连接失败！原因：{e}")
        als = 2
        item['Alist 连接'] = f"失败"
        digest_content += f"Alist 连接：{item['Alist 连接']}\n"
    
    return cds, qbs, als, item, digest_content


if __name__ == "__main__":
    logger = Log("check-log", "check").logger
    log_queue  = Queue()
    log_thread = Thread(target=log_writer, args=(log_queue, logger))
    log_thread.start()
    log_queue.put(f"---------------启动环境检测---------------")
    ch = check_connect(log_queue)
    log_queue.put(ch[3])
    log_queue.put(f"---------------环境检测完成---------------\n")
    log_queue.put(None)
    log_thread.join()

    title = "环境检测"
    items = ch[3]
    font_color = "white"
    border_color = "#C8E8FF"
    title_color = "#2861A1"
    head_color = "#2861A1"
    item_color_A = "#64A4E8"
    item_color_B = "#3871C1"
    content = notify_template(title, items, font_color, border_color, title_color, head_color, item_color_A, item_color_B)

    wecom_app(title, content, ch[4])

