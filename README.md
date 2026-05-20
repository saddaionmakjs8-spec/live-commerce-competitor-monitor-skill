# 直播竞品盯播分析 Skill

这是一个用于长期监控电商直播间的 Codex Skill，适合做抖音、TikTok Shop 或类似直播带货场景的竞品分析。

它关注的不是简单复盘，而是把直播过程整理成可复用的数据：

- 完整录屏与录制分段
- 逐字稿与话术分段
- 画面变化截图
- 在线人数、点赞、评论、商品卡、下单信号等时间序列
- 话术、场景变化、商品切换和转化信号之间的关系假设
- 本地 HTML 可视化看板

## 使用方式

把本仓库作为 Codex Skill 安装或复制到本地 skill 目录后，使用下面这类需求即可触发：

```text
帮我监控某个竞争对手直播间，记录话术、在线人数、点赞、评论、商品卡和下单信号。
```

正式任务必须至少录制 10 分钟。如果判断直播是循环内容，也要在完成一个可确认循环且录制不少于 10 分钟后再停止。

## 输出原则

交付给用户看的文件夹应当直接可读，避免只留下技术中间文件。核心交付包括：

- `完整录屏.mov`
- `逐字稿.txt`
- `关键截图/`
- `结构化数据/`
- `分析报告.md`
- `采集说明.md`

技术性原始文件可以保留在 `raw/` 或 `report/` 中，但不能替代面向用户的整理版交付。

## 文件说明

- `SKILL.md`：Skill 主说明和执行约束。
- `references/local-douyin-capture.md`：使用本地抖音 App 采集时的流程。
- `references/data-schema.md`：事件与字段结构。
- `references/delivery-package.md`：面向用户的交付文件夹规范。
- `references/analysis-method.md`：话术、场景、指标关系的分析方法。
- `scripts/build_delivery_package.py`：整理交付文件夹。
- `scripts/build_live_report.py`：根据结构化数据生成分析报告。
- `scripts/build_html_dashboard.py`：把交付目录生成可直接打开的本地 HTML 看板。

## Skill 名称

Codex 识别用的 skill 名称为：

```text
直播竞品盯播分析
```

如果从 GitHub 安装，可以使用：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo saddaionmakjs8-spec/live-commerce-competitor-monitor-skill --path . --name 直播竞品盯播分析
```
