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
- **现代化 UI**：基于 customtkinter，Fluent + 医疗风格设计
- **玻璃质感卡片**：半透明背景，轻盈柔和
- **高 DPI 支持**：使用 CTkImage 适配高分辨率屏幕
- **全屏展示**：二维码可全屏显示，方便相机拍摄
- **后台处理**：多线程扫描，GUI 不卡顿
- **配置持久化**：自动保存用户设置
- **日志系统**：完整操作日志记录

---

## 二、技术选型

| 用途 | 库 | 说明 |
|------|-----|------|
| GUI | `customtkinter` | 现代化 tkinter 封装，支持高 DPI |
| 二维码生成 | `qrcode[pil]` | pip 安装 |
| 二维码识别 | `pyzbar` | pip 安装，需要 DLL 依赖 |
| 备选识别 | `zxing-cpp` | pyzbar 不可用时的备选 |
| 图片处理 | `Pillow` | pip 安装 |
| 打印 | `os.startfile` | Windows 系统调用 |

### 安装命令
```bash
pip install -r requirements.txt
```

或手动安装：
```bash
pip install customtkinter qrcode[pil] pyzbar Pillow zxing-cpp numpy
```

### Windows 上 pyzbar 的特殊依赖
`pyzbar` 在 Windows 需要 `zbar` 的 DLL，新版本通常自带。打包 exe 时需要手动添加 DLL 文件。

---

## 三、文件结构

```
photo_sorting/
├── main.py              ← 唯一入口，所有代码写在这一个文件里
├── requirements.txt     ← 依赖列表
├── README.txt           ← 用户使用说明
└── Guide.md             ← 本开发指南
```

### 用户数据目录
```
~/.photo_sorting/
├── config.json          ← 用户配置（文件夹路径、操作模式等）
└── photo_sorting.log    ← 运行日志
```

---

## 四、Design Tokens（视觉规范）

### 颜色体系

| 用途 | 颜色 | 说明 |
|------|------|------|
| 页面背景 | `#F3F4F6` | 轻盈、柔和、医疗感 |
| 卡片背景 | `#FFFFFFCC` | 半透明白，模拟玻璃 |
| 卡片边框 | `#E5E7EB` | 低对比度、柔和 |
| 主色（按钮） | `#2A7BF4` | Fluent 蓝 |
| 主色 hover | `#1E63D8` | 深一点的蓝 |
| 次按钮背景 | `#F9FAFB` | 白灰色 |
| 次按钮边框 | `#D1D5DB` | 轻边框 |
| 文本主色 | `#1F2937` | 深灰，不用纯黑 |
| 文本次色 | `#6B7280` | 标签、提示文字 |
| 成功色 | `#22C55E` | 绿色 |
| 警告色 | `#F59E0B` | 橙色 |
| 错误色 | `#EF4444` | 红色 |

### 字体体系

| 用途 | 字号 | 字重 |
|------|------|------|
| 标题（Section Title） | 16px | Medium |
| 标签（Label） | 14px | Regular |
| 输入框文字 | 14px | Regular |
| 按钮文字 | 14px | Medium |
| 提示文字 | 12px | Regular |

字体优先级：`Microsoft YaHei UI` > `Segoe UI`

### 间距体系

| 用途 | 数值 |
|------|------|
| 页面左右边距 | 24px |
| 卡片之间 | 24px |
| 卡片内边距 | 20px |
| 表单行距 | 12px |
| 按钮之间 | 8px |

### 圆角体系

| 组件 | 圆角 |
|------|------|
| 卡片 | 16px |
| 输入框 | 12px |
| 按钮 | 12px |
| 二维码预览框 | 16px |

### DesignTokens 类

