#!/usr/bin/env python3
# _*_ coding:utf-8 _*_


import re
import os
import errno
from datetime import datetime, timedelta

from __config import chinese_pattern


DIVISORS = [1, 1024, 1024 ** 2, 1024 ** 3, 1024 ** 4, 1024 ** 5, 1024 ** 6]
UNITS    = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]


def format_size(size_bytes):
    """
    将文件大小从字节转换为可读形式，保留两位小数，返回字符串。
    size: int bytes
    return: str
    """
    if not isinstance(size_bytes, (int, float)):
        raise ValueError("输入必须是数字！")

    if size_bytes <= 0:
        return "0 B"

    # 使用循环简化条件判断
    for index, divisor in enumerate(DIVISORS):
        if divisor <= size_bytes <= DIVISORS[index+1]:
            return f"{size_bytes / DIVISORS[index]:.2f} {UNITS[index]}"

    return f"{size_bytes / divisor:.2f} {UNITS[-1]}"


def format_time(time_input, input_format='%Y-%m-%d %H:%M:%S'):
    """
    将输入的时间（时间戳、datetime对象或特定格式的字符串）格式化为'%Y-%m-%d %H:%M:%S'，
    并计算与当前时间的时间差，返回小时和分钟时间差。

    time_input: 可以是时间戳（整数或浮点数）、datetime对象或特定格式的字符串。
    input_format: 如果time_input是字符串，则此参数指定其格式。
    return: 一个包含小时差和分钟差的元组。
    """
    try:
        # 如果输入是时间戳（整数或浮点数），则转换为datetime对象
        if isinstance(time_input, (int, float)):
            time_obj = datetime.fromtimestamp(time_input)
        # 如果输入是字符串，则根据给定的格式解析为datetime对象  
        elif isinstance(time_input, str):
            time_obj = datetime.strptime(time_input, input_format)
        # 如果输入已经是datetime对象，则直接使用  
        elif isinstance(time_input, datetime):
            time_obj = time_input
        else:
            raise ValueError("输入必须为数字类型时间戳、datetime 对象，或者指定格式的字符串！")

        # 获取当前时间，考虑时区问题
        current_time = datetime.now()

        # 计算时间差
        time_difference = current_time - time_obj

        # 转换为总秒数
        total_seconds = time_difference.total_seconds()

        # 考虑时间差可能为负值的情况
        if total_seconds < 0:
            raise ValueError("输入必须为过去的时间！")

        # 转换为小时和分钟
        hours_difference   = int(total_seconds // 3600)
        minutes_difference = int(total_seconds // 60)

    except ValueError as e:
        print(f"错误: {e}")
        return None

    return time_obj, hours_difference, minutes_difference


def format_seconds(seconds):
    # 定义时间单位及其对应的秒数
    time_units = [
        ("小时", 3600),
        ("分钟", 60),
        ("秒", 1)
    ]

    # 初始化结果列表
    parts = []
    
    # 遍历时间单位
    for unit_name, unit_seconds in time_units:
        # 计算当前单位下的时间数量，并取整
        amount, seconds = divmod(int(seconds), unit_seconds)
        
        # 如果时间数量大于0，则添加到结果列表中
        if amount > 0:
            parts.append(f"{amount}{unit_name}")
    
    # 使用' '连接结果列表中的各个部分，并返回
    return ' '.join(parts) if parts else '0秒'


def recursive_chmod(path, mode):
    """
    将文件夹或文件路径的权限修改为指定值。
    path: str
    mode: example: 0o755
    """
    try:
        if not os.path.exists(path):
            print(f"路径 {path} 不存在")
            return
        if not isinstance(mode, int) or not (0o000 <= mode <= 0o777):
            print(f"无效的权限模式: {mode}")
            return

        # 改变给定路径的权限
        os.chmod(path, mode)

        # 如果是目录，则递归处理其内容
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                # 跳过符号链接
                if any(os.path.islink(d) for d in dirs):
                    print(f"跳过符号链接目录: {d}")
                    dirs.remove(d)  # 避免无限循环
                for file in files:
                    file_path = os.path.join(root, file)
                    os.chmod(file_path, mode)

            # 对当前遍历的目录设置权限，避免重复对每个文件和子目录设置
            os.chmod(root, mode)

    except Exception as e:
        print(f"更改权限时发生错误: {e}")


def recursive_chown(path: str, uid: int, gid: int):
    """
    将文件夹或文件路径的所属用户和所属组修改为指定值。
    :param path: str - 需要改变所有权的文件或目录路径
    :param uid: int - 指定的用户ID
    :param gid: int - 指定的组ID
    :return: Tuple[int, int] - 成功更改的数量，(文件更改数量, 目录更改数量)
    """
    if not path or not isinstance(uid, int) or not isinstance(gid, int) or uid < 0 or gid < 0:
        raise ValueError("路径必须为非空字符, uid 和 gid 必须为非负整数！")

    file_count = 0
    dir_count = 0

    try:
        os.chown(path, uid, gid)
        file_count += 1
    except OSError as e:
        if e.errno == errno.EACCES:
            print(f"目录没有操作权限: {path}")
        elif e.errno == errno.ENOENT:
            print(f"目录不存在: {path}")
        else:
            raise e

    # 如果是目录，则递归处理其内容
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    os.chown(dir_path, uid, gid)
                    dir_count += 1
                except OSError as e:
                    if e.errno == errno.EACCES:
                        print(f"目录没有操作权限: {dir_path}")
                    elif e.errno == errno.ENOENT:
                        print(f"目录不存在: {dir_path}")
                    else:
                        raise e

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.chown(file_path, uid, gid)
                    file_count += 1
                except OSError as e:
                    if e.errno == errno.EACCES:
                        print(f"目录没有操作权限: {file_path}")
                    elif e.errno == errno.ENOENT:
                        print(f"目录不存在: {file_path}")
                    else:
                        raise e

    return file_count, dir_count


def get_folder_byte_size(folder_path):
    """
    计算指定路径文件夹的大小并返回字节值。
    folder_path: str
    return: int bytes
    """
    total_size = 0

    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)

                if os.path.islink(file_path):
                    continue

                try:
                    # 尝试获取文件大小，可能因文件系统权限问题而失败
                    total_size += os.path.getsize(file_path)
                except OSError as e:
                    print(f"获取该文件大小错误 {file_path}: {e}")

    except FileNotFoundError as fnf_error:
        print(f"目录不存在: {fnf_error}")
    except PermissionError as p_error:
        print(f"目录没有访问权限: {p_error}")

    return total_size


def chinese_name_filter(file_name):
    # 假设输入已经是Unicode编码，或在处理前进行解码
    # 检查捕获的字符串中是否包含中文字符
    match = re.match(chinese_pattern, file_name, re.UNICODE)
    if match:
        before_pattern = match.group(1)
        if re.search(r'[\u4e00-\u9fff]', before_pattern):
            return True
    return False


def delete_more(nas_mount_file_path, nas_slink_file_path, nas_strm_file_path, logger=""):
    mount_base_path = os.path.splitext(nas_mount_file_path)[0]
    if os.path.exists(nas_mount_file_path):
        os.remove(nas_mount_file_path)
        if logger:
            logger.put(f"删除刮削错误文件：{nas_mount_file_path}")
        else:
            print(f"删除刮削错误文件：{nas_mount_file_path}")
    nfo_path = f"{mount_base_path}.nfo"
    if os.path.exists(nfo_path):
        os.remove(nfo_path)
        if logger:
            logger.put(f"删除刮削错误文件：{nfo_path}")
        else:
            print(f"删除刮削错误文件：{nfo_path}")
    jpg_path = f"{mount_base_path}-thumb.jpg"
    if os.path.exists(jpg_path):
        os.remove(jpg_path)
        if logger:
            logger.put(f"删除刮削错误文件：{jpg_path}")
        else:
            print(f"删除刮削错误文件：{jpg_path}")
    mount_parent_path = os.path.dirname(nas_mount_file_path)
    if os.path.exists(mount_parent_path) and not os.listdir(mount_parent_path):
        os.rmdir(mount_parent_path)
        if logger:
            logger.put(f"删除刮削错误文件：{mount_parent_path}")
        else:
            print(f"删除刮削错误文件夹：{mount_parent_path}")

    if nas_slink_file_path:
        slink_base_path = os.path.splitext(nas_slink_file_path)[0]
        if os.path.exists(nas_slink_file_path):
            os.remove(nas_slink_file_path)
            if logger:
                logger.put(f"删除刮削错误文件：{nas_slink_file_path}")
            else:
                print(f"删除刮削错误文件：{nas_slink_file_path}")
        nfo_path = f"{slink_base_path}.nfo"
        if os.path.exists(nfo_path):
            os.remove(nfo_path)
            if logger:
                logger.put(f"删除刮削错误文件：{nfo_path}")
            else:
                print(f"删除刮削错误文件：{nfo_path}")
        jpg_path = f"{slink_base_path}-thumb.jpg"
        if os.path.exists(jpg_path):
            os.remove(jpg_path)
            if logger:
                logger.put(f"删除刮削错误文件：{jpg_path}")
            else:
                print(f"删除刮削错误文件：{jpg_path}")
        slink_parent_path = os.path.dirname(nas_slink_file_path)
        if os.path.exists(slink_parent_path) and not os.listdir(slink_parent_path):
            os.rmdir(slink_parent_path)
            if logger:
                logger.put(f"删除刮削错误文件：{slink_parent_path}")
            else:
                print(f"删除刮削错误文件夹：{slink_parent_path}")

    if nas_strm_file_path:
        strm_base_path = os.path.splitext(nas_strm_file_path)[0]
        strm_path = f"{strm_base_path}.strm"
        if os.path.exists(strm_path):
            os.remove(strm_path)
            if logger:
                logger.put(f"删除刮削错误文件：{strm_path}")
            else:
                print(f"删除刮削错误文件：{strm_path}")
        nfo_path = f"{strm_base_path}.nfo"
        if os.path.exists(nfo_path):
            os.remove(nfo_path)
            if logger:
                logger.put(f"删除刮削错误文件：{nfo_path}")
            else:
                print(f"删除刮削错误文件：{nfo_path}")
        jpg_path = f"{strm_base_path}-thumb.jpg"
        if os.path.exists(jpg_path):
            os.remove(jpg_path)
            if logger:
                logger.put(f"删除刮削错误文件：{jpg_path}")
            else:
                print(f"删除刮削错误文件：{jpg_path}")
        strm_parent_path = os.path.dirname(nas_strm_file_path)
        if os.path.exists(strm_parent_path) and not os.listdir(strm_parent_path):
            os.rmdir(strm_parent_path)
            if logger:
                logger.put(f"删除刮削错误文件：{strm_parent_path}")
            else:
                print(f"删除刮削错误文件夹：{strm_parent_path}")