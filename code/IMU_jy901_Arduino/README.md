# IMU JY901 Arduino

这个目录放 JY901 / WitMotion IMU 的 Arduino SDK、示例程序和上位机可视化工具。它和视觉 PnP 目录是两条线：这里负责 IMU 姿态数据采集，视觉目录负责相机标记位姿。

## 目录结构

- `Arduino_sdk/`：WitMotion 官方 Arduino SDK 和示例。
- `Arduino_sdk/examples/`：IIC、Modbus、普通串口等示例工程。
- `tools/imu_visualizer.py`：Python 上位机可视化工具，用于读取 Arduino 串口输出并显示两个 IMU 的姿态。
- `tools/imu_calibration.example.json`：IMU 可视化工具的示例配置文件。

## 原始 SDK 文档

官方快速上手文档：

```text
https://wit-motion.yuque.com/wumwnr/ltst03/rqyk6g?singleDoc
```

## 当前用途

当前目标是采集 2 个 IMU 传感器的数据，并通过 Python 工具实时显示：

- 加速度。
- 角速度。
- 欧拉角。
- 两个 IMU 的姿态变化。
- 最近串口原始输出。

## Arduino 端

Arduino 示例代码位于：

```text
Arduino_sdk/examples/
```

常见示例：

- `wit_c_sdk_iic/wit_c_sdk_iic.ino`：IIC 方式读取 IMU。
- `wit_c_sdk_modbus/wit_c_sdk_modbus.ino`：Modbus 方式读取 IMU。
- `wit_c_sdk_normal/wit_c_sdk_normal.ino`：普通串口方式读取 IMU。

使用流程：

1. 用 Arduino IDE 打开对应 `.ino` 文件。
2. 确认 IMU 接线、地址和通信方式。
3. 选择正确开发板和串口。
4. 上传程序到 Arduino。
5. 关闭 Arduino IDE 的串口监视器，再运行 Python 可视化工具。

串口监视器和 Python 不能同时占用同一个 COM 口。

## Python 依赖

可视化工具需要：

```powershell
C:\Python313\python.exe -m pip install pyserial numpy matplotlib
```

如果已经安装过，就不需要重复安装。

## 查看串口

从项目根目录运行：

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\IMU_jy901_Arduino\tools\imu_visualizer.py --list-ports
```

它会列出当前电脑可用的串口，例如 `COM6`。

## 运行可视化工具

直接指定串口运行：

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\IMU_jy901_Arduino\tools\imu_visualizer.py --port COM6 --baud 9600
```

如果使用配置文件：

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\IMU_jy901_Arduino\tools\imu_visualizer.py --config .\code\IMU_jy901_Arduino\tools\imu_calibration.example.json
```

## 配置文件说明

示例配置文件：

```text
tools/imu_calibration.example.json
```

主要包含：

- `serial.port`：串口号，例如 `COM6`。
- `serial.baudrate`：波特率，例如 `9600`。
- `sensors.sensor1.label`：第一个 IMU 的显示名称。
- `sensors.sensor1.address`：第一个 IMU 的地址。
- `sensors.sensor1.angle.bias_deg`：角度偏置修正。
- `sensors.sensor1.angle.scale`：角度缩放修正。
- `sensors.sensor1.angle.matrix`：坐标轴映射或姿态矩阵修正。

`sensor2` 同理。

## 常见问题

### Missing dependency

如果出现：

```text
Missing dependency: No module named 'matplotlib'
```

安装依赖：

```powershell
C:\Python313\python.exe -m pip install pyserial numpy matplotlib
```

### Serial error

可能原因：

- COM 口选错。
- Arduino IDE 串口监视器还开着。
- Arduino 没有上传对应程序。
- USB 线松动或驱动异常。
- 波特率和 Arduino 程序不一致。

### 有窗口但没有数据

优先检查：

- Arduino 串口是否真的在输出 IMU 数据。
- 两个 IMU 的地址是否正确。
- `baudrate` 是否匹配。
- 传感器供电和接线是否稳定。

## 和视觉位姿的关系

视觉位姿目录：

```text
../01_realtime_pose/
```

IMU 目录：

```text
./
```

后续如果要做视觉 + IMU 融合，可以把视觉输出的 `T_camera_marker` 和 IMU 输出的姿态统一到同一个手掌坐标系里。但这一步需要额外做坐标系标定，不能直接把两个结果简单相加。