```python
class DesignTokens:
    COLOR_PAGE_BG = "#F3F4F6"
    COLOR_CARD_BG = "#FFFFFFCC"
    COLOR_CARD_BORDER = "#E5E7EB"
    COLOR_PRIMARY = "#2A7BF4"
    COLOR_PRIMARY_HOVER = "#1E63D8"
    COLOR_SECONDARY_BG = "#F9FAFB"
    COLOR_SECONDARY_BORDER = "#D1D5DB"
    COLOR_TEXT_PRIMARY = "#1F2937"
    COLOR_TEXT_SECONDARY = "#6B7280"
    COLOR_SUCCESS = "#22C55E"
    COLOR_WARNING = "#F59E0B"
    COLOR_ERROR = "#EF4444"
    
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_SIZE_TITLE = 16
    FONT_SIZE_LABEL = 14
    FONT_SIZE_INPUT = 14
    FONT_SIZE_BUTTON = 14
    FONT_SIZE_HINT = 12
    
    SPACING_PAGE = 24
    SPACING_CARD = 24
    SPACING_CARD_PADDING = 20
    SPACING_FORM_ROW = 12
    SPACING_BUTTON = 8
    
    RADIUS_CARD = 16
    RADIUS_INPUT = 12
    RADIUS_BUTTON = 12
    RADIUS_PREVIEW = 16
    
    HEIGHT_INPUT = 40
    HEIGHT_BUTTON = 42
    QR_PREVIEW_SIZE = 260
    
    @classmethod
    def font_title(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_TITLE, "bold")
    
    @classmethod
    def font_label(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_LABEL)
    
    @classmethod
    def font_button(cls):
        return ctk.CTkFont(cls.FONT_FAMILY, cls.FONT_SIZE_BUTTON, "bold")
```

---

## 五、二维码数据格式

### 编码内容（字符串）
```
NAME:张三|DATE:20240304|ID:001
```

| 字段 | 说明 | 示例 |
|------|------|------|
| NAME | 患者姓名 | 张三 |
| DATE | 就诊日期，格式 YYYYMMDD | 20240304 |
| ID | 当日序号，3 位补零 | 001 |

### 文件夹命名规则
```
{NAME}_{DATE}
示例：张三_20240304
```
如果同名文件夹已存在，自动追加 `_2`、`_3`……

---

## 六、配置管理

### Config 单例类

```python
class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config_dir = Path.home() / '.photo_sorting'
        self.config_file = self.config_dir / 'config.json'
        self._defaults = {
            'src_folder': '',
            'dest_folder': '',
            'same_folder': True,
            'mode': 'copy',
            'last_qr_name': '',
            'last_qr_id': 1,
            'window_geometry': '800x560'
        }
        self._config = self._load()
    
    def save(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    @property
    def src_folder(self) -> str:
        return self._config.get('src_folder', '')
    
    @src_folder.setter
    def src_folder(self, value: str):
        self.set('src_folder', value)
```

### 持久化内容
- 源文件夹路径
- 输出文件夹路径
- 是否与源文件夹相同
- 操作模式（复制/移动）
- 上次输入的患者姓名
- 上次使用的序号
- 窗口大小位置

---

## 七、日志系统

### 配置

```python
def setup_logging():
    log_dir = Path.home() / '.photo_sorting'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'photo_sorting.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
```

### 日志记录点
- 程序启动/关闭
- 配置加载/保存
- 二维码识别结果
- 照片分组进度
- 文件操作详情
- 错误信息

---

## 八、GUI 界面设计

### 整体布局
```
┌─────────────────────────────────────────────────┐
│  [Tab: 生成二维码]  [Tab: 整理照片]             │  ← CTkTabview
├─────────────────────────────────────────────────┤
│                                                 │
│         （当前 Tab 内容区域）                    │
│         玻璃质感卡片布局                         │
│                                                 │
├─────────────────────────────────────────────────┤
│  ●  就绪                                        │  ← 状态栏
└─────────────────────────────────────────────────┘
```

### 窗口属性
```python
root = ctk.CTk()
root.title("口腔照片自动分类工具")
root.geometry(config.get('window_geometry', '800x560'))
root.resizable(True, True)
root.minsize(700, 500)
root.configure(fg_color=DesignTokens.COLOR_PAGE_BG)
```

### 玻璃质感卡片

