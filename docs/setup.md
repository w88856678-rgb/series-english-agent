# 安装、运行与开发指南

日常怎么学，请先看 [产品首页](../README.md)。这份文档供首次安装、手动制作课程和开发时查阅。

运行环境：Python 3.9+，不需要安装第三方 Python 包或构建网页。学习 Agent 使用 Codex 等宿主的模型与工具；没有联网搜索能力时，可导入自己的字幕。

## 先体验网页（无需模型）

```sh
git clone https://github.com/w88856678-rgb/series-english-agent.git
cd series-english-agent
python3 skills/series-english/scripts/course.py init --library library --demo
python3 skills/series-english/scripts/course.py serve --library library --port 8765
```

打开 **http://127.0.0.1:8765/**。Windows 可把 `python3` 换成 `python`。示例是原创短剧 Coffee & Plans 的两节课程，共 15 条记录、12 个不同表达，第二节含 3 个复习词。**这不是《老友记》台词或原声。**

`init` 拒绝非空目录。已有课程库直接 `serve`，不要重新初始化。端口被占用时换一个端口，不要停止其他应用。

## 安装 Skill，开始和 Agent 学习

```sh
python3 scripts/install_skill.py
```

默认安装到 `$CODEX_HOME/skills/series-english`，未设置时为 `~/.codex/skills/series-english`。重新加载宿主的技能列表。其他支持相同 Skill 格式的宿主，可用 `--dest <技能父目录>` 指定位置；兼容性需按宿主能力确认。安装器不会覆盖已有 Skill。

示例请求：

> 用 $series-english 帮我学《海绵宝宝》第一季第一集。中文释义，B1 水平，课程保存在我的新课程库里。

> 用 $series-english 把这个 SRT 做成英语课程，每集最多 50 个实用表达，重复的保留为复习词。

> 用 $series-english 根据我导出的学习进度复习，先练 5 个词，一次问我一题。

如果未安装 Skill，也可在仓库中让 Agent 阅读 `skills/series-english/SKILL.md` 并遵循它。详细工作流程见 [学习 Agent](agent.md)。

## 手动制作或检查课程

先让 Agent 按 [课程格式](../skills/series-english/references/course-format.md) 编写课程 JSON；CLI 负责解析、验证和写入，不会自动理解词义。

```sh
python3 skills/series-english/scripts/course.py prepare subtitles.srt --source "用户提供的字幕" --output private/evidence.json
python3 skills/series-english/scripts/course.py validate private/lesson.json --evidence private/evidence.json
python3 skills/series-english/scripts/course.py add private/lesson.json --evidence private/evidence.json --library library
python3 skills/series-english/scripts/course.py export my-series-s01e01 --library library --output exports
```

`add` 默认拒绝覆盖同集，明确更新时加 `--replace`。证据文件放在 `private/`，不放网站目录。`sourceLine` 和 `sourceForm` 会从网页数据中移除。跨集复习按同剧季、集排序重算，与导入顺序无关。

Anki：导入生成的 CSV，指令头已设置 Basic 卡片与字段。正面是原创英文例句，背面是译文、表达释义与音标。

## 发音、进度与边界

- 发音由浏览器和操作系统的英语语音提供，优先选择美式声音；可选声音与品质因设备而异。有些声音可能需要网络，取决于设备提供商。缺少声音时页面给出提示，不声称已播放。
- 没有录音、发音评分或剧集原声。连续跟读会播放词组和例句，再留出跟读时间。
- 进度存储在当前浏览器、当前网址下。更换端口、设备或清理浏览器数据前，请导出备份；恢复时按更新时间合并，不覆盖更新的记录。
- Agent 通过用户主动导出的文件读取进度，不会实时读取浏览器状态；不会自动发通知。
- 词形存在不等于词义正确。验证器检查结构和出现位置，语境、IPA、例句仍需 Agent 审校。每集最多 50 个是默认目标，不为凑数虚构表达。

## 部署与隐私

生成的 `library/` 是独立静态网站，可部署到静态托管服务，包括 GitHub Pages。这是可选操作，推送代码不会自动公开你的课程。发布前仅选择有权分享的课程库。此仓库不包含个人《老友记》课程、数据库、绝对私人路径、字幕缓存或预生成第三方音频。

本地服务器只监听 `127.0.0.1`，只用于个人学习。没有多用户账号、云端进度同步或服务器模型 API。如果要做在线聊天产品，需要另外设计身份验证、密钥存储、模型后端与用量限制。

## 开发与贡献

```sh
python3 -m unittest discover -s tests -v
node --check skills/series-english/assets/web/app.js
```

Python 工具测试覆盖字幕解析、无依据表达拒绝、重复与路径校验、反序导入、拒绝覆盖、导出和安装后的独立运行。GitHub Actions 在 Linux、macOS、Windows 上执行检查；网页语音仍须按设备实际测试。

欢迎通过 Issue 报告复现步骤，通过 PR 提交修改。请使用原创或获授权的小型样例，不上传完整商业剧集字幕、个人学习记录或 API 密钥。安全报告方式见 [SECURITY.md](../SECURITY.md)。

