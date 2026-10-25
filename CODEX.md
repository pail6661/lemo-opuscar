# Lemo-Opuscar：Codex / ChatGPT 使用说明

这是 **Lemo-Opuscar 的 Codex 适配版**，保留 Lemomo / LemoLab 原作的 59 种正式风格、导演指南、个人风格流程、音频和渲染工具，并补充 Windows 原生安装、工具启动器及 Codex Skill。

原项目：[lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar)。原作者的 Claude 插件仍在 `plugin/`，继续按原方式使用；这份适配不需要把它安装到 Claude。

## 使用位置

在 **Codex App 或 Codex CLI** 中打开本仓库，通过当前已登录的 Codex 会话和用户选择的模型制作视频。无需另办 Claude 账号，也无需为核心流程配置额外 API key。模型调用遵循你现有 Codex 的使用额度；本项目不会替你购买额度。

ChatGPT 可以讨论选题、脚本、画面和修改意见。有本地执行能力的 Codex 负责写文件、调用工具和渲染。普通浏览器中的 ChatGPT 对话不会自动读取电脑上的 Skill，也不能只凭聊天完成本地渲染；需要把任务交给具有本地工具的执行环境。

原风格为 Claude 调校，适配入口并不等于已经证明所有风格在当前模型下达到同等画质。每支新片仍须检查实际成片。原指南中的模型名称说明样片来源，不要求 Codex 切换模型。

## Windows 原生准备

需要可用的 PowerShell、Git、Node.js 20+、Python 3.11–3.12 和 FFmpeg。已有 uv 时，安装器会为新环境选择 Python 3.12，无需改动系统 Python；离线中文前端的已发布版本暂不支持 Python 3.13。此适配的共享渲染与音频流程可以在 Windows 原生运行；上游一些独立样片仍包含 `sh`、macOS 工具或额外依赖，不能把“核心工具已安装”说成“59 支旧样片都已在 Windows 重建”。

在仓库根目录的 PowerShell 中运行：

```powershell
# 只检查当前环境。
& .\tools\setup-codex.ps1 -Diagnose

# 安装核心依赖：浏览器渲染、Python 音频与图像处理。
& .\tools\setup-codex.ps1 -Tier core

# 将 Codex Skill 安装到当前 CODEX_HOME/skills。
& .\tools\setup-codex.ps1 -InstallSkill
```

如果系统执行策略拦截脚本，可在一次子进程中使用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup-codex.ps1 -Tier core
```

这不会永久更改系统执行策略。缺少系统工具时先按诊断补齐；依赖安装结果以脚本输出和实际检查为准。

按片子需要增加依赖和资源：

```powershell
# 仅需要配音时安装：Kokoro、在线中文TTS入口、语音识别检查。
& .\tools\setup-codex.ps1 -Tier voice

# 仅拨弦物理建模需要这一层；普通采样器属于core。
& .\tools\setup-codex.ps1 -Tier music

