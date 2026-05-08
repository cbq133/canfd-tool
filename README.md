# 通用CAN FD调试工具 (Multi-Vendor)

一款基于 PyQt5 的通用 CAN/CAN FD 调试工具，支持多厂家 CAN 设备。

## 支持的设备厂家

| 厂家 | 设备型号 | 状态 |
|-----|---------|------|
| **ZLG周立功** | USBCANFD-100U/200U/400U, USBCAN-2E-U/4E-U | ✅ 完整支持 |
| **Vector** | VN1610, VN1630, VN1640, VN5650 | ⚠️ 需安装XL Driver |
| **PEAK** | PCAN-USB, PCAN-USB Pro, PCAN-USB FD | ⚠️ 需安装PCAN驱动 |

## 功能特性

- **多厂家支持**: 一键切换 ZLG/Vector/PEAK 设备
- **CAN类型**: CAN / CAN FD 模式切换
- **波特率**: 125K/250K/500K/1M (仲裁), 1M/2M/4M/5M/8M (数据)
- **消息发送**: 标准帧/扩展帧, 单次/循环发送
- **消息接收**: 实时显示, ID过滤, CSV/TXT保存
- **状态监控**: 连接状态, 收发计数, 错误计数

## 下载

从 [Releases](../../releases) 页面下载最新版本的 Windows 可执行文件。

## 使用方法

1. 安装对应厂家的 CAN 设备驱动程序
2. 下载 `CANFDTool.exe`
3. 直接运行，无需安装 Python

### 驱动安装要求

| 厂家 | 驱动下载 |
|-----|---------|
| ZLG | [周立功官网](https://www.zlg.cn/) |
| Vector | Vector Driver Setup (随硬件提供) |
| PEAK | [PEAK官网](https://www.peak-system.com/) |

## 系统要求

- Windows 7/8/10/11 (x64)
- 对应厂家的 CAN 设备驱动程序

## 开发

```bash
pip install -r requirements.txt
python main.py
```

## 文件说明

```
canfd-tool-github/
├── main.py                 # 主程序 (支持多厂家)
├── can_driver.py           # 通用CAN驱动接口
├── requirements.txt        # Python依赖
├── .github/workflows/      # GitHub Actions自动构建
└── README.md              # 本说明文件
```

## 许可证

MIT License

## 更新日志

### v1.1.0
- 新增多厂家设备支持 (ZLG/Vector/PEAK)
- 重构驱动架构，统一接口

### v1.0.0
- 初始版本，支持ZLG设备
