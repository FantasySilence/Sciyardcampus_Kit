# 数苑校园工具包（Sciyardcampus Kit）接手文档

- 更新时间：2026-11-24
- 当前版本：`0.1.0`
- 当前分支：`master`（直接提交、直接推送，不开 PR）
- 远端：`git@github.com:FantasySilence/Sciyardcampus_Kit.git`
- 本文档面向后续接手开发的人；先读第 1、2、4、9、10 节即可跑起来。

---

## 1. 项目是什么

把「数苑校园」试卷预览里的题目从安卓模拟器采集下来，**逐题检查、可编辑文字**，最后按每题选择
「文字 / 图片」导出成 Word 题库。

技术形态：

- Python 3.12 后端（pywebview 的 `js_api`）；
- Vue 3 + Vite 前端（本地 HTTP 托管，WebView2 渲染）；
- 业务算法移植自 `Sciyardcampus_file_export`；
- 外壳与插件式工具注册表参考 `LSP_PlayerKit`。

两个工具：

| 工具 | 状态 | 说明 |
|---|---|---|
| 采集导出 `export` | 可用 | 采集 → 自动 OCR → 预览检查 → 导出 Word → 历史 |
| 作业发布 `publish` | 占位 | 页面 + 后端骨架，`check` 返回 `NOT_IMPLEMENTED` |

---

## 2. 当前完成度

已完成并验证：

- 整卷 / 单题型采集，复用上游切题、去重、滚动对齐；
- 预检（整屏 + 题卡框 + 题号/题型）；
- 采集任务内自动 OCR，公式/表格/图像标签；
- 检查会话持久化（关应用再打开仍在）；
- 预览剔除/恢复、单题重新识别；
- **预览文字可编辑**，700ms 防抖自动写回 txt，切题/离开/导出前强制保存；
- **每题选择 Word 呈现方式**：自动 / 文字 / 图片；
- 导出 Word，覆盖确认，打开文件/目录；
- 历史产物 + 无 session 的旧产物合成会话；
- 环境自检、一键 adb connect、数据目录自定义；
- 打包 exe（onedir）。

验证结果（最近一次）：

```powershell
.venv\Scripts\ruff.exe check src tests      # 通过
.venv\Scripts\python.exe -m pytest tests -q # 49 passed
cd web; npx vue-tsc --noEmit                # 通过
cd web; npm run build                       # 通过
```

真机验证：MuMu 12（1600×900，adb `127.0.0.1:16384`）上实际采集 2 题、OCR、导出 Word 成功。
OCR 仍有上游的识别误差（公式、个别中文），这是已知限制，不是应用层 bug。

---

## 3. 环境要求

| 项 | 本机实测值 |
|---|---|
| 系统 | Windows 11 |
| Python | 3.12.7（工作区 `.venv`） |
| WebView2 | 已安装 |
| Tesseract | `C:\Program Files\Tesseract-OCR\tesseract.exe`，含 `chi_sim` / `eng` |
| MuMu adb | `D:\BlueStacks_nxt_cn\MuMuPlayer\nx_device\15.0\shell\adb.exe` |
| Node / npm | v24.21.0 / 11.19.0 |

约束：

- **只使用工作区 `.venv`**，不要装全局 Python 包；
- 前端依赖只在 `web/node_modules`；
- 不修改两个参考仓库：
  - `D:\GitsProject\Sciyardcampus_file_export`
  - `D:\GitsProject\LSP_PlayerKit`

---

## 4. 快速启动

### 4.1 源码运行

```powershell
cd D:\GitsProject\Sciyardcampus_Kit

# 1. 虚拟环境（已有可跳过；必须 Python 3.12）
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2. 前端（首次或改前端后）
cd web
npm install
npm run build
cd ..

# 3. 启动
.venv\Scripts\python.exe main.py
```

开发热更新：

```powershell
# 终端 1
cd web; npm run dev

# 终端 2
.venv\Scripts\python.exe main.py --dev --debug
```

### 4.2 exe 运行

```powershell
dist\Sciyardcampus_Kit\Sciyardcampus_Kit.exe
```

exe 与 `_internal/` 必须放在同一个文件夹；不要单独拷 exe。
exe 不依赖本机 Python/Node，但 Tesseract 仍是外部依赖。

### 4.3 常用参数

```powershell
.venv\Scripts\python.exe main.py --data-dir "D:\some\data"
.venv\Scripts\python.exe main.py --dev --debug
```

---

## 5. 目录结构

