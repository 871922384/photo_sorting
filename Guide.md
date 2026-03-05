# 口腔照片自动分类工具 — 开发指南

> 完整开发文档，包含项目概述、技术选型、功能说明、使用方法

---

## 一、项目概述

### 背景
口腔科医生用相机为每位患者拍摄口腔照片，拍摄前先拍一张含患者信息的**二维码卡片**作为分隔标志，所有照片导入电脑后需要自动按患者分类到独立文件夹。

### 目标
一个**单文件、离线、纯 Python** 的桌面 GUI 程序，运行于**内网 Windows 电脑**，包含两个功能模块：
1. **二维码生成**：输入患者信息 → 生成并打印/显示二维码（支持全屏展示供拍摄）
2. **照片整理**：扫描导入的照片文件夹 → 识别二维码分隔符 → 自动分类到对应患者文件夹

### 技术特点
- **现代化 UI**：基于 customtkinter，浅色模式，蓝色主题
- **高 DPI 支持**：使用 CTkImage 适配高分辨率屏幕
- **全屏展示**：二维码可全屏显示，方便相机拍摄
- **后台处理**：多线程扫描，GUI 不卡顿

---

## 二、技术选型

| 用途 | 库 | 说明 |
|------|-----|------|
| GUI | `customtkinter` | 现代化 tkinter 封装，支持高 DPI |
| 二维码生成 | `qrcode[pil]` | pip 安装 |
| 二维码识别 | `pyzbar` | pip 安装，需要系统依赖 |
| 图片处理 | `Pillow` | pip 安装 |
| 打印 | `win32print` / `os.startfile` | 优先用 `os.startfile` |

### 安装命令
```bash
pip install customtkinter qrcode[pil] pyzbar Pillow
```

### Windows 上 pyzbar 的特殊依赖
`pyzbar` 在 Windows 需要 `zbar` 的 DLL：
```bash
pip install pyzbar    # 新版本通常自带 DLL
```

**备选方案**：如果 `pyzbar` 导入报错，改用 `zxing-cpp`：
```bash
pip install zxing-cpp numpy
```
代码会自动检测并使用可用的库。

---

## 三、文件结构

```
photo_sorting/
├── main.py          ← 唯一入口，所有代码写在这一个文件里
├── README.txt       ← 用户使用说明
└── Guide.md         ← 本开发指南
```

不需要任何子模块、配置文件、数据库。

---

## 四、二维码数据格式

### 编码内容（字符串）
```
NAME:张三|DATE:20240304|ID:001
```

| 字段 | 说明 | 示例 |
|------|------|------|
| NAME | 患者姓名 | 张三 |
| DATE | 就诊日期，格式 YYYYMMDD | 20240304 |
| ID | 当日序号，3 位补零 | 001 |

### 解码函数
```python
def parse_qr_content(text: str) -> dict | None:
    try:
        parts = dict(item.split(':') for item in text.split('|'))
        return {
            'name': parts['NAME'].strip(),
            'date': parts['DATE'].strip(),
            'id': parts['ID'].strip()
        }
    except Exception:
        return None
```

### 文件夹命名规则
```
{NAME}_{DATE}
示例：张三_20240304
```
如果同名文件夹已存在，自动追加 `_2`、`_3`……

---

## 五、GUI 界面设计

### 整体布局
```
┌─────────────────────────────────────────────────┐
│     口腔照片自动分类工具                        │  ← 蓝色标题栏
├─────────────────────────────────────────────────┤
│  [Tab: 生成二维码]  [Tab: 整理照片]             │  ← CTkTabview
├─────────────────────────────────────────────────┤
│                                                 │
│         （当前 Tab 内容区域）                    │
│                                                 │
├─────────────────────────────────────────────────┤
│  ●  就绪                              v1.0      │  ← 状态栏
└─────────────────────────────────────────────────┘
```

### 窗口属性
```python
root = ctk.CTk()
root.title("口腔照片自动分类工具")
root.geometry("800x560")
root.resizable(True, True)
root.minsize(700, 500)
```

### 主题设置
```python
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
```

### 颜色方案
| 元素 | 颜色 |
|------|------|
| 主按钮 | `#2563EB` → `#1D4ED8` (hover) |
| 次要按钮 | 透明 + `#2563EB` 边框 |
| 全屏按钮 | `#16A34A` → `#15803D` (hover) |
| 状态指示 | 绿 `#22C55E` / 蓝 `#3B82F6` / 橙 `#F59E0B` / 红 `#EF4444` |

