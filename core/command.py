import asyncio
import argparse
from core.types import Cluster
from core.logger import logger


def parse_command(command):
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="对指令进行解析")

    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="可用的指令")

    # 封禁部分
    ban_parser = subparsers.add_parser("ban", help="封禁某个节点")
    ban_parser.add_argument("id", type=str, help="需要封禁的节点 ID")
    # ban_parser.add_argument("-t", "--time", type=int, default=24, help="封禁的持续时间（单位: 小时）")
    ban_parser.add_argument(
        "-r", "--reason", type=str, default="😡😡😡", help="封禁理由"
    )

    # 解封部分
    unban_parser = subparsers.add_parser("unban", help="解封某个节点")
    unban_parser.add_argument("id", type=str, help="需要解封的节点 ID")

    # 解析命令行参数
    try:
        args = parser.parse_args(command.split())
    except SystemExit:
        # 如果参数解析失败，返回 None
        return None
    except Exception as e:
        # 如果发生其他异常，打印错误信息并返回 None
        logger.error(f"Error: {e}")
        return None

    # 返回解析后的参数
    return args


async def execute_command(command: str):
    # 提示用户输入命令
    command = command.lower()

    # 解析命令
    args = parse_command(command)

    # 如果解析失败，打印错误信息并返回 None
    if args is None:
        return "给出的指令无效，请重试。"
    else:
        # 根据命令执行相应操作
        if args.command == "ban":
            cluster = Cluster(args.id)
            if await cluster.initialize() != False:
                await cluster.edit(isBanned=True, ban_reason=args.reason)
                return f"节点 {args.id} 已被封禁，理由: {args.reason}"
            else:
                return "指令无效，需要封禁的节点并不存在。"
        elif args.command == "unban":
            cluster = Cluster(args.id)
            if await cluster.initialize():
                await cluster.edit(isBanned=False, ban_reason="")
                return f"节点 {args.id} 已被解封。"
            else:
                return "指令无效，需要解封的节点并不存在。"
