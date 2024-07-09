#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
Created By Xiaodi
小迪同学:
https://github.com/xushier/HD-Icons
https://space.bilibili.com/32313260
2024/02/12
"""

import os
import logging
import logging.handlers
from datetime import datetime, timedelta



class Log:
    def __init__(self, log_folder, log_name, log_size=3, log_count=5):
        log_path     = log_folder
        max_log_size = log_size * 1048576
        back_count   = log_count
        os.makedirs(log_path, exist_ok=True)
        self.log_file = f"{log_path}/{str(datetime.now().date())}.log"
        handler       = logging.handlers.RotatingFileHandler(self.log_file, maxBytes=max_log_size, backupCount=back_count)
        formatter     = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger = logging.getLogger(log_name)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        self.logger = logger