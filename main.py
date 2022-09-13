import datetime
import json
import os
import sys
import time

import requests
import urllib3
from colorama import Fore, Back, Style
from git import Git
from git import Repo
from tqdm import tqdm


# 定义函数

# 加载配置
def load_config() -> None:
    global config
    if os.path.isfile("config.json"):
        config_file = open("config.json", "r", encoding='utf-8')
        config = json.load(config_file)
        config_file.close()
    else:
        config = {
            "ssl_vertify": False,
            "storge_dir": "sync_data/",
            "github_proxy": "https://github.com/",
            "github_file_download_proxy": "https://github.com/",
            "github_api_proxy": "https://api.github.com/",
            "clone_mirror": "https://github.com/",
            "timeout": 2
        }
        save_config()


# 保存配置
def save_config() -> None:
    global config
    config_file = open("config.json", "w", encoding='utf-8')
    json.dump(config, config_file)
    config_file.close()


# 清空控制台
def clear_console() -> None:
    f_handler = open('practice.log', 'w', encoding='utf-8')
    old_stdout = sys.stdout
    sys.stdout = f_handler
    os.system('cls')
    sys.stdout = old_stdout


def load_sync_info() -> None:
    global sync_info
    if os.path.isfile(config["storge_dir"] + "sync_info.json"):
        sync_info_file = open(config["storge_dir"] + "sync_info.json", "r", encoding='utf-8')
        sync_info = json.load(sync_info_file)
        sync_info_file.close()
    else:
        sync_info = {}
        save_sync_info()


def save_sync_info() -> None:
    global sync_info
    if os.path.exists(config["storge_dir"]) is False:
        os.mkdir(config["storge_dir"])
    sync_info_file = open(config["storge_dir"] + "sync_info.json", "w", encoding='utf-8')
    json.dump(sync_info, sync_info_file)
    sync_info_file.close()


# 检查登录
def check_login(username: str, token: str) -> dict:
    try:
        req = requests.post(url=config["github_api_proxy"] + "user",
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
                                'Content-type': 'application/json'
                            },
                            auth=(username, token),
                            verify=config["ssl_vertify"],
                            timeout=60)
    except ConnectionError or TimeoutError:
        return {
            "err": -3
        }
    if req.status_code == 200:
        return {
            "err": 0,
            "status_code": req.status_code,
            "response": req.text
        }
    elif req.status_code == 401:
        return {
            "err": 1,
            "status_code": req.status_code,
            "response": req.text
        }
    elif req.status_code == 429:
        return {
            "err": -1,
            "status_code": req.status_code,
            "reset_time": req.headers["x-ratelimit-reset"],
            "response": req.text
        }
    else:
        return {
            "err": -2,
            "status_code": req.status_code,
            "response": req.text
        }


# 检查仓库是否存在
def check_repo(repo: str) -> dict:
    try:
        req = requests.get(url=config["github_proxy"] + repo,
                           headers={
                               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
                           },
                           timeout=60,
                           verify=config["ssl_vertify"])
    except ConnectionError or TimeoutError:
        return {
            "err": -3
        }
    if req.status_code == 200:
        return {
            "err": 0
        }
    elif req.status_code == 429:
        return {
            "err": -1,
            "reset_time": req.headers["x-ratelimit-reset"],
        }
    elif req.status_code == 404:
        return {
            "err": 1,
        }
    else:
        return {
            "err": -2,
            "status_code": req.status_code,
            "response": req.text
        }


# 清空控制台并打印标题
def print_title() -> None:
    clear_console()
    print("{0:#^100}".format(" Github-repo-sync ") +
          "\n\n" +
          "{0:^100}".format("github.com/xvzhenduo/Github-repo-sync") +
          "\n\n" +
          "{0:#^100}".format("") +
          "\n")


# 加载仓库列表
def load_repo_list() -> None:
    global repo_list
    if not os.path.exists("repo_list.json"):
        repo_list = []
        repo_list_file = open("repo_list.json", "w", encoding='utf-8')
        json.dump(repo_list, repo_list_file)
        repo_list_file.close()
    else:
        repo_list_file = open("repo_list.json", "r", encoding='utf-8')
        repo_list = json.load(repo_list_file)
        repo_list_file.close()


# 保存仓库列表
def save_repo_list() -> None:
    global repo_list
    repo_list_file = open("repo_list.json", "w", encoding='utf-8')
    json.dump(repo_list, repo_list_file)
    repo_list_file.close()


