# JavSP 项目详解

## 项目概述

JavSP（Jav Scraper Package）是一个汇总多站点数据的 AV 元数据刮削器。它能够从影片文件名中提取番号信息，自动抓取并汇总多个站点的数据，按照指定的规则分类整理影片文件，并创建供 Emby、Jellyfin、Kodi 等媒体管理软件使用的元数据文件。

**核心功能**：
- 自动识别影片番号
- 支持处理影片分片
- 汇总多个站点的数据生成 NFO 数据文件
- 多线程并行抓取
- 下载高清封面
- 基于 AI 人体分析裁剪素人等非常规封面的海报
- 自动检查和更新新版本
- 翻译标题和剧情简介

## 项目结构

```
JavSP/
├── config.yml                    # 主配置文件
├── pyproject.toml               # Python 项目配置（使用 Poetry）
├── README.md                    # 项目说明文档
├── CHANGELOG.md                 # 版本变更日志
├── LICENSE                      # 许可证文件
├── setup.py                     # 旧版安装脚本
├── poetry.lock                  # Poetry 依赖锁文件
├── .gitignore                   # Git 忽略文件
├── .dockerignore                # Docker 忽略文件
├── .envrc                       # direnv 环境配置
│
├── data/                        # 数据文件
│   ├── actress_alias.json      # 女优别名映射（用于 normalize_actress_name 功能）
│   ├── genre_avsox.csv         # AVSOX 站点分类翻译数据
│   ├── genre_javbus.csv        # JavBus 站点分类翻译数据
│   ├── genre_javdb.csv         # JavDB 站点分类翻译数据
│   └── genre_javlib.csv        # JavLib 站点分类翻译数据
│
├── docker/                      # Docker 配置
│   └── Dockerfile              # Docker 构建文件
│
├── image/                       # 图片资源
│   ├── JavSP.svg               # 项目 Logo
│   ├── sub_mark.png            # 字幕标记图标
│   └── unc_mark.png            # 无码标记图标
│
├── javsp/                       # 核心代码
│   ├── __main__.py             # 程序入口点
│   ├── avid.py                 # 番号识别相关
│   ├── chromium.py             # Chromium 浏览器相关
│   ├── config.py               # 配置管理（Pydantic 模型）
│   ├── datatype.py             # 数据类型定义
│   ├── file.py                 # 文件操作相关
│   ├── func.py                 # 通用功能函数
│   ├── image.py                # 图片处理相关
│   ├── lib.py                  # 库函数
│   ├── nfo.py                  # NFO 文件生成
│   ├── print.py                # 打印输出相关
│   ├── prompt.py               # 用户提示交互
│   │
│   ├── cropper/                # 封面裁剪模块
│   │   └── ...                 # AI 人脸识别裁剪
│   │
│   └── web/                    # 网络爬虫模块
│       ├── base.py             # 基础爬虫类
│       ├── exceptions.py       # 爬虫异常定义
│       ├── translate.py        # 翻译功能
│       ├── proxyfree.py        # 免代理地址管理
│       ├── airav.py            # Airav 爬虫
│       ├── avsox.py            # AVSOX 爬虫
│       ├── avwiki.py           # AVWiki 爬虫
│       ├── dl_getchu.py        # Getchu 爬虫
│       ├── fanza.py            # Fanza 爬虫
│       ├── fc2.py              # FC2 爬虫
│       ├── fc2fan.py           # FC2Fan 爬虫
│       ├── fc2ppvdb.py         # FC2PPVDB 爬虫
│       ├── gyutto.py           # Gyutto 爬虫
│       ├── jav321.py           # Jav321 爬虫
│       ├── javbus.py           # JavBus 爬虫
│       ├── javdb.py            # JavDB 爬虫
│       ├── javlib.py           # JavLib 爬虫
│       ├── javmenu.py          # JavMenu 爬虫
│       ├── mgstage.py          # MGStage 爬虫
│       ├── njav.py             # NJav 爬虫
│       ├── prestige.py         # Prestige 爬虫
│       ├── arzon.py            # Arzon 爬虫
│       └── arzon_iv.py         # Arzon IV 爬虫
│
├── tools/                       # 工具脚本
│   ├── airav_search.py         # Airav 搜索工具
│   ├── call_crawler.py         # 爬虫调用测试工具
│   ├── check_genre.py          # 分类检查工具
│   ├── config_migration.py     # 配置文件迁移工具
│   └── version.py              # 版本管理工具
│
└── unittest/                    # 单元测试
    └── ...                     # 测试文件
```