```python
card = ctk.CTkFrame(
    parent,
    corner_radius=DesignTokens.RADIUS_CARD,
    fg_color=DesignTokens.COLOR_CARD_BG,
    border_width=1,
    border_color=DesignTokens.COLOR_CARD_BORDER
)
```

### 主按钮样式

```python
btn = ctk.CTkButton(
    parent,
    text="生成二维码",
    fg_color=DesignTokens.COLOR_PRIMARY,
    hover_color=DesignTokens.COLOR_PRIMARY_HOVER,
    corner_radius=DesignTokens.RADIUS_BUTTON,
    height=DesignTokens.HEIGHT_BUTTON,
    font=DesignTokens.font_button(),
    text_color=DesignTokens.COLOR_WHITE
)
```

### 次按钮样式

```python
btn = ctk.CTkButton(
    parent,
    text="清空",
    fg_color=DesignTokens.COLOR_SECONDARY_BG,
    hover_color=DesignTokens.COLOR_SECONDARY_HOVER,
    border_width=1,
    border_color=DesignTokens.COLOR_SECONDARY_BORDER,
    text_color=DesignTokens.COLOR_TEXT_PRIMARY,
    corner_radius=DesignTokens.RADIUS_BUTTON,
    height=DesignTokens.HEIGHT_BUTTON,
    font=DesignTokens.font_button()
)
```

---

## 九、模块一：二维码生成 Tab

### 布局
```
┌── 生成二维码 ──────────────────────────────────┐
│                                                │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 患者信息     │  │ 二维码预览           │   │
│  │              │  │                      │   │
│  │ 患者姓名     │  │  ┌────────────┐      │   │
│  │ [________]   │  │  │            │      │   │
│  │              │  │  │  260x260   │      │   │
│  │ 就诊日期     │  │  │  二维码    │      │   │
│  │ [________]   │  │  │            │      │   │
│  │              │  │  └────────────┘      │   │
│  │ 当日序号     │  │                      │   │
│  │ [________]   │  │ 生成后可保存或全屏   │   │
│  │              │  │                      │   │
│  │ [生成二维码] │  │ [保存] [打印]        │   │
│  │ [清空]       │  │ [📺 全屏展示]        │   │
│  │              │  │                      │   │
│  │ 编码内容     │  │                      │   │
│  │ NAME:...     │  │                      │   │
│  └──────────────┘  └──────────────────────┘   │
└────────────────────────────────────────────────┘
```

### 标签在输入框上方布局

```python
# 标签
ctk.CTkLabel(
    card,
    text="患者姓名",
    font=DesignTokens.font_label(),
    text_color=DesignTokens.COLOR_TEXT_SECONDARY
).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

# 输入框（撑满宽度）
ctk.CTkEntry(
    card,
    textvariable=self.name_var,
    height=DesignTokens.HEIGHT_INPUT,
    font=DesignTokens.font_input(),
    corner_radius=DesignTokens.RADIUS_INPUT,
    fg_color=DesignTokens.COLOR_WHITE,
    text_color=DesignTokens.COLOR_TEXT_PRIMARY
).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
```

### 全屏展示

```python
def show_fullscreen_qr(self):
    fs = tk.Toplevel(self.root)
    fs.configure(bg='black')
    fs.attributes('-fullscreen', True)
    fs.attributes('-topmost', True)
    fs.overrideredirect(True)
    fs.focus_force()
    
    fs.update_idletasks()
    screen_w = fs.winfo_width()
    screen_h = fs.winfo_height()
    
    qr_size = int(min(screen_w, screen_h) * 0.65)
    qr_img = self.current_qr_image.resize((qr_size, qr_size), RESAMPLING_FILTER)
    qr_photo = ImageTk.PhotoImage(qr_img)
    
    container = tk.Frame(fs, bg='black')
    container.place(relx=0.5, rely=0.5, anchor='center')
    
    qr_label = tk.Label(container, image=qr_photo, bg='black')
    qr_label.image = qr_photo
    qr_label.pack(pady=(0, 20))
    
    fs.bind('<Escape>', lambda e: fs.destroy())
    fs.bind('<Button-1>', lambda e: fs.destroy())
```

