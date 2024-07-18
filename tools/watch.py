#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - 硬链文件实时监控');
0 21 * * * watch.py
"""


import os
import sys
import time
from queue import Queue
from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


from clouddrive2 import CD2
from link import dl_to_path
from _Config import part_link_mode, nas_mount_root_path, nas_hlink_root_path, nas_slink_root_path, nas_strm_root_path, cd2_cloud_root_path, mdata_ext
from __utils import chinese_name_filter, delete_more
from __logger import Log
from __notifier import wecom_app


cd2 = CD2()

class LocalFileSystem(FileSystemEventHandler):
    def __init__(self, q):
        self.queue = q
    def on_created(self, event):
        self.queue.put(event)
    
    # def on_deleted(self, event):
    #     if event.is_directory:
    #         print(f"监测到目录删除： {os.path.basename(event.src_path)}")
    #     else:
    #         print(f"监测到文件删除： {os.path.basename(event.src_path)}")

    # def on_modified(self, event):
    #     if event.is_directory:
    #         print(f"监测到目录修改： {os.path.basename(event.src_path)}")
    #     else:
    #         print(f"监测到文件修改： {os.path.basename(event.src_path)}")

    # def on_moved(self, event):
    #     if event.is_directory:
    #         print(f"监测到目录移动： {event.src_path} 被移动至 {event.dest_path}")
    #     else:
    #         print(f"监测到文件移动： {event.src_path} 被移动至 {event.dest_path}")


def process_file_change(q, logger):
    while True:
        event = q.get()
        if event is None:
            break
        slink_path = event.src_path.replace(nas_hlink_root_path, nas_slink_root_path)
        strm_path  = event.src_path.replace(nas_hlink_root_path, nas_strm_root_path)
        if event.is_directory:
            logger.put(f"监测到目录创建：{os.path.basename(event.src_path)}")
            if part_link_mode == "slink":
                if not nas_slink_root_path:
                    logger.put("部分链接的模式为软链接，但软链接根路径未设置！")
                    wecom_app("实时监控错误！", "\n部分链接的模式为软链接，但软链接根路径未设置！", "", False)
                    sys.exit("部分链接的模式为软链接，但软链接根路径未设置！")
                os.makedirs(slink_path, exist_ok=True)
            if part_link_mode == "strm":
                if not nas_strm_root_path:
                    logger.put("部分链接的模式为 STRM，但 STRM 根路径未设置！")
                    wecom_app("实时监控错误！", "\n部分链接的模式为 STRM，但 STRM 根路径未设置！", "", False)
                    sys.exit("部分链接的模式为 STRM，但 STRM 根路径未设置！")
                os.makedirs(strm_path, exist_ok=True)
            if part_link_mode == "both":
                if not nas_slink_root_path or not nas_strm_root_path:
                    logger.put("部分链接的模式为 both，但软链接或 STRM 根路径未设置！")
                    wecom_app("实时监控错误！", "\n部分链接的模式为 both，但软链接或 STRM 根路径未设置！", "", False)
                    sys.exit("部分链接的模式为 both，但软链接或 STRM 根路径未设置！")
                os.makedirs(slink_path, exist_ok=True)
                os.makedirs(strm_path, exist_ok=True)
            wecom_app("【实时监控】\n", f"创建文件夹：\n{os.path.basename(event.src_path)}", "", False)
        else:
            logger.put(f"监测到文件创建：{os.path.basename(event.src_path)}")
            file_name = os.path.basename(event.src_path)
            file_ext  = os.path.splitext(file_name)[1][1:].lower()
            # if not chinese_name_filter(file_name) and file_ext not in mdata_ext:
            #     cloud_path = event.src_path.replace(nas_hlink_root_path, cd2_cloud_root_path)
            #     mount_path = event.src_path.replace(nas_hlink_root_path, nas_mount_root_path)
            #     try:
            #         cd2.uplist = cd2.cd2.upload_tasklist.list()
            #         d = cd2.file_exists_in_upload_list(cloud_path)
            #     except:
            #         logger.put("监测到程序异常，请检查！")
            #         sys.exit(1)
            #     while not d[0]:
            #         logger.put(f"监测到文件状态：文件不在上传列表，等待中······")
            #         time.sleep(5)
            #         cd2.uplist = cd2.cd2.upload_tasklist.list()
            #         d = cd2.file_exists_in_upload_list(cloud_path)
            #     logger.put(f"监测到文件状态：文件已在上传列表，上传状态为：{cd2.upstat[d[1]]}")  
            #     cd2.task.cancel(cloud_path)
            #     logger.put("取消该上传任务。\n")
            #     delete_more(mount_path, slink_path, strm_path, logger)
            #     wecom_app("【实时监控】\n", f"识别错误，取消上传：\n{os.path.basename(event.src_path)}", "", False)
            #     return False
            if file_ext in mdata_ext:
                slink_exist = os.path.exists(slink_path)
                strm_exist  = os.path.exists(strm_path)
                try:
                    if part_link_mode == "slink" and not slink_exist:
                        dl_to_path(event.src_path, slink_path)
                    if part_link_mode == "strm" and not strm_exist:
                        dl_to_path(event.src_path, strm_path)
                    if part_link_mode == "both":
                        if not slink_exist:
                            dl_to_path(event.src_path, slink_path)
                        if not strm_path:
                            dl_to_path(event.src_path, strm_path)
                except:
                    mount_path = event.src_path.replace(nas_hlink_root_path, nas_mount_root_path)
                    if os.path.exists(mount_path):
                        if part_link_mode == "slink" and not slink_exist:
                            dl_to_path(event.src_path, slink_path)
                        if part_link_mode == "strm" and not strm_exist:
                            dl_to_path(event.src_path, strm_path)
                        if part_link_mode == "both":
                            if not slink_exist:
                                dl_to_path(event.src_path, slink_path)
                            if not strm_path:
                                dl_to_path(event.src_path, strm_path)
                logger.put(f"元数据下载完成：{os.path.basename(event.src_path)}")
                wecom_app("【实时监控】\n", f"下载元数据：\n{os.path.basename(event.src_path)}", "", False)
            else:
                cloud_path = event.src_path.replace(nas_hlink_root_path, cd2_cloud_root_path)
                retry = 5
                time.sleep(3)
                try:
                    upload_count = cd2.cd2.GetUploadFileCount().fileCount
                    if upload_count > 150:
                        page = upload_count // 50
                        filelist = cd2.task.list(page=page, page_size=50)
                        filelist.extend(cd2.task.list(page = page - 1, page_size=50))
                        filelist.extend(cd2.task.list(page = page - 1, page_size=50))
                    else:
                        filelist = cd2.task.list()
                    cd2.uplist = filelist
                    d = cd2.file_exists_in_upload_list(cloud_path)
                except:
                    logger.put("监测到程序异常，请检查！")
                    sys.exit(1)
                while not d[0] and retry:
                    retry -= 1
                    logger.put(f"监测到文件状态：文件不在上传列表，等待中···剩余重试次数：{retry}")
                    time.sleep(2)
                    upload_count = cd2.cd2.GetUploadFileCount().fileCount
                    if upload_count > 150:
                        page = upload_count // 50
                        filelist = cd2.task.list(page=page, page_size=50)
                        filelist.extend(cd2.task.list(page = page - 1, page_size=50))
                        filelist.extend(cd2.task.list(page = page - 1, page_size=50))
                    else:
                        filelist = cd2.task.list()
                    cd2.uplist = filelist
                    d = cd2.file_exists_in_upload_list(cloud_path)
                if d[0]:
                    logger.put(f"监测到文件状态：文件已在上传列表，上传状态为：{cd2.upstat[d[1]]}")
                    cd2.task.pause(cloud_path)
                    logger.put("暂停该上传任务。\n")
                    wecom_app("【实时监控】\n", f"暂停上传任务：\n{os.path.basename(event.src_path)}", "", False)
                else:
                    logger.put(f"已重试 5 次，未在上传列表发现文件，跳过该文件。请检查 CD2 监控是否开启！\n")
                    wecom_app("【实时监控】\n", f"已重试 5 次，未在上传列表发现文件，跳过该文件。请检查 CD2 备份任务开关是否打开！", "", False)


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


if __name__ == "__main__":
    q = Queue()
    local_observer = Observer()
    local_event_handler = LocalFileSystem(q)
    local_observer.schedule(local_event_handler, path=nas_hlink_root_path, recursive=True)
    local_observer.start()

    logger = Log("watch-log", "watch").logger
    log_queue  = Queue()
    log_thread = Thread(target=log_writer, args=(log_queue, logger))
    log_thread.start()
    log_queue.put(f"---------------启动实时监控---------------")

    threads = [Thread(target=process_file_change, args=(q, log_queue), daemon=True) for _ in range(5)]
    for t in threads:
        t.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_queue.put("---------------实时监控中断---------------")
        local_observer.stop()
        q.put(None)
        for t in threads:
            t.join()
        log_queue.put(None)
        log_thread.join()
  
    local_observer.join()