```text
Sciyardcampus_Kit/
├─ main.py                      入口：把 src/ 加进 sys.path，调用 scikit.app.run()
├─ src/scikit/
│  ├─ const.py                  全项目唯一常量表（默认值/路径/设备/算法/设置范围）
│  ├─ app.py                    窗口、本地 HTTP、/media 路由、WebView 缓存
│  ├─ api.py                    js_api 门面：app_state / settings / tool_call / jobs / env / storage
│  ├─ jobs.py                   后台任务：Job、Reporter、JobManager、取消
│  ├─ session.py                检查会话：create/load/update/set_render_mode
│  ├─ env.py                    adb / Tesseract / 数据目录自检
│  ├─ errors.py                 AppError + 统一 {ok,data|error} 信封
│  ├─ paths.py                  资源/前端/AppData 路径
│  ├─ platform/                 与业务无关：locator/store/schema/registry/params/storage
│  ├─ device/                   adb、鼠标兜底、模拟器窗口/DPI
│  ├─ pipeline/                 切题、版面、OCR、文本整理、采集、Word、产物扫描
│  └─ tools/
│     ├─ export/                采集导出工具（manifest/schema/actions）
│     └─ publish/               作业发布占位
├─ web/
│  ├─ src/App.vue               左轨 + 命令栏 + 工作区 + 设置抽屉
│  ├─ src/platform/             bridge/i18n/theme/settings/toast/tools/jobs/media/types
│  ├─ src/tools/export/         View + StepCapture/StepReview/StepExport/HistoryPanel
│  ├─ src/tools/publish/        占位页
│  └─ dist/                     前端构建产物（Git 忽略，需 npm run build）
├─ tests/                       49 项 pytest（fixtures 在上游题卡副本）
├─ resources/
│  ├─ version.json              版本号
│  └─ images/app.ico            应用图标
├─ packaging/
│  ├─ Sciyardcampus_Kit.spec    PyInstaller onedir
│  └─ build.ps1                 一键构建前端 + 打包
├─ docs/                        README 截图
├─ dist/Sciyardcampus_Kit/      本地 exe（Git 忽略）
├─ .venv/                       工作区虚拟环境（Git 忽略）
├─ web/node_modules/            前端依赖（Git 忽略）
└─ .temp/                       中间产物目录（保留目录，内容 Git 忽略）
```

---

## 6. 运行机制

### 6.1 一次前端调用

```text
Vue 组件
  └─ invoke / callTool（web/src/platform/bridge.ts）
       └─ window.pywebview.api.xxx
            └─ scikit/api.py
                 └─ Registry.call(tool, action, payload, ctx)
                      └─ tools/<id>/actions.py
```

所有公开 API 返回信封：

```json
{ "ok": true, "data": ... }
{ "ok": false, "error": { "code": "...", "message": "...", "detail": "..." } }
```

### 6.2 长任务

采集/OCR/导出都不在 `tool_call` 里同步跑：

```text
tool_call('export','start_capture', ...)
  → { jobId }
前端 useJob() 每 500ms 调 job_status(jobId, since)
  → 增量日志 + 进度 + 最近产物 + 终态 result/error
```

- 同一时刻只允许一个任务，重复启动返回 `JOB_BUSY`；
- 取消是协作式：`Reporter.check()` / `Reporter.sleep()`；
- 任务结束写会话；OCR 失败时采集结果仍保留。

### 6.3 采集 → 导出数据流

```text
adb 截屏
  → QuestionCard.split / header_number / footer_type
  → 保存 resources/row_pngs/<题型>/<题号>.png
  → session（items: index/number/kind/png/txt/tags/included/exportMode）
  → OCR 写 row_txt/<题号>[_标签].txt
  → 预览编辑文字（写回 txt）
  → 每题选择 auto/text/image
  → docx.py 生成 resources/word_output/*.docx
```

### 6.4 会话（session）

位置：`<数据根>/.scikit/sessions/<id>.json`

关键字段：

```json
{
  "id": "12位hex",
  "scope": {"mode": "paper|type", "paper": "...", "pngType": "..."},
  "items": [
    {
      "index": 273,
      "number": 273,
      "kind": "选择题",
      "png": "resources/row_pngs/选择题/273.png",
      "txt": "resources/row_txt/选择题/273_formula.txt",
      "tags": ["formula"],
      "included": true,
      "exportMode": "auto",
      "ocrError": ""
    }
  ],
  "stats": {"total": 3, "included": 2, "textCount": 1, "imageCount": 1}
}
```