## 核心模块详解

### 1. 配置系统 (`config.py`)

JavSP 使用 `confz` 库进行配置管理，支持多种配置源：
- **YAML 配置文件** (`config.yml`)：主配置文件
- **环境变量**：前缀为 `JAVSP_`，支持嵌套配置（如 `JAVSP_SCANNER_INPUT_DIRECTORY`）
- **命令行参数**：使用 `-o` 前缀（如 `-oscanner.input_directory '/path'`）

配置模型使用 Pydantic 进行验证，确保类型安全。主要配置类别包括：

- **Scanner**：文件扫描配置（忽略模式、文件扩展名、最小文件大小等）
- **Network**：网络配置（代理、重试次数、超时时间、免代理地址）
- **Crawler**：爬虫配置（站点选择、必需字段、工作模式等）
- **Summarizer**：数据汇总和文件整理配置（命名规则、NFO 生成、封面处理等）
- **Translator**：翻译配置（引擎选择、API 密钥、翻译字段）
- **Other**：其他配置（交互模式、更新检查等）

### 2. 主程序流程 (`__main__.py`)

程序的主要执行流程：

1. **初始化配置**：加载并验证配置文件
2. **导入爬虫模块**：根据配置动态导入所需的爬虫
3. **扫描影片文件**：在指定目录中扫描符合条件的视频文件
4. **识别番号**：从文件名中提取番号信息
5. **多线程抓取**：并行从多个站点抓取元数据
6. **数据汇总**：合并多个来源的数据，按优先级选择最佳信息
7. **翻译处理**：可选地翻译标题和剧情简介
8. **文件整理**：根据命名规则创建目录和文件
9. **封面下载**：下载封面图片并进行 AI 裁剪处理
10. **NFO 生成**：创建媒体服务器兼容的元数据文件
11. **文件移动**：将整理好的文件移动到目标目录

### 3. 爬虫系统 (`web/` 目录)

JavSP 支持多个 AV 数据源站点，每个站点对应一个独立的爬虫模块：

**支持的站点**：
- `airav`, `avsox`, `avwiki`, `dl_getchu`, `fanza`, `fc2`, `fc2fan`, `fc2ppvdb`
- `gyutto`, `jav321`, `javbus`, `javdb`, `javlib`, `javmenu`, `mgstage`
- `njav`, `prestige`, `arzon`, `arzon_iv`

**爬虫分类**：
- **normal**：普通番号（如 ABC-123）
- **fc2**：FC2 系列番号
- **cid**：内容 ID（如 `cid:sqte00300`）
- **getchu**：Getchu 游戏
- **gyutto**：Gyutto 同人作品

每个爬虫模块必须实现 `parse_data()` 函数，接收 `MovieInfo` 对象并填充数据。

### 4. 数据处理 (`datatype.py`)

定义了核心的数据类型：

- **Movie**：影片信息，包含文件路径、番号、数据源等
- **MovieInfo**：从网站抓取的元数据，包含标题、演员、封面 URL、分类等

### 5. 文件整理系统

**命名规则系统**：
支持使用变量模板生成文件路径和名称，可用变量包括：
- `{num}`：番号
- `{title}`：标题
- `{actress}`：女优
- `{series}`：系列
- `{director}`：导演
- `{producer}`：制作商
- `{publisher}`：发行商
- `{censor}`：打码情况
- `{label}`：标签

**路径生成**：
```yaml
output_folder_pattern: '#整理完成/{actress}/[{num}] {title}'
basename_pattern: '{num}'
```

### 6. 数据文件系统 (`data/` 目录)

JavSP 使用本地数据文件来支持特定的功能，这些文件在程序运行时被加载和使用：

