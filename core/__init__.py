import os
import re
import json
import hmac
import time
import asyncio
import hashlib
from pathlib import Path
from random import choice, choices, random
from datetime import datetime, timezone

import aiohttp
from aiohttp import web
import aiohttp.log
from aiohttp.web import Request
from aiohttp_cors import setup, ResourceOptions

import core.const as const
import core.utils as utils
from core.logger import logger
import core.datafile as datafile
from core.database import database
import core.command as command
import core.settings as settings
from core.upstream import git_repository, mcim
from core.types import Cluster, FileObject

import logging
import socketio

import aiosqlite

from apscheduler.schedulers.background import BackgroundScheduler

## 初始化变量
now_bytes = 0
now_bytes = 0
online_cluster_list = []
online_cluster_list_json = []

routes = web.RouteTableDef()
app = web.Application()

sio = socketio.AsyncServer(async_mode="aiohttp")
sio.attach(app)

# 允许所有跨域请求
cors = setup(
    app,
    defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        ),
        "/socket.io/": ResourceOptions(  # 明确指定 socket.io 不使用 CORS
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
            max_age=3600,
        ),
    },
)

# IODINE @ HOME
## 定时执行
scheduler = BackgroundScheduler()
scheduler.add_job(
    utils.save_calculate_filelist, "interval", minutes=5, id="refresh_filelist"
)


## 每天凌晨重置数据
def reset_data():
    data = datafile.read_json_from_file_noasync("daily.json")
    data["lastModified"] = int(time.time())
    data["bytes"] = 0
    data["hits"] = 0
    data["nodes"] = {}
    logger.info("已重置数据。")
    datafile.write_json_to_file_noasync("daily.json", data)


scheduler.add_job(reset_data, "cron", day_of_week="mon-sun", hour=0, minute=0)


## 新建节点
@routes.get("/api/node/create")
async def fetch_create_cluster(
    request: Request,
    token: str | None,
    name: str | None,
    secret: str | None,
    bandwidth: str | None,
):
    if token != settings.TOKEN:
        return web.Response("没有权限", 401)
    return await database.create_cluster(name, secret, bandwidth)


## 删除节点
@routes.get("/api/node/delete")
async def fetch_delete_cluster(request: Request, token: str | None, id: str | None):
    if token != settings.TOKEN:
        return web.Response("没有权限", 401)
    return await database.delete_cluster(id)


## 以 JSON 格式返回主控状态
@routes.get("/api/status")
async def fetch_status(request: Request):
    return web.json_response(
        {
            "name": "iodine-at-home",
            "author": "ZeroNexis",
            "version": settings.VERSION,
            "currentNodes": len(online_cluster_list),
            "online_node_list": online_cluster_list,
        }
    )


## 以 JSON 格式返回排名
@routes.get("/api/rank")
async def fetch_version(request: Request):
    data = await datafile.read_json_from_file("daily.json")
    result = utils.multi_node_privacy(
        utils.combine_and_sort_clusters(
            await database.get_clusters(), data["nodes"], online_cluster_list
        )
    )
    return web.json_response(result)


# OpenBMCLAPI 部分
## 下发 challenge（有效时间: 5 分钟）
@routes.get("/openbmclapi-agent/challenge")
async def fetch_challenge(request: Request):
    clusterId = request.query.get("clusterId", "")
    cluster = Cluster(clusterId)
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist and cluster.isBanned == 0:
        return web.json_response(
            {
                "challenge": utils.encode_jwt(
                    {
                        "cluster_id": clusterId,
                        "cluster_secret": cluster.secret,
                        "exp": int(time.time()) + 1000 * 60 * 5,
                    }
                )
            }
        )
    elif cluster_is_exist and cluster.isBanned == True:
        return web.Response(
            text=f"节点被封禁，原因: {cluster.ban_reason}",
            status=403,
        )
    else:
        return web.Response(text="未找到节点", status=404)


