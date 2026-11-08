# DeepSeek Moe 鼠标指针包

给 `D:\李天雄\RWCursorEditor.exe`（RealWorld Cursor Editor 2023.1 便携版）配套做的整套 Windows 指针方案，
蓝鲸少女配色（DeepSeek 品牌蓝 `#4D6BFE`）。

包含**两套**，二选一即可：

| 方案 | 普通指针 | 特点 |
|---|---|---|
| **DeepSeek Moe**（推荐） | 蓝色渐变箭头 | 精度最高，日常最省心 |
| **DeepSeek Moe Chan** | **原图抠像**当指针 | 用你给的那张画直接抠出来，热区在呆毛尖上 |

娘化版是**真的用原图**做的：`tools/ref.png` 抠掉白底和字幕，裁出头部（`whale_girl_head.png`），
按 32/48/64 三档重采样后嵌入 `.cur`；忙碌/帮助/后台运行用的是同一张脸做的圆形徽章。
热区自动取「最顶端那一行像素的中心」，也就是呆毛尖。

---

## 快速安装

双击运行其中一个（**不需要管理员权限**，只写当前用户的注册表）：

- `安装-稳重版.bat`  → DeepSeek Moe
- `安装-娘化版.bat`  → DeepSeek Moe Chan
- `还原.bat`        → 恢复安装前的指针

装完之后也会出现在
**设置 → 蓝牙和其他设备 → 鼠标 → 其他鼠标设置 → 指针** 的下拉列表里，名字是 `DeepSeek Moe`。

> 安装时会把文件复制到 `%LOCALAPPDATA%\DeepSeekMoe\Cursors`，
> 原方案备份在 `backup_cursors.json`。

---

## 为什么"绝对好用"

| 设计点 | 说明 |
|---|---|
| 热区（hotspot）精确 | 箭头顶端、I 字中心、手形指尖、十字中心都落在实际笔尖像素上，点哪就是哪 |
| 三档分辨率 | 每个光标内含 **32 / 48 / 64 px** 三张图，100% / 150% / 200% 缩放都清晰，不糊 |
| 锐利描边 | 用斜接偏移（miter offset）生成白色描边，箭头尖端保持尖锐，不是圆角糊团 |
| 轮廓克制 | 箭头 12×21 px，接近系统原生尺寸；不会挡文字、不挡链接 |
| 深浅双背景 | 蓝色填充 + 白描边 + 一圈极细深色轮廓，白底黑底都看得清 |
| 动画节制 | 忙碌 10 帧 @83ms、后台 8 帧 @100ms，循环无跳帧 |

## 文件清单

```
install.ps1                安装/还原脚本（ASCII，可单独调用）
backup_cursors.json        首次安装时自动生成的原始方案备份
cursors/                   DeepSeek Moe      16 个 .cur / .ani
cursors_moe/               DeepSeek Moe Chan 16 个 .cur / .ani
preview.png / preview_moe.png   预览图（32px 放大 3 倍）
tools/                     生成与校验脚本（Python + Pillow）
```

其中 14 个静态 `.cur`，2 个动画 `.ani`（`busy` 忙碌、`appstarting` 后台运行）。

## 想自己再改

用本机的 RealWorld Cursor Editor 直接打开即可：

```
D:\李天雄\RWCursorEditor.exe  "…\cursors\arrow.cur"
```

- 拖动热区：编辑器里 `Cursor → Set Hotspot`（或双击光标编辑热区）
- 改颜色：`Effects → Fill / Colorize`
- 导出：另存为 `.cur`（静态）或 `.ani`（动画）

重新生成整套（改了 `tools/gen_cursors.py` 之后）：

```
python tools\gen_cursors.py      # 生成两套
python tools\validate.py         # 结构校验
python tools\sheet.py cursors preview.png
```

## 说明

- 只写入 `HKCU\Control Panel\Cursors`，不改系统文件、不需要管理员。
- 卸载：运行 `还原.bat`，再删掉 `%LOCALAPPDATA%\DeepSeekMoe` 即可。
- 全屏游戏/远程桌面里部分程序会忽略自定义指针，这是 Windows 的限制。