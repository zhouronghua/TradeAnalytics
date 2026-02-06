# 安装指南

## 系统要求

- **操作系统**: Windows 10/11, macOS, Linux
- **Python版本**: 3.8 或以上
- **网络**: 需要稳定的互联网连接

## 安装步骤

### 1. 检查Python版本

打开命令行/终端，运行：

```bash
python --version
```

确保版本号为 3.8.0 或以上。如果没有安装Python，请访问 [python.org](https://www.python.org/) 下载安装。

### 2. 进入项目目录

```bash
cd E:\code\TradeAnalytics
```

### 3. 安装依赖包

#### 方法1：使用国内镜像源（推荐，速度快）

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 方法2：使用默认源

```bash
pip install -r requirements.txt
```

#### 方法3：手动安装各个包

如果上述方法失败，可以逐个安装：

```bash
pip install akshare>=1.11.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pandas>=1.5.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install numpy>=1.23.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install schedule>=1.1.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 验证安装

运行测试脚本：

```bash
python test_basic.py
```

如果所有测试通过，说明安装成功。

### 5. 启动程序

```bash
python main.py
```

## 常见问题

### 问题1：pip命令不存在

**原因**: Python未正确安装或未添加到系统PATH

**解决方案**:
- Windows: 重新安装Python，勾选"Add Python to PATH"选项
- macOS/Linux: 使用 `python3` 和 `pip3` 命令

### 问题2：pip install速度很慢

**原因**: 默认使用国外镜像源

**解决方案**: 使用国内镜像源（见上方方法1）

### 问题3：安装时出现权限错误

**Windows解决方案**:
```bash
# 以管理员身份运行命令提示符，或使用用户安装
pip install -r requirements.txt --user
```

**macOS/Linux解决方案**:
```bash
# 使用用户安装（推荐）
pip install -r requirements.txt --user

# 或使用sudo（不推荐）
sudo pip install -r requirements.txt
```

### 问题4：akshare安装失败

**原因**: 依赖冲突或网络问题

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用镜像源重试
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir
```

### 问题5：numpy编译错误（Windows）

**原因**: 缺少C++编译器

**解决方案**:
```bash
# 安装预编译的wheel包
pip install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

或访问 [这里](https://www.lfd.uci.edu/~gohlke/pythonlibs/) 下载对应版本的whl文件手动安装。

## 虚拟环境（推荐）

为了避免包冲突，建议使用虚拟环境：

### 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 在虚拟环境中安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 退出虚拟环境

```bash
deactivate
```

## 升级依赖包

如需升级到最新版本：

```bash
pip install --upgrade akshare pandas numpy schedule
```

## 卸载

如需完全卸载：

```bash
# 删除虚拟环境（如果使用了）
# Windows
rmdir /s venv

# macOS/Linux
rm -rf venv

# 卸载依赖包
pip uninstall akshare pandas numpy schedule -y
```

## 获取帮助

如果遇到其他问题，请：
1. 查看错误信息
2. 检查Python版本是否符合要求
3. 确认网络连接正常
4. 查阅 QUICK_START.md 文档
