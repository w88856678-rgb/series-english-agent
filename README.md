# 一集一练 · Series English Agent

**给 Agent 一集字幕，把剧里的英语变成自己的表达。**

可安装的 Skill + 宿主驱动的学习 Agent + 独立练习网页。支持真人剧和动画，不限定《老友记》。Python 3.9+，零第三方 Python 依赖，无需 npm 构建。

![练习网页](docs/preview.png)

## 能做什么

- 读取 SRT / VTT / TXT 字幕，制作词义、IPA、原创例句和中文解释。
- 核验词汇出现的位置；跨集重复表达保留为复习词。
- 在网页逐词学习、隐藏中文、听词组和例句、调语速、连续跟读。
- 标记待复习 / 已掌握，按 1、3、7、14、30 天安排复习。
- 导出或恢复进度，把导出文件交给 Agent 做针对性练习。
- 导出 Anki CSV 和 Markdown 笔记。

**Agent 运行在 Codex 等支持 Skill、文件操作和命令执行的宿主中。网页没有内置聊天模型，也不会自行搜索字幕。** 模型调用使用宿主账号与额度，本工具不收集 API 密钥。搜索能力取决于宿主；没有搜索工具时可直接导入用户字幕。

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

如果未安装 Skill，也可在仓库中让 Agent 阅读 `skills/series-english/SKILL.md` 并遵循它。详细工作流程见 [学习 Agent](docs/agent.md)。

## 手动制作或检查课程

先让 Agent 按 [课程格式](skills/series-english/references/course-format.md) 编写课程 JSON；CLI 负责解析、验证和写入，不会自动理解词义。

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

欢迎通过 Issue 报告复现步骤，通过 PR 提交修改。请使用原创或获授权的小型样例，不上传完整商业剧集字幕、个人学习记录或 API 密钥。安全报告方式见 [SECURITY.md](SECURITY.md)。

## 许可与致谢

项目代码和原创示例采用 [MIT License](LICENSE)。追剧提词的初始工作流参考 **狗哥笔记的 gbro-series-vocab**，保留其 [MIT 声明](LICENSES/gbro-series-vocab-MIT.txt)。本项目扩展了课程网页、证据校验、跨集复习与进度导出，使用原创练习句；并非原作者官方产品。

开源代码许可不授予影视字幕、视频或第三方音频的使用权。请自行确认所导入及公开分享内容的权利。第三方说明见 [NOTICE.md](NOTICE.md)。
