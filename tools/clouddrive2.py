#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - CD2 信息检测');
30 15 * * * clouddrive2.py
"""

import os
import sys
from clouddrive import CloudDriveClient
from CloudDrive_pb2 import AddOfflineFileRequest, FileRequest, OfflineFileListAllRequest

from _Config import xd_cd2_url, xd_cd2_usr, xd_cd2_pwd, xd_save_path, xd_account_id, cd2_cloud_root_path
from __notify_template import notify_template_col4
from __notifier import wecom_app
from __logger import Log
from __utils import format_size


class CD2:
    def __init__(self):
        self.cd2_url    = xd_cd2_url
        self.cd2_usr    = xd_cd2_usr
        self.cd2_pwd    = xd_cd2_pwd
        self.save_path  = xd_save_path
        self.root_path  = "/" + self.save_path.split("/")[1]
        self.cd2        = CloudDriveClient(self.cd2_url, self.cd2_usr, self.cd2_pwd)

        self.task    = self.cd2.upload_tasklist
        self.uplist  = self.task.list()
        self.fs      = self.cd2.fs
        self.mounted = self.cd2.GetMountPoints().mountPoints[0].isMounted

        self.upstat = {
            'Pause': '暂停中',
            'WaitingforPreprocessing': '等待中',
            'Preprocessing': '处理中',
            'Transfer': '进行中',
            'Inqueue': '排队中',
            'Finish': '结束中',
            'Error': '失败了',
            'FatalError': '出错了'
        }


    def file_count(self):
        info = self.cd2.GetFileDetailProperties(FileRequest(path = cd2_cloud_root_path))
        totalSize = format_size(info.totalSize)
        totalFileCount = info.totalFileCount
        totalFolderCount = info.totalFolderCount
        return totalSize, totalFileCount, totalFolderCount


    def cd2_info(self):
        """
        获取 CD2 相关信息。
        """
        info = {}
        if not self.mounted:
            print("CloudDrive2 掉挂载！退出脚本")
            send("CD2 掉挂载！", "如题")
            sys.exit(1)

        tbyte = 1099511627776
        space = self.cd2.GetSpaceInfo(FileRequest(path = self.root_path))
        total_space = space.totalSpace // tbyte
        used_space  = space.usedSpace // tbyte
        free_space  = space.freeSpace // tbyte

        update_info = self.cd2.HasUpdate()
        hasUpdate   = update_info.hasUpdate
        newVersion  = update_info.newVersion
        updateLog   = update_info.description

        run_info    = self.cd2.GetRuntimeInfo()
        nowVersion  = run_info.productVersion.split(" ")[0]

        if xd_account_id:
            ol_quota = self.cd2.ListAllOfflineFiles(OfflineFileListAllRequest(cloudName="115", cloudAccountId=xd_account_id)).status
        else:
            ol_quota = False

        if self.mounted:
            info['mount'] = "已挂载"
            info['used']  = f"{used_space} TB"
            info['free']  = f"{free_space} TB"
            info['nowVersion']  = nowVersion
            if ol_quota and xd_account_id:
                info['quota_free']  = ol_quota.quota
                info['quota_total'] = ol_quota.total
                info['quota_used']  = ol_quota.total - ol_quota.quota
            else:
                info['quota_used']  = "未指定账户"
                info['quota_free']  = "未指定账户"
        if hasUpdate:
            info['hasUpdate']  = "有新版本"
            info['newVersion'] = newVersion
            info['updateLog']  = updateLog
        else:
            info['hasUpdate']  = "无更新"
            info['newVersion'] = ""
            info['updateLog']  = ""
        
        return info

    def upload_list(self):
        count = self.cd2.GetUploadFileCount().fileCount
        task  = self.uplist
        pause, upload, error = 0, 0, 0
        if task:
            for t in task:
                state = t['status']
                if state == 'Pause':
                    pause += 1
                elif state == 'Error' or state == 'FatalError':
                    error += 1
                else:
                    upload += 1
        return count, pause, upload, error

    def file_exists_in_upload_list(self, file_path):
        """
        判断指定文件路径是否在cd2上传列表中，存在则返回上传状态。
        search_string: str
        return: bool, str
        """
        for dict_item in self.uplist:
            for key, value in dict_item.items():
                if file_path in str(value):
                    return True, dict_item['status']
        return False, None

    def file_exists_in_remote(self, nas_hlink_file_path, cd2_cloud_file_path):
        """
        判断指定文件名是否存在于云盘中。
        file_path: str
        return: bool
        """
        if os.path.exists(nas_hlink_file_path) and self.fs.exists(cd2_cloud_file_path):
            return True
        else:
            return False

    def pause_file_in_upload_list(self, cd2_cloud_file_path):
        """
        暂停文件上传。
        """
        self.uplist.pause(cd2_cloud_file_path)

    def resume_file_in_upload_list(self, cd2_cloud_file_path):
        """
        继续文件上传。
        """
        self.uplist.resume(cd2_cloud_file_path)

    def reload_file_in_upload_list(self, cd2_hlink_file_path, cd2_cloud_file_path):
        """
        重新上传文件。
        """
        self.fs.move(cd2_hlink_file_path, cd2_cloud_file_path)


if __name__ == "__main__":
    item = []
    try:
        cd   = CD2()
        ct   = cd.file_count()
        cd2  = cd.cd2_info()
        task = cd.upload_list()
    except Exception as e:
        print(f"CD2 异常，请检查：{e}")
        wecom_app("CD2 异常", f"请检查：{e}")
        sys.exit(1)

    logger = Log("clouddrive2-log", "clouddrive2").logger

    if cd2['hasUpdate'] == "有新版本":
        info2 = (cd2['hasUpdate'], cd2['newVersion'])
    else:
        info2 = (cd2['hasUpdate'], cd2['nowVersion'])

    item = [
        ("CD2", cd2['mount']),
        info2,
        ("已用空间", cd2['used']),
        ("可用空间", cd2['free']),
        ("已用配额", cd2['quota_used']),
        ("可用配额", cd2['quota_free']),
        ("上传总数", task[0]),
        ("暂停中", task[1]),
        ("上传中", task[2]),
        ("上传错误", task[3]),
        ("库大小", ct[0]),
        ("库文件数", ct[1]),
        ("库目录数", ct[2])
    ]

    if cd2['updateLog']:
        info_judge = True
        info_content = cd2['updateLog']
    else:
        info_judge = False
        info_content = ""

    logger.info(item)
    logger.info("\n")
    print(item)

    title = "CD2信息"
    items = item
    font_color = "white"

    border_color = "#AE8CC9"
    title_color = "#593B8B"
    head_color = "#593B8B"
    item_color_A = "#886ABC"
    item_color_B = "#684B99"
    content = notify_template_col4(title, items, font_color, border_color, title_color, head_color, item_color_A, item_color_B, info=info_judge, info_content=info_content, title1="项目", title2="数量(个)")
    digest = f"媒体库大小：{ct[0]}\n媒体库文件数：{ct[1]}\n媒体库文件夹数：{ct[2]}\n上传任务列表：{task[0]}\n暂停中任务：{task[1]}\n上传中任务：{task[2]}\n错误的任务：{task[3]}\n"

    wecom_app(title, content, digest)

