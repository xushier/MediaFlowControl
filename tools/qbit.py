#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - QB 自动化删除');
0 9,21 * * * qbit.py
"""

import re
import sys
import logging
import logging.handlers
from queue import Queue
from threading import Thread
from qbittorrent import Client


from __config import xd_qb_url, xd_qb_usr, xd_qb_pwd, xd_qb_delete, xd_qb_delete_error, qb_error_tracker_keyword, qb_domain_keyword
from __logger import Log
from __notifier import wecom_app
from __notify_template import notify_template


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


class QB:
    def __init__(self, logger, qb_url=xd_qb_url, qb_usr=xd_qb_usr, qb_pwd=xd_qb_pwd):
        self.qb_url = qb_url
        self.qb_usr = qb_usr
        self.qb_pwd = qb_pwd
        self.qb     = Client(self.qb_url, verify=False)
        self.qb.login(self.qb_usr, self.qb_pwd)

        self.categories = self.qb_categories()
        self.torrents   = self.qb_torrents(stat='seeding')

        self.logger = logger

    def qb_create_category(self, new_category):
        """
        创建 Qbittirrent 客户端的分类。

        """
        new_category = new_category.replace(" ", "").lower()
        return self.qb.create_category(new_category)

    def qb_remove_category(self, categories):
        """
        删除 Qbittirrent 客户端的分类。

        """
        return self.qb.remove_category(categories)

    def qb_set_category(self, torrent_hash, category):
        """
        设置 Qbittirrent 客户端的分类。

        """
        return self.qb.set_category(torrent_hash, category)
    
    def qb_categories(self):
        """
        获取 Qbittirrent 客户端的分类。

        """
        categories = self.qb._post("torrents/categories", data="").keys()
        return list(categories)
    
    def qb_torrents(self, **filters):
        """
        获取 Qbittirrent 指定种子。

        """
        return self.qb.torrents(**filters)

    def delete_true(self, infohash_list):
        """
        删除 Qbittirrent 指定种子及文件。

        """
        return self.qb.delete_permanently(infohash_list)

    def get_trackers(self, infohash):
        """
        获取指定种子 Tracker 信息。
        """
        return self.qb.get_torrent_trackers(infohash)

    def remove_invalid_sort(self):
        """
        移除未使用的分类。
        """
        categories = self.qb_categories()
        invalid_categories = set()
        for c in categories:
            torrents = self.qb_torrents(category=c)
            if not torrents:
                invalid_categories.add(c)
        if invalid_categories:
            self.logger.put(invalid_categories)
            encode = "\n".join(invalid_categories)
            self.qb_remove_category(encode)
            self.logger.put(f"移除 {len(invalid_categories)} 个未使用的分类。")
            return len(invalid_categories)
        else:
            return None
    

    def can_delete(self):
        """
        删除满足条件的种子。

        """
        self.logger.put("----------删除可删种子----------")
        ts = self.qb_torrents(filter="seeding")
        hash_list = set()
        idt_error = 0
        for t in ts:
            if "可删" in t['category']:
                name = t['category'].split("-")[3]
                seeding_time = t['seeding_time'] // 3600
                size = t['size'] // 1073741824
                breakout = False
                for keyword, hrtime in qb_domain_keyword.items():
                    if keyword in t['tracker'] or keyword in t['magnet_uri']:
                        if seeding_time < hrtime * 24:
                            self.logger.put(f"{keyword}，{t['tags']}，{t['category']}, 做种 {seeding_time} 小时，不足 {hrtime * 24} 小时，暂不删除")
                            breakout = True
                            break
                if breakout:
                    continue
                if re.search(r'[a-zA-Z]', name) and not re.search(r'[\u4e00-\u9fff]', name):
                    self.logger.put(f"片名：{name}，可能刮削错误，暂不删除")
                    idt_error += 1
                    continue
                self.logger.put(f"可删, {size} GB, 做种 {seeding_time} 小时, {t['tags']}, {t['category']}")
                hash_list.add(t['hash'])
        count = len(hash_list)
        if count:
            self.delete_true(list(hash_list))
            self.logger.put(f"本次删除 {count} 个可删除种子，有 {idt_error} 个种子可能刮削错误")
            return count, idt_error
        else:
            self.logger.put(f"本次运行没有检测到可以删除的种子。有 {idt_error} 个种子可能刮削错误。")
            return 0, idt_error


    def delete_error(self):
        """
        删除下载中的已失效种子。

        """
        self.logger.put("----------删除失效种子----------")
        ts = self.qb_torrents(filter='downloading')
        hash_list = set()
        for t in ts:
            infohash = t['hash']
            progress = round(t['progress'] * 100, 2)
            infotracker = self.get_trackers(infohash)[-1]['msg']
            for keyword in qb_error_tracker_keyword:
                if keyword in infotracker:
                    size = t['size'] // 1073741824
                    self.logger.put(f"种子已失效, {size} GB, 进度：{progress} %, 服务器信息：{infotracker}")
                    hash_list.add(infohash)
        count = len(hash_list)
        if count:
            self.delete_true(list(hash_list))
            self.logger.put(f"本次删除 {count} 个可删除种子。")
            return count
        else:
            self.logger.put("本次运行没有检测到已失效的种子。")
            return 0


if __name__ == "__main__":
    item = {}

    logger = Log("qb-delete-log", "qb-delete").logger
    log_queue   = Queue()
    log_thread = Thread(target=log_writer, args=(log_queue, logger))
    log_thread.start()
    log_queue.put(f"---------------启动 QB 自动化删除---------------")

    try:
        qb = QB(log_queue)
    except Exception as e:
        log_queue.put(f"QB 异常，请检查：{e}")
        wecom_app("QB 异常", f"请检查：{e}")
        sys.exit(1)

    digest_content = ""
    if xd_qb_delete:
        can_del = qb.can_delete()
        item['删除可删种子'] = f"{can_del[0]}个"
        item['可能刮削错误种子'] = f"{can_del[1]}个"
        digest_content = f"删除可删种子：{can_del[0]}个\n可能刮削错误种子：{can_del[1]}个\n"
    else:
        item['删除可删种子'] = f"未启用"
        item['可能刮削错误种子'] = f"未启用"
        digest_content = f"删除可删种子：未启用\n可能刮削错误种子：未启用\n"

    if xd_qb_delete_error:
        err_del = qb.delete_error()
        item['删除失效种子'] = f"{err_del}个"
        digest_content += f"删除失效种子：{err_del}个\n"
    else:
        item['删除失效种子'] = f"未启用"
        digest_content += f"删除失效种子：未启用\n"

    fail = qb.qb_torrents(filter="seeding", category="")
    idt_fail =len(fail)
    if idt_fail:
        log_queue.put(f"有 {idt_fail} 个种子可能识别失败，请手动刮削！\n{fail}")
        digest_content += f"可能识别失败种子：{idt_fail} 个\n"
    else:
        idt_fail = 0
        
    invalid_sort = qb.remove_invalid_sort()
    if not invalid_sort:
        invalid_sort = 0

    item['可能刮削失败种子'] = f"{idt_fail}个"
    item['删除未使用分类'] = f"{invalid_sort}个"
    digest_content += f"删除未使用分类：{invalid_sort}个\n"

    log_queue.put(None)
    log_thread.join()

    title = "QB 自动清理"
    items = item
    font_color = "white"
    border_color = "#C8E8FF"
    title_color = "#2861A1"
    head_color = "#2861A1"
    item_color_A = "#64A4E8"
    item_color_B = "#3871C1"
    content = notify_template(title, items, font_color, border_color, title_color, head_color, item_color_A, item_color_B)

    wecom_app(title, content, digest_content)