# 仅下载本片所需的大资源。
& .\tools\setup-codex.ps1 -Assets voice
& .\tools\setup-codex.ps1 -Assets hdri
& .\tools\setup-codex.ps1 -Assets instruments-karoryfer
```

`voice`、`music` 层隐含 `core`。大资源还包括乐器采样包，具体支持名称以安装脚本为准；不必为试做一支片下载所有采样库。模型、字体、三维资源和公开数据各自沿用原许可。

安装器和 `tools/lemo.ps1` 负责恢复已配置的缓存位置与仓库虚拟环境；通常无需每次手工设置环境变量。库内 Python 环境在 `.venv/`，Windows 可执行文件为 `.venv/Scripts/python.exe`。风格专有依赖应装进片子的独立环境，避免影响共享工具。

## 安装后的 Skill

重新打开一个 Codex 对话，或刷新其技能列表后，用 `$lemo-opuscar` 调用。可以直接描述题材：

> 用 $lemo-opuscar 做一支 30 秒的中文白板讲解视频，讲咖啡为什么会让人清醒。竖屏 1080×1920，先给我看分镜，再出完整工程。

Skill 按以下顺序找库：当前目录及父目录中的本仓库 → `LEMO_OPUSCAR_HOME` → 本地安装时生成的 `library-path.txt`。最后一项仅存在于安装到本机的 Skill 中，公开 Skill 不写入任何人的电脑路径。移动仓库后，重新安装或设置 `LEMO_OPUSCAR_HOME`。安装器遇到指向另一份库的同名 Skill 会拒绝覆盖，应先明确要保留哪份。

也可不安装 Skill，直接在 Codex 中打开本仓库并说明“按 `CODEX.md` 制作视频”。Skill 是可复用入口，不是模型或外部服务。

## 四种入口

| 想做什么 | 可以这样说 |
|---|---|
| 用库里的风格做片 | “用水彩笔刷做一支 40 秒的咖啡品牌故事，中文旁白。” |
| 改一个风格 | “把瑞士动态排版改成我的品牌风格，保留网格，使用我的品牌色。” |
| 从空白创建风格 | “做一个暖色黑板粉笔画风格，动作慢一些，先验证样张。” |
| 用已保存的个人风格做片 | “用我的夜浮世绘风格做下一集，讲夜市的一碗面。” |

可用中文名、英文名或文件夹名指定风格。还没决定时，Codex 会按题材推荐，并展示完整风格清单。全部 **59 种、11 类** 见 [风格索引](styles/README.md)；[在线图库](https://lemomo-ai.github.io/lemo-opuscar/)可看样片。`styles/_template` 是模板，不计入 59 种。

[OPUSCAR98](https://lemomo-ai.github.io/lemo-opuscar/opuscar98/#styles) 另有 98 个风格提示词、镜头拆解与示例片段；它是一份独立附录，不等于 98 个完整的 `styles/` 工程。

### 全部 59 种风格

以下按仓库的 [catalog.json](styleboard/catalog.json) 整理，各风格的素材、画法、镜头与声音要求见 [完整索引](styles/README.md)链接的 `STYLE.md`。

| 类别 | 数量 | 风格 |
|---|---:|---|
| 剪辑与纪实 | 8 | 字幕新闻、1920s 新闻影片、实时倒计时分屏、延时交响、视觉调查、构成主义蒙太奇、体育战术板、电视新闻包装 |
| 实证影像 | 8 | 卫星简报、工程简报板、点云测绘、白模投影、数据实物化、产品拆解、显微叙事、档案灯台 |
| 手绘与绘画 | 7 | 蜡笔儿童绘本、水彩笔刷、中国水墨、油画厚涂、一笔画、白板讲解、钢笔淡彩 |
| 东方传统 | 4 | 皮影戏、浮世绘、红色窗花剪纸、纸雕灯影 |
| 印刷与版画 | 5 | Risograph 孔版印刷、复古半调案卷、木刻版画、铜版画、丝印旅行海报 |
| 图形与排版 | 7 | 瑞士动态排版、60s 间谍片头、装饰艺术、蓝图 / 工程制图、彩色玻璃窗、象形运动图形、ASCII / CRT 终端 |
| 信息与发布 | 5 | 数据叙事、等距信息图、暗色科技发布、活体实机录屏、科幻全息界面 |
| 卡通与动画 | 4 | 1930s 橡皮管卡通、80 年代赛璐璐动画、科幻情景喜剧卡通、50s 扁平卡通 |
| 游戏 | 4 | 16-bit 像素 RPG、HD-2D、微游戏快闪、综艺节奏扁平 |
| 电影与时代 | 2 | 1920s 默片、后室 / 新怪谈 |
| 材质与 3D | 5 | 积木玩具、纸片立体书、移轴微缩、低多边形等距、玻璃质感产品 |

### 图库和参考片页面

| 页面 | 已有能力 | 源码证据 |
|---|---|---|
| [59 种风格图库](https://lemomo-ai.github.io/lemo-opuscar/) | 按 11 类筛选、记住上次类别、显示封面/时长/适用场景、弹层播放样片、打开完整风格说明。完整质量视频在 GitHub Releases；样片绘制源码在各风格的 `demo/`。 | [页面模板](styleboard/template.html)、[生成器](styleboard/build.py) |
| [OPUSCAR98](https://lemomo-ai.github.io/lemo-opuscar/opuscar98/#styles) | 中英切换、按年代和 2D/2.5D/3D 筛选、关键词搜索、复制风格提示词、展开镜头与导演编排、定位/循环单个片段、小窗播放、下载整片 1080p。 | [页面源码](styleboard/opuscar98/index.html)、[98 条参考数据](styleboard/opuscar98_styles.json) |

主图库没有独立字幕轨开关或完整剪辑界面；它用来选风格和看参考。帖子预告的 Lemo Movie Studio / MCP 制作工作台和未来日系动漫批次，未包含在本次适配中。仓库里的 `tools/directory/` 是“Claude 插件目录发行版”的构建模板，不是这个图形工作台，见 [上游维护说明](MAINTAINING.md#directory-edition)。

## 保留的制作能力

- **画面：** Canvas 二维动画、WebGL 着色器、Three.js 三维场景、材质、景深、环境光和后期效果；以时间函数逐帧绘制，可精确定位任意时刻。
- **导演：** 原创内容方案、叙事、节奏、镜头、角色表演、风格样张、可选故事板；借用样片的技法，重新组织自己的内容。
- **真实素材：** 剪辑纪实类可组织录像、照片、档案、文件和数据；实证影像类可使用卫星图、点云、CAD/PCB、显微图等。真实产品拆解需要真实工程文件，不能凭宣传图伪造准确结构。
- **配音：** 离线 Kokoro 及中文在线 TTS 入口、用户已有录音、逐句语音识别检查和时间戳。使用在线服务前说明会发送旁白文字，并依用户授权选择；可以使用离线方案。
- **配乐音效：** 采样乐器、拨弦物理建模、程序合成、逐事件音效、压缩、背景音乐避让和混音。
- **字幕：** 跟随画面设计的字幕，以及单独导出的 SRT；配音与字幕默认使用用户的沟通语言。
- **输出：** 默认 1920×1080、24fps，可指定竖屏、尺寸和帧率；支持多进程渲染、静帧、接触表、MP4、封面和完整源码。
- **检查：** 页面错误、文字阅读时长、动作关键帧、配音识别、响度、黑帧、素材和事实来源；自动工具检查后仍应观看成片。
- **个人风格：** 基于现成风格或从空白建立、样张对照、15–30 秒测试片、命名保存并重复使用；用户风格放在库外，更新库时保留。

这套工具通过代码作画和组织素材，不下载视频扩散模型。需要生图、图生视频或收费服务的特殊方案须另行接入，不能默认已经包含。普通裁剪与转码也不必调用完整导演流程。

## 原生工具入口

统一通过 `tools/lemo.ps1` 调用共享工具。数组形式适合中文目录和带空格的文件名：

```powershell
$filmRoot = Join-Path $PWD 'films/my-first-film'
$lemoTool = Join-Path $PWD 'tools/lemo.ps1'

