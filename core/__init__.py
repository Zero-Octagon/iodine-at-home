# 第三方库
import re
import time
import pytz
import asyncio
import uvicorn
import importlib
from pluginbase import PluginBase
from fastapi import FastAPI, Response
from datetime import datetime, timezone
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dateutil.relativedelta import relativedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import socketio
from socketio.asgi import ASGIApp

# 本地库
from core.mdb import cdb
import core.const as const
import core.utils as utils
from core.logger import logger
from core.config import config
from core.types import Cluster, oclm
from core.filesdb import FilesDB
from core.dns.cloudflare import cf_client

# 路由库
from core.routes.agent import router as agent_router
from core.routes.openbmclapi import router as openbmclapi_router
from core.routes.services import router as services_router
from core.routes.api.v0 import router as api_v0_router

# 网页部分
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"正在 {config.get('host')}:{config.get('port')} 上监听服务器..."
    )
    yield
    async with FilesDB() as db:
        await db.close()
    logger.success("主控退出成功。")

app = FastAPI(
    title="iodine@home",
    summary="开源的文件分发主控，并尝试兼容 OpenBMCLAPI 客户端",
    version="2.0.0",
    license_info={
        "name": "The MIT License",
        "url": "https://raw.githubusercontent.com/ZeroNexis/iodine-at-home/main/LICENSE",
    },
    lifespan=lifespan
)

app.include_router(agent_router, prefix="/openbmclapi-agent")
app.include_router(openbmclapi_router, prefix="/openbmclapi")
app.include_router(services_router)
app.include_router(api_v0_router, prefix="/api/v0")

## 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 插件部分
async def load_plugins():
    global app
    plugin_base = PluginBase(package="plugin")
    plugin_source = plugin_base.make_plugin_source(searchpath=["./plugins"])
    for plugin_name in plugin_source.list_plugins():
        logger.info(f"插件 {plugin_name} 加载中...")
        plugin = importlib.import_module("plugins." + plugin_name)
        logger.info(f"插件「{plugin.__NAME__}」加载成功！")
        if hasattr(plugin, "__API__") and plugin.__API__:
            if hasattr(plugin, "router"):
                app.include_router(plugin.router, prefix=f"/{plugin.__NAMESPACE__}")
                logger.success(f"已注册插件 API 路由：{plugin.__NAMESPACE__}, {plugin.router.routes}")
            else:
                logger.warning(
                    f"插件「{plugin.__NAME__}」未定义 Router ，无法加载该插件的路径！"
                )
        await plugin.init()


# SocketIO 部分
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket = ASGIApp(sio)

