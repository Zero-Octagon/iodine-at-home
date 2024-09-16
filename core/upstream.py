import os
import json
import aiohttp
import hashlib
import asyncio
from pathlib import Path
import core.datafile as datafile
from core.types import FileObject
from core.logger import logger


# 从 GitHub 仓库获取最新版本，并下载到 files 目录下
class git_repository:
    # 接收 url、directory 等参数
    def __init__(self, url, directory: Path):
        self.url = url
        self.directory = directory

    # 下载文件
    def fetch(self) -> None:
        logger.tinfo("upstream.info.fetch_git_repo", url=self.url)
        # 检查目录是否存在，不存在则创建
        try:
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
                # 下载文件
                result = os.system(f"git clone {self.url} {self.directory}")
            else:
                current_dir = os.getcwd()
                os.chdir(self.directory)
                result = os.system("git pull")
                os.chdir(current_dir)
            logger.tinfo("upstream.info.fetch_git_repo_success", url=self.url)
            return result
        except Exception as e:
            ...  # 记录异常信息
            logger.error(e)
            return -1

    def get_file_list(self) -> list[FileObject]:
        return git_repository.iterate_directory(self.directory, self.directory)

    @staticmethod
    def iterate_directory(root: str, subroot: str) -> list[FileObject]:
        file_list = []
        for current, directories, files in os.walk(subroot):

            directories[:] = [d for d in directories if not d.startswith(".")]

            for directory in directories:
                file_list += git_repository.iterate_directory(
                    root, os.path.join(current, directory)
                )
            for file in files:
                path = os.path.join(current, file)[len(root) :]
                path = path.replace("\\", "/")
                path = path if path.startswith("/") else ("/" + path)
                file = FileObject(os.path.join(current, file))
                file.path = path
                file_list.append(file)
        return file_list


class mcim:
    def __init__(self):
        asyncio.run(self.get_filelist())
    async def get_filelist(self):
        url = "https://mod.mcimirror.top/file_cdn/list"
        all_data = []
        last_id = 0

        filesizes = 0

        async with aiohttp.ClientSession() as client:
            while True:
                params = {
                    "last_id": last_id,
                    "page_size": 9999
                }
                response = await client.get(url, params=params, timeout=1000)
                data = await response.json()

                if not data:
                    break

                all_data.extend(data)
                last_id = data[-1]["_id"]  # 假设每条数据都有一个"id"字段
                for i in data:
                    filesizes += i["size"]
            client.close()

        await datafile.write_json_to_file('mcim.json', all_data)
        logger.info(f"数据总数 {len(all_data)}")  # 打印获取到的数据总数
        logger.info(f'占用空间 {filesizes}')


# def main():
#     upstream = Upstream('https://github.com/Mxmilu666/bangbang93HUB', 'files')
#     upstream.fetch()
#     files = upstream.get_file_list()
#     for file in files:
#         print(file)

# if __name__ == '__main__':
#     main()