# 前提：片子已有index.html，并实现READY、DUR和render(t)。
& $lemoTool -Tool still -Arguments @($filmRoot, '1.5', '--size', '1920x1080')
& $lemoTool -Tool events -Arguments @($filmRoot)
& $lemoTool -Tool readcheck -Arguments @($filmRoot)
& $lemoTool -Tool render -Arguments @($filmRoot, '--fps', '24', '--out', "$filmRoot/out/video.mp4")

# 前提：项目的配乐/混音源码已经实际生成mix.wav。
& $lemoTool -Tool mux -Arguments @("$filmRoot/out/video.mp4", "$filmRoot/out/mix.wav", "$filmRoot/my-first-film.mp4", '24', '0')
```

支持 `still`、`render`、`events`、`readcheck`、`mux`、`tts`、`tts-zh`、`asr`、`srt`、`sheet`、`fetch`。参数含义见 [工具参考](core/README.md)；`render` 对应 `video.mjs`，`mux` 对应跨平台的 `core/render/mux.py`。`mux` 最后两个位置参数为帧率与胶片颗粒强度，`0` 关闭颗粒。

配音例子（先安装 voice 层和所需模型）：

```powershell
& $lemoTool -Tool tts -Arguments @("$filmRoot/lines.json", "$filmRoot/voices")
& $lemoTool -Tool asr -Arguments @("$filmRoot/lines.json", "$filmRoot/voices", '--lang', 'en')
```

中文离线 Kokoro 的 `lines.json` 设置 `lang: "cmn"` 并使用可用的 `zf_*` 或 `zm_*` 音色。voice 层包含 `misaki[zh]`，将中文转换为当前 Kokoro v1.0 模型匹配的普通话音素；不直接套用英文/espeak 的中文读法。英文仍使用原来的前端。在线中文入口为 `tts-zh`，使用前须具备对应服务授权。语音检查、模型或素材下载失败时应报告真实错误，不把准备完成当成制作完成。

底层也可直接调用 Node 和仓库 Python。例如 Windows 下：

```powershell
& .\.venv\Scripts\python.exe .\core\render\mux.py video.mp4 mix.wav film.mp4 24 0
```

新片在 Windows 交付 `build.ps1`，把该片的绘制、音频、渲染和合成串起来；需要 POSIX 时再附 `build.sh`。上游示例命令中的 `.venv/bin/python`、`sh .../mux.sh` 和 `build.sh` 按本节替换，不要求安装 Claude。样片专属脚本若依赖 shell 工具，应只在新片工程内移植所需操作，不修改原库来迁就一支片。

## 从选题到交付

1. 明确主题、必需事实和素材、语言、时长、尺寸，以及是否先审分镜；已经给过的信息不再问。
2. 读取选定风格和导演/技术指南，在项目目录写原创 `TREATMENT.md`，再看样片源码学技法。剪辑纪实类先整理真实来源；个人风格创建按 `MY-STYLES.md` 的顺序进行。
3. 用真正的绘制代码出样张。用户要求审故事板时，在该处停下来让用户看；未要求时继续制作。
4. 制作声音、画面和字幕；渲染并混音。新片工程默认位于 `films/<名字>/`，也可用用户指定的输出目录；不把作品写进 `styles/`。
5. 检查接触表、关键动作、文字、语音、响度和黑帧，再完整观看带声音的最终文件并修正。有任何未完成的验收应明确指出。
6. 交付实际 MP4、`poster.jpg`、需要时的 SRT、`TREATMENT.md`、`CREDITS`、完整源码和 `build.ps1`。事实片保留 `FACTS.md`；不能把方案、样张或单项工具成功说成完整成片。

个人风格流程另见 [MY-STYLES.md](MY-STYLES.md)：先方案，再样张和测试片，经确认才加入个人风格索引。默认存在 `~/lemo-my-styles/`，也可指定其它目录；不要覆盖原风格或已有同名个人风格。

## 与上游的关系和授权

原始 [AGENTS.md](AGENTS.md)、[DIRECTOR.md](DIRECTOR.md)、[TECHNIQUE.md](TECHNIQUE.md)、59 种 `STYLE.md` 及 `plugin/` 保留。Codex 入口只适配执行环境、安装方式和命令；原 Claude 插件仍可独立使用。上游仍建议其原 Windows 用户使用 WSL，这份 fork 的 Windows 原生工具不自动改变上游支持承诺。

- 代码与文档为 MIT，保留原作者和许可证；复制的样片源码保留其 MIT 信息。
- 原样片及静帧为 CC BY 4.0，转载、改编、商用须按原说明署名 LemoLab、链接原库并注明是否修改；第三方素材另看各片 `CREDITS`。
- 用库做出的新片归用户，无需添加 LemoLab 片尾或水印；应保留实际第三方素材所需的署名和许可说明。
- 原 README 明确排除了三段配音的复用授权：综艺节奏扁平、纸雕灯影、电视新闻包装的指定配音。新片用本地 TTS、自己的录音或有权使用的声音，避免直接搬用。

完整授权边界见 [原中文说明](README.zh-CN.md#授权)和 [LICENSE](LICENSE)。本地安装、运行和产物不会自动发布到社交平台或上传给其他人。
