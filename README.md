# Hugging Face Daily Papers Archive

中文 | [English](README.en.md)

这是一个用于追踪 Hugging Face Daily Papers 的本地归档和静态网站项目。它会抓取每日论文列表，使用 OpenAI 兼容模型生成中文一句话摘要、机构标签和 topic 标签，并构建一个可在浏览器中查看的静态网站。

项目重点包括：

- 每日论文抓取、摘要生成和标签生成。
- 中文静态站点，支持日期归档、全局搜索、字段搜索和标签筛选。
- topic 趋势统计、异动榜，以及 Institution x Topic 矩阵。
- 本地管理模式，可在网页里手动修正错误的 institution/topic tag。
- topic 和 institution 合并审查 skill，所有合并都必须经过人工确认后才写入 alias。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

编辑 `.env`：

```text
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-model
```

只要接口兼容 chat completions 和 JSON 输出，就可以使用 OpenAI 兼容服务。

## 日常使用

抓取指定日期：

```powershell
python -m hf_daily fetch --date 2026-05-28
```

生成摘要和标签：

```powershell
python -m hf_daily generate --date 2026-05-28
```

构建静态网站：

```powershell
python -m hf_daily build
```

执行完整流程：

```powershell
python -m hf_daily run --date 2026-05-28
```

构建完成后打开 `site/index.html`。

## 本地管理模式

如果网页中某篇论文的 institution tag 或 topic tag 有误，可以启动本地管理模式：

```powershell
python -m hf_daily admin
```

打开命令行输出的本地地址，在论文卡片中点击 `Edit tags`，修改标签后点击 `Save draft`。修改会写入 `data/tags/tag_overrides.json`，并自动重建站点。原始的 `data/daily/*.json` 不会被改写。

输入新标签时，页面会基于当前已有标签提供自动补全。例如输入 `ali` 时，可以提示已有的 `alibaba-inc` 等标签。

## 网站功能

首页默认展示最新一个有论文的日期。`Date Archive` 只显示至少有一篇论文的日期；周末或无论文日期会在构建站点时自动过滤，不出现在日期归档中。

搜索和筛选包括：

- 默认全字段搜索。
- 可选择只搜索 title、topic tag、institution tag 等字段。
- 搜索结果覆盖所有日期，而不是只搜索当前日期。
- institution/topic tag 筛选同样跨全部已生成日期。

统计功能包括：

- topic trend 曲线：默认展示指定时间范围内数量最多的前 5 个 topic。
- 用户可指定想查看的 topic 曲线。
- topic 异动榜：对比当前区间和前一区间，查看增长最快的 topic。
- Institution x Topic 矩阵：独立页面展示 top institutions 与 topics 的交叉分布。

## 本地数据

- `data/raw/YYYY-MM-DD.json`：Hugging Face API 原始响应。
- `data/daily/YYYY-MM-DD.json`：标准化后的论文、摘要和标签。
- `data/tags/topics.json`：本地 topic tag 库。
- `data/tags/institutions.json`：本地 institution tag 库。
- `data/tags/topic_aliases.json`：经过人工确认的 topic 合并 alias。
- `data/tags/institution_aliases.json`：经过人工确认的 institution 合并 alias。
- `data/tags/tag_overrides.json`：网页管理模式写入的手动标签修正。
- `site/`：生成的静态网站。

每篇论文最终有两个核心标签：

- `institution_tag`：优先来自 Hugging Face 的 organization 字段，缺失时由模型保守推断。
- `topic_tag`：英文、中等粒度的方法或研究方向标签，会优先复用已有 topic。

公开仓库默认不提交 `.env`、`data/raw/`、`data/daily/` 和 `site/`。请不要把 API key 或私有生成数据提交到公开仓库。

## Codex Skills

本项目包含两个项目级 Codex skill，位于 `.codex/skills/`。它们只在本项目内生效，用于减少标签合并时的误合并风险。

### topic-merge-review

路径：`.codex/skills/topic-merge-review`

用途：

- 查找相似 topic。
- 生成候选合并审查包。
- 区分高置信、需要人工判断、应保持分开的 topic。
- 在用户明确批准后，写入 `data/tags/topic_aliases.json`。

辅助脚本：

```powershell
python .codex\skills\topic-merge-review\scripts\suggest_topic_merges.py --root .
```

核心规则：

1. 第一阶段只生成审查建议，不写文件。
2. 用户必须用明确的 `Approve:` 列出 alias 到 canonical 的映射。
3. 第二阶段只写 `data/tags/topic_aliases.json`。
4. 不重写 `data/daily/*.json`。

批准示例：

```text
Approve:
- LLM agent test-time scaling -> LLM test-time scaling
- video editing benchmark evaluation -> video editing
```

### institution-merge-review

路径：`.codex/skills/institution-merge-review`

用途：

- 查找 institution tag 中明显的大小写、标点、冠词、简称或官方名称变体。
- 生成候选合并审查包。
- 避免把母公司、实验室、校区、学院等不同实体错误合并。
- 在用户明确批准后，写入 `data/tags/institution_aliases.json`。

辅助脚本：

```powershell
python .codex\skills\institution-merge-review\scripts\suggest_institution_merges.py --root .
```

核心规则：

1. 第一阶段只生成审查建议，不写文件。
2. 用户必须用明确的 `Approve:` 列出 alias 到 canonical 的映射。
3. 第二阶段只写 `data/tags/institution_aliases.json`。
4. 不重写 `data/daily/*.json`。
5. 不把 `Unknown` 合并到真实机构。

批准示例：

```text
Approve:
- Alibaba -> alibaba-inc
- The University of Hong Kong -> University of Hong Kong
```

## 定时任务示例

Windows Task Scheduler：

```powershell
$Action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"cd D:\Github\huggingface_daily; .\.venv\Scripts\Activate.ps1; python -m hf_daily run`""

$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

Register-ScheduledTask `
  -TaskName "HuggingFaceDailyPapers" `
  -Action $Action `
  -Trigger $Trigger `
  -Description "Fetch Hugging Face daily papers and rebuild the static archive."
```

默认日期使用本地 Asia/Shanghai 日期。如需固定日期，可传入 `--date YYYY-MM-DD`。

## GitHub Actions 示例

如果需要在 GitHub 自动生成，可保存为 `.github/workflows/daily.yml`：

```yaml
name: Daily Hugging Face Papers

on:
  schedule:
    - cron: "0 1 * * *"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .
      - run: python -m hf_daily run
        env:
          OPENAI_BASE_URL: ${{ secrets.OPENAI_BASE_URL }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: ${{ secrets.OPENAI_MODEL }}
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
```

## 测试

```powershell
python -m pytest -q
```
