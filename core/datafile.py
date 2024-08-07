import json
import asyncio
import aiofiles
from pathlib import Path

# JSON 部分
json_read_lock = asyncio.Lock()
json_write_lock = asyncio.Lock()

## 读取 JSON
async def read_json_from_file(filename: str):
    data_file = Path(f"./data/{filename}")
    async with json_read_lock:
        async with aiofiles.open(data_file, "r", encoding="utf-8") as f:
            content = await f.read()
            result = json.loads(content)
    return result

## 写入 JSON
async def write_json_to_file(filename: str, content):
    data_file = Path(f"./data/{filename}")
    async with json_write_lock:
        async with aiofiles.open(data_file, 'w', encoding="utf-8") as f:
            await f.write(json.dumps(content))

# FILELIST 部分
filelist_read_lock = asyncio.Lock()
filelist_write_lock = asyncio.Lock()

## 读取 FILELIST
async def read_filelist_from_cache(filename: str):
    cache_file = Path(f"./data/{filename}")
    async with filelist_read_lock:
        async with aiofiles.open(cache_file, "rb") as f:
            filelist_content = await f.read()
            filelist = filelist_content
    return filelist

## 写入 FILELIST
async def write_filelist_to_cache(filename: str, filelist):
    cache_file = Path(f"./data/{filename}")
    async with filelist_write_lock:
        async with aiofiles.open(cache_file, 'wb') as f:
            f.write(filelist)

## 写入 FILELIST - 无异步版
def write_filelist_to_cache_nosaync(filename: str, filelist):
    cache_file = Path(f"./data/{filename}")
    with open(cache_file, 'wb') as f:
        f.write(filelist)