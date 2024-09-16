import asyncio
import aiosqlite
from aiosqlite import Cursor
from pathlib import Path
import motor.motor_asyncio
import core.datafile as datafile
import core.settings as settings

class Database:
    def __init__(self):
        self.conn = None

    # def __init__(self, ):
    #     self.client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{settings.MDB_USERNAME}:{settings.MDB_PASSWORD}@{settings.MDB_HOST}")

    async def connect(self):
        self.conn = await aiosqlite.connect("./data/database.db")
        self.cursor = await self.conn.cursor()

    async def close(self):
        await self.conn.close()

    async def create_table(self):
        await self.connect()
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS CLUSTER_LIST
            (
                CLUSTER_NAME TEXT,
                CLUSTER_ID TEXT PRIMARY KEY,
                CLUSTER_SECRET TEXT,
                CLUSTER_BANDWIDTH INTEGER,
                CLUSTER_TRUST INTEGER,
                CLUSTER_ISBANNED BOOLEAN,
                CLUSTER_BANREASON TEXT,
                CLUSTER_HOST TEXT,
                CLUSTER_PORT INTEGER,
                CLUSTER_VERSION TEXT,
                CLUSTER_RUNTIME TEXT
            )
        """
        )
        await self.conn.commit()
        await self.close()

    async def create_cluster(
        self,
        name: str,
        id: str,
        secret: str,
        bandwidth: int,
        trust: int = 0,
        isBanned: bool = False,
        banreason: str = "",
        host: str = "",
        port: int = 80,
        version: str = "",
        runtime: str = "",
    ):
        await self.connect()
        await self.conn.execute(
            """
            INSERT INTO CLUSTER_LIST (
                CLUSTER_NAME,
                CLUSTER_ID,
                CLUSTER_SECRET,
                CLUSTER_BANDWIDTH,
                CLUSTER_TRUST,
                CLUSTER_ISBANNED,
                CLUSTER_BANREASON,
                CLUSTER_HOST,
                CLUSTER_PORT,
                CLUSTER_VERSION,
                CLUSTER_RUNTIME
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                id,
                secret,
                bandwidth,
                trust,
                isBanned,
                banreason,
                host,
                port,
                version,
                runtime,
            ),
        )
        await self.conn.commit()
        await self.close()
        return True

    async def delete_cluster(self, id: str):
        await self.connect()
        await self.conn.execute(
            """
            DELETE FROM CLUSTER_LIST WHERE CLUSTER_ID = ?
        """,
            (id,),
        )
        await self.conn.commit()
        await self.close()
        return True

    async def query_cluster_data(self, id: str):
        await self.connect()
        async with self.conn.execute(
            """
            SELECT * FROM CLUSTER_LIST WHERE CLUSTER_ID = ?
        """,
            (id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, row))
            else:
                result = False
        await self.close()
        return result

    async def edit_cluster(
        self,
        id: str,
        name: str = None,
        secret: str = None,
        bandwidth: int = None,
        trust: int = None,
        isBanned: bool = None,
        ban_reason: str = None,
        host: str = None,
        port: int = None,
        version: str = None,
        runtime: str = None,
    ):
        if await self.query_cluster_data(id) != False:
            await self.connect()
            update_data = {}
            if name is not None:
                update_data["CLUSTER_NAME"] = name
            if secret is not None:
                update_data["CLUSTER_SECRET"] = secret
            if bandwidth is not None:
                update_data["CLUSTER_BANDWIDTH"] = bandwidth
            if trust is not None:
                update_data["CLUSTER_TRUST"] = trust
            if isBanned is not None:
                update_data["CLUSTER_ISBANNED"] = isBanned
            if ban_reason is not None:
                update_data["CLUSTER_BANREASON"] = ban_reason
            if host is not None:
                update_data["CLUSTER_HOST"] = host
            if port is not None:
                update_data["CLUSTER_PORT"] = port
            if version is not None:
                update_data["CLUSTER_VERSION"] = version
            if runtime is not None:
                update_data["CLUSTER_RUNTIME"] = runtime

            # 构建更新语句
            set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values()) + [id]
            query = f"""
                UPDATE CLUSTER_LIST
                SET {set_clause}
                WHERE CLUSTER_ID = ?
            """

            # 执行更新
            await self.conn.execute(query, values)
            await self.conn.commit()
            result = True
        else:
            result = False
        await self.close()
        return result

    async def get_clusters(self):
        await self.connect()
        async with self.conn.execute("SELECT * FROM CLUSTER_LIST") as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]
        await self.close()
        return result


database = Database()
