import sys
from core.logger import logger

py_version = sys.version_info

if py_version < (3, 9):
    logger.tinfo(
        "main.info.python_version",
        major=py_version[0],
        minor=py_version[1],
        patch=py_version[2],
    )
    logger.tinfo("main.info.supported_version")
    sys.exit(1)
import core

core.init()  # 初始化