# 核心功能
@app.middleware("http")
async def _(request,call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    response_size = len(response.body) if hasattr(response, 'body') else 0
    referer = request.headers.get('Referer')
    user_agent = request.headers.get('user-agent', '-')
    logger.info(
        f"Serve {response.status_code} | {process_time:.2f}s | {response_size}B | "
        f"{request.client.host} | {request.method} | {request.url.path} | \"{user_agent}\" | \"{referer}\""
    )
    return response

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
        logger.debug(f"节点 {sid} 连接失败: 认证出错")


## 当节点端退出连接时
@sio.on("disconnect")
async def on_disconnect(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist and oclm.include(cluster.id):
        oclm.remove(cluster.id)
        logger.debug(f"{sid} 异常断开连接，已从在线列表中删除")
    else:
        logger.debug(f"节点 {sid} 断开了连接")


## 节点请求证书时
@sio.on("request-cert")
async def on_cluster_request_cert(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False:
        return [{"message": "错误: 节点似乎并不存在，请检查配置文件"}]
    logger.debug(f"节点 {cluster.id} 请求证书")
    if cluster.cert_fullchain != "" and cluster.cert_privkey != "" and cluster.cert_expiry != "" and cluster.cert_expiry > datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00'):
        return [
            None, {
                "_id": cluster.id,
                "clusterId": cluster.id,
                "cert": cluster.cert_fullchain,
                "key": cluster.cert_privkey,
                "expires": cluster.cert_expiry,
                "__v": 0
            }
        ]
    else:
        cert, key = await cf_client.get_certificate(f"{cluster.id}.{config.get('cluster-certificate.domain')}")
        if cert == None or key == None:
            return [{"message": "错误: 证书获取失败，请重新尝试。"}]
        current_time = datetime.now(pytz.utc)
        future_time = current_time + relativedelta(months=3)
        formatted_time = future_time.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        await cluster.edit(cert_fullchain=cert, cert_privkey=key, cert_expiry=formatted_time)
        return [
            None, {
                "_id": cluster.id,
                "clusterId": cluster.id,
                "cert": cluster.cert_fullchain,
                "key": cluster.cert_privkey,
                "expires": cluster.cert_expiry,
                "__v": 0
            }
        ]

## 节点启动时
@sio.on("enable")
async def on_cluster_enable(sid, data: dict, *args):
    # {'host': '127.0.0.1', 'port': 11451, 'version': '1.11.0', 'byoc': True, 'noFastEnable': True, 'flavor': {'runtime': 'python/3.12.2 python-openbmclapi/2.1.1', 'storage': 'file'}}
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False:
        return [{"message": "错误: 节点似乎并不存在，请检查配置文件"}]
    if oclm.include(cluster.id):
        return [{"message": "错误: 节点已经在线，请检查配置文件"}]
    host = data.get("host", data.get("ip"))
    byoc = data.get("byoc", False)
    if byoc == False:
        all_records = await cf_client.get_all_records()
        for record in all_records:
            if cluster.id in record["name"]:
                cf_id = record["id"]
                break
            else:
                cf_id = None
        if cf_id == None:
            await cf_client.create_record(cluster.id, "A", data.get("host", data.get("ip")))
        else:
            await cf_client.update_record(id, cluster.id, "A", data.get("host", data.get("ip")))
        host = f"{cluster.id}.{config.get('cluster-certificate.domain')}"

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
    bandwidth = await utils.measure_cluster(10, cluster)
    if bandwidth[0] and bandwidth[1] >= 10:
        await cluster.edit(measureBandwidth=int(bandwidth[1]))
        if cluster.trust < 0:
            await sio.emit("message", "节点信任度过低，请保持稳定在线。", sid)
        oclm.append(cluster.id)
        logger.debug(f"节点 {cluster.id} 上线: 测量带宽 = {bandwidth[1]}Mbps")
        return [None, True]
    elif bandwidth[0] and bandwidth[1] < 10:
        logger.debug(f"{cluster.id} 测速不合格: {bandwidth[1]}Mbps")
        return [
            {
                "message": f"错误: 测量带宽小于 10Mbps，（测量的带宽数值为 {bandwidth[1]}），请重试尝试上线"
            }
        ]
    else:
        logger.debug(f"{cluster.id} 测速失败: {bandwidth[1]}")
        return [{"message": f"错误: {bandwidth[1]}"}]
    
## 节点保活时
@sio.on("keep-alive")
async def on_cluster_keep_alive(sid, data, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False or oclm.include(cluster.id) == False:
        return [None, False]
    logger.debug(
        f"节点 {cluster.id} 保活成功: 次数 = {data["hits"]}, 数据量 = {utils.hum_convert(data['bytes'])}"
    )
    return [None, datetime.now(timezone.utc).isoformat()]

@sio.on("disable")  ## 节点禁用时
async def on_cluster_disable(sid, *args):
    session = await sio.get_session(sid)
    cluster = Cluster(str(session["cluster_id"]))
    cluster_is_exist = await cluster.initialize()
    if cluster_is_exist == False:
        logger.debug("某节点尝试禁用集群失败: 节点不存在")
    else:
        try:
            oclm.remove(cluster.id)
            logger.debug(f"节点 {cluster.id} 禁用集群")
        except ValueError:
            logger.debug(f"节点 {cluster.id} 尝试禁用集群失败: 节点没有启用")
    return [None, True]

def init():
    logger.clear()
    logger.info("加载中……")
    try:
        asyncio.run(load_plugins())
        app.mount("/", socket)
        uvicorn.run(app, host=config.get('host'), port=config.get(path='port'), log_level='warning', access_log=False)
    except Exception as e:
        logger.error(e)
