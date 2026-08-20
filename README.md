# Glovity 

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
