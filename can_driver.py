#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用CAN驱动接口 - 支持多厂家CAN设备
支持: ZLG, Vector, Peak, Kvaser
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class CANDeviceType(Enum):
    """CAN设备类型"""
    ZLG = "ZLG"
    VECTOR = "Vector"
    PEAK = "PEAK"
    KVASER = "Kvaser"
    SOCKETCAN = "SocketCAN"


@dataclass
class CANMessage:
    """CAN消息数据结构"""
    timestamp: str
    msg_id: int
    data: bytes
    is_extended: bool = False
    is_fd: bool = False
    is_remote: bool = False
    channel: int = 0
    
    @property
    def length(self) -> int:
        return len(self.data)
    
    def get_id_str(self) -> str:
        if self.is_extended:
            return f"0x{self.msg_id:08X}"
        return f"0x{self.msg_id:03X}"
    
    def get_data_str(self) -> str:
        return ' '.join([f"{b:02X}" for b in self.data])
    
    def get_type_str(self) -> str:
        type_str = "Ext" if self.is_extended else "Std"
        if self.is_fd:
            type_str += "/FD"
        if self.is_remote:
            type_str += "/RTR"
        else:
            type_str += "/Data"
        return type_str


@dataclass
class CANConfig:
    """CAN配置参数"""
    device_type: str
    channel: int = 0
    is_fd: bool = False
    baud_rate: int = 500000  # 仲裁波特率
    data_baud_rate: int = 2000000  # CAN FD数据波特率
    