# 文件下载
def download(url: str, title: str, path: str) -> dict:
    # header
    download_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
    }
    resp = requests.get(url, stream=True, headers=download_headers, verify=config["ssl_vertify"])
    total = int(resp.headers.get('content-length', 0))
    with open(path, 'wb') as file1, tqdm(
            desc=title,
            total=total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file1.write(data)
            bar.update(size)
    return {
        "err": 0,
        "original": resp.headers.get('content-length', 0),
        "actual": os.stat(path).st_size
    }


# 同步releases
def sync_release_page(repo: str, sync_prereleases: bool, sync_zipball: bool, sync_tarball: bool,
                      sync_release_note: bool, rename_rule: str, add_time: int, page: int) -> dict:
    print(Fore.CYAN + "正在初始化储存目录..." + Style.RESET_ALL)
    global sync_info
    releases = {}
    if repo not in sync_info:
        sync_info[repo] = {}
    if "releases" not in sync_info[repo]:
        sync_info[repo]["releases"] = {}
    if not os.path.exists(config["storge_dir"] + repo.replace("/", " ")):
        os.mkdir(config["storge_dir"] + repo.replace("/", " "))
    print(Fore.CYAN + "正在获取Release列表..." + Style.RESET_ALL)
    if "username" in config and "token" in config:
        auth = (config["username"], config["token"])
    else:
        auth = ()
    if ("ETag" + str(page)) in sync_info[repo]:
        Etag = sync_info[repo]["ETag" + str(page)]
    else:
        Etag = ""
    try:
        req = requests.get(
            url=config["github_api_proxy"] + "repos/" + repo + "/releases?per_page=100&page=" + str(page),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
                'Content-type': 'application/json',
                "If-None-Match": Etag
            },
            auth=auth,
            verify=config["ssl_vertify"],
            timeout=60)
    except ConnectionError or TimeoutError:
        return {
            "err": -3
        }
    print(Fore.CYAN + "正在解析数据..." + Style.RESET_ALL)
    if req.status_code == 404:
        return {
            "err": 1
        }
    elif req.status_code == 429:
        return {
            "err": -1,
            "reset_time": req.headers["x-ratelimit-reset"],
        }
    elif req.status_code == 304:
        print("304")
        cache_file = open(config["storge_dir"] + "cache" + "/" + repo.replace("/", " ") + str(page) + ".json", "r",
                          encoding="utf-8")
        releases = json.load(cache_file)
        cache_file.close()
    elif req.status_code != 200 and req.status_code != 403:
        return {
            "err": -2,
            "status_code": req.status_code,
            "response": req.text
        }
    # 缓存结果
    if req.status_code == 200:
        print(200)
        if not os.path.exists(config["storge_dir"] + "cache"):
            os.mkdir(config["storge_dir"] + "cache")
        cache_file = open(config["storge_dir"] + "cache" + "/" + repo.replace("/", " ") + str(page) + ".json", "w",
                          encoding='utf-8')
        cache_file.write(req.text)
        cache_file.close()
        sync_info[repo]["ETag" + str(page)] = req.headers["Etag"]
        save_sync_info()
        releases = json.loads(req.text)
    if "block" in releases:
        return {
            "err": 2,
            "response": req.text
        }
    for j in range(0, len(releases)):
        print("\nRelease ID: " + str(releases[j]["id"]) + "(p" + str(page) + ": " + str(j + 1) + "/" + str(
            len(releases)) + ")")
        # 根据rename rule生成release名字
        date = datetime.datetime.strptime(releases[j]["published_at"], "%Y-%m-%dT%H:%M:%SZ")
        release = {
            "id": str(releases[j]["id"]),
            "name": str(releases[j]["name"]),
            "tag_name": str(releases[j]["tag_name"]),
            "if_prerelease_bool": str(releases[j]["prerelease"]),
            "year": str(date.strftime("%Y")),
            "month": str(date.strftime("%m")),
            "day": str(date.strftime("%d")),
            "h": str(date.strftime("%H")),
            "m": str(date.strftime("%M")),
            "s": str(date.strftime("%S"))
        }
        if releases[j]["prerelease"] is True:
            release["if_prerelease_str"] = "Release"
        else:
            release["if_prerelease_str"] = "PreRelease"
        release_name = rename_rule.replace("**id**", release["id"])
        release_name = release_name.replace("**name**", release["name"])
        release_name = release_name.replace("**tag_name**", release["tag_name"])
        release_name = release_name.replace("**if_prerelease_bool**", release["if_prerelease_bool"])
        release_name = release_name.replace("**if_prerelease_str**", release["if_prerelease_str"])
        release_name = release_name.replace("**year**", release["year"])
        release_name = release_name.replace("**month**", release["month"])
        release_name = release_name.replace("**day**", release["day"])
        release_name = release_name.replace("**h**", release["h"])
        release_name = release_name.replace("**m**", release["m"])
        release_name = release_name.replace("**s**", release["s"])
        release_name = release_name.replace("\\", "_")
        release_name = release_name.replace("/", "")
        release_name = release_name.replace(":", "_")
        release_name = release_name.replace("*", "_")
        release_name = release_name.replace("?", "_")
        release_name = release_name.replace("\"", "_")
        release_name = release_name.replace("<", "_")
        release_name = release_name.replace(">", "_")
        release_name = release_name.replace("|", "_")
        print("Release name: " + release_name + "(" + repo + ")")
        print(Fore.CYAN + "正在初始化下载..." + Style.RESET_ALL)
        # 初始化
        if str(releases[j]["id"]) not in sync_info[repo]["releases"]:
            sync_info[repo]["releases"][str(releases[j]["id"])] = {
                "assets": False,
                "release_note": False,
                "zipball": False,
                "tarball": False,
                "name": release_name
            }
        if sync_info[repo]["releases"][str(releases[j]["id"])]["name"] != release_name and os.path.exists(
                config["storge_dir"] + repo.replace("/", " ") + sync_info[repo]["releases"][str(releases[j]["id"])][
                    "name"]):
            os.rename(
                config["storge_dir"] + repo.replace("/", " ") + sync_info[repo]["releases"][str(releases[j]["id"])][
                    "name"], config["storge_dir"] + repo.replace("/", " ") + release_name)
        if sync_info[repo]["releases"][str(releases[j]["id"])]["name"] != release_name and os.path.exists(
                config["storge_dir"] + repo.replace("/", " ") + "/" +
                sync_info[repo]["releases"][str(releases[j]["id"])][
                    "name"] + ".md"):
            os.rename(config["storge_dir"] + repo.replace("/", " ") + "/" +
                      sync_info[repo]["releases"][str(releases[j]["id"])]["name"] + ".md",
                      config["storge_dir"] + repo.replace("/", " ") + "/" + release_name + ".md")
        if releases[j]["prerelease"] is True and sync_prereleases is False:
            continue
        if time.mktime(
                datetime.datetime.strptime(releases[j]["published_at"], "%Y-%m-%dT%H:%M:%SZ").timetuple()) < add_time:
            continue
        if not os.path.exists(config["storge_dir"] + repo.replace("/", " ") + "/" + release_name):
            os.mkdir(config["storge_dir"] + repo.replace("/", " ") + "/" + release_name)
        # 下载二进制文件
        print(Fore.CYAN + "正在下载Release二进制文件..." + Style.RESET_ALL)
        if sync_info[repo]["releases"][str(releases[j]["id"])]["assets"] is False:
            for k in range(0, len(releases[j]["assets"])):
                url = releases[j]["assets"][k]["browser_download_url"]
                url = url.replace("https://github.com/", config["github_file_download_proxy"])
                fname = releases[j]["assets"][k]["name"]
                if len(fname) <= 30:
                    title = fname
                else:
                    title = fname[0:13] + "..." + fname[len(fname) - 14:]
                download_result = False
                for m in range(0, 3):
                    # noinspection PyBroadException
                    try:
                        dl_result = download(url, title + "(" + str(m) + ")",
                                             config["storge_dir"] + repo.replace("/",
                                                                                 " ") + "/" + release_name + "/" + fname)
                    except Exception:
                        continue
                    if str(dl_result["original"]) != str(dl_result["actual"]):
                        continue
                    download_result = True
                    break
                if download_result is False:
                    return {
                        "err": -3
                    }
                time.sleep(config["timeout"])
            sync_info[repo]["releases"][str(releases[j]["id"])]["assets"] = True
            save_sync_info()
        # 保存Release Note
        if sync_release_note is True and sync_info[repo]["releases"][str(releases[j]["id"])]["release_note"] is False:
            release_note_file = open(config["storge_dir"] + repo.replace("/", " ") + "/" + release_name + ".md", "w",
                                     encoding='utf-8')
            if releases[j]["body"] is not None:
                release_note_file.write(releases[j]["body"])
            release_note_file.close()
            sync_info[repo]["releases"][str(releases[j]["id"])]["release_note"] = True
            save_sync_info()
        # 下载zip归档
        print(Fore.CYAN + "正在下载Release zip归档..." + Style.RESET_ALL)
        if sync_zipball is True and sync_info[repo]["releases"][str(releases[j]["id"])]["zipball"] is False:
            url = config["github_file_download_proxy"] + repo + "/archive/refs/tags/" + str(
                releases[j]["tag_name"]) + ".zip"
            title = str(releases[j]["tag_name"]) + ".zip"
            fname = str(releases[j]["tag_name"]) + ".zip"
            download_result = False
            for m in range(0, 3):
                # noinspection PyBroadException
                try:
                    download(url, title + "(" + str(m) + ")",
                             config["storge_dir"] + repo.replace("/", " ") + "/" + release_name + "/" + fname)
                except Exception:
                    continue
                download_result = True
                break
            if download_result is False:
                return {
                    "err": -3
                }
            sync_info[repo]["releases"][str(releases[j]["id"])]["zipball"] = True
            save_sync_info()
        # 下载tar归档
        print(Fore.CYAN + "正在下载Release tar归档..." + Style.RESET_ALL)
        if sync_tarball is True and sync_info[repo]["releases"][str(releases[j]["id"])]["tarball"] is False:
            url = config["github_file_download_proxy"] + repo + "/archive/refs/tags/" + str(
                releases[j]["tag_name"]) + ".tar.gz"
            title = str(releases[j]["tag_name"]) + ".tar.gz"
            fname = str(releases[j]["tag_name"]) + ".tar.gz"
            download_result = False
            for m in range(0, 3):
                # noinspection PyBroadException
                try:
                    download(url, title + "(" + str(m) + ")",
                             config["storge_dir"] + repo.replace("/", " ") + "/" + release_name + "/" + fname)
                except Exception:
                    continue
                download_result = True
                break
            if download_result is False:
                return {
                    "err": -3
                }
            sync_info[repo]["releases"][str(releases[j]["id"])]["tarball"] = True
            save_sync_info()
    if len(releases) < 100:
        if_end_page = True
    else:
        if_end_page = False
    return {
        "err": 0,
        "end": if_end_page
    }