#### 6.1 `actress_alias.json` - 女优别名映射
**用途**：当配置 `crawler.normalize_actress_name: true` 时，用于统一女优的多个艺名。
**数据结构**：JSON 格式，键为固定名称，值为该女优的所有别名列表。
**示例**：
```json
{
  "新ありな": ["新有菜", "新ありな", "橋本ありな", "上乃木まな", "岩谷志季", "橋本有菜"],
  "三上悠亞": ["三上悠亜", "三上悠亞", "鬼头桃菜"]
}
```
**使用时机**：在数据汇总阶段，程序会将抓取到的女优名称与别名映射进行匹配，将不同的别名统一为固定名称。

#### 6.2 `genre_*.csv` - 分类翻译数据
**用途**：为各个站点的分类标签提供统一的翻译，确保生成的 NFO 文件中的分类信息易于理解且保持一致。
**支持站点**：
- `genre_avsox.csv` - AVSOX 站点分类
- `genre_javbus.csv` - JavBus 站点分类  
- `genre_javdb.csv` - JavDB 站点分类
- `genre_javlib.csv` - JavLib 站点分类

**数据结构**：CSV 格式，包含以下列：
- `id`：分类的唯一标识符
- `url`：分类的页面 URL
- `zh_tw`/`zh_cn`：繁体/简体中文名称
- `ja`：日文名称
- `en`：英文名称
- `translate`：翻译后的名称（程序实际使用的翻译）
- `note`：备注信息（如为何删除某些标签）

**使用时机**：在生成 NFO 文件时，程序会将抓取到的原始分类标签转换为统一的翻译版本。

#### 6.3 数据文件的维护
**更新工具**：`tools/check_genre.py` 脚本用于抓取各站点的最新分类数据并生成 CSV 文件。
**维护流程**：
1. 运行脚本获取最新分类数据
2. 人工校对翻译，确保准确性和一致性
3. 将翻译后的数据保存到对应的 CSV 文件
4. 程序运行时自动加载这些翻译数据

### 7. AI 封面裁剪 (`cropper/`)

使用 Slimeface 进行 AI 人脸识别，自动裁剪素人等非常规封面：
- 识别特定番号系列（如 `^\d{6}[-_]\d{3}$`, `^ARA`, `^SIRO` 等）
- 自动裁剪封面以突出主体
- 可添加水印标记（字幕、无码等）

## 安装与运行

### 使用 Poetry（推荐）

```bash
# 克隆项目
git clone https://github.com/Yuukiy/JavSP.git
cd JavSP

# 安装依赖
poetry install

# 运行程序
poetry run javsp
```

**注意**：由于项目使用动态版本控制和 Poetry 虚拟环境，请务必使用 `poetry run javsp` 或先激活虚拟环境（`poetry shell`）后再运行 `python -m javsp`。直接使用系统 Python 运行 `python -m javsp` 可能导致包元数据查找失败。

### 使用 Docker

```bash
# 拉取镜像
docker pull ghcr.io/yuukiy/javsp:latest

# 运行容器
docker run -v /path/to/videos:/videos -v /path/to/config:/app/config ghcr.io/yuukiy/javsp:latest
```

### 直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python -m javsp
```

## 配置详解

### 基本配置步骤

1. **复制配置文件**（如需要自定义）：
   ```bash
   cp config.yml config.custom.yml
   ```

2. **编辑配置文件**：
   - 设置 `scanner.input_directory`：指定要整理的视频目录
   - 配置 `network.proxy_server`：如有需要，设置代理服务器
   - 调整 `crawler.selection`：选择要使用的爬虫站点
   - 自定义 `summarizer.path`：设置文件整理规则

3. **运行程序**：
   ```bash
   poetry run javsp -c config.custom.yml
   ```

### 重要配置项

#### 扫描配置
```yaml
scanner:
  input_directory: null  # 留空时会在运行时询问
  filename_extensions: [.3gp, .avi, .f4v, .flv, .iso, .m2ts, .m4v, .mkv, .mov, .mp4, .mpeg, .rm, .rmvb, .ts, .vob, .webm, .wmv, .strm, .mpg]
  minimum_size: 232MiB  # 忽略小于此大小的文件
```

#### 网络配置
```yaml
network:
  proxy_server: null  # 代理服务器，如 'http://127.0.0.1:1080'
  retry: 3  # 网络错误重试次数
  timeout: PT10S  # 超时时间（ISO 8601 格式）
