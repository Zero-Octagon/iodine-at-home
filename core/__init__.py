# 第三方库
import re
import time
import asyncio
import uvicorn
from pluginbase import PluginBase
from fastapi import FastAPI, Response
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import socketio
from socketio.asgi import ASGIApp

# 本地库
from core.mdb import cdb
import core.const as const
import core.utils as utils
from core.logger import logger
from core.config import config
from core.types import Cluster
from core.filesdb import filesdb

# 路由库
from core.routes.agent import app as agent_router
from core.routes.openbmclapi import app as openbmclapi_router
from core.routes.services import app as services_router

# 网页部分
app = FastAPI(
    title="iodine@home",
    summary="开源的文件分发主控，并尝试兼容 OpenBMCLAPI 客户端",
    version="2.0.0",
    license_info={
        "name": "The MIT License",
        "url": "https://raw.githubusercontent.com/ZeroNexis/iodine-at-home/main/LICENSE",
    },
)

app.include_router(agent_router, prefix="/openbmclapi-agent")
app.include_router(openbmclapi_router, prefix="/openbmclapi")
app.include_router(services_router)

## 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 插件部分
plugin_base = PluginBase(package="plugin")
plugin_source = plugin_base.make_plugin_source(searchpath=["./plugins"])


async def load_plugins():
    for plugin_name in plugin_source.list_plugins():
        logger.info(f"插件 {plugin_name} 加载中...")
        plugin = plugin_source.load_plugin(plugin_name)
        logger.info(f"插件「{plugin.__NAME__}」加载成功！")
        if hasattr(plugin, "__API__") and plugin.__API__:
            if hasattr(plugin, "app"):
                app.include_router(plugin.app, prefix=f"/{plugin.__NAMESPACE__}")
            else:
                logger.warning(
                    f"插件「{plugin.__NAME__}」未定义 App ，无法加载该插件的路径！"
                )
        await plugin.init()


# SocketIO 部分
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket = ASGIApp(sio)

# 核心功能
online_cluster_list = []
online_cluster_list_json = []


## 节点端连接时
@sio.on("connect")
async def on_connect(sid, *args):
    token_pattern = r"'token': '(.*?)'"
    token = re.search(token_pattern, str(args)).group(1)
    if token.isspace():
        sio.disconnect(sid)
        logger.debug(f"客户端 {sid} 连接失败: 缺少 token 令牌")
    cluster = Cluster(utils.decode_jwt(token)["cluster_id"])
    if await cluster.initialize() == False:
        sio.disconnect(sid)
        logger.debug(f"客户端 {sid} 连接失败: 集群 {cluster.id} 不存在")
    if cluster.secret == utils.decode_jwt(token)["cluster_secret"]:
        await sio.save_session(
            sid,
            {
                "cluster_id": cluster.id,
                "cluster_secret": cluster.secret,
                "token": token,
            },
        )
        logger.debug(f"客户端 {sid} 连接成功: CLUSTER_ID = {cluster.id}")
        await sio.emit(
            "message",
            "欢迎使用 iodine@home，本项目已在 https://github.com/ZeroNexis/iodine-at-home 开源，期待您的贡献与支持。",
            sid,
        )
    else:
        sio.disconnect(sid)
        logger.debug(f"客户端 {sid} 连接失败: 认证出错")


## 当节点端退出连接时
@sio.on("disconnect")
async def on_disconnect(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist and cluster.json() in online_cluster_list_json and cluster.id in online_cluster_list:
        online_cluster_list.remove(cluster.id)
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
    await cluster.edit(
        host=data.get("host", session.get("ip")),
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
        logger.debug(f"节点 {cluster.id} 上线: {bandwidth[1]}Mbps")
        if cluster.trust < 0:
            await sio.emit("message", "节点信任度过低，请保持稳定在线。", sid)
        return [None, True]
    elif bandwidth[0] and bandwidth[1] < 10:
        logger.debug(f"{cluster.id} 测速不合格: {bandwidth[1]}Mbps")
        return [
            {
                "message": f"错误: 测量带宽小于 10Mbps，（测量得 {bandwidth[1]}），请重试尝试上线"
            }
        ]
    else:
        logger.debug(f"{cluster.id} 测速未通过: {bandwidth[1]}")
        return [{"message": f"错误: {bandwidth[1]}"}]
    
## 节点保活时
@sio.on("keep-alive")
async def on_cluster_keep_alive(sid, data, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False or cluster.id not in online_cluster_list:
        return [None, False]
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


def init():
    # asyncio.run(filesdb.delete_all())
    try:
        asyncio.run(load_plugins())
        app.mount("/", socket)
        logger.info(
            f"正在 {config.get('host')}:{config.get(path='port')} 上监听服务器..."
        )

        uvicorn.run(
            app,
            host=config.get("host"),
            port=config.get(path="port"),
            log_level="warning",
        )
    except KeyboardInterrupt:
        logger.info("主控成功关闭。")