def sync_repo(repo: str) -> dict:
    sync_repo_num = 0
    for j in range(0, len(repo_list)):
        if repo_list[j]["repo"] == repo:
            sync_repo_num = j
            break
    page_num = 1
    print("\n\nRepo: " + repo)
    if repo_list[sync_repo_num]["sync_releases"] is True:
        while True:
            result = sync_release_page(repo,
                                       repo_list[sync_repo_num]["sync_prereleases"],
                                       repo_list[sync_repo_num]["sync_zipball"],
                                       repo_list[sync_repo_num]["sync_tarball"],
                                       repo_list[sync_repo_num]["sync_release_note"],
                                       repo_list[sync_repo_num]["release_rename_rule"],
                                       repo_list[sync_repo_num]["ignore_releases_before"],
                                       page_num)
            if result["err"] == 0 and result["end"] is True:
                break
            elif result["err"] != 0:
                return result
            page_num = page_num + 1
    if repo_list[sync_repo_num]["sync_source_code"] is True:
        print(Fore.CYAN + "正在拉取源码..." + Style.RESET_ALL)
        sync_source_code_return = sync_source_code(repo)
        if sync_source_code_return["err"] != 0:
            return sync_source_code_return
        print(Fore.GREEN + "完成" + Style.RESET_ALL)
    return {
        "err": 0
    }