- `exportMode`：`auto`（按标签）/ `text` / `image`；
- 旧会话没有该字段时，`SessionStore.load()` 会补成 `auto`；
- 导出必须读 session 的 `included` + `exportMode`，不能重新扫目录；
- 没有 session 的旧产物在 `session_get` 时现场建 `source=files` 会话。

### 6.5 文字编辑

- 前端 `StepReview.vue` 的 `textarea` 绑定本地草稿；
- 700ms 防抖调 `tool_call('export','save_text', {sessionId,index,text})`；
- 后端写入该题现有 txt；没有 txt 时按标签生成新文件名；
- 同时清空 `ocrError`，并刷新 session；
- 切题、上一步、导出、组件卸载前都会 flush。

### 6.6 Word 呈现方式

- `auto`：有 formula/table/image 标签贴原图，否则转正文（上游行为）；
- `text`：强制使用 txt；
- `image`：强制贴 png；
- 缺文件时互相回退并写日志；
- 统计中的 `textCount` / `imageCount` 按实际模式计算，不按标签估算。

---

## 7. 数据与配置

### 7.1 默认数据根

`locator.default_dir() = app_dir()`：

- 源码运行：仓库根 → `resources/`、`.scikit/`；
- exe 运行：exe 同级 → `resources/`、`.scikit/`。

### 7.2 布局

```text
<数据根>/
├─ resources/
│  ├─ row_pngs/<题型>/*.png
│  ├─ row_txt/<题型>/*.txt
│  ├─ row_paper/<卷名>/pngs|txts/
│  └─ word_output/*.docx
└─ .scikit/
   ├─ settings/ backups/ sessions/
   ├─ probe/ thumbs/ tmp/
   └─ webview/（WebView2 缓存）
```

### 7.3 自定义目录

设置 → 数据与存储 → 更改位置，`resources/` 和 `.scikit/` 一起搬走。

也支持：

- `--data-dir <path>`；
- 环境变量 `SCIYARDKIT_DATA_DIR`；
- exe 同级 `portable.json`：`{"dataDir": "..."}`。

只读资源（图标/版本号）在打包后来自 `_internal/resources`，与用户数据 `resources/` 分开。

---

## 8. 关键设计约定

1. **常量只在 `src/scikit/const.py`**
   - `DEFAULT_TUNING`：算法默认值唯一来源；
   - `DEFAULT_EXPORT_SETTINGS`：工具出厂设置；
   - `EXPORT_FIELD_LIMITS`：设置字段范围；
   - 其它模块 `from scikit import const`，不要新增散落常量。
2. **工具之间零 import**：`tools/export` 与 `tools/publish` 互不引用。
3. **pipeline 不 import webview、不 print、不读设置**：I/O 通过参数注入。
4. **所有外部子进程隐藏窗口**：adb/Tesseract 使用 `CREATE_NO_WINDOW` + 超时。
5. **默认只走 adb**：不再静默退回鼠标截图；鼠标兜底需显式开启并自动最小化应用。
6. **导出以 session 为准**：`included` + `exportMode`，保证预览所见即导出内容。
7. **标签与文字解耦**：编辑文字不改标签；需要重判标签时点「重新识别」。

---

## 9. 测试

```powershell
# 全部（49 项，含 Tesseract 集成）
.venv\Scripts\python.exe -m pytest tests -q

# 跳过需要 Tesseract 的用例
.venv\Scripts\python.exe -m pytest tests -q -m "not ocr"

# 只跑样式/静态
.venv\Scripts\ruff.exe check src tests

# 前端
cd web
npx vue-tsc --noEmit
npm run build
```

测试目录：

| 文件 | 覆盖 |
|---|---|
| `test_textfmt.py` | 分段、公式标记、标签 |
| `test_cards.py` | 切题/裁剪/标题编号（含 OCR） |
| `test_capture_flow.py` | 假设备采集 + 真实 OCR |
| `test_session.py` | 会话、勾选、exportMode |
| `test_docx.py` | 文字/图片/剔除/显式模式 |
| `test_export.py` | 文字编辑写回、导出、覆盖 |
| `test_jobs.py` | 进度、日志、取消、互斥 |
| `test_api.py` | 信封、设置、历史、自定义目录 |
| `test_paths.py` | 默认目录与布局 |
| `test_shapes.py` | 表格/插图判断 |
| `test_boundaries.py` | 工具互不 import、pipeline 无 webview/print |

---