### 字体统一
```python
font=("Microsoft YaHei", 13)
```

---

## 六、模块一：二维码生成 Tab

### 布局
```
┌── 生成二维码 ──────────────────────────────────┐
│                                                │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │  患者信息    │  │  二维码预览          │   │
│  │              │  │                      │   │
│  │  姓名：[___] │  │  ┌────────────┐      │   │
│  │  日期：[___] │  │  │            │      │   │
│  │  序号：[___] │  │  │  280x280   │      │   │
│  │              │  │  │  二维码    │      │   │
│  │ [生成] [清空]│  │  │            │      │   │
│  │              │  │  └────────────┘      │   │
│  │ 编码内容显示 │  │  [保存] [打印]       │   │
│  └──────────────┘  │                      │   │
│                    │ [📺 全屏展示]        │   │
│                    └──────────────────────┘   │
└────────────────────────────────────────────────┘
```

### 核心功能

**1. 输入校验**
| 字段 | 校验规则 | 错误提示 |
|------|----------|----------|
| 姓名 | 不能为空，不能包含 `\ / : * ? " < > \|` | "姓名不能包含特殊字符" |
| 日期 | 必须为 8 位数字，格式 YYYYMMDD | "日期格式错误" |
| 序号 | 1-999 的整数 | "序号须为 1-999 的整数" |

**2. 序号递增逻辑**
```python
# 正确顺序：
# 1. 读取当前序号（用于本次生成）
id_num = int(self.id_var.get().strip())

# 2. 生成二维码，编码内容用当前序号
self.current_qr_image = generate_qr_image(name, date, id_num)

# 3. 更新预览（280x280）和编码内容文本
img_size = (280, 280)
qr_resized = self.current_qr_image.resize(img_size, RESAMPLING_FILTER)
self.qr_photoimage = CTkImage(light_image=qr_resized, size=img_size)
content = f"NAME:{name}|DATE:{date}|ID:{id_num:03d}"
self.content_var.set(content)

# 4. 序号 +1，写回输入框（为下一次做准备）
next_id = id_num + 1
if next_id > 999:
    next_id = 1
self.id_var.set(f"{next_id:03d}")
```

**3. 全屏展示（重点功能）**
```python
def show_fullscreen_qr(self):
    if self.current_qr_image is None:
        return

    # 从 root 获取屏幕尺寸
    screen_w = self.root.winfo_screenwidth()
    screen_h = self.root.winfo_screenheight()

    # 创建全屏窗口（Windows 兼容方式）
    fs = tk.Toplevel(self.root)
    fs.configure(bg='black')
    fs.attributes('-topmost', True)
    fs.overrideredirect(True)  # 去掉标题栏和边框
    fs.geometry(f"{screen_w}x{screen_h}+0+0")  # 手动铺满屏幕
    fs.lift()
    fs.focus_force()

    # 二维码尺寸：屏幕高度的 68%
    qr_size = int(screen_h * 0.68)
    qr_img = self.current_qr_image.resize((qr_size, qr_size), RESAMPLING_FILTER)
    qr_photo = ImageTk.PhotoImage(qr_img)

    # 二维码居中显示
    qr_label = tk.Label(fs, image=qr_photo, bg='black')
    qr_label.image = qr_photo
    qr_label.pack(expand=True, pady=(int(screen_h * 0.04), 8))

    # 患者信息大字显示
    info_text = f"{self.name_var.get()}    {self.date_var.get()}"
    info_label = tk.Label(
        fs, text=info_text,
        font=("Microsoft YaHei", 36, "bold"),
        fg='white', bg='black'
    )
    info_label.pack(pady=(0, 16))

    # 提示文字
    hint_label = tk.Label(
        fs, text="按 ESC 键或单击任意位置关闭",
        font=("Microsoft YaHei", 13),
        fg='#6B7280', bg='black'
    )
    hint_label.pack()

    # 关闭事件绑定
    fs.bind('<Escape>', lambda e: fs.destroy())
    fs.bind('<Button-1>', lambda e: fs.destroy())
```

**关键点**：
- 使用 `overrideredirect(True)` 去掉窗口装饰
- 使用 `geometry(f"{screen_w}x{screen_h}+0+0")` 手动铺满
- 二维码占屏幕 68% 高度
- 按 ESC 或点击任意位置关闭

---

## 七、模块二：照片整理 Tab

