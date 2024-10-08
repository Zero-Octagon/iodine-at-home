import sys
import os
import getpass
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import QPainter

# 检查命令行参数
if '-nogui' in sys.argv:
    import core
    from core.logger import logger
    print("你看到这个消息代表nogui模式开始启动")

    py_version = sys.version_info

    if py_version < (3, 11):
        logger.info(
            f"你使用的 Python 版本是 {py_version[0]}.{py_version[1]}.{py_version[2]}，",
        )
        logger.info("而该程序要求使用 3.11 版本及以上的 Python，请及时更换。")
        sys.exit(1)

    core.init()  # 初始化
else:
    class TerminalWindow(QWidget):
        def __init__(self):
            super().__init__()

            self.process = None  # 初始化进程为 None
            self.update_overload = True  # 标志位，控制是否更新过载值
            
            # 创建一个垂直布局
            layout = QVBoxLayout(self)

            # 创建文本框用于显示命令的输出
            self.output_display = QPlainTextEdit(self)
            self.output_display.setReadOnly(True)  # 设置为只读
            self.output_display.setFixedHeight(150)  # 限制输出框高度
            layout.addWidget(self.output_display)

            # 创建一个水平布局用于放置负载标签
            load_layout = QHBoxLayout()

            # 创建显示当前负载的标签
            self.load_label = QLabel("当前负载：没有收到负载信息。", self)
            load_layout.addWidget(self.load_label)

            layout.addLayout(load_layout)  # 将负载标签的布局添加到主布局

            # 创建一个垂直布局用于放置输入框和按钮
            v_layout = QVBoxLayout()

            # 创建输入框并设置样式
            self.input_line = QLineEdit(self)
            self.input_line.setStyleSheet("border: 2px solid black; border-radius: 10px; padding: 8px;")  # 设置黑色边框和圆角
            v_layout.addWidget(self.input_line)

            # 创建发送输入的按钮
            btn_send = QPushButton("发送输入", self)
            btn_send.setFixedSize(200, 40)  # 设置按钮大小
            btn_send.clicked.connect(self.send_input)  # 连接按钮点击事件
            v_layout.addWidget(btn_send)

            layout.addLayout(v_layout)  # 将输入框和按钮的布局添加到主布局

            # 添加立即停机按钮
            btn_shutdown = QPushButton("立即停机", self)
            btn_shutdown.setFixedSize(200, 40)  # 设置按钮大小
            btn_shutdown.clicked.connect(self.confirm_shutdown)
            layout.addWidget(btn_shutdown)

            # 添加“创建节点”按钮
            btn_create_node = QPushButton("创建节点", self)
            btn_create_node.setFixedSize(200, 40)  # 设置按钮大小
            btn_create_node.clicked.connect(self.create_node)  # 连接按钮点击事件
            layout.addWidget(btn_create_node)  # 将按钮添加到布局

            # 添加关闭 Iodine 按钮
            btn_close_iodine = QPushButton("关闭 Iodine", self)
            btn_close_iodine.setFixedSize(200, 40)  # 设置按钮大小
            btn_close_iodine.clicked.connect(self.close_iodine)
            layout.addWidget(btn_close_iodine)

            # 创建一个水平布局用于显示时间和欢迎信息
            bottom_layout = QHBoxLayout()

            # 获取用户名
            user_name = getpass.getuser()  # 获取当前用户的用户名
            self.welcome_label = QLabel(f"欢迎, {user_name}!", self)  # 创建欢迎标签
            self.welcome_label.setStyleSheet("font-size: 16px; color: #FFFFFF;")  # 设置样式
            bottom_layout.addWidget(self.welcome_label, alignment=Qt.AlignRight | Qt.AlignBottom)  # 将欢迎标签添加到布局中

            # 创建当前时间标签
            self.time_label = QLabel(self)
            bottom_layout.addWidget(self.time_label, alignment=Qt.AlignRight | Qt.AlignBottom)  # 将时间标签添加到右下角

            layout.addLayout(bottom_layout)  # 将底部布局添加到主布局

            self.setLayout(layout)  # 设置主布局

            # 连接输入框的回车事件
            self.input_line.returnPressed.connect(self.send_input)

            # 创建定时器来更新时间
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_time)  # 连接定时器到更新时间方法
            self.timer.start(1000)  # 每秒更新一次

            self.update_time()  # 初始化显示一次时间

        def update_time(self):
            """更新时间标签"""
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间
            self.time_label.setText(current_time)  # 设置标签文本为当前时间

        def append_output(self, text):
            """在输出框中打印文本"""
            self.output_display.appendPlainText(text)

        def send_input(self):
            """将输入框内容发送给正在执行的 Python 文件"""
            input_text = self.input_line.text().strip()  # 获取输入框中的文本
            if self.process is not None and self.process.state() == QProcess.Running:
                self.process.write((input_text + '\n').encode())  # 将内容发送到执行的进程中
                self.append_output(f"已发送: {input_text}")  # 显示已发送的信息
                self.input_line.clear()  # 清空输入框
            else:
                self.append_output("没有正在运行的进程，无法发送输入。")

        def confirm_shutdown(self):
            """确认后停机的处理"""
            reply = QMessageBox.question(self, '确认停机',
                                          '你是否要立刻停机？停机后主控也将停止。',
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.process and self.process.state() == QProcess.Running:
                    self.process.kill()  # 停止正在运行的进程
                self.append_output("系统正在停机...")
                self.close()  # 关闭窗口

        def close_iodine(self):
            """关闭 Iodine 进程"""
            if self.process and self.process.state() == QProcess.Running:
                self.process.kill()  # 停止正在运行的进程
                self.append_output("Iodine 进程已关闭。")  # 更新输出显示
            else:
                QMessageBox.warning(self, "警告", "Iodine 进程未运行。")  # 提示进程未运行

        def update_output(self):
            """更新输出显示并更新负载信息"""
            try:
                output = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')  # 读取输出并使用替换错误策略
                self.append_output(output)  # 显示命令输出

                # 检查输出的内容并处理负载信息
                for line in output.splitlines():
                    if self.update_overload and line.startswith("overload:"):  # 仅在更新过载值标志为 True 时处理
                        overload_info = line.split(":", 1)  # 提取冒号后的部分
                        if len(overload_info) > 1:
                            overload_message = overload_info[1].strip()  # 去掉空格
                            self.load_label.setText("当前负载：" + overload_message)  # 更新负载标签显示
                            
                            try:
                                overload_value = int(overload_message)  # 将过载值转换为整数
                                self.append_output(f"设置负载值为: {overload_value}")  # 调试信息，确认值已设置
                            except ValueError:
                                self.append_output("错误：过载值无法转换为整数。")  # 打印错误信息
            except Exception as e:
                self.append_output(f"更新输出时发生错误: {str(e)}")  # 打印错误信息

        def create_node(self):
            """打开secretaid.py脚本"""
            try:
                script_path = r"D:\iodine-at-home\core\secretaid.py"  # 指定secretaid.py的完整路径
                command = "python"  # 使用python命令
                args = [script_path]  # 将脚本路径作为参数传入

                self.update_overload = False  # 点击创建节点后不再更新过载值
                self.process = QProcess(self)  # 使用 self.process 成员变量
                self.process.setProcessChannelMode(QProcess.MergedChannels)  # 合并标准输出和标准错误
                self.process.readyReadStandardOutput.connect(self.update_output)  # 监听输出
                self.process.finished.connect(lambda: self.append_output("脚本执行完毕。"))  # 脚本执行完毕后的提示

                self.process.start(command, args)  # 启动进程执行脚本
                if not self.process.waitForStarted():
                    raise Exception("进程启动失败")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开脚本时发生错误: {str(e)}")  # 提示错误信息

    class MainWindow(QWidget):
        def __init__(self):
            super().__init__()

            self.setWindowFlags(Qt.FramelessWindowHint)  # 去掉原生标题栏
            self.setGeometry(100, 100, 800, 350)  # 窗口初始位置和大小
            self.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF; font-family: 'Microsoft YaHei';")  # 设置样式

            self.startPos = None  # 用于移动窗口

            # 创建自定义标题栏
            title_bar_layout = QHBoxLayout()
            title_bar_layout.setContentsMargins(0, 0, 0, 0)

            # 添加标题字样
            title_label = QLabel("iodine-at-home", self)
            title_label.setStyleSheet("font-size: 20px; color: #FFFFFF;")  # 设置标题字体颜色为白色
            title_bar_layout.addWidget(title_label)

            # 添加最小化按钮
            btn_minimize = QPushButton("_", self)
            btn_minimize.setFixedSize(30, 30)
            btn_minimize.setStyleSheet("background-color: transparent; color: #FFFFFF; border: none; font-size: 20px;")
            btn_minimize.clicked.connect(self.showMinimized)  # 最小化窗口
            title_bar_layout.addWidget(btn_minimize)

            # 添加关闭按钮
            btn_close = QPushButton("X", self)
            btn_close.setFixedSize(30, 30)
            btn_close.setStyleSheet("background-color: transparent; color: #FFFFFF; border: none; font-size: 20px;")
            btn_close.clicked.connect(self.close)  # 关闭窗口
            title_bar_layout.addWidget(btn_close)

            # 将自定义标题栏添加到主布局
            main_layout = QVBoxLayout(self)
            main_layout.addLayout(title_bar_layout)

            # 创建终端窗口
            self.terminal_window = TerminalWindow()
            main_layout.addWidget(self.terminal_window)  # 添加终端窗口到布局

            self.setLayout(main_layout)

        def mousePressEvent(self, event):
            """鼠标按下时记录起始位置"""
            if event.button() == Qt.LeftButton:
                self.startPos = event.pos()  # 记录鼠标按下时的位置

        def mouseMoveEvent(self, event):
            """鼠标移动时更新窗口位置"""
            if event.buttons() & Qt.LeftButton and self.startPos is not None:  # 检查左键是否按下
                self.move(self.pos() + event.pos() - self.startPos)  # 更新窗口的位置

        def mouseReleaseEvent(self, event):
            """鼠标释放时清空起始位置"""
            if event.button() == Qt.LeftButton:  # 判断是否为左键释放
                self.startPos = None  # 清空起始位置

        def paintEvent(self, event):
            """绘制带圆角的窗口"""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)  # 开启抗锯齿
            painter.setBrush(self.palette().window())  # 使用窗口背景色
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 20, 20)  # 绘制圆角矩形


    # 主程序入口
    if __name__ == "__main__":
        app = QApplication(sys.argv)
        window = MainWindow()
        
        try:
            window.show()
            sys.exit(app.exec_())
        except Exception as e:
            print(f"未处理的异常: {str(e)}")  # 打印到控制台
            QMessageBox.critical(window, "未处理的异常", f"程序发生错误: {str(e)}")
            sys.exit(1)
