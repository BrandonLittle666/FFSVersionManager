# FreeFileSync 版本查看器

一个用于查看 FreeFileSync 同步文件历史版本的图形界面工具。

![](https://minioapi.shaunnet.xyz:443/picgo/20250518232712316.png "软件界面")

## 功能特点

- 支持打开多个 FreeFileSync 配置
- 右键菜单快速查看文件历史版本
- 单实例运行，避免重复启动
- 支持拖放文件查看历史版本
- 支持通过sqlite数据库管理文件备注

## 系统要求

- Windows 10 或更高版本
- Python 3.12 或更高版本
- FreeFileSync 11.0 或更高版本
- uv 包管理器

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/BrandonLittle666/FFSVersionManager.git
cd FFSVersionManager
```

2. 同步依赖：

```bash
uv sync
```

## 使用方法

### 启动程序

```bash
uv run main.py
```

### 添加配置

1. 点击工具栏的"添加配置"按钮
2. 选择 FreeFileSync 的批处理文件（.ffs_batch）

### 查看文件历史版本

1. 在文件资源管理器中右键点击文件
2. 选择"查看文件历史版本"
3. 程序会显示该文件的所有历史版本

### 快捷键

- `Esc`: 隐藏主窗口
- `Ctrl+Q` 真正退出程序

### 工具栏功能

- **添加配置**: 添加新的 FreeFileSync 同步配置
- **显示配置**: 显示已添加的同步配置
- **注册右键菜单**: 注册文件右键菜单（需要管理员权限）
- **删除右键菜单**: 删除文件右键菜单（需要管理员权限）
- **重置窗口**: 重置窗口大小和位置
- **刷新**: 刷新文件历史列表

### 文件历史视图

- 显示文件的所有历史版本
- 显示文件大小和修改时间
- 支持双击打开文件
- 支持右键菜单操作

### 备注功能

右键点击历史文件面板（右侧面板）中的某个文件，会显示 `查看备注` 和 `编辑备注` 两个选项。编辑的备注会保存再 `%HOME%/FFSVersionManager/ffs_file_remarks.db` 目录下的数据库文件中

## 配置说明

配置文件为 `%Home%/FFSVersionManager/config.toml` 

配置文件包含：

- 已添加的ffs配置列表
- 窗口位置和大小
- 列宽设置

## 注意事项

1. 注册右键菜单需要管理员权限
2. 确保 FreeFileSync 的批处理文件路径正确

## 常见问题

1. **无法找到历史版本**

   - 检查同步配置是否正确添加
   - 确认文件是否被同步过
2. **程序无法启动**

   - 检查 Python 版本
   - 确认所有依赖已安装
   - 查看日志文件

## 开发说明

### 项目结构

```
FFSVersionManager/
├── src/
│   ├── core/           # 核心功能模块
│   ├── gui/            # 图形界面模块
|   ├── res/            # 资源文件
|   ├── const           # 常量
│   └── utils           # 工具函数模块
└── main                # 入口
```

### 构建发布版本

使用 uv 构建发布版本：

```bash
# 需要安装 nuitka

.\install.bat

```

构建完成后，可以在 `build` 目录下找到构建好的可执行文件。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request