### 布局
```
┌── 整理照片 ────────────────────────────────────┐
│                                                │
│  ┌─────────────────────────────────────────┐  │
│  │  文件夹设置                              │  │
│  │  源文件夹：[_______________] [浏览]     │  │
│  │  输出文件夹：[_____________] [浏览]     │  │
│  │  ☑ 与源文件夹相同                        │  │
│  │  操作模式：● 复制  ○ 移动               │  │
│  └─────────────────────────────────────────┘  │
│                                                │
│  [开始预览] [刷新]                            │
│  ┌─────────────────────────────────────────┐  │
│  │  预览结果（可滚动）                      │  │
│  │  [OK] 组 01  张三_20240304  (5 张)       │  │
│  │  [OK] 组 02  李四_20240304  (8 张)       │  │
│  │  [WARN] 组 03  未识别_001  (3 张)        │  │
│  └─────────────────────────────────────────┘  │
│                                                │
│  进度条 ████████░░░░░░░░  60%                │
│  [确认执行] [取消] [查看日志]                 │
└────────────────────────────────────────────────┘
```

### 核心处理流程

```
1. 用户选择源文件夹
2. 点击「开始预览」
3. 扫描文件夹内所有图片（按自然排序）
4. 逐张检测是否含二维码
5. 分组
6. 在 CTkScrollableFrame 中显示预览结果
7. 用户确认后执行文件操作
```

### 支持的图片格式
```python
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
```

### 文件名自然排序
```python
def natural_sort_key(filename: str) -> list:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r'(\d+)', filename)
    ]

files.sort(key=lambda f: natural_sort_key(os.path.basename(f)))
```

### 二维码识别（兼容多库）
```python
# 启动时检测可用库
HAS_PYZBAR = False
HAS_ZXING = False

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except ImportError:
    pass

try:
    import zxingcpp
    import numpy as np
    HAS_ZXING = True
except ImportError:
    pass

# Pillow 兼容性
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS

# 自动选择识别库
def detect_qr(filepath: str) -> str | None:
    if HAS_PYZBAR:
        return detect_qr_pyzbar(filepath)
    elif HAS_ZXING:
        return detect_qr_zxing(filepath)
    else:
        return None
```

### 分组逻辑
```python
def group_photos(sorted_files: list[str], progress_callback=None) -> list[dict]:
    groups = []
    current_group = None
    unrecognized_counter = 0

    for i, filepath in enumerate(sorted_files):
        if progress_callback:
            progress_callback(i + 1, total)

        qr_content = detect_qr(filepath)
        if qr_content is not None:
            parsed = parse_qr_content(qr_content)
            if parsed:
                if current_group:
                    groups.append(current_group)
                # 开始新组
                current_group = {
                    'name': parsed['name'],
                    'date': parsed['date'],
                    'id': parsed['id'],
                    'folder_name': f"{parsed['name']}_{parsed['date']}",
                    'photos': [],
                    'qr_photo': filepath,
                    'status': 'ok'
                }
                continue

        # 非二维码图片
        if current_group is None:
            unrecognized_counter += 1
            current_group = {
                'name': f'未识别_{unrecognized_counter:03d}',
                'folder_name': f'未识别_{unrecognized_counter:03d}',
                'photos': [],
                'qr_photo': None,
                'status': 'unrecognized'
            }

        current_group['photos'].append(filepath)

    if current_group:
        groups.append(current_group)

    return groups
```

### 后台线程处理
```python
def start_preview(self):
    self.preview_btn.configure(state="disabled")
    self.status_var.set("正在扫描，请稍候...")

    def update_progress(current, total):
        percent = current / total
        self.progress_bar.set(percent)
        self.progress_label.configure(text=f"扫描中... {current}/{total}")
        self.root.update_idletasks()

    def worker():
        try:
            files = get_sorted_images(src)
            groups = group_photos(files, update_progress)
            self.preview_groups = groups
            self.root.after(0, lambda: self.update_preview_list(groups))
            self.root.after(0, lambda: self.preview_btn.configure(state="normal"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

    threading.Thread(target=worker, daemon=True).start()
```

---

## 八、边界情况处理

| 情况 | 处理方式 |
|------|----------|
| 源文件夹为空 | 提示"文件夹中没有找到支持的图片" |
| 文件夹内无二维码 | 将所有照片归为一组 `未识别_001`，警告提示 |
| 第一张不是二维码 | 把前面的照片归入 `未识别_001` |
| 两个二维码之间没有照片 | 跳过，不创建空文件夹 |
| 二维码拍模糊 | 识别失败，当普通照片并入当前组 |
| 文件名重复 | copy/move 时追加 `_dup1`, `_dup2` 后缀 |
| 文件夹同名冲突 | 自动追加 `_2`, `_3` 等后缀 |
| 输出文件夹不存在 | 自动创建 |
| 图片文件损坏 | 跳过，记录日志 |