---

## 十、模块二：照片整理 Tab

### 布局
```
┌── 整理照片 ────────────────────────────────────┐
│                                                │
│  ┌─────────────────────────────────────────┐  │
│  │ 文件夹设置                               │  │
│  │                                          │  │
│  │ 源文件夹                                 │  │
│  │ [________________________] [浏览]        │  │
│  │                                          │  │
│  │ 输出文件夹                               │  │
│  │ [________________________] [浏览]        │  │
│  │                                          │  │
│  │ ☑ 与源文件夹相同                         │  │
│  │ 操作模式 ● 复制  ○ 移动                 │  │
│  └─────────────────────────────────────────┘  │
│                                                │
│  [开始预览] [刷新]                             │
│  ┌─────────────────────────────────────────┐  │
│  │  预览结果（可滚动）                      │  │
│  │  [OK] 组 01  张三_20240304  (5 张)       │  │
│  │  [OK] 组 02  李四_20240304  (8 张)       │  │
│  │  [WARN] 组 03  未识别_001  (3 张)        │  │
│  └─────────────────────────────────────────┘  │
│                                                │
│  进度条 ████████░░░░░░░░                      │
│  [确认执行] [取消] [查看日志]                  │
└────────────────────────────────────────────────┘
```

### 支持的图片格式
```python
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
```

### 后台线程处理
```python
def worker():
    try:
        files = get_sorted_images(src)
        groups = group_photos(files, update_progress)
        self.preview_groups = groups
        self.root.after(0, lambda: self.update_preview_list(groups))
    except Exception as e:
        logger.error(f"预览失败: {e}")
        self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

threading.Thread(target=worker, daemon=True).start()
```

---

## 十一、错误处理规范

### 精确异常捕获

```python
# 二维码内容解析
def parse_qr_content(text: str) -> dict | None:
    try:
        parts = dict(item.split(':') for item in text.split('|'))
        return {
            'name': parts['NAME'].strip(),
            'date': parts['DATE'].strip(),
            'id': parts['ID'].strip()
        }
    except (ValueError, KeyError) as e:
        logger.debug(f"二维码内容解析失败: {text}, 错误: {e}")
        return None

# 文件操作
def execute_grouping(...):
    try:
        ...
    except PermissionError as e:
        logger.error(f"权限错误: {group['folder_name']}, {e}")
    except OSError as e:
        logger.error(f"系统错误: {group['folder_name']}, {e}")
    except Exception as e:
        logger.error(f"处理失败: {group['folder_name']}, {e}")
```

---

## 十二、打包发布

### PyInstaller 命令

```bash
pyinstaller --onefile --windowed --name "口腔照片自动分类工具" --clean \
    --add-binary "pyzbar路径\libiconv.dll;pyzbar" \
    --add-binary "pyzbar路径\libzbar-64.dll;pyzbar" \
    main.py
```

### 注意事项
1. pyzbar 的 DLL 需要手动添加
2. 首次运行可能被 Windows Defender 拦截
3. 程序会在用户目录创建配置和日志文件

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
- `requirements.txt`：依赖列表
- `README.txt`：给最终用户的使用说明
- `Guide.md`：本开发指南

### 系统要求
- Python 3.10+
- Windows 10/11
- 屏幕分辨率：建议 1280x720 以上

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

---

## 十五、更新日志

### v1.1
- ✅ Fluent + 医疗风格 UI 重设计
- ✅ Design Tokens 视觉规范系统
- ✅ 玻璃质感卡片组件
- ✅ 配置持久化功能
- ✅ 标准日志系统
- ✅ 精确异常捕获
- ✅ requirements.txt 依赖管理

### v1.0
- ✅ 基于 customtkinter 的现代化 UI
- ✅ 二维码生成与全屏展示
- ✅ 照片自动分类
- ✅ HighDPI 支持（CTkImage）
- ✅ 后台多线程处理
- ✅ 进度条实时反馈
- ✅ 详细处理日志
- ✅ Windows 兼容全屏窗口
