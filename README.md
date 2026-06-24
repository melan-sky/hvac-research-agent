# HVAC 系统节能技术检索智能体

这是一个面向 HVAC 系统节能技术调研的研究型联网搜索智能体。系统围绕“真实联网搜索、结果筛选、论文线索补充、小报生成、页面展示”这条主流程实现，适合课程作业演示和主题资料初筛。

## 功能

- 输入 HVAC 相关关键词后进行真实联网检索。
- 支持国内渠道和国际化渠道，国际化渠道适合在可访问英文搜索结果时补充资料。
- 对搜索结果做相关性筛选、来源类型识别和排序。
- 单跳读取部分结果页面正文，不做站点递归爬取。
- 补充 ScienceDirect、Crossref、arXiv 等论文线索。
- 支持论文 PDF 可用时一键下载汇总。
- 支持两个关键词并列检索对比。
- 自动生成面向用户问题的技术小报。

## 文件结构

- `simple_web.py`：推荐运行入口，内置网页界面。
- `desktop_app.py`：Windows 桌面壳入口，用于打包 exe。
- `search_engine.py`：联网搜索、结果解析、正文读取、论文 PDF 下载。
- `ranker.py`：查询范围判断、相关性评分、结果筛选。
- `summarizer.py`：小报生成。
- `models.py`：数据结构。
- `requirements.txt`：Python 依赖。
- `HVAC检索智能体.spec`：PyInstaller 打包配置。
- `洛克/`、`背景/`：界面图片资源。

## 本地运行

```powershell
cd research-agent
python -m pip install -r requirements.txt
python simple_web.py
```

打开浏览器访问：

```text
http://127.0.0.1:8501
```

## 打包为 Windows 应用

```powershell
cd research-agent
python -m pip install pyinstaller
pyinstaller --clean --noconfirm HVAC检索智能体.spec
```

生成结果位于：

```text
dist/HVAC系统节能技术检索智能体.exe
```

## 说明

- 程序不使用本地资料库伪造搜索结果。
- 程序不做 sitemap、站内 BFS/DFS 或全站爬虫。
- 程序只访问搜索结果页给出的链接，并尝试读取前若干条正文。
- 小报内容基于本次联网检索结果生成。
