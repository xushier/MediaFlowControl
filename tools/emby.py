#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
new Env('小迪 - Emby 整库刷新');
30 12 * * * emby.py
"""


import requests
import json
import re

from typing import List, Optional, Union, Dict, Generator, Tuple, Any
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from requests import Session, Response
from pathlib import Path

import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

from __notifier import wecom_app
from __logger import Log
from _Config import emby_url, emby_token
logger = Log("emby-log", "emby").logger


class RequestUtils:
    _headers: dict = None
    _cookies: Union[str, dict] = None
    _proxies: dict = None
    _timeout: int = 20
    _session: Session = None

    def __init__(self,
                 headers: dict = None,
                 ua: str = None,
                 cookies: Union[str, dict] = None,
                 proxies: dict = None,
                 session: Session = None,
                 timeout: int = None,
                 referer: str = None,
                 content_type: str = None,
                 accept_type: str = None):
        if not content_type:
            content_type = "application/x-www-form-urlencoded; charset=UTF-8"
        if headers:
            self._headers = headers
        else:
            self._headers = {
                "User-Agent": ua,
                "Content-Type": content_type,
                "Accept": accept_type,
                "referer": referer
            }
        if cookies:
            if isinstance(cookies, str):
                self._cookies = self.cookie_parse(cookies)
            else:
                self._cookies = cookies
        if proxies:
            self._proxies = proxies
        if session:
            self._session = session
        if timeout:
            self._timeout = timeout

    def request(self, method: str, url: str, raise_exception: bool = False, **kwargs) -> Optional[Response]:
        """
        发起HTTP请求
        :param method: HTTP方法，如 get, post, put 等
        :param url: 请求的URL
        :param raise_exception: 是否在发生异常时抛出异常，否则默认拦截异常返回None
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: HTTP响应对象
        :raises: requests.exceptions.RequestException 仅raise_exception为True时会抛出
        """
        if self._session is None:
            req_method = requests.request
        else:
            req_method = self._session.request
        kwargs.setdefault("headers", self._headers)
        kwargs.setdefault("cookies", self._cookies)
        kwargs.setdefault("proxies", self._proxies)
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("verify", False)
        kwargs.setdefault("stream", False)
        try:
            return req_method(method, url, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.debug(f"请求失败: {e}")
            if raise_exception:
                raise
            return None

    def get(self, url: str, params: dict = None, **kwargs) -> Optional[str]:
        """
        发送GET请求
        :param url: 请求的URL
        :param params: 请求的参数
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: 响应的内容，若发生RequestException则返回None
        """
        response = self.request(method="get", url=url, params=params, **kwargs)
        return str(response.content, "utf-8") if response else None

    def post(self, url: str, data: Any = None, json: dict = None, **kwargs) -> Optional[Response]:
        """
        发送POST请求
        :param url: 请求的URL
        :param data: 请求的数据
        :param json: 请求的JSON数据
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: HTTP响应对象，若发生RequestException则返回None
        """
        if json is None:
            json = {}
        return self.request(method="post", url=url, data=data, json=json, **kwargs)

    def put(self, url: str, data: Any = None, **kwargs) -> Optional[Response]:
        """
        发送PUT请求
        :param url: 请求的URL
        :param data: 请求的数据
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: HTTP响应对象，若发生RequestException则返回None
        """
        return self.request(method="put", url=url, data=data, **kwargs)

    def get_res(self,
                url: str,
                params: dict = None,
                data: Any = None,
                json: dict = None,
                allow_redirects: bool = True,
                raise_exception: bool = False,
                **kwargs) -> Optional[Response]:
        """
        发送GET请求并返回响应对象
        :param url: 请求的URL
        :param params: 请求的参数
        :param data: 请求的数据
        :param json: 请求的JSON数据
        :param allow_redirects: 是否允许重定向
        :param raise_exception: 是否在发生异常时抛出异常，否则默认拦截异常返回None
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: HTTP响应对象，若发生RequestException则返回None
        :raises: requests.exceptions.RequestException 仅raise_exception为True时会抛出
        """
        return self.request(method="get",
                            url=url,
                            params=params,
                            data=data,
                            json=json,
                            allow_redirects=allow_redirects,
                            raise_exception=raise_exception,
                            **kwargs)

    def post_res(self,
                 url: str,
                 data: Any = None,
                 params: dict = None,
                 allow_redirects: bool = True,
                 files: Any = None,
                 json: dict = None,
                 raise_exception: bool = False,
                 **kwargs) -> Optional[Response]:
        """
        发送POST请求并返回响应对象
        :param url: 请求的URL
        :param data: 请求的数据
        :param params: 请求的参数
        :param allow_redirects: 是否允许重定向
        :param files: 请求的文件
        :param json: 请求的JSON数据
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :param raise_exception: 是否在发生异常时抛出异常，否则默认拦截异常返回None
        :return: HTTP响应对象，若发生RequestException则返回None
        :raises: requests.exceptions.RequestException 仅raise_exception为True时会抛出
        """
        return self.request(method="post",
                            url=url,
                            data=data,
                            params=params,
                            allow_redirects=allow_redirects,
                            files=files,
                            json=json,
                            raise_exception=raise_exception,
                            **kwargs)

    def put_res(self,
                url: str,
                data: Any = None,
                params: dict = None,
                allow_redirects: bool = True,
                files: Any = None,
                json: dict = None,
                raise_exception: bool = False,
                **kwargs) -> Optional[Response]:
        """
        发送PUT请求并返回响应对象
        :param url: 请求的URL
        :param data: 请求的数据
        :param params: 请求的参数
        :param allow_redirects: 是否允许重定向
        :param files: 请求的文件
        :param json: 请求的JSON数据
        :param raise_exception: 是否在发生异常时抛出异常，否则默认拦截异常返回None
        :param kwargs: 其他请求参数，如headers, cookies, proxies等
        :return: HTTP响应对象，若发生RequestException则返回None
        :raises: requests.exceptions.RequestException 仅raise_exception为True时会抛出
        """
        return self.request(method="put",
                            url=url,
                            data=data,
                            params=params,
                            allow_redirects=allow_redirects,
                            files=files,
                            json=json,
                            raise_exception=raise_exception,
                            **kwargs)

    @staticmethod
    def cookie_parse(cookies_str: str, array: bool = False) -> Union[list, dict]:
        """
        解析cookie，转化为字典或者数组
        :param cookies_str: cookie字符串
        :param array: 是否转化为数组
        :return: 字典或者数组
        """
        if not cookies_str:
            return {}
        cookie_dict = {}
        cookies = cookies_str.split(";")
        for cookie in cookies:
            cstr = cookie.split("=")
            if len(cstr) > 1:
                cookie_dict[cstr[0].strip()] = cstr[1].strip()
        if array:
            return [{"name": k, "value": v} for k, v in cookie_dict.items()]
        return cookie_dict

    @staticmethod
    def standardize_base_url(host: str) -> str:
        """
        标准化提供的主机地址，确保它以http://或https://开头，并且以斜杠(/)结尾
        :param host: 提供的主机地址字符串
        :return: 标准化后的主机地址字符串
        """
        if not host:
            return host
        if not host.endswith("/"):
            host += "/"
        if not host.startswith("http://") and not host.startswith("https://"):
            host = "http://" + host
        return host

    @staticmethod
    def adapt_request_url(host: str, endpoint: str) -> Optional[str]:
        """
        基于传入的host，适配请求的URL，确保每个请求的URL是完整的，用于在发送请求前自动处理和修正请求的URL。
        :param host: 主机头
        :param endpoint: 端点
        :return: 完整的请求URL字符串
        """
        if not host and not endpoint:
            return None
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        host = RequestUtils.standardize_base_url(host)
        return urljoin(host, endpoint) if host else endpoint

    @staticmethod
    def combine_url(host: str, path: Optional[str] = None, query: Optional[dict] = None) -> Optional[str]:
        """
        使用给定的主机头、路径和查询参数组合生成完整的URL。
        :param host: str, 主机头，例如 https://example.com
        :param path: Optional[str], 包含路径和可能已经包含的查询参数的端点，例如 /path/to/resource?current=1
        :param query: Optional[dict], 可选，额外的查询参数，例如 {"key": "value"}
        :return: str, 完整的请求URL字符串
        """
        try:
            # 如果路径为空，则默认为 '/'
            if path is None:
                path = '/'
            host = RequestUtils.standardize_base_url(host)
            # 使用 urljoin 合并 host 和 path
            url = urljoin(host, path)
            # 解析当前 URL 的组成部分
            url_parts = urlparse(url)
            # 解析已存在的查询参数，并与额外的查询参数合并
            query_params = parse_qs(url_parts.query)
            if query:
                for key, value in query.items():
                    query_params[key] = value

            # 重新构建查询字符串
            query_string = urlencode(query_params, doseq=True)
            # 构建完整的 URL
            new_url_parts = url_parts._replace(query=query_string)
            complete_url = urlunparse(new_url_parts)
            return str(complete_url)
        except Exception as e:
            logger.debug(f"Error combining URL: {e}")
            return None


class EmbyRefresh:
    def __init__(self, emby_url=emby_url, api_key=emby_token):
        if not emby_url.endswith('/'):
            emby_url += '/'
        self._host = emby_url
        self._apikey = api_key
        self.folders = self.get_emby_folders()

    def get_server_id(self) -> Optional[str]:
        """
        获得服务器信息
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sSystem/Info?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("Id")
            else:
                logger.error(f"媒体库刷新：System/Info 未获取到返回数据")
        except Exception as e:

            logger.error(f"媒体库刷新：连接System/Info出错：" + str(e))
        return None

    def get_user_count(self) -> int:
        """
        获得用户数量
        """
        if not self._host or not self._apikey:
            return 0
        req_url = "%semby/Users/Query?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("TotalRecordCount")
            else:
                logger.error(f"媒体库刷新：Users/Query 未获取到返回数据")
                return 0
        except Exception as e:
            logger.error(f"媒体库刷新：连接Users/Query出错：" + str(e))
            return 0

    def get_user(self, user_name: str = None) -> Optional[Union[str, int]]:
        """
        获得管理员用户
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sUsers?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                users = res.json()
                # 先查询是否有与当前用户名称匹配的
                if user_name:
                    for user in users:
                        if user.get("Name") == user_name:
                            return user.get("Id")
                # 查询管理员
                for user in users:
                    if user.get("Policy", {}).get("IsAdministrator"):
                        return user.get("Id")
            else:
                logger.error(f"媒体库刷新：Users 未获取到返回数据")
        except Exception as e:
            logger.error(f"媒体库刷新：连接Users出错：" + str(e))
        return None

    def get_emby_folders(self) -> List[dict]:
        """
        获取Emby媒体库路径列表
        """
        if not self._host or not self._apikey:
            return []
        req_url = "%semby/Library/SelectableMediaFolders?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json()
            else:
                logger.error(f"媒体库刷新：Library/SelectableMediaFolders 未获取到返回数据")
                return []
        except Exception as e:
            logger.error(f"媒体库刷新：连接Library/SelectableMediaFolders 出错：" + str(e))
            return []

    def get_emby_virtual_folders(self) -> List[dict]:
        """
        获取Emby媒体库所有路径列表（包含共享路径）
        """
        if not self._host or not self._apikey:
            return []
        req_url = "%semby/Library/VirtualFolders/Query?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            print(res.json())
            if res:
                library_items = res.json().get("Items")
                librarys = []
                for library_item in library_items:
                    library_name = library_item.get('Name')
                    pathInfos = library_item.get('LibraryOptions', {}).get('PathInfos')
                    library_paths = []
                    for path in pathInfos:
                        if path.get('NetworkPath'):
                            library_paths.append(path.get('NetworkPath'))
                        else:
                            library_paths.append(path.get('Path'))

                    if library_name and library_paths:
                        librarys.append({
                            'Name': library_name,
                            'Path': library_paths
                        })
                return librarys
            else:
                logger.error(f"媒体库刷新：Library/VirtualFolders/Query 未获取到返回数据")
                return []
        except Exception as e:
            logger.error(f"媒体库刷新：连接Library/VirtualFolders/Query 出错：" + str(e))
            return []

    def get_emby_movies_id_by_name(self,
                   name: str,
                   year: str = None,
                   tmdb_id: int = None) -> Optional[list]:
        """
        根据标题和年份，检查电影是否在Emby中存在，存在则返回列表
        :param name: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :param tmdb_id: tmdbid，可以为空
        :return: id 列表
        """
        if not self._host or not self._apikey:
            return None
        req_url = ("%semby/Items?"
                   "IncludeItemTypes=Movie"
                   "&Fields=ProductionYear"
                   "&StartIndex=0"
                   "&Recursive=true"
                   "&SearchTerm=%s"
                   "&Limit=10"
                   "&IncludeSearchTypes=false"
                   "&api_key=%s") % (
                      self._host, name, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    ret_movies = set()
                    for res_item in res_items:
                        item_tmdbid = res_item.get("ProviderIds", {}).get("Tmdb")
                        if tmdb_id and item_tmdbid:
                            if str(item_tmdbid) == str(tmdb_id):
                                ret_movies.add(res_item.get('Id'))
                        else:
                            if res_item.get('Name') == name and (not year or str(res_item.get('ProductionYear')) == str(year)):
                                ret_movies.add(res_item.get('Id'))
                    return ret_movies
        except Exception as e:
            logger.error(f"媒体库刷新：连接Items出错：" + str(e))
            return None
        return set()

    def get_emby_series_id_by_name(self, name: str, year: str) -> Optional[str]:
        """
        根据名称查询Emby中剧集的SeriesId
        :param name: 标题
        :param year: 年份
        :return: None 表示连不通，""表示未找到，找到返回ID
        """
        if not self._host or not self._apikey:
            return None
        req_url = ("%semby/Items?"
                   "IncludeItemTypes=Series"
                   "&Fields=ProductionYear"
                   "&StartIndex=0"
                   "&Recursive=true"
                   "&SearchTerm=%s"
                   "&Limit=10"
                   "&IncludeSearchTypes=false"
                   "&api_key=%s") % (
                      self._host, name, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    for res_item in res_items:
                        if res_item.get('Name') == name and (
                                not year or str(res_item.get('ProductionYear')) == str(year)):
                            return {res_item.get('Id'),}
        except Exception as e:
            logger.error(f"媒体库刷新：连接Items出错：" + str(e))
            return None
        return set()

    def get_emby_library_id_by_item(self, item: dict) -> Optional[str]:
        """
        根据媒体信息查询在哪个媒体库，返回要刷新的媒体库的ID
        :param item: {type, name, year, tmdbid, sort, link_path}
        """
        if not item['name'] or not item['year'] or not item['type']:
            return None
        if item['type'] == "Series":
            item_id = self.get_emby_series_id_by_name(item['name'], item['year'])
        else:
            item_id = self.get_emby_movies_id_by_name(item['name'], item['year'])
        if item_id:
            return item_id

        item_path = Path(item['link_path'])
        # 匹配子目录
        for folder in self.folders:
            for subfolder in folder.get("SubFolders"):
                try:
                    # 匹配子目录
                    subfolder_path = Path(subfolder.get("Path"))
                    if item_path.is_relative_to(subfolder_path):
                        return folder.get("Id")
                except Exception as err:
                    logger.debug(f"媒体库刷新：匹配子目录出错：{err}")
        # 如果找不到，只要路径中有分类目录名就命中
        for folder in self.folders:
            for subfolder in folder.get("SubFolders"):
                if subfolder.get("Path") and re.search(r"[/\\]%s" % item['sort'], subfolder.get("Path")):
                    return folder.get("Id")
        # 刷新根目录
        return "/"


    def refresh_emby_library_by_id(self, item_id: str) -> bool:
        """
        通知 Emby 刷新指定 ID 的媒体库
        """
        if not self._host or not self._apikey:
            return False
        req_url = "%semby/Items/%s/Refresh?Recursive=true&api_key=%s" % (self._host, item_id, self._apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
            else:
                logger.info(f"媒体库刷新：刷新媒体库对象 {item_id} 失败，无法连接Emby！")
        except Exception as e:
            logger.error(f"媒体库刷新：连接Items/Id/Refresh出错：" + str(e))
            return False
        return False


    def refresh_root_library(self) -> bool:
        """
        通知 Emby 刷新整个媒体库
        """
        if not self._host or not self._apikey:
            return False
        req_url = "%semby/Library/Refresh?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
            else:
                logger.info(f"媒体库刷新：刷新媒体库失败，无法连接Emby！")
        except Exception as e:
            logger.error(f"媒体库刷新：连接Library/Refresh出错：" + str(e))
            return False
        return False


    def refresh_library_by_items(self, items: list) -> bool:
        """
        按类型、名称、年份来刷新媒体库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        if not items:
            return False

        logger.info(f"媒体库刷新：开始刷新Emby媒体库...")
        library_ids = set()
        for item in items:
            library_id = self.get_emby_library_id_by_item(item)
            logger.info(f"媒体库刷新：{item['name']} - {item['year']} - {item['sort']} - {library_id} - {item['link_path']}")
            print(f"媒体库刷新：{item['name']} - {item['year']} - {item['sort']} - ID:{library_id} - {item['link_path']}")
            if library_id:
                library_ids.update(library_id)

        if "/" in library_ids:
            logger.info(f"媒体库刷新：有项目在库中不存在且未识别到路径，刷新整库。")
            print(f"媒体库刷新：有项目在库中不存在且未识别到路径，刷新整库。")
            return self.refresh_root_library()
        for library_id in library_ids:
            if library_id != "/":
                return self.refresh_emby_library_by_id(library_id)
        logger.info(f"媒体库刷新：Emby媒体库刷新完成")



if __name__ == "__main__":
    e = EmbyRefresh()
    r = e.refresh_root_library()
    if r:
        print("Emby 整库刷新成功！")
        wecom_app("Emby 刷新", f"\nEmby 整库刷新成功！")
    else:
        print("Emby 整库刷新失败！")
        wecom_app("Emby 刷新", f"\nEmby 整库刷新失败！")