## 10. 打包

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
# 产物：dist\Sciyardcampus_Kit\Sciyardcampus_Kit.exe
```

- onedir；`web/dist` + `resources` 一起打包；
- PyInstaller 中间产物默认写 `.temp/build`，不污染仓库；
- spec 使用 `collect_data_files("webview")` 和 hiddenimports；
- `*.spec` 在 `.gitignore` 里，`packaging/Sciyardcampus_Kit.spec` 是强制跟踪的，改完照常 `git add`。

---

## 11. Git 约定（已与负责人确认）

1. **直接提交、直接推送到 `master`，不再开 PR。**
2. **保留 `.temp/` 目录本身**；清理中间产物时只删里面的内容，不要删目录。
   - `.temp/*` 被忽略，`.temp/.gitkeep` 保留；
   - 所有开发中间产物（spike、测试数据、日志、截图、临时构建）都放 `.temp/`。
3. Commit message 用 Conventional Commits：

```text
chore: ...
feat(backend): ...
feat(web): ...
test: ...
build: ...
docs: ...
fix: ...
```

4. 常用流程：

```powershell
git status --short
git add <paths>
git diff --cached --stat
git commit -m "feat: ..."
git push origin master
```

5. 不要提交：

- `.venv/`、`web/node_modules/`、`web/dist/`、`dist/`、`.temp/*`；
- 本地数据、会话、生成的题库产物。

---

## 12. 已知限制

- 只支持 Windows；依赖 WebView2 和 Win32 窗口/DPI。
- 识别依赖数苑页面的固定版式（红色「（x分）」标题行 + 浅灰页脚）。
- 公式/表格/图像默认贴原图；改文字导出时 OCR 精度仍有限。
- 比一屏还高的题会跳过，需要手动补截。
- 作业发布未实现，只有骨架。
- 单实例/关闭时任务确认尚未实现；退出应用会中断后台任务（已写产物保留）。
- WebView2 缓存放在数据根 `.scikit/webview/`，体积会随使用增长。
- 许可证：业务逻辑上游 MIT，界面参考 LSP_PlayerKit GPLv3（作者同为
  Fantasy_Silence）；对外分发前确认许可兼容性，见 `NOTICE`。

---

## 13. 常见问题

| 现象 | 处理 |
|---|---|
| 启动提示「前端资源缺失」 | `cd web && npm install && npm run build` |
| adb 无设备 | 启动 MuMu；点「连接」`127.0.0.1:16384`；`adb devices` 确认 |
| OCR 不可用 | 安装 Tesseract + `chi_sim`；设置里指定 `tesseract.exe` |
| 截图报 `ADB_CAPTURE_FAILED` | 模拟器没启动/掉线；重新 connect；确认分辨率 1600×900 |
| 题卡识别不到 | 确认停在试卷预览页，标题行有红色「（x分）」 |
| 采集很慢 | 属正常：滚动 + 每题标题 OCR；可减少题量 |
| 打包后没图标/没前端 | 检查 `web/dist` 存在、spec datas、hiddenimports |
| 数据找不到 | 设置 → 数据与存储；源码默认仓库根，exe 默认 exe 同级 |

---

## 14. 接手第一天检查清单

- [ ] `git switch master && git pull`
- [ ] 确认 `.venv` 是 Python 3.12.7，`pip install -r requirements-dev.txt`
- [ ] `cd web && npm install && npm run build`
- [ ] `.venv\Scripts\python.exe -m pytest tests -q`（49 passed）
- [ ] `.venv\Scripts\python.exe main.py` 能开窗
- [ ] 设置 → 数据与存储，确认数据根
- [ ] 启动 MuMu，打开一份试卷预览，点「连接 / 预检」验证 adb
- [ ] 真机采集 2 题 → 编辑文字 → 切图片模式 → 导出 Word
- [ ] 读 `src/scikit/const.py`、`tools/export/actions.py`、`session.py`、`docx.py`
- [ ] 记住：直接推 master、保留 `.temp/` 目录

---

## 15. 后续可做

1. 实现「作业发布」：登录、选卷、班级、截止时间、发布状态。
2. 单实例锁 + 关闭时任务确认。
3. 公式 OCR 后处理 / 可编辑公式（OMML）。
4. Tesseract 安装引导或便携打包（体积换开箱即用）。
5. 采集进度更细（当前题号、预计剩余时间）。
6. 题库页支持批量重识别、按标签筛选。
7. 单元测试补充：旧 session 兼容、缺图/缺 txt 回退、超大文本。