```

#### 爬虫配置
```yaml
crawler:
  selection:
    normal: [airav, avsox, javbus, javdb, javlib, jav321, mgstage, prestige]
    fc2: [fc2, avsox, javdb, javmenu, fc2ppvdb]
    cid: [fanza]
  required_keys: [cover, title]  # 必须获取的字段
  use_javdb_cover: fallback  # 优先使用非 JavDB 封面避免水印
```

#### 整理配置
```yaml
summarizer:
  move_files: true  # 是否移动文件
  path:
    output_folder_pattern: '#整理完成/{actress}/[{num}] {title}'
    basename_pattern: '{num}'
  cover:
    highres: true  # 下载高清封面
    add_label: false  # 在封面添加标签
```

#### 翻译配置
```yaml
translator:
  engine: null  # 翻译引擎：google, bing, baidu, claude, openai
  fields:
    title: true  # 翻译标题
    plot: true   # 翻译剧情简介
```

## 使用示例

### 基本使用
```bash
# 使用默认配置
poetry run javsp

# 指定配置文件
poetry run javsp -c /path/to/config.yml

# 通过命令行参数覆盖配置
poetry run javsp -- -oscanner.input_directory '/path/to/videos'
```

### 环境变量配置
```bash
# 设置扫描目录
export JAVSP_SCANNER_INPUT_DIRECTORY='/path/to/videos'

# 设置代理
export JAVSP_NETWORK_PROXY_SERVER='http://127.0.0.1:1080'

# 运行程序
poetry run javsp
```

### Docker 使用
```bash
# 基本运行
docker run -v /host/videos:/videos ghcr.io/yuukiy/javsp:latest

# 使用自定义配置
docker run -v /host/videos:/videos -v /host/config.yml:/app/config.yml ghcr.io/yuukiy/javsp:latest -c /app/config.yml

# 设置环境变量
docker run -v /host/videos:/videos -e JAVSP_SCANNER_INPUT_DIRECTORY=/videos ghcr.io/yuukiy/javsp:latest
```

## 自定义配置

### 1. 文件命名规则

可以通过修改 `summarizer.path.output_folder_pattern` 和 `summarizer.path.basename_pattern` 来自定义文件整理方式：

```yaml
summarizer:
  path:
    # 按制作商和系列整理
    output_folder_pattern: '#整理完成/{producer}/{series}/[{num}] {title}'
    
    # 按女优整理（最多10人）
    # output_folder_pattern: '#整理完成/{actress}/[{num}] {title}'
    
    # 按发行日期整理
    # output_folder_pattern: '#整理完成/{publish_date|%Y-%m}/{num} {title}'
```

### 2. 爬虫优先级调整

调整 `crawler.selection` 中站点的顺序可以改变数据获取的优先级：

```yaml
crawler:
  selection:
    normal: [javdb, javbus, avsox, airav]  # JavDB 优先
```

### 3. 封面处理

```yaml
summarizer:
  cover:
    highres: true  # 下载高清封面（8-10MB）
    crop:
      engine:  # 启用 AI 裁剪
        name: slimeface
      on_id_pattern:  # 对特定番号系列使用 AI 裁剪
        - '^\d{6}[-_]\d{3}$'  # 如 123456-789
        - '^ARA'  # ARA 系列
        - '^SIRO'  # SIRO 系列
```

### 4. 翻译设置

```yaml
translator:
  engine:
    name: google  # 使用 Google 翻译（免费）
  # 或使用百度翻译
  # engine:
  #   name: baidu
  #   app_id: 'your_app_id'
  #   api_key: 'your_api_key'
```

## 故障排除

### 常见问题

1. **无法识别番号**
   - 检查文件名是否包含干扰信息
   - 调整 `scanner.ignored_id_pattern`
   - 使用手动模式检查番号识别

2. **网络连接失败**
   - 检查代理设置 `network.proxy_server`
   - 调整超时时间 `network.timeout`
   - 检查免代理地址是否有效

3. **封面下载失败**
   - 检查网络连接
   - 尝试关闭高清封面下载 `summarizer.cover.highres: false`
   - 检查站点是否被屏蔽

4. **路径过长错误**
   - 调整 `summarizer.path.length_maximum`
   - 简化命名规则
   - 启用自动标题截短

### 调试模式

```bash
# 查看详细日志
poetry run javsp --debug

