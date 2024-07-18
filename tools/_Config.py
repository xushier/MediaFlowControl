#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
Created By Xiaodi
小迪同学:
https://github.com/xushier/HD-Icons
https://space.bilibili.com/32313260
2024/02/12
"""



# 使用前请安装必须的 Python 模块。需要的模块名在文件 requirements 里。到依赖管理安装即可。然后修改以下配置。

############################################## 必填项 ################################################

# QB。一条龙任务、QB 清理任务的依赖项。
xd_qb_delete_error = True    # 删除下载中的错误的种子（站点已删除的种子）
xd_qb_delete = True          # 删除影视一条龙标记的可删的种子
xd_qb_url = "http://"
xd_qb_usr = ""
xd_qb_pwd = ""

# Emby 信息。用于刷新 Emby 库。
emby_url   = "http://"
emby_token = ""
# Emby 刷新路径。可选值：strm、slink
link_emby_refresh = "strm"

# CD2。CD2 信息。save_path 为 CD2 内的使用的 115 网盘的根路径。account_id 为对应账户的昵称。
xd_cd2_url    = "http://"
xd_cd2_usr    = ""
xd_cd2_pwd    = ""
xd_save_path  = "/115(xxx)"
xd_account_id = "xxx"

# Alist。环境检测任务的依赖项。
# /d/ 后为 Alist 挂载路径，该路径后需要是和硬链结构一样的、包含电影/电视剧/动漫这样的文件夹。
xd_alist_root_url  = "https://xxxx.xxx.xxx/d/媒体库挂载名字"
xd_alist_url  = "http://"
xd_alist_user = ""
xd_alist_pwd  = ""

# Path。各任务依赖项。
nas_qbitt_root_path = "/mnt/cache/Download/qb"    # QB下载根路径

nas_hlink_root_path = "/mnt/cache/Download/hlink"    # 硬链接根路径
nas_mount_root_path = "/mnt/cache/115/115(xxx)/媒体库"    # 挂载媒体库根路径
cd2_hlink_root_path = "/Download/hlink"     # 硬链接根路径
cd2_cloud_root_path = "/115(xxx)/媒体库"    # CD2 内媒体库根路径
nas_slink_root_path = "/mnt/cache/Link/slink"    # 软链接媒体库根路径
nas_strm_root_path  = "/mnt/cache/Link/strm"     # STRM 媒体库根路径

############################################## 必填项 ################################################


############################################## 自定义项 ##############################################

# 以下为一条龙依赖项。

# 仅通知有数量的项目。默认关闭。
notify_only_new = False

# 硬链接影视文件夹所在层级。
hlink_media_depth  = 7
# QB 影视文件夹所在层级
qbitt_media_depth  = 6

# 首传递增时间。若首传，递增的等待时长。
increment_hours = 4

# 秒传重试次数。预处理指定的次数后还是首传则开启传输。
upload_try_times = 5

# 秒传重试时间。预处理指定的次数后还是首传则开启传输。
upload_try_hours = 100

# 文件权限。链接文件和元数据文件的权限。
xd_uid = 1000
xd_gid = 100
xd_mod = 0o755

# 全量链接模式。全量链接任务的依赖项。可选值：strm、slink、both。
full_link_mode = "both"
# 全量链接时，链接进度的通知时间间隔。单位为秒，默认一个小时。
notify_interval = 3600

# 部分链接模式。一条龙任务内单文件的链接模式，值同上。
part_link_mode = "both"

# 指定发布组做种时长，单位：天
qb_domain_keyword = {
    "chdbits": 6,
    "btschool": 5
}

# QB 失效种子 Tracker 信息关键词
qb_error_tracker_keyword = [
    "exist", "anned", "register", "音轨", "压制", "重新上传", "Dupe", "Nuked", "出错"
]

# 名称匹配正则
movies_pattern = r'^(.*?)\s*\((\d{4})\)\s*(?:\{|\[)tmdb(?:id)?(?:-|=)(\d+)(?:\}|\])'
series_pattern = r'^(.*?)\s*\((\d{4})\)\s*(?:\{|\[)tmdb(?:id)?(?:-|=)(\d+)(?:\}|\])'
chinese_pattern = r'^(.*?) ?(S\d+E\d+|(?:\{|\[)tmdb(?:id)?(?:-|=)\d+(?:\}|\]))'

# 链接文件扩展名
media_ext = [
    "mp4", "mkv", "m2ts", "iso", "wmv", "3gp", "ts", "flv", 
    "rm", "rmvb", "avi", "mov", "vob", "m4v", "f4v", "webm", 
    "mpg", "mpeg", "asf", "asx", "dat"
    ]

# 下载文件扩展名
mdata_ext = [
    "nfo", "jpg", "jpeg", "png", "gif", "webp", "txt", "md5", 
    "xml", "srt", "ass", "sup", "mp3", "aac", "doc", "docx", 
    "pdf", "ssa", "sub", "vtt", "smi"
    ]

# CD2 上传按发布组的等待时长，单位：小时，若压制组不在以下列表，则以文件大小为基准
group_slice = [
    "CMCT", "ADE", "FRDS", "CHD", "WiKi", 
    "beAst", "PTer", "OurTV", "HHWEB"
    ]

group_wait  = [
    8, 5, 5, 24, 10, 
    12, 15, 6, 8
    ]

# CD2 上传按文件大小的等待时长，单位：小时
size_slice = [
    0, 1073741824, 5*1073741824, 10*1073741824, 20*1073741824, 
    30*1073741824, 50*1073741824, 70*1073741824, 300*1073741824, 
    900*1073741824, 10000*1073741824
    ]

size_wait  = [
    1, 3, 6, 10, 
    15, 22, 30, 42, 
    66, 100
    ]

############################################## 自定义项 ##############################################
