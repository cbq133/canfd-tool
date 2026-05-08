#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用CAN FD调试工具 - 支持多厂家设备
支持: ZLG, Vector, PEAK
"""

import sys
import time
import csv
from datetime import datetime
from typing import Optional, List

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QComboBox, QPushButton, QLineEdit, QTableWidget,
        QTableWidgetItem, QGroupBox, QGridLayout, QSpinBox,
        QFileDialog, QMessageBox, QHeaderView
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
except ImportError:
    print("请先安装PyQt5: pip install PyQt5")
    sys.exit(1)

from can_driver import (
    CANDriverFactory, CANDeviceType, CANConfig, CANMessage,
    ZLGCANDriver, VectorCANDriver, PeakCANDriver
)


class ReceiveThread(QThread):
    """CAN接收线程"""
    message_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, driver, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                if self.driver and self.driver.is_connected:
                    messages = self.driver.receive(100)
                    for msg in messages:
                        self.message_received.emit(msg)
                time.sleep(0.001)
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"接收错误: {str(e)}")

    def stop(self):
        self.running = False
        self.wait(1000)


class CANFDTool(QMainWindow):
    """通用CAN FD工具主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("通用CAN FD调试工具 (ZLG/Vector/PEAK)")
        self.setMinimumSize(1100, 750)

        self.driver = None
        self.receive_thread = None
        self.cyclic_timer = None

        self.tx_count = 0
        self.rx_count = 0
        self.error_count = 0
        self.messages = []

        self.init_ui()
        self.refresh_device_list()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === 设备配置区域 ===
        device_group = QGroupBox("设备配置")
        device_layout = QGridLayout(device_group)

        # 厂家选择
        device_layout.addWidget(QLabel("设备厂家:"), 0, 0)
        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems(["ZLG周立功", "Vector", "PEAK"])
        self.vendor_combo.currentTextChanged.connect(self.on_vendor_changed)
        device_layout.addWidget(self.vendor_combo, 0, 1)

        # 设备类型
        device_layout.addWidget(QLabel("设备类型:"), 0, 2)
        self.device_combo = QComboBox()
        device_layout.addWidget(self.device_combo, 0, 3)

        # 通道选择
        device_layout.addWidget(QLabel("通道:"), 1, 0)
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["CH1", "CH2"])
        device_layout.addWidget(self.channel_combo, 1, 1)

        # CAN类型
        device_layout.addWidget(QLabel("CAN类型:"), 1, 2)
        self.can_type_combo = QComboBox()
        self.can_type_combo.addItems(["CAN", "CAN FD"])
        self.can_type_combo.currentTextChanged.connect(self.on_can_type_changed)
        device_layout.addWidget(self.can_type_combo, 1, 3)

        # 仲裁波特率
        device_layout.addWidget(QLabel("仲裁波特率:"), 2, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["125K", "250K", "500K", "1M"])
        self.baud_combo.setCurrentText("500K")
        device_layout.addWidget(self.baud_combo, 2, 1)

        # 数据波特率 (CAN FD)
        device_layout.addWidget(QLabel("数据波特率:"), 2, 2)
        self.data_baud_combo = QComboBox()
        self.data_baud_combo.addItems(["1M", "2M", "4M", "5M", "8M"])
        self.data_baud_combo.setCurrentText("2M")
        device_layout.addWidget(self.data_baud_combo, 2, 3)

        # 连接按钮
        self.connect_btn = QPushButton("连接设备")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        device_layout.addWidget(self.connect_btn, 3, 0, 1, 2)

        # 状态标签
        self.status_label = QLabel("状态: 未连接")
        self.status_label.setStyleSheet("color: red;")
        device_layout.addWidget(self.status_label, 3, 2, 1, 2)

        main_layout.addWidget(device_group)

        # === 发送区域 ===
        send_group = QGroupBox("发送消息")
        send_layout = QGridLayout(send_group)

        send_layout.addWidget(QLabel("帧ID (Hex):"), 0, 0)
        self.id_input = QLineEdit("0x123")
        send_layout.addWidget(self.id_input, 0, 1)

        send_layout.addWidget(QLabel("帧类型:"), 0, 2)
        self.frame_type_combo = QComboBox()
        self.frame_type_combo.addItems(["标准帧", "扩展帧"])
        send_layout.addWidget(self.frame_type_combo, 0, 3)

        send_layout.addWidget(QLabel("数据长度:"), 0, 4)
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 64)
        self.dlc_spin.setValue(8)
        send_layout.addWidget(self.dlc_spin, 0, 5)

        send_layout.addWidget(QLabel("数据 (Hex, 空格分隔):"), 1, 0)
        self.data_input = QLineEdit("01 02 03 04 05 06 07 08")
        send_layout.addWidget(self.data_input, 1, 1, 1, 4)

        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)
        send_layout.addWidget(self.send_btn, 1, 5)

        # 循环发送
        send_layout.addWidget(QLabel("循环间隔 (ms):"), 2, 0)
        self.cyclic_spin = QSpinBox()
        self.cyclic_spin.setRange(10, 10000)
        self.cyclic_spin.setValue(100)
        self.cyclic_spin.setSingleStep(10)
        send_layout.addWidget(self.cyclic_spin, 2, 1)

        self.cyclic_btn = QPushButton("开始循环")
        self.cyclic_btn.setCheckable(True)
        self.cyclic_btn.clicked.connect(self.toggle_cyclic)
        self.cyclic_btn.setEnabled(False)
        send_layout.addWidget(self.cyclic_btn, 2, 2)

        self.tx_count_label = QLabel("发送计数: 0")
        send_layout.addWidget(self.tx_count_label, 2, 4)

        main_layout.addWidget(send_group)

        # === 接收区域 ===
        recv_group = QGroupBox("接收消息")
        recv_layout = QVBoxLayout(recv_group)

        # 过滤和按钮
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("ID过滤 (Hex):"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("例如: 0x100")
        filter_layout.addWidget(self.filter_input)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_messages)
        filter_layout.addWidget(self.clear_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_messages)
        filter_layout.addWidget(self.save_btn)

        recv_layout.addLayout(filter_layout)

        # 消息表格
        self.msg_table = QTableWidget()
        self.msg_table.setColumnCount(6)
        self.msg_table.setHorizontalHeaderLabels(["时间", "ID", "长度", "数据", "类型", "通道"])
        self.msg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.msg_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.msg_table.setMaximumRowCount(1000)
        recv_layout.addWidget(self.msg_table)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.rx_count_label = QLabel("接收计数: 0")
        stats_layout.addWidget(self.rx_count_label)

        self.error_count_label = QLabel("错误计数: 0")
        self.error_count_label.setStyleSheet("color: red;")
        stats_layout.addWidget(self.error_count_label)

        stats_layout.addStretch()
        recv_layout.addLayout(stats_layout)

        main_layout.addWidget(recv_group)

    def refresh_device_list(self):
        """刷新设备列表"""
        self.on_vendor_changed()

    def on_vendor_changed(self):
        """厂家选择改变"""
        vendor = self.vendor_combo.currentText()
        self.device_combo.clear()

        if vendor == "ZLG周立功":
            devices = ZLGCANDriver.DEVICE_TYPES.keys()
        elif vendor == "Vector":
            devices = ["VN1610", "VN1630", "VN1640", "VN5650"]
        elif vendor == "PEAK":
            devices = ["PCAN-USB", "PCAN-USB Pro", "PCAN-USB FD"]
        else:
            devices = []

        self.device_combo.addItems(list(devices))

    def on_can_type_changed(self):
        """CAN类型改变"""
        is_fd = self.can_type_combo.currentText() == "CAN FD"
        self.data_baud_combo.setEnabled(is_fd)
        if is_fd:
            self.dlc_spin.setMaximum(64)
        else:
            self.dlc_spin.setMaximum(8)

    def toggle_connection(self):
        """切换连接状态"""
        if self.driver and self.driver.is_connected:
            self.disconnect_device()
        else:
            self.connect_device()

    def connect_device(self):
        """连接设备"""
        try:
            vendor = self.vendor_combo.currentText()
            device_type = self.device_combo.currentText()
            channel = self.channel_combo.currentIndex()
            is_fd = self.can_type_combo.currentText() == "CAN FD"

            baud_map = {"125K": 125000, "250K": 250000, "500K": 500000, "1M": 1000000}
            data_baud_map = {"1M": 1000000, "2M": 2000000, "4M": 4000000, "5M": 5000000, "8M": 8000000}

            baud_rate = baud_map.get(self.baud_combo.currentText(), 500000)
            data_baud_rate = data_baud_map.get(self.data_baud_combo.currentText(), 2000000)

            # 创建驱动
            if vendor == "ZLG周立功":
                self.driver = ZLGCANDriver()
            elif vendor == "Vector":
                self.driver = VectorCANDriver()
            elif vendor == "PEAK":
                self.driver = PeakCANDriver()
            else:
                raise ValueError(f"不支持的厂家: {vendor}")

            # 配置并连接
            config = CANConfig(
                device_type=device_type,
                channel=channel,
                is_fd=is_fd,
                baud_rate=baud_rate,
                data_baud_rate=data_baud_rate
            )

            if self.driver.open(config):
                self.status_label.setText(f"状态: 已连接 ({device_type})")
                self.status_label.setStyleSheet("color: green;")
                self.connect_btn.setText("断开连接")
                self.connect_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
                self.send_btn.setEnabled(True)
                self.cyclic_btn.setEnabled(True)

                # 启动接收线程
                self.receive_thread = ReceiveThread(self.driver)
                self.receive_thread.message_received.connect(self.on_message_received)
                self.receive_thread.error_occurred.connect(self.on_receive_error)
                self.receive_thread.start()
            else:
                raise RuntimeError("连接失败")

        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"无法连接设备:\n{str(e)}")
            self.driver = None

    def disconnect_device(self):
        """断开设备"""
        if self.receive_thread:
            self.receive_thread.stop()
            self.receive_thread = None

        if self.driver:
            self.driver.close()
            self.driver = None

        self.status_label.setText("状态: 未连接")
        self.status_label.setStyleSheet("color: red;")
        self.connect_btn.setText("连接设备")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.send_btn.setEnabled(False)
        self.cyclic_btn.setEnabled(False)

    def send_message(self):
        """发送消息"""
        if not self.driver or not self.driver.is_connected:
            return

        try:
            # 解析ID
            id_str = self.id_input.text().strip()
            if id_str.startswith("0x"):
                msg_id = int(id_str, 16)
            else:
                msg_id = int(id_str)

            # 解析数据
            data_str = self.data_input.text().strip()
            data_bytes = bytes([int(b, 16) for b in data_str.split() if b])

            # 限制长度
            dlc = self.dlc_spin.value()
            data_bytes = data_bytes[:dlc]

            # 创建消息
            is_extended = self.frame_type_combo.currentText() == "扩展帧"
            is_fd = self.can_type_combo.currentText() == "CAN FD"

            msg = CANMessage(
                timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
                msg_id=msg_id,
                data=data_bytes,
                is_extended=is_extended,
                is_fd=is_fd,
                channel=self.channel_combo.currentIndex()
            )

            if self.driver.send(msg):
                self.tx_count += 1
                self.tx_count_label.setText(f"发送计数: {self.tx_count}")
            else:
                self.error_count += 1
                self.error_count_label.setText(f"错误计数: {self.error_count}")

        except Exception as e:
            QMessageBox.warning(self, "发送错误", f"发送失败:\n{str(e)}")
            self.error_count += 1
            self.error_count_label.setText(f"错误计数: {self.error_count}")

    def toggle_cyclic(self):
        """切换循环发送"""
        if self.cyclic_btn.isChecked():
            self.cyclic_btn.setText("停止循环")
            interval = self.cyclic_spin.value()
            self.cyclic_timer = QTimer(self)
            self.cyclic_timer.timeout.connect(self.send_message)
            self.cyclic_timer.start(interval)
        else:
            self.cyclic_btn.setText("开始循环")
            if self.cyclic_timer:
                self.cyclic_timer.stop()
                self.cyclic_timer = None

    def on_message_received(self, msg: CANMessage):
        """接收到消息"""
        # 过滤检查
        filter_str = self.filter_input.text().strip()
        if filter_str:
            try:
                if filter_str.startswith("0x"):
                    filter_id = int(filter_str, 16)
                else:
                    filter_id = int(filter_str)
                if msg.msg_id != filter_id:
                    return
            except:
                pass

        self.messages.append(msg)
        self.rx_count += 1
        self.rx_count_label.setText(f"接收计数: {self.rx_count}")

        # 添加到表格
        row = self.msg_table.rowCount()
        self.msg_table.insertRow(row)
        self.msg_table.setItem(row, 0, QTableWidgetItem(msg.timestamp))
        self.msg_table.setItem(row, 1, QTableWidgetItem(msg.get_id_str()))
        self.msg_table.setItem(row, 2, QTableWidgetItem(str(msg.length)))
        self.msg_table.setItem(row, 3, QTableWidgetItem(msg.get_data_str()))
        self.msg_table.setItem(row, 4, QTableWidgetItem(msg.get_type_str()))
        self.msg_table.setItem(row, 5, QTableWidgetItem(f"CH{msg.channel + 1}"))

        # 滚动到最新
        self.msg_table.scrollToBottom()

    def on_receive_error(self, error_msg: str):
        """接收错误"""
        self.error_count += 1
        self.error_count_label.setText(f"错误计数: {self.error_count}")

    def clear_messages(self):
        """清空消息"""
        self.msg_table.setRowCount(0)
        self.messages.clear()
        self.rx_count = 0
        self.rx_count_label.setText("接收计数: 0")

    def save_messages(self):
        """保存消息"""
        if not self.messages:
            QMessageBox.information(self, "提示", "没有消息可保存")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "保存消息", "can_messages.csv",
            "CSV文件 (*.csv);;文本文件 (*.txt)"
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["时间", "ID", "长度", "数据", "类型", "通道"])
                    for msg in self.messages:
                        writer.writerow([
                            msg.timestamp,
                            msg.get_id_str(),
                            msg.length,
                            msg.get_data_str(),
                            msg.get_type_str(),
                            f"CH{msg.channel + 1}"
                        ])
                QMessageBox.information(self, "成功", f"已保存 {len(self.messages)} 条消息")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

    def closeEvent(self, event):
        """关闭窗口"""
        self.disconnect_device()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CANFDTool()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