# 或设置日志级别
export JAVSP_LOG_LEVEL=DEBUG
poetry run javsp
```

## 扩展开发

### 添加新的爬虫

1. 在 `javsp/web/` 目录下创建新的爬虫模块（如 `new_site.py`）
2. 实现 `parse_data(info: MovieInfo)` 函数
3. 在 `config.py` 的 `CrawlerID` 枚举中添加新站点
4. 更新配置文件中的爬虫选择

### 自定义数据处理

可以修改以下模块来自定义数据处理逻辑：
- `javsp/func.py`：通用功能函数
- `javsp/nfo.py`：NFO 文件生成逻辑
- `javsp/image.py`：图片处理函数

## 许可证与限制

JavSP 采用双重许可证：
- **GPL-3.0 License**：开源许可证，要求衍生作品也开源
- **Anti 996 License**：禁止在 996 工作制环境下使用

**使用限制**：
- 本软件仅供学习 Python 和技术交流使用
- 请勿在微博、微信等墙内的公共社交平台上宣传此项目
- 用户在使用本软件时，请遵守当地法律法规
- 禁止将本软件用于商业用途

## 总结

JavSP 是一个功能强大的 AV 元数据刮削器，具有以下特点：

1. **高度可配置**：通过 YAML 配置文件、环境变量和命令行参数提供灵活的配置选项
2. **多站点支持**：集成多个主流 AV 数据源，数据获取全面
3. **智能处理**：AI 封面裁剪、自动番号识别、多线程抓取等
4. **媒体服务器友好**：生成标准的 NFO 文件，兼容 Emby、Jellyfin、Kodi
5. **跨平台**：支持 Windows、Linux、macOS，提供 Docker 镜像

通过合理的配置，JavSP 可以自动化完成影片整理工作，大大提升媒体库管理的效率。

## 功能增强与改进记录

### 2025年12月22日：海报读写优化与刮削模式模块化

**背景**：JavSP 在刮削数据时对海报文件的读写可能过于频繁，容易通过 raidrive 本地化的网盘风控。同时，动漫和欧美的刮削模块需要独立出来，通过更灵活的方式来选择刮削模式。

**改进内容**：

#### 1. 海报文件读写优化（减少网盘风控风险）
- **内存中比较封面**：新增 `download_cover_to_memory()` 函数，将封面图片下载到内存中进行比较
- **一次性写入最佳封面**：优化 `download_cover()` 函数，选择分辨率最高的封面一次性写入磁盘
- **减少磁盘读写**：避免多次磁盘写入操作，降低触发 raidrive 本地化网盘风控的风险

#### 2. 刮削模式模块化（普通、动漫、欧美模式独立）
- **新增刮削模式选择**：添加 `--mode` 命令行参数，支持 `auto`（自动检测）、`normal`（普通）、`anime`（动漫）、`western`（欧美）四种模式
- **配置文件支持**：在 `config.yml` 中添加 `default_mode` 配置项，设置默认刮削模式
- **交互式选择**：在交互模式下提供用户选择界面
- **影片过滤**：新增 `filter_movies_by_mode()` 函数，根据选择的模式过滤影片列表

#### 3. 配置系统增强
- **命令行参数集成**：在 `config.py` 中集成 `--mode` 参数解析
- **默认模式配置**：在 `Other` 配置类中添加 `default_mode` 字段
- **向后兼容**：保持原有配置的兼容性，默认使用 `auto` 模式

#### 4. 动漫和欧美类型识别增强
- **番号识别优化**：增强 `guess_av_type()` 函数，更好地识别动漫和欧美番号
- **命名规则优化**：为动漫和欧美类型提供简化的命名规则
- **文件夹结构**：动漫文件整理到 `Anime/` 目录，欧美文件整理到 `Western/` 目录

**使用方式**：
```bash
# 自动检测模式（默认）
python -m javsp

# 指定刮削模式
python -m javsp --mode anime      # 只处理动漫
python -m javsp --mode western    # 只处理欧美
python -m javsp --mode normal     # 只处理普通AV

# 查看帮助
python -m javsp --help
```

**配置示例**：
```yaml
other:
  # 默认刮削模式: auto(自动检测), normal(普通), anime(动漫), western(欧美)
  default_mode: auto