def sync_source_code(repo: str) -> dict:
    print(Fore.CYAN + "正在初始化储存目录..." + Style.RESET_ALL)
    if not os.path.exists(config["storge_dir"] + repo.replace("/", " ")):
        os.mkdir(config["storge_dir"] + repo.replace("/", " "))
    if not os.path.exists(config["storge_dir"] + repo.replace("/", " ") + "/" + "source code"):
        os.mkdir(config["storge_dir"] + repo.replace("/", " ") + "/" + "source code")
    # noinspection PyBroadException
    try:
        repo_object = Repo(os.path.abspath(config["storge_dir"] + repo.replace("/", " ") + "/" + "source code"))
    except BaseException:
        git = Git(os.path.abspath(config["storge_dir"] + repo.replace("/", " ") + "/" + "source code"))
        git.init()
        repo_object = Repo(os.path.abspath(config["storge_dir"] + repo.replace("/", " ") + "/" + "source code"))
    g = repo_object.git
    for j in range(0, 3):
        try:
            g.pull(config["clone_mirror"] + repo + ".git")
        except Exception as e:
            print(e)
            print("retrying(" + str(j + 1) + ")...")
            continue
        return {
            "err": 0
        }
    return {
        "err": 3
    }


# 初始化
print(Fore.CYAN + "正在初始化..." + Style.RESET_ALL)
# 初始化全局变量
config = {}
repo_list = []
input_value = {}
sync_info = {}
load_config()
load_repo_list()
load_sync_info()
# 忽略SSL证书错误
urllib3.disable_warnings()
# 代码开始
while True:
    print_title()
    if "username" not in config:
        login_text = "登录(未登录)"
    else:
        login_text = "重新登录(已登录:" + config["username"] + ")"
    choice = input("0: 退出\n"
                   "1: " + login_text + "\n" +
                   "2: 添加新的repo到同步列表\n" +
                   "3: 立即同步所有储存库\n"
                   "4: 修改储存库同步设置\n"
                   "5: 从同步列表中删除指定的储存库\n" +
                   "6: 设置\n"
                   "7: 关于\n" +
                   "请输入数字:")
    if choice == "0":
        exit()
    elif choice == "1":
        # 登录
        print_title()
        print(Fore.YELLOW +
              "在获取token时请将「Expiration」设置为「No expiration」以防止token过期\n"
              "请务必至少给予token「user」权限以便验证token是否正确\n" +
              Style.RESET_ALL +
              Fore.CYAN +
              "如何获取OAuth token:\n"
              "https://docs.github.com/cn/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-token\n" +
              Style.RESET_ALL)
        input_username = input("用户名: ")
        input_token = input("OAuth token: ")
        login_result = check_login(input_username, input_token)
        if login_result["err"] == 0:
            config["username"] = input_username
            config["token"] = input_token
            save_config()
            print_title()
            print("\r" + Fore.GREEN + "登录成功!" + Style.RESET_ALL)
            print(login_result["response"])
        elif login_result["err"] == 1:
            print(Fore.RED + Back.LIGHTBLUE_EX +
                  "用户名或OAuth token错误.\n" +
                  Style.RESET_ALL)
            print("如果你认为这是由Bug引起的,请到issue反馈并附带以下内容:\n" + "Status code: " + str(
                login_result["status_code"]) + "\nResponse: " + login_result["response"])
        elif login_result["err"] == -1:
            print(Fore.RED + Back.LIGHTBLUE_EX +
                  "你的请求过于频繁触发了Github API的Rate limit(未登录单个IP地址不得超过60次/小时，已登录单个用户不得超过5000次/小时).\n"
                  "Rate limit将于" + time.localtime(login_result["reset_time"]) + "重置,请在之后重试" +
                  Style.RESET_ALL)
            print("如果你认为这是由Bug引起的,请到issue反馈并附带以下内容:\n" + "Status code: " + str(
                login_result["status_code"]) + "\nResponse: " + login_result["response"])
        elif login_result["err"] == -2:
            print(Fore.RED + Back.LIGHTBLUE_EX +
                  "未知错误.\n" +
                  Style.RESET_ALL)
            print(
                "请到issue反馈并附带以下内容:\n" + "Status code: " + str(login_result["status_code"]) + "\nResponse: " +
                login_result["response"])
        elif login_result["err"] == -3:
            print(
                Fore.RED + Back.LIGHTBLUE_EX + "无法连接到GitHub API(api.github.com),请检查网络连接并重试.\n" + Style.RESET_ALL)
        os.system("pause")
    elif choice == "2":
        # 添加要同步的repo
        new_repo = {}
        while True:
            print_title()
            new_repo["repo"] = input("请输入仓库主页完整url或者「owner/repo」格式(仅支持GitHub):\n")
            new_repo["repo"] = new_repo["repo"].replace("https://github.com/", "")
            if new_repo["repo"][-1:] == "/":
                new_repo["repo"] = new_repo["repo"][0:-1]
            is_in_list = False
            for i in range(0, len(repo_list)):
                if new_repo["repo"] == repo_list[i]["repo"]:
                    is_in_list = True
                    break
            if is_in_list:
                print(Fore.RED + Back.LIGHTBLUE_EX + "该仓库已在同步列表,请勿重复添加." + Style.RESET_ALL)
                os.system("pause")
            else:
                check_repo_result = check_repo(new_repo["repo"])
                if check_repo_result["err"] == 0:
                    break
                elif check_repo_result["err"] == 1:
                    print(Fore.RED + Back.LIGHTBLUE_EX +
                          "该储存库不存在或不是公开储存库.\n" +
                          Style.RESET_ALL)
                    os.system("pause")
                elif check_repo_result["err"] == -1:
                    print(Fore.RED + Back.LIGHTBLUE_EX +
                          "你的请求过于频繁触发了Github API的Rate limit(未登录单个IP地址不得超过60次/小时，已登录单个用户不得超过5000次/小时).\n"
                          "Rate limit将于" + time.localtime(check_repo_result["reset_time"]) + "重置,请在之后重试" +
                          Style.RESET_ALL)
                    print("如果你认为这是由Bug引起的,请到issue反馈并附带以下内容:\n" + "Status code: " + str(
                        check_repo_result["status_code"]) + "\nResponse: " + check_repo_result["response"])
                    os.system("pause")
                elif check_repo_result["err"] == -3:
                    print(
                        Fore.RED + Back.LIGHTBLUE_EX + "无法连接到GitHub(github.com),请检查网络连接并重试.\n" + Style.RESET_ALL)
                    os.system("pause")
                elif check_repo_result["err"] == -2:
                    print(Fore.RED + Back.LIGHTBLUE_EX +
                          "未知错误.\n" +
                          Style.RESET_ALL)
                    print(
                        "请到issue反馈并附带以下内容:\n" + "Status code: " + str(
                            check_repo_result["status_code"]) + "\nResponse: " + check_repo_result["response"])
                    os.system("pause")
                else:
                    print(json.dumps(check_repo_result))
                    os.system("pause")
        while True:
            print_title()
            input_new_repo_if_sync_releases = input("是否同步Release(「True」/「False」):\n")
            if input_new_repo_if_sync_releases.lower() in ["t", "true"]:
                new_repo["sync_releases"] = True
                break
            elif input_new_repo_if_sync_releases.lower() in ["f", "false"]:
                new_repo["sync_releases"] = False
                break
            else:
                print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                os.system("pause")
        if new_repo["sync_releases"] is True:
            while True:
                print_title()
                input_new_repo_if_sync_prereleases = input("是否同步PreRelease(「True」/「False」):\n")
                if input_new_repo_if_sync_prereleases in ["t", "true"]:
                    new_repo["sync_prereleases"] = True
                    break
                elif input_new_repo_if_sync_prereleases in ["f", "false"]:
                    new_repo["sync_prereleases"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_zipball = input("是否同步Release的zip归档(「True」/「False」):\n")
                if input_new_repo_if_sync_zipball in ["t", "true"]:
                    new_repo["sync_zipball"] = True
                    break
                elif input_new_repo_if_sync_zipball in ["f", "false"]:
                    new_repo["sync_zipball"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_tarball = input("是否同步Release的tar归档(「True」/「False」):\n")
                if input_new_repo_if_sync_tarball in ["t", "true"]:
                    new_repo["sync_tarball"] = True
                    break
                elif input_new_repo_if_sync_tarball in ["f", "false"]:
                    new_repo["sync_tarball"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_release_note = input("是否同步Release note(「True」/「False」):\n")
                if input_new_repo_if_sync_release_note in ["t", "true"]:
                    new_repo["sync_release_note"] = True
                    break
                elif input_new_repo_if_sync_release_note in ["f", "false"]:
                    new_repo["sync_release_note"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_ignore_release_before = input("是否忽略在此之前发布的Release(「True」/「False」):\n")
                if input_new_repo_if_ignore_release_before in ["t", "true"]:
                    input_new_repo_if_ignore_release_before = True
                    break
                elif input_new_repo_if_ignore_release_before in ["f", "false"]:
                    input_new_repo_if_ignore_release_before = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            if input_new_repo_if_ignore_release_before is True:
                new_repo["ignore_releases_before"] = int(time.time())
            else:
                new_repo["ignore_releases_before"] = 0
            while True:
                print_title()
                new_repo["release_rename_rule"] = input("支持以下魔术变量\n"
                                                        "**id**                     release的id\n"
                                                        "**name**                   release的名称\n"
                                                        "**tag_name**               release的tag名称\n"
                                                        "**if_prerelease_bool**     是否是prerelease(True/False)\n"
                                                        "**if_prerelease_str**      是否是prerelease(PreRelease/Release)\n"
                                                        "**year**                   发布年的份\n"
                                                        "**month**                  发布的月份\n"
                                                        "**day**                    发布时间是当月的第几天\n"
                                                        "**h**                      发布的小时\n"
                                                        "**m**                      发布的分钟\n"
                                                        "**s**                      发布的秒数\n\n"
                                                        "Release的命名方式:\n")
                # noinspection PyRedeclaration
                temp = new_repo["release_rename_rule"].replace("**id**", "")
                temp = temp.replace("**name**", "")
                temp = temp.replace("**tag_name**", "")
                temp = temp.replace("**if_prerelease_bool**", "")
                temp = temp.replace("**if_prerelease_str**", "")
                temp = temp.replace("**year**", "")
                temp = temp.replace("**month**", "")
                temp = temp.replace("**day**", "")
                temp = temp.replace("**h**", "")
                temp = temp.replace("**m**", "")
                temp = temp.replace("**s**", "")
                if "\\" in temp or "/" in temp or ":" in temp or "*" in temp or "<" in temp or ">" in temp or "|" in temp:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,不得包含\\/:*<>|)." + Style.RESET_ALL)
                    os.system("pause")
                else:
                    break
        while True:
            print_title()
            input_new_repo_if_sync_source_code = input(
                "是否同步源码(即通过「git pull」拉取,所以启用此功能需要安装git并将其添加到环境变量)(「True」/「False」):\n")
            if input_new_repo_if_sync_source_code in ["t", "true"]:
                new_repo["sync_source_code"] = True
                break
            elif input_new_repo_if_sync_source_code in ["f", "false"]:
                new_repo["sync_source_code"] = False
                break
            else:
                print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                os.system("pause")
        repo_list.append(new_repo)
        save_repo_list()
        print_title()
        print("\r" + Fore.GREEN + "储存库已添加到同步列表!\n" + Style.RESET_ALL + json.dumps(new_repo))
        os.system("pause")
    elif choice == "3":
        print_title()
        for i in range(0, len(repo_list)):
            sync_repo_return = sync_repo(repo_list[i]["repo"])
            if sync_repo_return["err"] != 0:
                print(Fore.RED + "\n\n\n同步出现错误" + Style.RESET_ALL)
                os.system("paue")
                continue
        print(Fore.GREEN + "\n\n\n全部同步完成" + Style.RESET_ALL)
        os.system("pause")
    elif choice == "4":
        print_title()
        new_repo = {"repo": input("请输入仓库主页完整url或者「owner/repo」格式(仅支持GitHub):\n")}
        new_repo["repo"] = new_repo["repo"].replace("https://github.com/", "")
        if new_repo["repo"][-1:] == "/":
            new_repo["repo"] = new_repo["repo"][0:-1]
        is_in_list = False
        repo_num = 0
        for i in range(0, len(repo_list)):
            if new_repo["repo"] == repo_list[i]["repo"]:
                is_in_list = True
                repo_num = i
                break
        if not is_in_list:
            print(Fore.RED + Back.LIGHTBLUE_EX + "该仓库不在同步列表,请先添加." + Style.RESET_ALL)
            os.system("pause")

        while True:
            print_title()
            input_new_repo_if_sync_releases = input("是否同步Release(「True」/「False」):\n")
            if input_new_repo_if_sync_releases.lower() in ["t", "true"]:
                new_repo["sync_releases"] = True
                break
            elif input_new_repo_if_sync_releases.lower() in ["f", "false"]:
                new_repo["sync_releases"] = False
                break
            else:
                print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                os.system("pause")
        if new_repo["sync_releases"] is True:
            while True:
                print_title()
                input_new_repo_if_sync_prereleases = input("是否同步PreRelease(「True」/「False」):\n")
                if input_new_repo_if_sync_prereleases in ["t", "true"]:
                    new_repo["sync_prereleases"] = True
                    break
                elif input_new_repo_if_sync_prereleases in ["f", "false"]:
                    new_repo["sync_prereleases"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_zipball = input("是否同步Release的zip归档(「True」/「False」):\n")
                if input_new_repo_if_sync_zipball in ["t", "true"]:
                    new_repo["sync_zipball"] = True
                    break
                elif input_new_repo_if_sync_zipball in ["f", "false"]:
                    new_repo["sync_zipball"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_tarball = input("是否同步Release的tar归档(「True」/「False」):\n")
                if input_new_repo_if_sync_tarball in ["t", "true"]:
                    new_repo["sync_tarball"] = True
                    break
                elif input_new_repo_if_sync_tarball in ["f", "false"]:
                    new_repo["sync_tarball"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_sync_release_note = input("是否同步Release note(「True」/「False」):\n")
                if input_new_repo_if_sync_release_note in ["t", "true"]:
                    new_repo["sync_release_note"] = True
                    break
                elif input_new_repo_if_sync_release_note in ["f", "false"]:
                    new_repo["sync_release_note"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            while True:
                print_title()
                input_new_repo_if_ignore_release_before = input("是否忽略在此之前发布的Release(「True」/「False」):\n")
                if input_new_repo_if_ignore_release_before in ["t", "true"]:
                    input_new_repo_if_ignore_release_before = True
                    break
                elif input_new_repo_if_ignore_release_before in ["f", "false"]:
                    input_new_repo_if_ignore_release_before = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            if input_new_repo_if_ignore_release_before is True:
                new_repo["ignore_releases_before"] = int(time.time())
            else:
                new_repo["ignore_releases_before"] = 0
            while True:
                print_title()
                new_repo["release_rename_rule"] = input("支持以下魔术变量\n"
                                                        "**id**                     release的id\n"
                                                        "**name**                   release的名称\n"
                                                        "**tag_name**               release的tag名称\n"
                                                        "**if_prerelease_bool**     是否是prerelease(True/False)\n"
                                                        "**if_prerelease_str**      是否是prerelease(PreRelease/Release)\n"
                                                        "**year**                   发布年的份\n"
                                                        "**month**                  发布的月份\n"
                                                        "**day**                    发布时间是当月的第几天\n"
                                                        "**h**                      发布的小时\n"
                                                        "**m**                      发布的分钟\n"
                                                        "**s**                      发布的秒数\n\n"
                                                        "Release的命名方式:\n")
                # noinspection PyRedeclaration
                temp = new_repo["release_rename_rule"].replace("**id**", "")
                temp = temp.replace("**name**", "")
                temp = temp.replace("**tag_name**", "")
                temp = temp.replace("**if_prerelease_bool**", "")
                temp = temp.replace("**if_prerelease_str**", "")
                temp = temp.replace("**year**", "")
                temp = temp.replace("**month**", "")
                temp = temp.replace("**day**", "")
                temp = temp.replace("**h**", "")
                temp = temp.replace("**m**", "")
                temp = temp.replace("**s**", "")
                if "\\" in temp or "/" in temp or ":" in temp or "*" in temp or "<" in temp or ">" in temp or "|" in temp:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,不得包含\\/:*<>|)." + Style.RESET_ALL)
                    os.system("pause")
                else:
                    break
        while True:
            print_title()
            input_new_repo_if_sync_source_code = input(
                "是否同步源码(即通过「git pull」拉取,所以启用此功能需要安装git并将其添加到环境变量)(「True」/「False」):\n")
            if input_new_repo_if_sync_source_code in ["t", "true"]:
                new_repo["sync_source_code"] = True
                break
            elif input_new_repo_if_sync_source_code in ["f", "false"]:
                new_repo["sync_source_code"] = False
                break
            else:
                print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                os.system("pause")
        repo_list.pop(repo_num)
        repo_list.append(new_repo)
        save_repo_list()
        print_title()
        print("\r" + Fore.GREEN + "设置已保存!\n" + Style.RESET_ALL + json.dumps(new_repo))
        os.system("pause")

    elif choice == "5":
        print_title()
        # ToDo 删除储存库
    elif choice == "6":
        print_title()
        choice = input("0: 返回\n"
                       "1: 是否启用ssl vertify: " + str(config["ssl_vertify"]) + "\n" +
                       "   (如果要使用如Watt Toolkit等DNS代理或不支持https的GitHub加速网址，请务必关闭)\n"
                       "2: 同步数据储存位置: " + config["storge_dir"] + "\n" +
                       "3: GitHub镜像地址: " + config["github_proxy"] + "\n" +
                       "4: GitHub镜像地址(用于下载文件): " + config["github_file_download_proxy"] + "\n" +
                       "5: GitHub镜像地址(用于拉取储存库): " + config["clone_mirror"] + "\n" +
                       "6: GitHub API镜像地址: " + config["github_api_proxy"] + "\n" +
                       "7: 下载Release间的时间间隔(秒): " + str(config["timeout"]) + "\n" +
                       "请输入数字: ")
        if choice == "0":
            continue
        elif choice == "1":
            while True:
                print_title()
                input_new_repo_if_sync_release_note = input("是否启用ssl vertify(「True」/「False」):\n")
                if input_new_repo_if_sync_release_note in ["t", "true"]:
                    config["ssl_vertify"] = True
                    break
                elif input_new_repo_if_sync_release_note in ["f", "false"]:
                    config["ssl_vertify"] = False
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入「True」/「False」)." + Style.RESET_ALL)
                    os.system("pause")
            save_config()
        elif choice == "2":
            while True:
                print_title()
                print("支持绝对路径&相对路径(相对于main.py),请以\"/\"结尾.\n"
                      "注意请填写存在的目录(需要提前建好填写的文件夹)")
                storge_dir = input("同步数据储存位置: ")
                storge_dir = storge_dir.replace("\\", "/")
                if storge_dir[-1:] != "/":
                    storge_dir = storge_dir + "/"
                if os.path.exists(storge_dir):
                    config["storge_dir"] = storge_dir
                    save_config()
                    load_sync_info()
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请输入存在的目录)." + Style.RESET_ALL)
                    os.system("pause")
        elif choice == "3":
            while True:
                print_title()
                print("在你更改设置时我们不会对你的地址的可用性(是否可以连接)或者使用限制做验证，请保证地址可用\n"
                      "镜像地址的调用方式为直接将url中的https://github.com/替换为你填写的地址,部分加速下载服务使用「网址 + Github的链接」的方式，你可以直接填写「https://链接/https://github.com/」"
                      "请注意部分镜像站存在rate limit，且有仓库最大大小限制(如hub.fastgit.xyz限制仓库大小<2GB)"
                      "链接需要以「http://」或者「https://」开头")
                github_proxy = input("GitHub镜像地址: ")
                if github_proxy[-1:] != "/":
                    github_proxy = github_proxy + "/"
                if github_proxy[0:8] == "https://" or github_proxy[0:7] == "http://":
                    config["github_proxy"] = github_proxy
                    save_config()
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请重新输入." + Style.RESET_ALL)
                    os.system("pause")
        elif choice == "4":
            while True:
                print_title()
                print("在你更改设置时我们不会对你的地址的可用性(是否可以连接)或者使用限制做验证，请保证地址可用\n"
                      "镜像地址的调用方式为直接将url中的https://github.com/替换为你填写的地址,部分加速下载服务使用「网址 + Github的链接」的方式，你可以直接填写「https://链接/https://github.com/」"
                      "请注意部分镜像站存在rate limit，且有仓库最大大小限制(如hub.fastgit.xyz限制仓库大小<2GB)"
                      "链接需要以「http://」或者「https://」开头")
                github_file_download_proxy = input("GitHub镜像地址(用于下载文件): ")
                if github_file_download_proxy[-1:] != "/":
                    github_file_download_proxy = github_file_download_proxy + "/"
                if github_file_download_proxy[0:8] == "https://" or github_file_download_proxy[0:7] == "http://":
                    config["github_file_download_proxy"] = github_file_download_proxy
                    save_config()
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请重新输入." + Style.RESET_ALL)
                    os.system("pause")
        elif choice == "5":
            while True:
                print_title()
                print("在你更改设置时我们不会对你的地址的可用性(是否可以连接)或者使用限制做验证，请保证地址可用\n"
                      "镜像地址的调用方式为直接将url中的https://github.com/替换为你填写的地址,部分加速下载服务使用「网址 + Github的链接」的方式，你可以直接填写「https://链接/https://github.com/」"
                      "请注意部分镜像站存在rate limit，且有仓库最大大小限制(如hub.fastgit.xyz限制仓库大小<2GB)"
                      "链接需要以「http://」或者「https://」开头")
                clone_mirror = input("GitHub镜像地址(用于拉取储存库): ")
                if clone_mirror[-1:] != "/":
                    clone_mirror = clone_mirror + "/"
                if clone_mirror[0:8] == "https://" or clone_mirror[0:7] == "http://":
                    config["clone_mirror"] = clone_mirror
                    save_config()
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请重新输入." + Style.RESET_ALL)
                    os.system("pause")
        elif choice == "6":
            while True:
                print_title()
                print("在你更改设置时我们不会对你的地址的可用性(是否可以连接)或者使用限制做验证，请保证地址可用\n"
                      "镜像地址的调用方式为直接将url中的https://github.com/替换为你填写的地址,部分加速下载服务使用「网址 + Github的链接」的方式，你可以直接填写「https://链接/https://github.com/」"
                      "请注意部分镜像站存在rate limit，且有仓库最大大小限制(如hub.fastgit.xyz限制仓库大小<2GB)"
                      "链接需要以「http://」或者「https://」开头")
                github_api_proxy = input("GitHub API镜像地址: ")
                if github_api_proxy[-1:] != "/":
                    github_api_proxy = github_api_proxy + "/"
                if github_api_proxy[0:8] == "https://" or github_api_proxy[0:7] == "http://":
                    config["github_api_proxy"] = github_api_proxy
                    save_config()
                    break
                else:
                    print(Fore.RED + Back.LIGHTBLUE_EX + "无效的输入,请重新输入." + Style.RESET_ALL)
                    os.system("pause")
        elif choice == "7":
            while True:
                print_title()
                timeout = input("下载Release间的时间间隔(秒): ")
                try:
                    timeout = int(timeout)
                except TypeError:
                    continue
                config["timeout"] = timeout
                save_config()
                break
        elif choice == "7":
            print_title()
            print("本项目以MIT协议发布于 github.com/xvzhenduo/Github-repo-sync\n"
                  "如有问题请题issue或者发邮件至hq750303@163.com")
            os.system("pause")
