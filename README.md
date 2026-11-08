# DeepSeek Moe 鼠标指针包

一套适用于 Windows 的 DeepSeek 风格鼠标指针方案，采用品牌蓝 `#4D6BFE`。无需依赖特定电脑或用户目录；安装脚本会将光标文件复制到当前 Windows 用户的本地应用数据目录。

包含**两套**方案，任选其一安装：

| 方案 | 普通指针 | 特点 |
|---|---|---|
| **DeepSeek Moe**（推荐） | 蓝色渐变箭头 | 外观简洁，适合日常使用 |
| **DeepSeek Moe Chan** | 插画头像指针 | 使用项目内素材制作，热区位于呆毛尖端 |

娘化版使用 `tools/ref.png` 作为素材，去除背景和字幕后裁出头部（`whale_girl_head.png`），按 32/48/64 三档尺寸重采样并嵌入 `.cur` 文件；忙碌、帮助和后台运行指针使用同一头像制作圆形徽章。热区自动设置在最顶端像素行的中心。

---

## 快速安装

在 Windows 上双击运行以下脚本之一（**不需要管理员权限**，只修改当前用户的指针设置）：

- `安装-稳重版.bat` → DeepSeek Moe
- `安装-娘化版.bat` → DeepSeek Moe Chan
- `还原.bat` → 恢复安装前的指针设置

安装后，可在 **设置 → 蓝牙和其他设备 → 鼠标 → 其他鼠标设置 → 指针** 中选择已安装的方案。

> 安装程序会将光标文件复制到 `%LOCALAPPDATA%\DeepSeekMoe\Cursors`，并在首次安装时备份原有指针方案到 `backup_cursors.json`。

---

## 设计特点

| 设计点 | 说明 |
|---|---|
| 热区精确 | 箭头尖端、I 字中心、手形指尖和十字中心对准对应的指针位置 |
| 三档分辨率 | 光标包含 **32 / 48 / 64 px** 尺寸，适配常见显示缩放比例 |
| 清晰描边 | 使用斜接偏移生成白色描边，尽量保持箭头尖端清晰 |
| 尺寸适中 | 箭头约 12×21 px，尽量减少对文字和链接的遮挡 |
| 深浅背景兼容 | 蓝色填充、白色描边和细深色轮廓便于在不同背景下辨认 |
| 动画指针 | 忙碌指针 10 帧 @83ms，后台运行指针 8 帧 @100ms |

## 文件清单

```
install.ps1                    安装/还原脚本（ASCII，可单独调用）
backup_cursors.json            首次安装时自动生成的原始方案备份
cursors/                       DeepSeek Moe，16 个 .cur / .ani
cursors_moe/                   DeepSeek Moe Chan，16 个 .cur / .ani
preview.png / preview_moe.png  预览图（32px 放大 3 倍）
tools/                         生成与校验脚本（Python + Pillow）
```

每套方案包含 14 个静态 `.cur` 文件和 2 个动画 `.ani` 文件（`busy` 忙碌、`appstarting` 后台运行）。

## 编辑光标

可以用 RealWorld Cursor Editor 打开项目中的 `.cur` 文件进行编辑。先从下方官网获取编辑器，再通过编辑器的 **File → Open** 打开，例如 `cursors/arrow.cur`。

- 调整热区：`Cursor → Set Hotspot`（或双击光标编辑热区）
- 修改颜色：`Effects → Fill / Colorize`
- 导出：另存为 `.cur`（静态）或 `.ani`（动画）

### RealWorld Cursor Editor 下载

- [官网产品与下载页面](https://www.rw-designer.com/cursor-maker)
- [便携版 ZIP（32 位）](https://www.rw-designer.com/userdata/rw_cursor_editor/RWCursorEditor32.zip)
- [便携版 ZIP（64 位）](https://www.rw-designer.com/userdata/rw_cursor_editor/RWCursorEditor64.zip)

官网下载页面可能更新版本信息；如需指定版本，请在下载前确认页面标注的版本号与系统架构。

## 从源码重新生成

修改 `tools/gen_cursors.py` 后，可运行：

```
python tools\gen_cursors.py      # 生成两套指针
python tools\validate.py         # 结构校验
python tools\sheet.py cursors preview.png
```

## 说明

- 安装程序只写入 `HKCU\Control Panel\Cursors`，不修改系统文件，也不需要管理员权限。
- 卸载时运行 `还原.bat`，之后可删除 `%LOCALAPPDATA%\DeepSeekMoe`。
- 部分全屏游戏或远程桌面程序可能忽略自定义指针，这是 Windows 或相关程序的限制。
- 重新生成指针需要 Python 和 Pillow；仅安装和使用已生成的光标文件不需要这些开发依赖。
