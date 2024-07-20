#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - 网盘影视一条龙');
*/10 * * * * media.py
"""


import os
import re
import json
import time
import sys
from queue import Queue
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from clouddrive2 import CD2

from __notify_template import notify_template_col4
from __notifier import wecom_app
from __logger import Log
from __utils import format_size, get_folder_byte_size, format_time, delete_more, chinese_name_filter
from _Config import *
from check import check_connect
from link import cd2_strm, cd2_slink
from qbit import QB
from emby import EmbyRefresh


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


class FileInfo:
    def __init__(self, log_queue):
        self.logger = log_queue
        self.check  = check_connect(self.logger)
        if self.check[0]:
            print(f"CD2连接失败或挂载失败！请检查！")
            wecom_app(f"CD2连接失败或挂载失败！请检查！", f"CD2连接失败或挂载失败！请检查！")
            sys.exit(1)
        if self.check[1]:
            print(f"QB连接失败或挂载失败！请检查！")
            wecom_app(f"QB连接失败或挂载失败！请检查！", f"QB连接失败或挂载失败！请检查！")
            sys.exit(1)

        self.cd2 = CD2()
        self.qb  = QB(self.logger)
        self.emby = EmbyRefresh()
    
        self.notify_content = []
        self.notify_info    = "相关项目：<br>"
        

        self.logger.put(f"--------------------初始化程序--------------------")
        if os.path.exists("media.json"):
            try:
                with open("media.json", "r", encoding="utf-8") as file:
                    self.control_dict = json.load(file)
            except json.JSONDecodeError as e:
                self.logger.put(f"初始化程序：解析JSON时出错: {e}")
        else:
            self.control_dict = {}

        self.logger.put(f"初始化程序：获取硬链文件数据······")
        with ThreadPoolExecutor(max_workers=8) as executor:
            h = executor.submit(self.get_files_info, nas_hlink_root_path, hlink_media_depth, "hlink")

        self.logger.put(f"初始化程序：获取 QB 文件数据······")
        with ThreadPoolExecutor(max_workers=8) as executor:
            q = executor.submit(self.get_files_info, nas_qbitt_root_path, qbitt_media_depth, "qb")

        while True:
            if h.done() and q.done():
                time.sleep(2)
                qs = q.result()
                hs = h.result()
                break
            time.sleep(1)

        self.qb_inode_name_dict    = qs
        self.hlink_inode_sort_data = hs
        self.uploaded_list         = self.hlink_inode_sort_data[0]
        self.uploading_list        = self.hlink_inode_sort_data[1]
        self.hlink_inode_sort_dict = self.hlink_inode_sort_data[2]
        self.all_files_count       = self.hlink_inode_sort_data[3]
        self.logger.put(f"--------------------初始化完成--------------------\n")


    def get_files_info(self, media_path, depth, position=""):
        uploaded_list  = []
        uploading_list = []
        qb_needed_data1 = {}
        qb_needed_data2 = {}
        files_info_count = 0
        temp_series_list = []
        new_control_dict = {}
        for root, dirs, files in os.walk(media_path):

            for f in files:
                file_name = f
                file_parent_path = root
                file_extension   = os.path.splitext(file_name)[1][1:].lower()
                if file_extension == "!qB":
                    continue
                file_path = os.path.join(file_parent_path, file_name)
                file_stat = os.stat(file_path)
                file_program_name, file_program_path, file_depth = self.__get_path_at_level__(file_path, depth)
                file_create_time, file_create_before_hour, file_create_before_minute = format_time(file_stat.st_mtime)

                file_inode       = file_stat.st_ino
                file_uid         = file_stat.st_uid
                file_gid         = file_stat.st_gid
                file_mode        = oct(file_stat.st_mode)
                file_nlink_count = file_stat.st_nlink

                file_size_byte          = file_stat.st_size
                file_size_human         = format_size(file_size_byte)
                file_program_size       = get_folder_byte_size(os.path.dirname(file_path))
                file_parent_size        = get_folder_byte_size(file_parent_path)
                file_program_size_human = format_size(file_program_size)
                file_parent_size_human  = format_size(file_parent_size)

                file_info = {
                    'file_name': file_name,
                    'file_path': file_path,
                    'file_parent_path': file_parent_path,
                    'file_program_name': file_program_name,
                    'file_program_path': file_program_path,
                    'file_create_time': file_create_time,
                    'file_create_before_hour': file_create_before_hour,
                    'file_create_before_minute': file_create_before_minute,
                    'file_extension': file_extension,
                    'file_size_byte': file_size_byte,
                    'file_size_human': file_size_human,
                    'file_program_size': file_program_size,
                    'file_program_size_human': file_program_size_human,
                    'file_inode': file_inode,
                    'file_uid': file_uid,
                    'file_gid': file_gid,
                    'file_mode': file_mode,
                    'file_nlink_count': file_nlink_count
                    }

                if position == "qb" and file_nlink_count > 1:
                    qb_needed_data1[file_inode] = file_program_name

                if position == "hlink":
                    #构造路径
                    if not cd2_cloud_root_path:
                        self.logger.put("初始化程序：CD2 云端媒体库根路径未设置！")
                        wecom_app("影视一条龙错误！", "初始化程序：CD2 云端媒体库根路径未设置！")
                        sys.exit("CD2 云端媒体库根路径未设置！")
                    else:
                        cd2_cloud_file_path = file_path.replace(nas_hlink_root_path, cd2_cloud_root_path)

                    if not cd2_hlink_root_path:
                        self.logger.put("初始化程序：硬链接媒体库根路径未设置！")
                        wecom_app("影视一条龙错误！", "初始化程序：硬链接媒体库根路径未设置！")
                        sys.exit("硬链接媒体库根路径未设置！")
                    else:
                        cd2_hlink_file_path = file_path.replace(nas_hlink_root_path, cd2_hlink_root_path)

                    if not nas_mount_root_path:
                        self.logger.put("初始化程序：挂载媒体库根路径未设置！")
                        wecom_app("影视一条龙错误！", "初始化程序：挂载媒体库根路径未设置！")
                        sys.exit("挂载媒体库根路径未设置！")
                    else:
                        nas_mount_file_path = file_path.replace(nas_hlink_root_path, nas_mount_root_path)

                    if part_link_mode == "slink" or part_link_mode == "both":
                        if not nas_slink_root_path:
                            self.logger.put("初始化程序：部分链接的模式为 both 或 slink，但软链接根路径未设置！")
                            wecom_app("影视一条龙错误！", "初始化程序：部分链接的模式为 both 或 slink，但软链接根路径未设置！")
                            sys.exit("部分链接的模式为 both 或 slink，但软链接根路径未设置！")
                        else:
                            nas_slink_file_path = file_path.replace(nas_hlink_root_path, nas_slink_root_path)
                    else:
                        nas_slink_file_path = ""

                    if part_link_mode == "strm" or part_link_mode == "both":
                        if not nas_strm_root_path:
                            self.logger.put("初始化程序：部分链接的模式为 both 或 STRM，但 STRM 根路径未设置！")
                            wecom_app("影视一条龙错误！", "初始化程序：部分链接的模式为 both 或 STRM，但 STRM 根路径未设置！")
                            sys.exit("部分链接的模式为 both 或 STRM，但 STRM 根路径未设置！")
                        else:
                            nas_strm_file_path = file_path.replace(nas_hlink_root_path, nas_strm_root_path)
                    else:
                        nas_strm_file_path = ""

                    # 子分类
                    file_program_subtype, _, _ = self.__get_path_at_level__(file_path, depth-1)

                    # 文件是否存在于网盘
                    local_exists_in_remote = self.cd2.file_exists_in_remote(file_path, cd2_cloud_file_path)

                    # 文件是否在上传，上传状态
                    local_exists_in_upload_list, upload_file_status = self.cd2.file_exists_in_upload_list(cd2_cloud_file_path)

                    # 不在网盘，不在上传，则上传
                    meta_match = re.match(r'^[a-zA-Z-\.]+$', file_name)
                    if not local_exists_in_remote and not local_exists_in_upload_list and ( chinese_name_filter(file_name) or meta_match ):
                        cd2_parent_path = os.path.dirname(cd2_cloud_file_path)
                        self.cd2.fs.makedirs(cd2_parent_path, exist_ok=True)
                        try:
                            self.cd2.fs.move(cd2_hlink_file_path, cd2_cloud_file_path)
                        except Exception as e:
                            self.logger.put(f"初始化程序：重新添加错误：{e}")
                        self.logger.put(f"初始化程序：该文件未上传，上传：{file_name}")
                        local_exists_in_upload_list, upload_file_status = self.cd2.file_exists_in_upload_list(cd2_cloud_file_path)
                    

                    # # 影视剧分类 法一
                    # isdir = any(os.path.isdir(item) for item in os.listdir(file_parent_path))
                    # if file_depth == depth+2 or file_name == 'tvshow.nfo' or (file_depth == depth+1 and isdir):
                    #     file_program_type = "Series"
                    #     size_byte = file_program_size
                    # else:
                    #     file_program_type = "Movie"
                    #     size_byte = file_size_byte

                    # 影视剧分类 法二
                    if file_program_path == file_parent_path and file_depth == depth+1 and file_extension in media_ext and file_size_byte > 10485760:
                        file_program_type = "Movie"
                        size_byte = file_size_byte
                    else:
                        file_program_type = "Series"
                        size_byte = file_program_size

                    upload_after_time = self.uptime(file_name, size_byte)

                    # QB 分类
                    if meta_match:
                        qb_sort = f"元数据"
                    elif file_program_type == "Series":
                        # 方法一
                        # if file_program_name in temp_series_list:
                        #     qb_sort = temp_series_list[1]
                        # else:
                        #     qb_sort = self.get_series_sort(file_program_path, file_program_name, file_name, file_program_subtype=file_program_subtype)
                        #     temp_series_list = [file_program_name, qb_sort]
                        
                        # 方法二
                        match = re.match(series_pattern, file_program_name, re.UNICODE)
                        if match:
                            series_name = match.group(1)
                            series_year = match.group(2)
                            series_tmdb = match.group(3)
                        else:
                            series_name = None
                            series_year = None
                            series_tmdb = None
                        file_info['series_name'] = series_name
                        file_info['series_year'] = series_year
                        file_info['series_tmdb'] = series_tmdb
                        if not chinese_name_filter(file_name):
                            qb_sort = f"请重新刮削-{series_year}-{file_program_subtype}-{series_name}"
                        else:
                            if local_exists_in_upload_list:
                                qb_sort = f"上传{self.cd2.upstat[upload_file_status]}-{series_year}-{file_program_subtype}-{series_name}"
                            if local_exists_in_remote:
                                qb_sort = f"已上传可删-{series_year}-{file_program_subtype}-{series_name}"
                            if not local_exists_in_remote and not local_exists_in_upload_list:
                                qb_sort = f"文件未上传-{series_year}-{file_program_subtype}-{series_name}"
                    else:
                        match = re.match(movies_pattern, file_program_name, re.UNICODE)
                        if match:
                            movies_name = match.group(1)
                            movies_year = match.group(2)
                            movies_tmdb = match.group(3)
                        else:
                            movies_name = None
                            movies_year = None
                            movies_tmdb = None
                        file_info['movies_name'] = movies_name
                        file_info['movies_year'] = movies_year
                        file_info['movies_tmdb'] = movies_tmdb
                        if not chinese_name_filter(file_name):
                            qb_sort = f"请重新刮削-{movies_year}-{file_program_subtype}-{movies_name}"
                        else:
                            if local_exists_in_upload_list:
                                qb_sort = f"上传{self.cd2.upstat[upload_file_status]}-{movies_year}-{file_program_subtype}-{movies_name}"
                            if local_exists_in_remote:
                                qb_sort = f"已上传可删-{movies_year}-{file_program_subtype}-{movies_name}"
                            if not local_exists_in_remote and not local_exists_in_upload_list:
                                qb_sort = f"文件未上传-{movies_year}-{file_program_subtype}-{movies_name}"
                    qb_sort = qb_sort.replace(" ", "").lower()


                    if cd2_cloud_file_path in self.control_dict.keys() and not local_exists_in_remote:
                        if self.control_dict[cd2_cloud_file_path]['process_count'] > upload_try_times or self.control_dict[cd2_cloud_file_path]['upload_time'] > upload_try_hours:
                            upload_after_time = self.control_dict[cd2_cloud_file_path]['upload_time']
                            process_count = self.control_dict[cd2_cloud_file_path]['process_count']
                            new_control_dict[cd2_cloud_file_path] = {'process_count': process_count, 'upload_time': upload_after_time}
                            self.logger.put(f"初始化程序：该文件处理过 {process_count} 次，上传累计需等待 {upload_after_time} 小时，等待时间过久，启动首传：{file_name}")
                            continue


                    # 持久化
                    if upload_file_status == 'Transfer' or upload_file_status == 'Inqueue':
                        if cd2_cloud_file_path not in self.control_dict.keys():
                            process_count = 0
                        else:
                            process_count = self.control_dict[cd2_cloud_file_path]['process_count'] + 1
                            upload_after_time = self.control_dict[cd2_cloud_file_path]['upload_time'] + increment_hours
                        new_control_dict[cd2_cloud_file_path] = {'process_count': process_count, 'upload_time': upload_after_time}
                    else:
                        if cd2_cloud_file_path in self.control_dict.keys():
                            upload_after_time = self.control_dict[cd2_cloud_file_path]['upload_time']
                            process_count = self.control_dict[cd2_cloud_file_path]['process_count']
                            if local_exists_in_remote:
                                self.control_dict.pop(cd2_cloud_file_path, None)
                            else:
                                new_control_dict[cd2_cloud_file_path] = {'process_count': process_count, 'upload_time': upload_after_time}

                    if file_create_before_hour >= upload_after_time:
                        file_allow_upload = True
                    else:
                        file_allow_upload = False

                    file_info_extra = {
                        'cd2_cloud_file_path': cd2_cloud_file_path,
                        'cd2_hlink_file_path': cd2_hlink_file_path,
                        'nas_mount_file_path': nas_mount_file_path,
                        'nas_slink_file_path': nas_slink_file_path,
                        'nas_strm_file_path': nas_strm_file_path,
                        'file_program_type': file_program_type,
                        'local_exists_in_remote': local_exists_in_remote,
                        'local_exists_in_upload_list': local_exists_in_upload_list,
                        'upload_file_status': upload_file_status,
                        'file_program_subtype': file_program_subtype,
                        'upload_after_time': upload_after_time,
                        'file_allow_upload': file_allow_upload,
                        'qb_sort': qb_sort
                    }

                    file_info.update(file_info_extra)


                    if local_exists_in_remote:
                        uploaded_list.append(file_info)
                    if local_exists_in_upload_list and file_extension in media_ext and file_size_byte > 10485760:
                        uploading_list.append(file_info)
                    if file_nlink_count > 1:
                        qb_needed_data2[file_inode] = qb_sort
        
                files_info_count += 1

    
        if position == "hlink":
            with open('media.json', 'w', encoding='utf-8') as f:
                json.dump(new_control_dict, f, ensure_ascii=False, indent=4)
            hlink_notify_info = [
                ('全部的硬链', files_info_count), 
                ('已传的文件', len(uploaded_list)), 
                ('在传的文件', len(uploading_list)), 
                ('首传的文件', len(new_control_dict))
                ]
            self.notify_content.extend(hlink_notify_info)
            return uploaded_list, uploading_list, qb_needed_data2, files_info_count
        elif position == "qb":
            return qb_needed_data1
        else:
            return file_info


    def link_and_delete(self, uploaded_list=""):
        """
        对已上传到网盘的文件进行链接和删除。
        """
        if uploaded_list == "":
            uploaded_list = self.uploaded_list
        if not uploaded_list:
            return

        
        self.logger.put(f"--------------------链接和删除--------------------")

        error_info = ""
        slk, slm, strm, stm, skip, de, scrap_add, link_error = 0, 0, 0, 0, 0, 0, 0, 0
        linked_program = ""
        refresh_items  = []
        for fi in uploaded_list:
            file_name             = fi['file_name']
            file_parent_path      = fi['file_parent_path']
            file_path             = fi['file_path']
            file_inode            = fi['file_inode']
            file_extension        = fi['file_extension']
            nas_slink_file_path   = fi['nas_slink_file_path']
            nas_mount_file_path   = fi['nas_mount_file_path']
            nas_strm_file_path    = fi['nas_strm_file_path']
            file_program_name     = fi['file_program_name']
            file_size_byte        = fi['file_size_byte']
            qb_sort               = fi['qb_sort']

            if "刮削" in qb_sort and file_size_byte > 10485760:
                delete_more(nas_mount_file_path, nas_slink_file_path, nas_strm_file_path, self.logger)
                if os.path.exists(file_path):
                    os.remove(file_path)
                # qs = qb_sort.split("-")
                # qs[0] = "请重新刮削"
                # new_qs = "-".join(qs)
                # self.hlink_inode_sort_dict[file_inode] = new_qs
                self.logger.put(f"链接和删除：该文件已上传，但可能刮削错误，删除各端视频和元数据，分类：{qb_sort}，{file_name}")
                scrap_add += 1
                if qb_sort not in linked_program and file_extension in media_ext:
                    linked_program += f"{qb_sort}<br>"
                continue

            # 链接
            if part_link_mode == "slink":
                if nas_slink_file_path:
                    sl = cd2_slink(nas_mount_file_path, nas_slink_file_path, file_extension, file_path, self.logger)
                    if isinstance(sl, tuple):
                        link_error += 1
                        error_info += f"{sl[1]}\n"
                    elif sl == "slink":
                        slk += 1
                    elif sl == "metadata":
                        slm += 1
                    else:
                        skip += 1
                else:
                    skip += 1
            if part_link_mode == "strm":
                if nas_strm_file_path:
                    st = cd2_strm(nas_mount_file_path, nas_strm_file_path, file_extension, file_path, self.logger)
                    if isinstance(st, tuple):
                        link_error += 1
                        error_info += f"{st[1]}\n"
                    elif st == "strm":
                        strm += 1
                    elif st == "metadata":
                        stm += 1
                    else:
                        skip += 1
                else:
                    skip += 1
            if part_link_mode == "both":
                if nas_slink_file_path:
                    sl = cd2_slink(nas_mount_file_path, nas_slink_file_path, file_extension, file_path, self.logger)
                    if isinstance(sl, tuple):
                        link_error += 1
                        error_info += f"{sl[1]}\n"
                    elif sl == "slink":
                        slk += 1
                    elif sl == "metadata":
                        slm += 1
                    else:
                        skip += 1
                else:
                    skip += 1
                if nas_strm_file_path:
                    st = cd2_strm(nas_mount_file_path, nas_strm_file_path, file_extension, file_path, self.logger)
                    if isinstance(st, tuple):
                        link_error += 1
                        error_info += f"{st[1]}\n"
                    elif st == "strm":
                        strm += 1
                    elif st == "metadata":
                        stm += 1
                    else:
                        skip += 1
                else:
                    skip += 1

            # 记录
            if qb_sort not in linked_program and file_extension in media_ext:
                linked_program += f"{qb_sort}<br>"

            # 删除
            if os.path.exists(file_path):
                os.remove(file_path)
                de += 1
                folder_size = get_folder_byte_size(file_parent_path)
                folder_size_human = format_size(folder_size)
                if folder_size == 0 and os.path.isdir(file_parent_path) and not os.listdir(file_parent_path):
                    os.rmdir(file_parent_path)
                    de += 1

            if qb_sort != "元数据" and file_size_byte > 10485760:
                if link_emby_refresh == "slink":
                    refresh_path = fi['file_program_path'].replace(nas_hlink_root_path, nas_slink_root_path)
                if link_emby_refresh == "strm":
                    refresh_path = fi['file_program_path'].replace(nas_hlink_root_path, nas_strm_root_path)

                if fi['file_program_type'] == "Series":
                    refresh_item = {
                        'type': fi['file_program_type'],
                        'name': fi['series_name'],
                        'year': fi['series_year'],
                        'tmdb': fi['series_tmdb'],
                        'sort': fi['file_program_subtype'],
                        'link_path': refresh_path
                    }
                    if refresh_item not in refresh_items:
                        refresh_items.append(refresh_item)
                        self.logger.put(f"记录刷新：{fi['series_name']} - {fi['series_year']} - tmdb={fi['series_tmdb']} - {fi['file_program_type']} - {fi['file_program_subtype']} - {refresh_path}")
                else:
                    refresh_item = {
                        'type': fi['file_program_type'],
                        'name': fi['movies_name'],
                        'year': fi['movies_year'],
                        'tmdb': fi['movies_tmdb'],
                        'sort': fi['file_program_subtype'],
                        'link_path': refresh_path
                    }
                    if refresh_item not in refresh_items:
                        refresh_items.append(refresh_item)
                        self.logger.put(f"记录刷新：{fi['movies_name']} - {fi['movies_year']} - tmdb={fi['movies_tmdb']} - {fi['file_program_type']} - {fi['file_program_subtype']} - {refresh_path}")

        if refresh_items:
            self.logger.put(f"链接和删除：开始媒体库刷新···")
            with ThreadPoolExecutor(max_workers=2) as executor:
                e = executor.submit(self.emby.refresh_library_by_items, refresh_items)
            while True:
                if e.done():
                    time.sleep(1)
                    es = e.result()
                    break
            if es:
                self.logger.put(f"链接和删除：媒体库刷新成功！")
            else:
                self.logger.put(f"链接和删除：媒体库刷新失败！")


        self.logger.put(f"--------------------链删已完成--------------------\n")

        link_delete_notify_info = [
            ('创建软链接', slk), 
            ('创建 STRM', strm), 
            ('删除的硬链', de), 
            ('已传刮错的', scrap_add), 
            ('下载元数据', stm + slm),
            ('链接错误的', link_error),
            ('链接跳过的', skip),
            ]
        if linked_program:
            self.notify_info += f"{linked_program}"
        self.notify_content.extend(link_delete_notify_info)
        return slk, slm, strm, stm, de, scrap_add, link_error, skip, error_info


    def upload_mission_control(self, uploading_list=""):
        """
        根据文件创建时间和大小来控制未上传文件在cd2上传列表里的状态。
        """
        if uploading_list == "":
            uploading_list = self.uploading_list
        if not uploading_list:
            return
        
        self.logger.put(f"--------------------上传任务控制------------------")

        count_pause  = 0
        count_resume = 0
        count_reload = 0
        error_add = 0
        scrap_add = 0
        linked_program = ""
        for f in uploading_list:
            file_name               = f['file_name']
            file_path               = f['file_path']
            file_size_human         = f['file_size_human']
            file_create_before_hour = f['file_create_before_hour']
            upload_file_status      = f['upload_file_status']
            cd2_cloud_file_path     = f['cd2_cloud_file_path']
            cd2_hlink_file_path     = f['cd2_hlink_file_path']
            nas_slink_file_path     = f['nas_slink_file_path']
            nas_mount_file_path     = f['nas_mount_file_path']
            nas_strm_file_path      = f['nas_strm_file_path']
            upload_after_time       = f['upload_after_time']
            file_allow_uploaded     = f['file_allow_upload']
            qb_sort                 = f['qb_sort']
            file_inode              = f['file_inode']
            file_program_type       = f['file_program_type']
            file_program_name       = f['file_program_name']
            file_program_subtype    = f['file_program_subtype']
            if file_program_type == "Movie":
                movies_name  = f['movies_name']
                movies_year  = f['movies_year']

            if "刮削" in qb_sort:
                self.cd2.task.cancel(cd2_cloud_file_path)
                delete_more(nas_mount_file_path, nas_slink_file_path, nas_strm_file_path, self.logger)
                if os.path.exists(file_path):
                    os.remove(file_path)
                # qs = qb_sort.split("-")
                # qs[0] = "请重新刮削"
                # new_qs = "-".join(qs)
                # self.hlink_inode_sort_dict[file_inode] = new_qs
                self.logger.put(f"上传任务控制：该文件正在上传，但可能刮削错误，取消该上传任务，删除各端视频和元数据，分类：{qb_sort}，{file_name}")
                scrap_add += 1
                if qb_sort not in linked_program:
                    linked_program += f"{qb_sort}<br>"
                continue

            if upload_file_status == 'Finish':
                if file_program_type == "Movie":
                    qs = qb_sort.split("-")
                    qs[0] = "已上传可删"
                    new_qs = "-".join(qs)
                    self.hlink_inode_sort_dict[file_inode] = new_qs
                continue

            if upload_file_status == 'Error' or upload_file_status == 'FatalError':
                try:
                    self.cd2.fs.move(cd2_hlink_file_path, cd2_cloud_file_path)
                    time.sleep(1)
                    self.cd2.task.pause(cd2_cloud_file_path)
                    error_add += 1
                    if file_program_type == "Movie":
                        self.hlink_inode_sort_dict[file_inode] = f"上传{self.cd2.upstat['Pause']}-{movies_year}-{file_program_subtype}-{movies_name}"
                    self.logger.put(f"上传任务控制：该文件上传遇到错误，重新添加并暂停：{file_name}")
                except Exception as e:
                    self.logger.put(f"上传任务控制：重新添加错误：{e}")
                continue

            if file_allow_uploaded:
                if upload_file_status == 'Transfer' or upload_file_status == 'Inqueue':
                    try:
                        self.cd2.fs.move(cd2_hlink_file_path, cd2_cloud_file_path)
                        time.sleep(1)
                        self.cd2.task.pause(cd2_cloud_file_path)
                        self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，已允许上传，但是首传，重新添加并暂停：{file_name}")
                        count_pause += 1
                        if file_program_type == "Movie":
                            self.hlink_inode_sort_dict[file_inode] = f"上传{self.cd2.upstat['Pause']}-{movies_year}-{file_program_subtype}-{movies_name}"
                    except Exception as e:
                        self.logger.put(f"上传任务控制：重新添加错误：{e}")
                elif upload_file_status == 'Pause':
                    self.cd2.task.resume(cd2_cloud_file_path)
                    self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，已允许上传，但是暂停，继续该任务：{file_name}")
                    count_resume += 1
                    if file_program_type == "Movie":
                        self.hlink_inode_sort_dict[file_inode] = f"上传{self.cd2.upstat['Preprocessing']}-{movies_year}-{file_program_subtype}-{movies_name}"
                else:
                    self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，已允许上传，继续处理：{file_name}")
            else:
                if upload_file_status == 'Transfer' or upload_file_status == 'Inqueue':
                    try:
                        self.cd2.fs.move(cd2_hlink_file_path, cd2_cloud_file_path)
                        time.sleep(1)
                        self.cd2.task.pause(cd2_cloud_file_path)
                        self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，不允许上传，且是首传，重新添加并暂停：{file_name}")
                        count_reload += 1
                        if file_program_type == "Movie":
                            self.hlink_inode_sort_dict[file_inode] = f"上传{self.cd2.upstat['Pause']}-{movies_year}-{file_program_subtype}-{movies_name}"
                    except Exception as e:
                        self.logger.put(f"上传任务控制：重新添加错误：{e}")
                elif upload_file_status == 'Preprocessing' or upload_file_status == 'WaitingforPreprocessing':
                    self.cd2.task.pause(cd2_cloud_file_path)
                    self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，不允许上传，正在处理中，暂停该任务：{file_name}")
                    count_pause += 1
                    if file_program_type == "Movie":
                        self.hlink_inode_sort_dict[file_inode] = f"上传{self.cd2.upstat['Pause']}-{movies_year}-{file_program_subtype}-{movies_name}"
                else:
                    self.logger.put(f"上传任务控制：该文件大小 {file_size_human}，创建于 {file_create_before_hour} 小时前，规定时间 {upload_after_time} 小时，暂停上传中，继续暂停：{file_name}")
            
            time.sleep(0.2)

        self.logger.put(f"--------------------任务控制完成------------------\n")

        upload_control_notify_info = [
            ('上传错误的', error_add),
            ('在传刮错的', scrap_add),
            ('暂停上传的', count_pause),
            ('继续上传的', count_resume),
            ('重新上传的', count_reload)
        ]
        self.notify_content.extend(upload_control_notify_info)
        if linked_program:
            self.notify_info += f"{linked_program}"

        return error_add, scrap_add, count_pause, count_resume


    def qb_category(self):
        """
        设置Qbittorrent种子分类。
        """

        self.logger.put(f"--------------------QB 任务分类-------------------")

        qb_inode       = set(self.qb_inode_name_dict.keys())
        hlink_inode    = set(self.hlink_inode_sort_dict.keys())
        combined_inode = qb_inode & hlink_inode
        if not combined_inode:
            self.logger.put(f"QB 任务分类：没有新的种子信息，无需更新！")
            return
        count = 0
        temp = {}
        self.qb.categories = self.qb.qb_categories()
        for i in combined_inode:
            h_name = self.qb_inode_name_dict[i]
            h_sort = self.hlink_inode_sort_dict[i]

            if h_name in temp.keys():
                if h_sort not in temp[h_name]:
                    temp[h_name].add(h_sort)
            else:
                temp[h_name] = {h_sort,}
            
            if len(temp[h_name]) > 1:
                state = set()
                for st in temp[h_name]:
                    if "未上传" in st:
                        state.add("未上传")
                    if "处理" in st:
                        state.add("处理")
                    if "等待" in st:
                        state.add("等待")
                    if "刮削" in st:
                        state.add("刮削")
                    if "进行" in st:
                        state.add("进行")
                    if "排队" in st:
                        state.add("排队")
                    if "暂停" in st:
                        state.add("暂停")
                    if "可删" in st:
                        state.add("有删")
                new_state = ",".join(state)
                a = h_sort.split("-")
                a[0] = f"{new_state}"
                h_sort = "-".join(a)

            for info in self.qb.qb_torrents(filter='seeding'):
                t_name     = info['name']
                t_category = info['category']
                t_hash     = info['hash']
                if t_name == h_name:
                    if h_sort == t_category:
                        break
                    if h_sort not in self.qb.categories:
                        self.qb.qb_create_category(h_sort)
                        self.qb.categories.append(h_sort)
                    time.sleep(0.2)
                    self.qb.qb_set_category(t_hash, h_sort)
                    self.logger.put(f"QB 任务分类：更新种子状态，{h_sort} - {t_name}")
                    count += 1
        if count == 0:
            self.logger.put(f"QB 任务分类：没有状态已改变的种子，无需更新！")
        self.logger.put(f"--------------------任务分类完成------------------\n")
        self.notify_content.append(('更新的分类', count))
        return count


    def uptime(self, file_name, file_size_byte):
        # 获取上传等待时长（按照发布组）
        for index, group in enumerate(group_slice):
            if group in file_name:
                upload_after_time = group_wait[index]
                return upload_after_time
        
        # 获取上传等待时长（按照大小）
        for index, size in enumerate(size_slice):
            if size_slice[index] <= file_size_byte <= size_slice[index+1]:
                upload_after_time = size_wait[index]
                return upload_after_time


    def __get_path_at_level__(self, path_str, level):
        """
        获取给定路径字符串中特定级别的子路径。
        :param path_str: 字符串表示的路径。
        :param level: 请求的路径层级。
        :return: 指定层数的子路径，从根路径到该子路径的完整路径，以及路径字符串的总层数。
        :raises ValueError: 当层数无效或路径字符串格式不正确时抛出。
        """

        if not isinstance(path_str, str):
            raise ValueError("path_str 必须是一个字符串类型。")

        # 确保路径以斜杠开头和结尾
        if not path_str.startswith('/'):
            path_str = '/' + path_str
        if not path_str.endswith('/'):
            path_str += '/'

        # 使用斜杠分隔路径，并去除空字符串部分
        path_segments = list(filter(None, path_str.split('/')))

        # 检查层数是否有效
        if level < 1 or level > len(path_segments):
            raise ValueError(f"指定层级 {level} 应小于路径的 {len(path_segments)} 层。")

        # 返回指定层数的路径，返回的是从根路径到指定层数的完整路径
        specified_path = path_segments[level - 1]
        full_path_to_specified = '/' + '/'.join(path_segments[:level])
        total_levels = len(path_segments)

        return specified_path, full_path_to_specified, total_levels


    def __check_episode_status__(self, program_path):
        """
        检查指定项目中的文件上传状态。
        """
        try:
            for root, dirs, files in os.walk(program_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    cd2_cloud_file_path = file_path.replace(nas_hlink_root_path, cd2_cloud_root_path)
                    yield self.cd2.file_exists_in_remote(file_path, cd2_cloud_file_path), file_path
        except Exception as e:
            self.logger.put("初始化程序：项目 {program_path}，检查状态时发生异常: {e}")


    def get_series_sort(self, program_path, program_name, file_name, file_program_subtype=""):
        """
        检查指定项目是否全部上传。
        program_path: str
        return: str
        """
        if not file_program_subtype:
            file_program_subtype = "剧集"

        if not os.path.exists(program_path) or not os.path.isdir(program_path):
            return f"{file_program_subtype},路径无效"

        match = re.match(series_pattern, program_name, re.UNICODE)
        if match:
            series_name = match.group(1)
            series_year = match.group(2)
        else:
            series_name = "未知"
            series_year = "未知"

        if not chinese_name_filter(file_name):
            return f"请重新刮削-{series_year}-{file_program_subtype}-{series_name}"

        status = {"已上传": 0, "未上传": 0}
        for is_uploaded, file_path in self.__check_episode_status__(program_path):
            if is_uploaded:
                status["已上传"] += 1
            else:
                status["未上传"] += 1

        if status["未上传"] > 0:
            return f"未全部上传-{series_year}-{file_program_subtype}-{series_name}"
        elif status["未上传"] == 0 and status["已上传"] > 0:
            return f"已全传可删-{series_year}-{file_program_subtype}-{series_name}"
        elif status["未上传"] > 0 and status["已上传"] == 0:
            return f"文件未上传-{series_year}-{file_program_subtype}-{series_name}"
        else:
            return f"{series_year}-{file_program_subtype}-{series_name}-状态未知"


if __name__ == "__main__":

    logger = Log("media-log", "media").logger
    log_queue  = Queue()
    log_thread = Thread(target=log_writer, args=(log_queue, logger))
    log_thread.start()

    all_info = FileInfo(log_queue)

    ld  = all_info.link_and_delete()
    umc = all_info.upload_mission_control()
    qc  = all_info.qb_category()

    item = all_info.notify_content

    if notify_only_new:
        filtered_item = [
            (a, b)
            for a, b in item
            if b != 0 and b != ''
        ]
        items = filtered_item
        log_queue.put(item)
        log_queue.put(filtered_item)
    else:
        items = item
        log_queue.put(item)


    info_content = all_info.notify_info
    if info_content == "相关项目：<br>" or info_content == "":
        info_judge = False
        log_queue.put("\n\n")
    else:
        info_judge = True
        # log_queue.put(info_content + "\n\n")


    log_queue.put(None)
    log_thread.join()

    if info_judge:
        title = "影音一条龙"
        font_color = "white"
        border_color = "#C8E8FF"
        title_color = "#2861A1"
        head_color = "#2861A1"
        item_color_A = "#64A4E8"
        item_color_B = "#3871C1"
        content = notify_template_col4(title, items, font_color, border_color, title_color, head_color, item_color_A, item_color_B, info=info_judge, info_content=info_content, title1="项目", title2="数量(个)")
        digest = f"{item[0][0]}：{item[0][1]}\n{item[1][0]}：{item[1][1]}\n{item[2][0]}：{item[2][1]}\n{item[3][0]}：{item[3][1]}"
    
        wecom_app(title, content, digest)

