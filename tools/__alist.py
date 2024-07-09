#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import os
from alist import AlistClient
from __config import xd_alist_url, xd_alist_user, xd_alist_pwd, xd_alist_root_url


class Alist:
    def __init__(self, alist_url=xd_alist_url, alist_user=xd_alist_user, alist_pwd=xd_alist_pwd, alist_root_url=xd_alist_root_url):
        self.alist_url  = alist_url
        self.alist_user = alist_user
        self.alist_pwd  = alist_pwd
        self.alist_root_url = alist_root_url
        self.al = AlistClient(self.alist_url, self.alist_user, self.alist_pwd)
        self.fs = self.al.fs

    def ismount(self):
        root_folder  = os.path.split(self.alist_root_url)[1]
        self.fs.chdir(f"/{root_folder}")
        return True

