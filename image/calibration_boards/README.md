# Calibration Boards

这个目录放相机标定用的棋盘格图片。

## 当前文件

- `checkerboard_10x7_1920x1080.png`：用于显示器投放的棋盘格 PNG。
- `checkerboard_10x7_1920x1080.svg`：同一棋盘格的矢量版本。

## 棋盘格参数

当前棋盘格为 `10x7` 个方格。OpenCV 标定时需要填写内部角点数量，所以参数是：

```text
columns = 9
rows = 6
```

如果在显示器上投放，且实测每个小方格边长是 24 mm，则标定参数为：

```text
square-size = 0.024
```

这里的单位是米。

## 标定命令

从项目根目录运行：

```powershell
cd D:\Desktop\github\glovity
C:\Python313\python.exe .\code\02_camera_calibration\calibrate_camera.py --columns 9 --rows 6 --square-size 0.024 --camera 0 --width 1280 --height 720 --min-samples 20 --output .\code\02_camera_calibration\camera_calibration.json
```

## 投放建议

- 尽量让图片按原比例显示，不要被拉伸。
- 实测屏幕上单个方格的实际边长。
- 标定时摄像头看到的是屏幕上的实际尺寸，所以以实测值为准。
- 避免屏幕反光和摩尔纹过强。
- 调整亮度，让黑白边界清晰但不过曝。

## 采集建议

标定时不要只拍正中间的一张棋盘格。建议采集：

- 中心位置。
- 四个角落。
- 不同距离。
- 不同倾斜角度。

这样求出来的相机内参和畸变参数会更稳定。

