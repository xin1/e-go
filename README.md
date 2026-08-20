# Glovity 视觉定位项目说明

这个项目当前主要围绕 ArUco / AprilTag / Find-GCP 标记识别、PnP 位姿估计和相机标定。当前已经可以通过摄像头识别标记，并实时计算标记相对摄像头的位置和姿态。

## 目录分类

- `code/01_realtime_pose/`：实时摄像头识别标记并计算手掌/标记位姿。
- `code/02_camera_calibration/`：相机标定脚本和标定结果 JSON。
- `code/03_pnp_algorithm_test/`：PnP 算法合成测试，不连接摄像头。
- `学习记录/`：开发总结和原理笔记。

## 运行实时位姿识别

推荐先进入项目根目录：

```powershell
cd D:\Desktop\github\glovity
```

如果使用当前已经识别成功的 Find-GCP 标记 ID 19，运行：

```powershell
C:\Python313\python.exe .\code\01_realtime_pose\aruco_palm_pose.py --calibration .\code\02_camera_calibration\camera_calibration.json --marker-length 0.04 --marker-id 19 --dictionary 99 --polarity both --camera 0 --width 1280 --height 720
```

如果想让程序锁定启动后检测到的第一个标记，把 `--marker-id 19` 改成 `--marker-id -1`（也可以直接省略 `--marker-id`）。锁定后不会跳到其他标记；按 `R` 可释放并重新选择：

```powershell
C:\Python313\python.exe .\code\01_realtime_pose\aruco_palm_pose.py --calibration .\code\02_camera_calibration\camera_calibration.json --marker-length 0.04 --marker-id -1 --dictionary 99 --polarity both --camera 0 --width 1280 --height 720
```

## 实时程序参数说明

- `--calibration`：相机标定文件路径，当前使用 `camera_calibration.json`。
- `--marker-length`：真实标记边长，单位是米。40 mm 就写 `0.04`。
- `--marker-id`：指定唯一追踪的标记 ID。写 `19` 表示只处理 ID 19；默认值 `-1` 表示锁定首次检测到的标记，按 `R` 可重新选择。
- `--dictionary`：标记字典。当前 Find-GCP 自定义 3x3 字典使用 `99`。
- `--polarity`：标记颜色极性。`normal` 只识别常规颜色，`inverted` 只识别黑白反相标记，`both` 会先试常规图，再试反相图。
- `--camera`：摄像头编号。一般内置或第一个 USB 摄像头是 `0`。
- `--width`：摄像头画面宽度，例如 `1280`。
- `--height`：摄像头画面高度，例如 `720`。

## 运行后的画面怎么看

画面中会显示：

- `Palm marker ID`：当前识别到的标记 ID。
- `t [m] x/y/z`：标记相对摄像头的位置，单位是米。
- `RPY [deg]`：姿态角，单位是度。
- `reprojection`：重投影误差，越小通常越好。
- `FPS`：实时运行帧率。

坐标轴含义：

- 红色轴：X 轴。
- 绿色轴：Y 轴。
- 蓝色轴：Z 轴。

相机坐标系一般可以理解为：

- X 向右。
- Y 向下。
- Z 向前，也就是从摄像头指向标记。

## 重新标定相机

标定图片在：

```text
image/calibration_boards/checkerboard_10x7_1920x1080.png
```

当前棋盘格是 `10x7` 个方格，对应 OpenCV 内角点数量：

```text
columns = 9
rows = 6
```

如果你在显示器上投放棋盘格，并且实测每个小方格边长是 24 mm，运行：

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\02_camera_calibration\calibrate_camera.py --columns 9 --rows 6 --square-size 0.024 --camera 0 --width 1280 --height 720 --min-samples 20 --output .\code\02_camera_calibration\camera_calibration.json
```

标定窗口中的操作：

- `Space`：采集当前棋盘格样本。
- `D`：删除上一张样本。
- `C`：样本数量足够后开始计算标定结果。
- `Q` 或 `Esc`：退出。

建议采集 20 张以上，角度和位置尽量变化：

- 棋盘格在画面中心。
- 棋盘格靠近画面四角。
- 棋盘格有不同倾斜角度。
- 距离摄像头有远有近。

## 运行 PnP 合成测试

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\03_pnp_algorithm_test\pnp_algorithm_test.py
```

测试结果里重点看：

- `Quality gate: PASS`：说明测试通过。
- `Inlier reproj. RMSE`：内点重投影误差。
- `Rotation error`：旋转误差。
- `Translation error`：平移误差。
- `Outliers rejected`：离群点剔除情况。

## 常见问题

### 我的标记颜色和示例相反

如果你的实体标记是最外围黑色、里面一圈白色、内部编码区为黑色，属于反相标记。当前程序默认使用：

```powershell
--polarity both
```

它会自动同时兼容常规标记和反相标记。如果你只想识别反相标记，可以写：

```powershell
--polarity inverted
```

### 显示 NO MARKER DETECTED

可能原因：

- `--dictionary` 选错了。Find-GCP 标记建议使用 `--dictionary 99`。
- 如果是反相标记，确认使用了 `--polarity both` 或 `--polarity inverted`。
- 标记太小、太远或模糊。
- 标记黑边不完整。
- 反光太强。
- 摄像头没有对焦。
- 画面曝光过亮或过暗。

### 检测到 ID，但姿态乱跳

可能原因：

- `--marker-id -1` 自动选择了不同标记面。
- 标记边长 `--marker-length` 填错。
- 相机标定文件不是当前摄像头或当前分辨率生成的。
- 标记平面不够平整，角点检测不稳定。

如果只追踪一个标记面，建议固定 ID，例如：

```powershell
--marker-id 19
```

### 出现 drawFrameAxes warning

类似提示：

```text
cv::drawFrameAxes Some of projected axes endpoints are out of frame.
```

这通常只是坐标轴画到画面外了，不代表 PnP 失败。可以把标记移到画面中间，或者后续把程序里的坐标轴长度调小。

### camera_calibration.json 是否必须

实时计算 3D 位姿时必须要。它提供相机内参和畸变参数。

但如果只是测试能不能识别标记 ID，则理论上不需要它。

## 当前推荐工作流

1. 确认 `camera_calibration.json` 存在。
2. 确认真实标记边长是 40 mm。
3. 使用 `--marker-length 0.04`。
4. 使用 `--dictionary 99`。
5. 如果当前标记 ID 是 19，优先使用 `--marker-id 19`。
6. 运行 `aruco_palm_pose.py` 查看实时位姿。