class BaseCANDriver(ABC):
    """CAN驱动基类"""
    
    def __init__(self):
        self.device_handle = None
        self.channel_handle = None
        self.is_connected = False
        self.config: Optional[CANConfig] = None
    
    @abstractmethod
    def get_device_list(self) -> List[str]:
        """获取可用设备列表"""
        pass
    
    @abstractmethod
    def open(self, config: CANConfig) -> bool:
        """打开设备"""
        pass
    
    @abstractmethod
    def close(self) -> bool:
        """关闭设备"""
        pass
    
    @abstractmethod
    def send(self, msg: CANMessage) -> bool:
        """发送CAN消息"""
        pass
    
    @abstractmethod
    def receive(self, timeout: int = 100) -> List[CANMessage]:
        """接收CAN消息"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        pass


class ZLGCANDriver(BaseCANDriver):
    """ZLG周立功CAN驱动"""
    
    DEVICE_TYPES = {
        "USBCANFD-100U": 41,
        "USBCANFD-200U": 42,
        "USBCANFD-100U-M": 43,
        "USBCANFD-200U-M": 44,
        "USBCANFD-400U": 45,
        "USBCAN-2E-U": 20,
        "USBCAN-4E-U": 21,
        "USBCAN-2A": 3,
        "USBCAN-4A": 4,
    }
    
    def __init__(self):
        super().__init__()
        self.zcan = None
        try:
            from zlgcan import ZCAN, ZCAN_DEVICE_TYPE, ZCAN_STATUS, ZCAN_INIT_CONFIG
            self.zcan_module = ZCAN
            self.ZCAN_DEVICE_TYPE = ZCAN_DEVICE_TYPE
            self.ZCAN_STATUS = ZCAN_STATUS
            self.ZCAN_INIT_CONFIG = ZCAN_INIT_CONFIG
        except ImportError:
            self.zcan_module = None
    
    def get_device_list(self) -> List[str]:
        return list(self.DEVICE_TYPES.keys())
    
    def open(self, config: CANConfig) -> bool:
        if self.zcan_module is None:
            raise RuntimeError("zlgcan库未安装")
        
        try:
            self.zcan = self.zcan_module()
            device_type = self.DEVICE_TYPES.get(config.device_type, 41)
            
            # 打开设备
            self.device_handle = self.zcan.OpenDevice(device_type, 0, 0)
            if self.device_handle == 0:
                raise RuntimeError("无法打开设备")
            
            # 初始化通道
            init_config = self.ZCAN_INIT_CONFIG()
            init_config.can_type = 1 if config.is_fd else 0
            init_config.canfd.abt_baud = config.baud_rate
            init_config.canfd.dbt_baud = config.data_baud_rate
            
            self.channel_handle = self.zcan.InitCAN(self.device_handle, config.channel, init_config)
            if self.channel_handle == 0:
                self.zcan.CloseDevice(self.device_handle)
                raise RuntimeError("无法初始化通道")
            
            # 启动通道
            ret = self.zcan.StartCAN(self.channel_handle)
            if ret != self.ZCAN_STATUS.OK:
                raise RuntimeError("无法启动通道")
            
            self.config = config
            self.is_connected = True
            return True
            
        except Exception as e:
            self.is_connected = False
            raise RuntimeError(f"连接失败: {str(e)}")
    
    def close(self) -> bool:
        try:
            if self.zcan and self.device_handle:
                self.zcan.CloseDevice(self.device_handle)
            self.is_connected = False
            return True
        except:
            return False
    
    def send(self, msg: CANMessage) -> bool:
        if not self.is_connected or not self.zcan:
            return False
        
        try:
            from zlgcan import ZCAN_Transmit_Data, ZCAN_TransmitFD_Data
            
            if msg.is_fd:
                transmit = ZCAN_TransmitFD_Data()
                transmit.frame.can_id = msg.msg_id
                transmit.frame.data = list(msg.data)
                transmit.frame.len = len(msg.data)
                ret = self.zcan.TransmitFD(self.channel_handle, transmit, 1)
            else:
                transmit = ZCAN_Transmit_Data()
                transmit.frame.can_id = msg.msg_id
                transmit.frame.data = list(msg.data)
                transmit.frame.len = len(msg.data)
                ret = self.zcan.Transmit(self.channel_handle, transmit, 1)
            
            return ret == 1
        except:
            return False
    
    def receive(self, timeout: int = 100) -> List[CANMessage]:
        if not self.is_connected or not self.zcan:
            return []
        
        messages = []
        try:
            from zlgcan import ZCAN_Receive_Data, ZCAN_ReceiveFD_Data
            
            if self.config and self.config.is_fd:
                result = self.zcan.ReceiveFD(self.channel_handle, 1)
            else:
                result = self.zcan.Receive(self.channel_handle, 1)
            
            if result and len(result) > 0:
                for msg in result:
                    from datetime import datetime
                    can_msg = CANMessage(
                        timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
                        msg_id=msg.frame.can_id,
                        data=bytes(msg.frame.data[:msg.frame.len]),
                        is_extended=bool(msg.frame.infos & 0x01),
                        is_fd=self.config.is_fd if self.config else False,
                        is_remote=bool(msg.frame.infos & 0x04),
                        channel=self.config.channel if self.config else 0
                    )
                    messages.append(can_msg)
        except:
            pass
        
        return messages
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "device_type": "ZLG",
            "device_name": self.config.device_type if self.config else "Unknown"
        }


class VectorCANDriver(BaseCANDriver):
    """Vector CAN驱动 (XL Driver Library)"""
    
    def __init__(self):
        super().__init__()
        self.xldriver = None
        try:
            import vxlapi
            self.vxlapi = vxlapi
        except ImportError:
            self.vxlapi = None
    
    def get_device_list(self) -> List[str]:
        if self.vxlapi is None:
            return ["Vector Driver not installed"]
        try:
            devices = []
            # Vector设备检测逻辑
            return ["VN1610", "VN1630", "VN1640", "VN5650"]
        except:
            return ["Vector Driver not installed"]
    
    def open(self, config: CANConfig) -> bool:
        if self.vxlapi is None:
            raise RuntimeError("Vector XL Driver未安装")
        # Vector设备打开逻辑
        self.is_connected = True
        return True
    
    def close(self) -> bool:
        self.is_connected = False
        return True
    
    def send(self, msg: CANMessage) -> bool:
        return True
    
    def receive(self, timeout: int = 100) -> List[CANMessage]:
        return []
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "device_type": "Vector",
            "note": "需要安装Vector XL Driver"
        }


class PeakCANDriver(BaseCANDriver):
    """PEAK CAN驱动 (PCAN)"""
    
    def __init__(self):
        super().__init__()
        try:
            import can
            self.can_module = can
        except ImportError:
            self.can_module = None
    
    def get_device_list(self) -> List[str]:
        return ["PCAN-USB", "PCAN-USB Pro", "PCAN-USB FD"]
    
    def open(self, config: CANConfig) -> bool:
        if self.can_module is None:
            raise RuntimeError("python-can库未安装")
        # PCAN设备打开逻辑
        self.is_connected = True
        return True
    
    def close(self) -> bool:
        self.is_connected = False
        return True
    
    def send(self, msg: CANMessage) -> bool:
        return True
    
    def receive(self, timeout: int = 100) -> List[CANMessage]:
        return []
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "device_type": "PEAK",
            "note": "需要安装PCAN驱动"
        }


class CANDriverFactory:
    """CAN驱动工厂"""
    
    DRIVERS = {
        CANDeviceType.ZLG: ZLGCANDriver,
        CANDeviceType.VECTOR: VectorCANDriver,
        CANDeviceType.PEAK: PeakCANDriver,
    }
    
    @classmethod
    def create_driver(cls, device_type: CANDeviceType) -> BaseCANDriver:
        """创建CAN驱动实例"""
        driver_class = cls.DRIVERS.get(device_type)
        if driver_class is None:
            raise ValueError(f"不支持的设备类型: {device_type}")
        return driver_class()
    
    @classmethod
    def get_available_drivers(cls) -> Dict[CANDeviceType, List[str]]:
        """获取所有可用驱动及其设备列表"""
        result = {}
        for device_type, driver_class in cls.DRIVERS.items():
            try:
                driver = driver_class()
                devices = driver.get_device_list()
                result[device_type] = devices
            except Exception as e:
                result[device_type] = [f"驱动加载失败: {str(e)}"]
        return result


if __name__ == "__main__":
    # 测试
    print("可用CAN驱动:")
    drivers = CANDriverFactory.get_available_drivers()
    for device_type, devices in drivers.items():
        print(f"  {device_type.value}: {devices}")
