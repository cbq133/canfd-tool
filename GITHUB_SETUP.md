# GitHub 仓库初始化指南

## 方法一：使用 GitHub 网页上传文件

### 步骤 1: 创建新仓库

1. 登录 GitHub: https://github.com
2. 点击右上角 **+** → **New repository**
3. 填写仓库信息:
   - Repository name: `canfd-tool`
   - Description: `通用CAN FD调试工具 - 支持多厂家设备`
   - 选择 **Private** (私有) 或 **Public** (公开)
   - ✅ 勾选 "Add a README file"
   - ✅ 勾选 "Add .gitignore" → 选择 "Python"
4. 点击 **Create repository**

### 步骤 2: 上传文件

1. 在仓库页面，点击 **Add file** → **Upload files**
2. 将以下文件拖拽上传:
   - `main.py`
   - `can_driver.py`
   - `requirements.txt`
   - `README.md`
   - `.github/workflows/build.yml`
3. 点击 **Commit changes**

### 步骤 3: 创建首个版本并自动构建

1. 进入仓库页面
2. 点击 **Create a new release** (在右侧栏或 Releases 页面)
3. 填写:
   - Tag version: `v1.0.0`
   - Release title: `CAN FD Tool v1.0.0`
   - Description: `初始版本`
4. 点击 **Publish release**

### 步骤 4: 下载构建好的 exe

1. GitHub Actions 会自动开始构建 (绿色进度条)
2. 构建完成后，进入 **Actions** 页面
3. 点击最新的 workflow run
4. 在 **Artifacts** 中点击 **CANFDTool-Windows** 下载

---

## 方法二：使用 Git 命令行

```bash
# 1. 在 GitHub 网页创建仓库后，克隆到本地
git clone https://github.com/你的用户名/canfd-tool.git

# 2. 进入目录
cd canfd-tool

# 3. 将文件复制到该目录
# (将 main.py, can_driver.py, requirements.txt, README.md 复制进来)
# 并创建 .github/workflows/build.yml

# 4. 添加所有文件
git add .

# 5. 提交
git commit -m "Initial commit"

# 6. 推送
git push origin main

# 7. 创建版本标签触发构建
git tag v1.0.0
git push origin v1.0.0
```

---

## 验证构建状态

1. 进入仓库 → **Actions** 页面
2. 看到绿色勾选 ✅ = 构建成功
3. 点击 workflow → **Artifacts** 下载 exe

---

## 后续更新代码

```bash
# 修改代码后
git add .
git commit -m "描述你的修改"
git push origin main

# 或创建新版本
git tag v1.1.0
git push origin v1.1.0
```

---

## 文件清单

确保上传以下所有文件:

```
canfd-tool/
├── main.py                    ✅
├── can_driver.py             ✅
├── requirements.txt          ✅
├── README.md                 ✅
├── LICENSE                   ✅
├── .gitignore                ✅
└── .github/
    └── workflows/
        └── build.yml         ✅
```
