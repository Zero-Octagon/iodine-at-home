import os
import ssl
import sys
import yaml
import httpx
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

versionPath = Path("./VERSION")
dotenvPath = Path("./settings/.env")

with open(versionPath, "r", encoding="UTF-8") as versionFile:
    VERSION = versionFile.read()

# 尝试打开配置文件
env_status = load_dotenv(dotenvPath)

if env_status == False:
    print("配置文件丢失，已创建一个空白文件。")
    with open(dotenvPath, "w") as cfgFile:
        cfgFile.write("")
    print(
        f"空白文件新建成功，你应该将 .env.example 内所有内容复制进 .env 并修改后运行程序。"
    )
    sys.exit(0)

# 读取配置文件信息
settings = dotenv_values(dotenvPath)

LANGUAGE = str(settings.get("LANGUAGE", "zh_cn"))
HOST = str(settings.get("HOST", "0.0.0.0"))
PORT = int(settings.get("PORT", 8080))
ACCESS_LOG_CONTENT = settings.get("ACCESS_LOG", "true").lower()

MDB_HOST = str(settings.get("MDB_HOST", ""))
MDB_USERNAME = str(settings.get("MDB_USERNAME", ""))
MDB_PASSWORD = str(settings.get("MDB_PASSWORD", ""))

STORAGE_TYPE = str(settings.get("STORAGE_TYPE", "local"))

ALIST_URL = str(settings.get("ALIST_URL", ""))
ALIST_USERNAME = str(settings.get("ALIST_USERNAME", ""))
ALIST_PASSWORD = str(settings.get("ALIST_PASSWORD", ""))

JWT_SECRET = str(settings.get("JWT_SECRET", "114514"))
TOKEN = str(settings.get("TOKEN", "123456"))

GIT_REPOSITORY = settings.get(
    "GIT_REPOSITORY_LIST", "https://github.com/Mxmilu666/bangbang93HUB"
)
GIT_REPOSITORY_LIST = GIT_REPOSITORY.split(",")

CERTIFICATES_STATUS = settings.get("CERTIFICATES", "False").lower()

if ACCESS_LOG_CONTENT == "true":
    ACCESS_LOG = True
elif ACCESS_LOG_CONTENT == "false":
    ACCESS_LOG = False
else:
    print(f"ACCESS_LOG 的值不正确，请修改为 true 或 false。")
    sys.exit(1)

if CERTIFICATES_STATUS == "true":
    CERT_PATH = Path(settings.get("CERT_PATH", ""))
    KEY_PATH = Path(settings.get("KEY_PATH", ""))
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)

# # 获取证书与密钥相关内容
# if CERTIFICATES_STATUS == True:
#     with open(CERT_PATH, "r", encoding="utf-8") as cert_file:
#         CERT = cert_file.read().strip()

#     with open(KEY_PATH, "r", encoding="utf-8") as key_file:
#         KEY = cert_file.read().strip()