```

**改进效果**：
1. 海报文件读写频率显著降低，减少网盘风控风险
2. 刮削模式更加灵活，可根据需要处理特定类型的影片
3. 动漫和欧美影片的识别和整理更加准确
4. 保持向后兼容，不影响现有用户的使用习惯

---

### 2025年12月21日：动漫电影处理功能增强

**背景**：JavSP 原本主要针对普通 AV 影片设计，对动漫（Anime）电影的支持有限。在实际使用中发现，动漫电影的文件命名、数据抓取和整理需要特殊处理。

**新增功能**：

#### 1. 动漫文件识别与处理
- **番号识别增强**：在 `javsp/avid.py` 的 `get_id()` 函数中添加动漫文件识别逻辑
  - 识别动漫文件名格式：`[厂商]标题 第X巻` 或 `[工作者][厂商]标题 ＃X 分辨率`
  - 返回格式：`ANIME:标题`（如 `ANIME:OVA妻に黙って即売会に行くんじゃなかった ＃2`）
- **动漫类型识别**：在 `guess_av_type()` 函数中添加动漫类型识别
  - 识别动漫番号前缀（如 `GLOD`, `HUNTB`, `ANIM`, `OVA` 等）
  - 返回类型：`anime`

#### 2. JavDB 爬虫动漫支持
- **动漫搜索优化**：在 `javsp/web/javdb.py` 中改进动漫搜索逻辑
  - 当识别为动漫文件时，使用标题进行搜索而非番号
  - 从搜索结果中提取实际番号（如 `GLOD-307`）
  - 更新影片信息中的番号为实际番号

#### 3. 文件名生成优化
- **动漫文件名生成**：在 `generate_names()` 函数中优化动漫文件名
  - 文件名包含番号和未翻译标题（如 `GLOD-307 OVA妻に黙って即売会に行くんじゃなかった ＃2`）
  - 是否翻译标题跟随配置文件设置
  - 动漫文件被整理到 `Anime` 目录（通过配置 `output_folder_pattern` 实现）

#### 4. 字幕文件移动功能
- **字幕文件自动移动**：在 `javsp/datatype.py` 的 `rename_files()` 方法中添加字幕文件移动功能
  - 查找与视频文件同名的字幕文件（相同的 basename，不同的扩展名）
  - 支持的字幕格式：`.srt`, `.ass`, `.ssa`, `.sub`
  - 字幕文件跟随视频文件一起移动和重命名
  - 示例：视频文件 `GLOD-307 OVA妻に黙って即売会に行くんじゃなかった ＃2.strm` 的字幕文件 `GLOD-307 OVA妻に黙って即売会に行くんじゃなかった ＃2.ass` 会被自动移动

#### 5. NFO 文件番号大写
- **番号统一大写**：在 `javsp/nfo.py` 的 `write_nfo()` 函数中确保番号使用大写字母
  - `uniqueid` 字段中的番号使用大写（如 `<uniqueid type="num" default="true">GLOD-307</uniqueid>`）
  - 标题中的番号也使用大写（如 `<title>GLOD-307 OVA 我不应该在没有告诉我妻子的情况下去参加特卖#2</title>`）
  - 同时处理 `info.title` 和 `info.nfo_title`

#### 6. 错误处理优化
- **文件已存在处理**：在 `datatype.py` 的 `move_file()` 函数中优化错误处理
  - 当目标文件已存在时，记录警告并跳过，而不是抛出异常中断任务
  - 确保后续任务可以继续执行，提高程序的健壮性

**配置示例**：
```yaml
summarizer:
  path:
    # 动漫文件整理到 Anime 目录
    output_folder_pattern: '#整理完成/{data_src|Anime}/{num} {rawtitle}'
    
    # 或使用条件表达式
    # output_folder_pattern: '#整理完成/{?data_src==anime:Anime:Normal}/{num} {rawtitle}'
```

**使用效果**：
1. 动漫文件被正确识别并整理到 `Anime` 目录
2. 字幕文件自动跟随视频文件移动
3. NFO 文件中的番号统一使用大写字母
4. 文件已存在时程序不会中断，继续处理其他文件