## 下发令牌（有效日期: 1 天）
@routes.post("/openbmclapi-agent/token")
async def fetch_token(request: Request):
    content_type = request.content_type
    if "application/json" in content_type:
        data = await request.json()
    elif (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        data = await request.post()
    else:
        return web.Response(status=400, text="Unsupported media type")
    clusterId = data.get("clusterId")
    challenge = data.get("challenge")
    signature = data.get("signature")
    cluster = Cluster(clusterId)
    cluster_is_exist = await cluster.initialize()
    h = hmac.new(cluster.secret.encode("utf-8"), digestmod=hashlib.sha256)
    h.update(challenge.encode())
    if (
        cluster_is_exist
        and utils.decode_jwt(challenge)["cluster_id"] == clusterId
        and utils.decode_jwt(challenge)["exp"] > int(time.time())
    ):
        if str(h.hexdigest()) == signature:
            return web.json_response(
                {
                    "token": utils.encode_jwt(
                        {"cluster_id": clusterId, "cluster_secret": cluster.secret}
                    ),
                    "ttl": 1000 * 60 * 60 * 24,
                }
            )
        else:
            return web.Response(text="没有授权", status=401)
    else:
        return web.Response(text="没有授权", status=401)


## 建议同步参数
@routes.get("/openbmclapi/configuration")
def fetch_configuration(request: Request):
    return web.json_response({"sync": {"source": "center", "concurrency": 1024}})


## 文件列表
@routes.get("/openbmclapi/files")
async def fetch_filesList(request: Request):
    # TODO: 获取文件列表
    filelist = await datafile.read_filelist_from_cache("filelist.avro")
    return web.Response(body=filelist, content_type="application/octet-stream")


## 普通下载（从主控或节点拉取文件）
@routes.get("/files/{path:.+}")
async def download_file(request: Request):
    path = request.match_info["path"]
    if Path(f"./files/{path}").is_file() == False:
        return web.HTTPNotFound()
    if Path(f"./files/{path}").is_dir == True:
        return web.HTTPNotFound()
    if len(online_cluster_list) == 0:
        return web.FileResponse(f"./files/{path}")
    else:
        cluster = choice(online_cluster_list_json)
        file = FileObject(f"./files/{path}")
        url = utils.get_url(
            cluster["host"],
            cluster["port"],
            f"/download/{file.hash}",
            utils.get_sign(file.hash, cluster["secret"]),
        )
        return web.HTTPFound(url)


## 应急同步（从主控拉取文件）
@routes.get("/openbmclapi/download/{hash}")
async def download_file_from_ctrl(request: Request, hash: str):
    try:
        filelist = await datafile.read_json_from_file("filelist.json")
        path = filelist[hash]["path"]
        return web.FileResponse(Path(f".{path}"))
    except ValueError:
        return web.Response(text="未找到文件", status=404)


## 举报
@routes.post("/openbmclapi/report")
async def fetch_report(request: Request):
    content_type = request.content_type
    if "application/json" in content_type:
        data = await request.json()
    elif (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        data = await request.post()
    else:
        return web.Response(
            status=400, text="不支持的媒体类型"
        )
    urls = data.get("urls")
    error = data.get("error")
    logger.warning(f"收到举报, 重定向记录: {urls}，错误信息: {error}")
    return web.Response(status=200)


## 节点端连接时
@sio.on("connect")
async def on_connect(sid, *args):
    token_pattern = r"'token': '(.*?)'"
    token = re.search(token_pattern, str(args)).group(1)
    if token.isspace():
        sio.disconnect(sid)
        logger.debug(f"客户端 {sid} 连接失败（原因: 未提交 token 令牌）")
    cluster = Cluster(utils.decode_jwt(token)["cluster_id"])
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist and cluster.secret == utils.decode_jwt(token)["cluster_secret"]:
        await sio.save_session(
            sid,
            {
                "cluster_id": cluster.id,
                "cluster_secret": cluster.secret,
                "token": token,
            },
        )
        logger.debug(f"客户端 {sid} 连接成功（CLUSTER_ID: {cluster.id}）")
        await sio.emit(
            "message",
            "欢迎使用 iodine@home，本项目已在 https://github.com/ZeroNexis/iodine-at-home 开源，期待您的贡献与支持。",
            sid,
        )
    else:
        sio.disconnect(sid)
        logger.debug(f"客户端 {sid} 连接失败（原因: 认证出错）")


## 当节点端退出连接时
@sio.on("disconnect")
async def on_disconnect(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist and cluster.json() in online_cluster_list_json:
        online_cluster_list_json.remove(cluster.json())
        logger.debug(f"{sid} 异常断开连接，已从在线列表中删除")
    else:
        logger.debug(f"客户端 {sid} 断开了连接")


## 节点启动时
@sio.on("enable")
async def on_cluster_enable(sid, data, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False:
        return [{"message": "错误: 节点似乎并不存在，请检查配置文件"}]
    if str(cluster.id) in online_cluster_list == True:
        return [{"message": "错误: 节点已经在线，请检查配置文件"}]
    host = data.get("host", session.get("ip"))
    await cluster.edit(
        host=host,
        port=data["port"],
        version=data["version"],
        runtime=data["flavor"]["runtime"],
    )
    if data["version"] != const.latest_version:
        await sio.emit(
            "message",
            f"当前版本已过时，推荐升级到 v{const.latest_version} 或以上版本。",
            sid,
        )
    time.sleep(1)
    bandwidth = await utils.measure_cluster(10, cluster.json())
    if bandwidth[0] and bandwidth[1] >= 10:
        online_cluster_list.append(cluster.id)
        online_cluster_list_json.append(cluster.json())
        logger.debug(f"节点 {cluster.id} 上线（测量带宽: {bandwidth[1]}）")
        if cluster.trust < 0:
            await sio.emit("message", "节点信任度过低，请保持稳定在线。", sid)
        return [None, True]
    elif bandwidth[0] and bandwidth[1] < 10:
        logger.debug(f"{cluster.id} 测速未通过（测量带宽: {bandwidth[1]}）")
        return [
            {"message": f"错误: 测量带宽小于 10Mbps，（测量得 {bandwidth[1]}），请重试尝试上线"}
        ]
    else:
        logger.debug(f"{cluster.id} 测速未通过（错误: {bandwidth[1]}）")
        return [
            {
                "message": f"错误: {bandwidth[1]}"
            }
        ]


## 节点保活时
@sio.on("keep-alive")
async def on_cluster_keep_alive(sid, data, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False or cluster.id not in online_cluster_list:
        return [None, False]
    daily = await datafile.read_json_from_file("daily.json")
    try:
        daily["nodes"][cluster.id]["hits"] += data["hits"]
        daily["nodes"][cluster.id]["bytes"] += data["bytes"]
    except KeyError:
        daily["nodes"][cluster.id] = {"hits": data["hits"], "bytes": data["bytes"]}
    await datafile.write_json_to_file("daily.json", daily)
    logger.debug(
        f"节点 {cluster.id} 保活（请求数: {data["hits"]} 次 | 请求数据量: {utils.hum_convert(data['bytes'])}）"
    )
    return [None, datetime.now(timezone.utc).isoformat()]


@sio.on("disable")  ## 节点禁用时
async def on_cluster_disable(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False:
        logger.debug("某节点尝试禁用集群失败（原因: 节点不存在）")
    else:
        try:
            online_cluster_list.remove(cluster.id)
            online_cluster_list_json.remove(cluster.json())
            logger.debug(f"节点 {cluster.id} 禁用集群")
        except ValueError:
            logger.debug(f"节点 {cluster.id} 尝试禁用集群失败（原因: 节点没有启用）")
    return [None, True]


# 运行主程序
def init():
    logger.info("正在进行运行前检查...")
    # 检查文件夹是否存在
    dataFolder = Path("./data/")
    dataFolder.mkdir(parents=True, exist_ok=True)
    if settings.STORAGE_TYPE == "local":
        fileFolder = Path("./files/")
        fileFolder.mkdir(parents=True, exist_ok=True)
    if settings.STORAGE_TYPE == "alist":
        from core.alist import alist
    # 检查每日数据
    dailyFile = Path("./files/daily.json")
    if dailyFile.exists == False:
        reset_data()
    daily = datafile.read_json_from_file_noasync("daily.json")
    if utils.are_the_same_day(int(time.time()), daily["lastModified"]) == False:
        reset_data()
    # 同步上游 git 仓库
    for i in settings.GIT_REPOSITORY_LIST:
        name = utils.extract_repo_name(i)
        git_repository(i, f"./files/{name}").fetch()
        scheduler.add_job(
            git_repository(i, f"./files/{name}").fetch,
            "interval",
            minutes=5,
            id=f"fetch_{name}",
        )
    # ----------------------------------------------
    # ----------------------------------------------
    # 计算文件列表
    utils.save_calculate_filelist()
    # aiohttp 初始化
    app.router.add_routes(routes)
    for route in list(app.router.routes()):
        if route.resource.canonical != "/socket.io/":
            cors.add(route)
    try:
        # mcim()
        scheduler.start()
        if settings.CERTIFICATES_STATUS == "true":
            logger.info("使用证书启动主控中...")
            logger.info(f"正在端口 {settings.PORT} 上监听服务器。")
            web.run_app(
                app,
                host=settings.HOST,
                port=settings.PORT,
                ssl_context=settings.ssl_context,
                print=None,
            )
        else:
            logger.info("使用普通模式启动主控中...")
            logger.info(f"正在端口 {settings.PORT} 上监听服务器。")
            web.run_app(app, host=settings.HOST, port=settings.PORT)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("主控已经停止运行。")