---

## 九、文件夹命名冲突处理

```python
def resolve_folder_name(base_path: str, folder_name: str) -> str:
    target = os.path.join(base_path, folder_name)
    if not os.path.exists(target):
        return folder_name
    counter = 2
    while os.path.exists(os.path.join(base_path, f"{folder_name}_{counter}")):
        counter += 1
    return f"{folder_name}_{counter}"
```

---

## 十、文件操作

```python
def execute_grouping(groups: list[dict], output_dir: str, mode: str = 'copy',
                     progress_callback=None) -> tuple[int, int, list]:
    success_count = 0
    fail_count = 0
    log_messages = []

    for i, group in enumerate(groups):
        try:
            folder_name = resolve_folder_name(output_dir, group['folder_name'])
            target_dir = os.path.join(output_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            # 二维码图片存入文件夹
            if group['qr_photo']:
                qr_dest = os.path.join(target_dir, os.path.basename(group['qr_photo']))
                shutil.copy2(group['qr_photo'], qr_dest)

            # 处理照片
            for photo in group['photos']:
                base_name = os.path.basename(photo)
                dest = os.path.join(target_dir, base_name)
                # 处理文件名重复
                if os.path.exists(dest):
                    name, ext = os.path.splitext(base_name)
                    counter = 1
                    while os.path.exists(dest):
                        dest = os.path.join(target_dir, f"{name}_dup{counter}{ext}")
                        counter += 1

                if mode == 'copy':
                    shutil.copy2(photo, dest)
                else:
                    shutil.move(photo, dest)

            success_count += 1
        except Exception as e:
            fail_count += 1
            log_messages.append(f"[FAIL] {group['folder_name']}: {e}")

    return success_count, fail_count, log_messages
```

---

## 十一、错误提示规范

| 级别 | 方法 | 使用场景 |
|------|------|----------|
| 信息 | `messagebox.showinfo` | 完成提示 |
| 警告 | `messagebox.showwarning` | 有未识别组、部分跳过 |
| 错误 | `messagebox.showerror` | 文件夹不存在、库未安装 |

启动时检测依赖库：
```python
if not HAS_PYZBAR and not HAS_ZXING:
    messagebox.showerror(
        "缺少依赖",
        "未找到二维码识别库。\n\n请在命令行执行：\npip install pyzbar"
    )
```

---

## 十二、HighDPI 支持

### CTkImage 使用
```python
# 导入
from PIL import Image, ImageTk
import customtkinter as ctk
CTkImage = ctk.CTkImage

# 使用
qr_resized = self.current_qr_image.resize((280, 280), RESAMPLING_FILTER)
self.qr_photoimage = CTkImage(light_image=qr_resized, size=(280, 280))
self.qr_label.configure(image=self.qr_photoimage, text="")
```

### Windows DPI 感知
```python
if __name__ == '__main__':
    root = ctk.CTk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = App(root)
    root.mainloop()
```

---

## 十三、测试建议

### 正常情况
二维码 → 5 张照片 → 二维码 → 3 张照片

### 边界情况
1. 开头无二维码：2 张普通照片 → 二维码 → 3 张照片
2. 连续二维码：二维码 → 二维码（中间无照片）
3. 只有照片无二维码：5 张普通照片
4. 同名患者同一天：两个 `张三_20240304` 组

### 全屏展示测试
1. 生成二维码后点击"全屏展示"
2. 确认窗口铺满整个屏幕
3. 确认二维码清晰可拍摄
4. 按 ESC 或点击关闭

---

## 十四、交付物

- `main.py`：单一 Python 文件，包含全部代码
- `README.txt`：给最终用户的使用说明
- `Guide.md`：本开发指南

### 系统要求
- Python 3.10+
- Windows 10/11
- 屏幕分辨率：建议 1280x720 以上

### 安装依赖
```bash
pip install customtkinter qrcode[pil] pyzbar Pillow
```

### 运行程序
```bash
python main.py
```

---

## 十五、更新日志

### v1.0
- ✅ 基于 customtkinter 的现代化 UI
- ✅ 二维码生成与全屏展示
- ✅ 照片自动分类
- ✅ HighDPI 支持（CTkImage）
- ✅ 后台多线程处理
- ✅ 进度条实时反馈
- ✅ 详细处理日志
- ✅ Windows 兼容全屏窗口
