# UI 视觉重设计 Spec

## Why
当前界面使用的是较为基础的 customtkinter 样式，需要按照设计师提供的 Fluent + 医疗风格视觉规范进行全面升级，提升用户体验和专业感。

## What Changes
- 重构颜色体系，采用 Fluent + 医疗风格配色
- 优化字体体系，使用轻盈感的 Windows 11 推荐字体
- 调整布局间距，建立统一的 Spacing System
- 实现玻璃质感卡片组件
- 重新设计输入框、按钮等组件样式
- 优化 Tab 视图和整体页面结构

## Impact
- Affected code: `main.py` 中所有 UI 相关代码
- Affected components: App 类中的 `init_qr_tab()`, `init_sort_tab()`, `create_widgets()`, `create_status_bar()` 方法

## ADDED Requirements

### Requirement: 颜色体系
系统应采用以下颜色规范：
- 页面背景：#F3F4F6
- 卡片背景（玻璃）：#FFFFFFCC
- 卡片边框：#E5E7EB
- 主色（按钮）：#2A7BF4
- 主色 hover：#1E63D8
- 次按钮背景：#F9FAFB
- 次按钮边框：#D1D5DB
- 文本主色：#1F2937
- 文本次色：#6B7280

#### Scenario: 颜色一致性
- **WHEN** 用户查看任意界面元素
- **THEN** 所有颜色应符合设计规范中定义的颜色值

### Requirement: 字体体系
系统应使用以下字体规范：
- 标题（Section Title）：16px，Medium
- 标签（Label）：14px，Regular
- 输入框文字：14px
- 按钮文字：14px，Medium
- 提示文字：12px，Regular
- 字体优先级：Microsoft YaHei UI > Segoe UI

### Requirement: 布局间距
系统应使用以下间距规范：
- 页面左右边距：24px
- 卡片之间：24px
- 卡片内边距：20px
- 表单行距：12px
- 按钮之间：8px
- 大组件之间：16px

### Requirement: 圆角体系
系统应使用以下圆角规范：
- 卡片：16px
- 输入框：12px
- 按钮：12px
- 二维码预览框：16px

### Requirement: 玻璃质感卡片
卡片组件应具有玻璃质感：
- 半透明白背景：#FFFFFFCC
- 轻边框：1px #E5E7EB
- 圆角：16px
- 内部留白大、元素稀疏

### Requirement: 输入框组件
输入框应符合以下规范：
- 高度：40px
- 圆角：12px
- 字体：14px
- 背景：白色（不透明）

### Requirement: 按钮组件
按钮应符合以下规范：
- 主按钮：背景 #2A7BF4，Hover #1E63D8，高度 42px，圆角 12px
- 次按钮：背景 #F9FAFB，边框 1px #D1D5DB，Hover #E5E7EB

### Requirement: 二维码预览框
二维码预览框应符合以下规范：
- 尺寸：260 × 260
- 背景：纯白
- 圆角：16px
- 居中显示
- 下方提示文字（12px 灰色）

### Requirement: Tab 视图
Tab 视图应符合以下规范：
- Tab 高度：48px
- 字体：14px
- 选中态：蓝色下划线 + 深色文字
- 未选中态：灰色文字

### Requirement: 患者信息卡片布局
患者信息卡片应采用标签在上方、输入框宽度撑满的设计：
- 标签在输入框上方
- 输入框宽度撑满卡片
- 行距统一 12px
- 卡片圆角 16px，半透明背景

## MODIFIED Requirements

### Requirement: 整体页面结构
页面结构应调整为：
- 顶部 Tab（生成二维码 / 整理照片）
- Section 1：患者信息卡片
- Section 2：二维码预览卡片
- Section 3：操作按钮区
