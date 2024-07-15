#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - 全量链接');
0 11 * * 6 link.py
"""

import os
import sys
import time
import shutil
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from queue import Queue

from __notify_template import notify_template_col4
from clouddrive2 import CD2
from __notifier import wecom_app
from __logger import Log
from __utils import recursive_chmod, recursive_chown, format_seconds
from _Config import media_ext, mdata_ext, full_link_mode, nas_mount_root_path, nas_slink_root_path, nas_strm_root_path, xd_alist_root_url, xd_uid, xd_gid, xd_mod, notify_interval, notify_only_new


mount_path = nas_mount_root_path
strm_path  = nas_strm_root_path
slink_path = nas_slink_root_path
alist_url  = xd_alist_root_url
strm_time  = time.time()
slink_time = time.time()
cd2 = CD2().file_count()[1]

def write_to_file(content, save_strm_path):
    """
    创建 STRM 文件并写入内容。
    """
    parent_path = os.path.dirname(save_strm_path)
    os.makedirs(parent_path, exist_ok=True)
    with open(save_strm_path, 'w', encoding='utf-8') as f:
        f.write(content)
    recursive_chmod(parent_path, xd_mod)
    recursive_chown(parent_path, xd_uid, xd_gid)

def dl_to_path(source, dest):
    """
    下载非视频文件。
    """
    parent_path = os.path.dirname(dest)
    os.makedirs(parent_path, exist_ok=True)
    shutil.copy2(source, dest)
    recursive_chmod(parent_path, xd_mod)
    recursive_chown(parent_path, xd_uid, xd_gid)

def filename_check(file_name):
    filename = file_name.replace('/', 'xd')
    filename = filename.replace('\\', 'xd')
    filename = filename.replace('\0', 'xd')

    split = os.path.splitext(filename)
    namepart = split[0]
    ext = split[1][1:].lower()
    if ext in mdata_ext or ext in media_ext:
        if len(namepart) > 245:
            filename = namepart[:245]
            filename = f"{filename}.{ext}"

    return filename


def strm_file(file_path, logger, retry=True, times=2):
    """
    为指定文件创建 STRM 文件，非视频文件直接下载。
    """
    basename = os.path.basename(file_path)
    try:
        save_mdata_path = file_path.replace(mount_path, strm_path)
        if not os.path.exists(file_path):
            logger.put(f"STRM：源文件不存在 - {file_path}")
            return "fnf", f"STRM：源文件不存在 - {basename}"
        else:
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in media_ext:
                save_strm_path = f"{os.path.splitext(save_mdata_path)[0]}.strm"
                if os.path.exists(save_strm_path):
                    logger.put(f"STRM：跳过 - {save_strm_path}")
                    return False
                else:
                    content = file_path.replace(mount_path, alist_url)
                    write_to_file(content, save_strm_path)
                    logger.put(f"STRM：视频 - {save_strm_path}")
                    return "strm"
            elif ext in mdata_ext:
                if os.path.exists(save_mdata_path):
                    logger.put(f"STRM：跳过 - {save_mdata_path}")
                    return False
                dl_to_path(file_path, save_mdata_path)
                logger.put(f"STRM：元数据 - {save_mdata_path}")
                return "metadata"
            else:
                logger.put(f"STRM：源文件格式不正确 - {basename}")
                return "fnf", f"STRM：源文件格式不正确 - {basename}"
    except FileNotFoundError:
        if retry and times > 0:
            logger.put(f"STRM：文件不存在，重试中 - {basename} - 剩余重试次数：{times}")
            return strm_file(file_path, logger, retry=True, times=times-1)
        else:
            logger.put(f"STRM：文件不存在，无法创建 STRM - {basename}")
            return f"STRM：文件不存在，无法创建 STRM - {basename}"
    except OSError as e:
        if "Filename too long" in str(e) or "ENAMETOOLONG" in str(e):
            logger.put(f"STRM：文件名过长错误: {basename}")
            return f"STRM：文件名过长错误: {basename}"
        else:
            logger.put(f"STRM：发生输入输出错误: {basename} - {e}")
            return f"STRM：发生输入输出错误: {basename} - {e}"
    except Exception as e:
        logger.put(f"STRM：链接发生错误 - {basename} - {e}")
        return "error", f"STRM：链接发生错误 - {basename} - {e}"


def strm_folder(folder_path, logger):
    """
    为指定目录创建 STRM 文件，非视频文件直接下载。
    """
    global strm_time
    media, data, skip, error, count = 0, 0, 0, 0, 0
    error_info = ""
    c = 0
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            count += 1
            f = filename_check(f)
            file_path = os.path.join(root, f)
            r = strm_file(file_path, logger)
            if isinstance(r, tuple):
                error += 1
                error_info += f"{r[1]}\n"
            elif r == "strm":
                media += 1
            elif r == "metadata":
                data += 1
            else:
                skip += 1
            c = round(count / cd2 * 100, 4)
            time_now = time.time()
            if time_now - strm_time > notify_interval:
                strm_time = time_now
                try:
                    cd2_new = CD2()
                except Exception as e:
                    logger.put(f"CD2 异常：{e}")
                    wecom_app("STRM 故障", f"CD2 异常，退出脚本：{e}")
                    sys.exit(1)
                wecom_app("STRM 进度", f"\n{count} / {cd2}, {c} %")
        print(f"当前文件夹：{os.path.basename(root)}，STRM 进度：{count} / {cd2}, {c} % ···············", end="\r", flush=True)
    return media, data, skip, error, error_info


def slink_file(file_path, logger, retry=True, times=2):
    """
    为指定文件创建 SLINK 文件，非视频文件直接下载。
    """
    basename = os.path.basename(file_path)
    try:
        save_slink_path = file_path.replace(mount_path, slink_path)
        if not os.path.exists(file_path):
            logger.put(f"软链接：源文件不存在 - {file_path}")
            return "fnf", f"软链接：源文件不存在 - {basename}"
        else:
            if os.path.exists(save_slink_path):
                logger.put(f"软链接：跳过 - {save_slink_path}")
                return False
            else:
                ext = os.path.splitext(file_path)[1][1:].lower()
                if ext in media_ext:
                    parent_path = os.path.dirname(save_slink_path)
                    os.makedirs(parent_path, exist_ok=True)
                    os.symlink(file_path, save_slink_path)
                    logger.put(f"软链接：视频 - {save_slink_path}")
                    return "slink"
                elif ext in mdata_ext:
                    dl_to_path(file_path, save_slink_path)
                    logger.put(f"软链接：元数据 - {save_slink_path}")
                    return "metadata"
                else:
                    logger.put(f"软链接：源文件格式不正确 - {basename}")
                    return "fnf", f"软链接：源文件格式不正确 - {basename}"
    except FileNotFoundError:
        if retry and times > 0:
            logger.put(f"软链接：文件不存在，重试中 - {basename} - 剩余重试次数：{times}")
            return slink_file(file_path, logger, retry=True, times=times-1)
        else:
            logger.put(f"软链接：文件不存在，无法创建软链接 - {basename}")
            return f"软链接：文件不存在，无法创建软链接 - {basename}"
    except OSError as e:
        if "Filename too long" in str(e) or "ENAMETOOLONG" in str(e):
            logger.put(f"软链接：文件名过长错误: {basename}")
            return f"软链接：文件名过长错误: {basename}"
        else:
            logger.put(f"软链接：发生输入输出错误: {basename} - {e}")
            return f"软链接：发生输入输出错误: {basename} - {e}"
    except Exception as e:
        logger.put(f"软链接：链接发生错误 - {basename} - {e}")
        return "error", f"软链接：链接发生错误 - {basename} - {e}"


def slink_folder(folder_path, logger):
    """
    为指定目录创建 SLINK 文件，非视频文件直接下载。
    """
    global slink_time
    media, data, skip, error, count = 0, 0, 0, 0, 0
    error_info = ""
    c = 0
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            count += 1
            f = filename_check(f)
            file_path = os.path.join(root, f)
            r = slink_file(file_path, logger)
            if isinstance(r, tuple):
                error += 1
                error_info += f"{r[1]}\n"
            elif r == "slink":
                media += 1
            elif r == "metadata":
                data += 1
            else:
                skip += 1
            c = round(count / cd2 * 100, 4)
            time_now = time.time()
            if time_now - slink_time > notify_interval:
                slink_time = time_now
                try:
                    cd2_new = CD2()
                except Exception as e:
                    logger.put(f"CD2 异常：{e}")
                    wecom_app("软链接故障", f"CD2 异常，退出脚本：{e}")
                    sys.exit(1)
                wecom_app("软链接进度", f"\n{count} / {cd2}, {c} %")
        print(f"当前文件夹：{os.path.basename(root)}，软链接进度：{count} / {cd2}, {c} % ···············", end="\r", flush=True)
    return media, data, skip, error, error_info


def cd2_slink(file_mount_path, file_slink_path, file_ext, file_path, logger, retry=True, times=2):
    basename = os.path.basename(file_mount_path)
    try:
        if not os.path.exists(file_mount_path):
            logger.put(f"软链接：源文件不存在 - {file_mount_path}")
            return "fnf", f"STRM：源文件不存在 - {basename}"
        else:
            if os.path.exists(file_slink_path):
                logger.put(f"软链接：跳过 - {file_slink_path}")
                return False
            else:
                if file_ext in media_ext:
                    parent_path = os.path.dirname(file_slink_path)
                    os.makedirs(parent_path, exist_ok=True)
                    os.symlink(file_mount_path, file_slink_path)
                    logger.put(f"软链接：视频 - {file_slink_path}")
                    return "slink"
                elif file_ext in mdata_ext:
                    try:
                        dl_to_path(file_path, file_slink_path)
                    except:
                        dl_to_path(file_mount_path, file_slink_path)
                    logger.put(f"软链接：元数据 - {file_slink_path}")
                    return "metadata"
                else:
                    logger.put(f"软链接：源文件格式不正确 - {basename}")
                    return "fnf", f"软链接：源文件格式不正确 - {basename}"
    except FileNotFoundError:
        if retry and times > 0:
            logger.put(f"软链接：文件不存在，重试中 - {basename} - 剩余重试次数：{times}")
            return cd2_slink(file_mount_path, file_slink_path, file_ext, file_path, logger, retry=True, times=times-1)
        else:
            logger.put(f"软链接：文件不存在，无法创建软链接 - {basename}")
            return f"软链接：文件不存在，无法创建软链接 - {basename}"
    except OSError as e:
        if "Filename too long" in str(e) or "ENAMETOOLONG" in str(e):
            logger.put(f"软链接：文件名过长错误: {basename}")
            return f"软链接：文件名过长错误: {basename}"
        else:
            logger.put(f"软链接：发生输入输出错误: {basename} - {e}")
            return f"软链接：发生输入输出错误: {basename} - {e}"
    except Exception as e:
        logger.put(f"软链接：链接发生错误 - {basename} - {e}")
        return "error", f"软链接：链接发生错误 - {basename} - {e}"


def cd2_strm(file_mount_path, file_strm_path, file_ext, file_path, logger, retry=True, times=2):
    basename = os.path.basename(file_mount_path)
    try:
        if not os.path.exists(file_mount_path):
            logger.put(f"STRM：源文件不存在 - {file_mount_path}")
            return "fnf", f"STRM：源文件不存在 - {basename}"
        else:
            if file_ext in media_ext:
                save_strm_path = f"{os.path.splitext(file_strm_path)[0]}.strm"
                if os.path.exists(save_strm_path):
                    logger.put(f"STRM：跳过 - {save_strm_path}")
                    return False
                else:
                    content = file_mount_path.replace(mount_path, alist_url)
                    write_to_file(content, save_strm_path)
                    logger.put(f"STRM：视频 - {save_strm_path}")
                    return "strm"
            elif file_ext in mdata_ext:
                if os.path.exists(file_strm_path):
                    logger.put(f"STRM：跳过 - {file_strm_path}")
                    return False
                dl_to_path(file_path, file_strm_path)
                logger.put(f"STRM：元数据 - {file_strm_path}")
                return "metadata"
            else:
                logger.put(f"STRM：源文件格式不正确 - {basename}")
                return "fnf", f"STRM：源文件格式不正确 - {basename}"
    except FileNotFoundError:
        if retry and times > 0:
            logger.put(f"STRM：文件不存在，重试中 - {basename} - 剩余重试次数：{times}")
            return cd2_strm(file_path, logger, retry=True, times=times-1)
        else:
            logger.put(f"STRM：文件不存在，无法创建 STRM - {basename}")
            return f"STRM：文件不存在，无法创建 STRM - {basename}"
    except OSError as e:
        if "Filename too long" in str(e) or "ENAMETOOLONG" in str(e):
            logger.put(f"STRM：文件名过长错误: {basename}")
            return f"STRM：文件名过长错误: {basename}"
        else:
            logger.put(f"STRM：发生输入输出错误: {basename} - {e}")
            return f"STRM：发生输入输出错误: {basename} - {e}"
    except Exception as e:
        logger.put(f"STRM：链接发生错误 - {basename} - {e}")
        return "error", f"STRM：链接发生错误 - {basename} - {e}"


def log_writer(log_queue, logger):
    while True:
        try:
            log_entry = log_queue.get(block=True)
            if log_entry is None:
                break
            logger.info(log_entry)
        except Exception as e:
            if str(e) != 'Empty':
                raise


if __name__ == "__main__":
    if full_link_mode not in ["strm", "slink", "both"]:
        print("链接模式变量 full_link_mode 未设置！可选值：strm、slink、both")
        wecom_app("全量链接模式未设置!", f"链接模式变量 full_link_mode 未设置！可选值：strm、slink、both")
        sys.exit(0)

    logger = Log("full-link-log", "full-link").logger
    log_queue  = Queue()
    log_thread = Thread(target=log_writer, args=(log_queue, logger))
    log_thread.start()
    item = {}
    info_content = ""
    wecom_app("全量链接开始", f"\n链接模式为{full_link_mode}")
    start_time = time.time()

    log_queue.put(f"---------------全量链接开始---------------")
    print(f"\n---------------全量链接开始---------------")

    if full_link_mode == "strm":
        if not strm_path:
            wecom_app("全量链接错误！", "全量链接的模式为 STRM，但 STRM 根路径未设置！")
            sys.exit("全量链接的模式为 STRM，但 STRM 根路径未设置！")
        else:
            with ThreadPoolExecutor(max_workers=12) as executor:
                st = executor.submit(strm_folder, mount_path, log_queue)
            while True:
                if st.done():
                    time.sleep(2)
                    rs = st.result()
                    break
                time.sleep(1)
            item['创建 STRM'] = f"{rs[0]}个"
            item['下载元数据'] = f"{rs[1]}个"
            item['跳过文件'] = f"{rs[2]}个"
            item['错误文件'] = f"{rs[3]}个"
            digest_content = f"创建 STRM：{rs[0]}个\n下载元数据：{rs[1]}个\n跳过文件：{rs[2]}个\n错误文件：{rs[3]}个\n"
            if rs[4]:
                info_content = f"{rs[4]}"
    elif full_link_mode == "slink":
        if not slink_path:
            wecom_app("全量链接错误！", "全量链接的模式为软链接，但软链接根路径未设置！")
            sys.exit("全量链接的模式为软链接，但软链接根路径未设置！")
        else:
            with ThreadPoolExecutor(max_workers=12) as executor:
                sl = executor.submit(slink_folder, mount_path, log_queue)
            while True:
                if sl.done():
                    time.sleep(2)
                    rs = sl.result()
                    break
                time.sleep(1)
            item['创建软链接'] = f"{rs[0]}个"
            item['下载元数据'] = f"{rs[1]}个"
            item['跳过文件'] = f"{rs[2]}个"
            item['错误文件'] = f"{rs[3]}个"
            digest_content = f"创建软链接：{rs[0]}个\n下载元数据：{rs[1]}个\n跳过文件：{rs[2]}个\n错误文件：{rs[3]}个\n"
            if rs[4]:
                info_content = f"{rs[4]}"
    else:
        if not strm_path or not slink_path:
            wecom_app("全量链接错误！", "全量链接的模式为 both，但软链接或 STRM 根路径未设置！")
            sys.exit("全量链接的模式为 both，但软链接或 STRM 根路径未设置！")
        with ThreadPoolExecutor(max_workers=12) as executor:
            st = executor.submit(strm_folder, mount_path, log_queue)
            sl = executor.submit(slink_folder, mount_path, log_queue)
        while True:
            if st.done() and sl.done():
                time.sleep(2)
                rs = st.result()
                rs1 = sl.result()
                break
            time.sleep(1)
        item['创建 STRM'] = f"{rs[0]}个"
        item['创建软链接'] = f"{rs1[0]}个"
        item['STRM 跳过'] = f"{rs[2]}个"
        item['软链接跳过'] = f"{rs1[2]}个"
        item['STRM 错误'] = f"{rs[3]}个"
        item['软链接错误'] = f"{rs1[3]}个"
        item['下载元数据'] = f"{rs1[1]}个"
        digest_content = f"创建 STRM：{rs[0]}个\n下载元数据：{rs[1]}个\n跳过文件：{rs[2]}个\n错误文件：{rs[3]}个\n\n创建软链接：{rs[0]}个\n下载元数据：{rs[1]}个\n跳过文件：{rs[2]}个\n错误文件：{rs[3]}个\n"
        if rs[4] or rs1[4]:
            info_content = f"{rs[4]}\n{rs1[4]}"

    end_time = time.time()
    time_human = format_seconds(end_time - start_time)
    item['共耗时'] = time_human

    log_queue.put(f"共耗时 {time_human}")
    log_queue.put(f"---------------全量链接结束---------------\n\n")
    print(f"\n---------------全量链接结束---------------\n\n共耗时 {time_human}")

    log_queue.put(None)
    log_thread.join()

    if info_content:
        info_judge = True
    else:
        info_judge = False

    items_list = list(item.items())
    if notify_only_new:
        filtered_item = [
            (a, b)
            for a, b in items_list
            if b != 0 and b != ''
        ]
        items = filtered_item
    else:
        items = items_list
    print(items)

    title = "全量链接"
    font_color = "white"
    border_color = "#C8E8FF"
    title_color = "#2861A1"
    head_color = "#2861A1"
    item_color_A = "#64A4E8"
    item_color_B = "#3871C1"
    content = notify_template_col4(title, items, font_color, border_color, title_color, head_color, item_color_A, item_color_B, info=info_judge, info_content=info_content, title1="项目", title2="数量(个)")
    digest = digest_content + f"共耗时 {time_human}"

    wecom_app(title, content, digest)