**测试验证**：
- 测试文件：`[荻原沙优][あんてきぬすっ]OVA妻に黙って即売会に行くんじゃなかった ＃2 1920x1080_.strm`
- 识别结果：番号 `GLOD-307`，类型 `anime`
- 整理结果：文件被移动到 `Anime/GLOD-307 OVA妻に黙って即売会に行くんじゃなかった ＃2/` 目录
- 字幕文件：同名的 `.ass` 文件被自动移动
- NFO 文件：番号显示为 `GLOD-307`（大写）

### 2025年12月18日：Python 3.14.1 兼容性修复

**问题描述**：在 Windows 11 上使用 Python 3.14.1 运行 `poetry install` 时遇到多个依赖包编译失败，导致项目无法运行。

**根本原因**：
1. Python 3.14.1 是较新的版本，许多依赖包尚未提供预编译的二进制轮子（wheel）
2. 缺少 Microsoft Visual C++ 14.0 或更高版本的编译工具链
3. 部分依赖包的版本约束过于严格，与 Python 3.14.1 不兼容

**解决方案**：

#### 1. 更新依赖包版本约束
修改 `pyproject.toml` 文件，放宽或更新以下依赖包的版本约束：

| 依赖包 | 原版本约束 | 更新后版本约束 | 说明 |
|--------|------------|----------------|------|
| `cx-freeze` | `^7.2.2` | `^8.5.1` | 解决与 `lief` 的版本冲突 |
| `pydantic` | `^2.9.2` | `^2.12.5` | 使用支持 Python 3.14 的版本 |
| `cryptography` | `^42.0.5` | `^46.0.3` | 使用提供 Python 3.14 二进制轮子的版本 |
| `pendulum` | `^3.0.0` | `^3.1.0` | 使用更新的 Rust 版本 |
| `pywin32` | `^306` | `^311` | 使用支持 Python 3.14 的版本 |
| `lief` | `^0.15.1` | `>=0.16.0,<=0.16.3` | 与 `cx-freeze` 8.5.1 兼容的版本范围 |
| `cffi` | `^1.17.1` | `^2.0.0` | 使用提供 Python 3.14 二进制轮子的版本 |
| `time-machine` | `^2.15.0` | `^3.2.0` | 使用提供 Python 3.14 二进制轮子的版本 |

#### 2. 手动安装二进制轮子
对于 Poetry 无法自动安装的包，使用 `pip` 手动安装预编译的二进制轮子：

```bash
# 在 Poetry 虚拟环境中执行
poetry run pip install --only-binary=:all: pillow
poetry run pip install --only-binary=:all: cryptography
poetry run pip install --only-binary=:all: pendulum
```

#### 3. 处理可选依赖
`slimeface` 包需要 MSVC 编译工具链，但它是可选依赖（仅用于 AI 封面裁剪）。如果不需要此功能，可以跳过安装。项目核心功能仍可正常运行。

#### 4. 验证修复结果
执行以下命令验证项目是否可运行：

```bash
# 检查依赖安装
poetry run pip list | grep -E "(pillow|cryptography|pendulum|pydantic)"

# 测试程序入口
poetry run javsp --help

# 测试模块导入
poetry run python -c "import javsp; print('导入成功')"
```

**修复效果**：
- ✅ 项目依赖安装成功
- ✅ 主程序 `javsp` 可正常启动
- ✅ 所有核心模块可正常导入
- ✅ 基本功能测试通过

**注意事项**：
1. 如果未来需要 `slimeface` 的 AI 裁剪功能，需要安装 Microsoft Visual C++ Build Tools
2. Python 3.14.1 仍处于早期阶段，建议关注依赖包的兼容性更新
3. 生产环境建议使用 Python 3.11 或 3.12 等更稳定的版本

**相关命令参考**：
```bash
# 更新特定依赖包
poetry add package@latest --lock

# 重新生成锁文件
poetry lock

# 仅安装主依赖（跳过开发依赖）
poetry install --only main

# 安装 MSVC 编译工具（如需编译 slimeface）
# 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

---

## 相关资源

- **GitHub 仓库**：https://github.com/Yuukiy/JavSP
- **Wiki 文档**：https://github.com/Yuukiy/JavSP/wiki
- **Docker 镜像**：https://github.com/Yuukiy/JavSP/pkgs/container/javsp
- **问题反馈**：https://github.com/Yuukiy/JavSP/issues

---
*文档最后更新：2025年12月22日*
