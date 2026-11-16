# pixel notes

中文学习笔记站。纯静态页面，无第三方运行时、跟踪脚本、远程字体或登录。

## 本地查看

```bash
python3 build.py
python3 -m http.server 8000
```

打开 `http://localhost:8000`。生成的 HTML 已提交到交付目录，GitHub Pages 无需构建。

## 写笔记

1. 在仓库根目录新建 `slug.md`。
2. 在 `notes.json` 添加 `slug/title/summary/date/topic/status/reading`。
3. 执行 `python3 build.py`，检查主页、文章和手机宽度。

Markdown 支持：`#` 标题（标题实际采用 JSON）、`##` 小节、段落、`-` 列表、数字列表、单段引用、代码块、行内代码、加粗和 HTTPS 链接。暂不支持表格、嵌套列表或原始 HTML。输入被转义，禁止脚本型链接。需要这些格式时应换用成熟 Markdown 构建器，不能在这个解析器里盲目扩写。

## GitHub Pages

仓库：`pixelieee/pixelieee.github.io`。公开地址：https://pixelieee.github.io/ 。Pages 来源为 `main` 分支根目录。所有内部链接均为相对路径。

需要调整发布来源时，在仓库 Settings → Pages 选择 Deploy from a branch，分支 `main`，目录 `/ (root)`。不需要提交凭据，也不需要 Actions 工作流。不要上传本地 `qa/` 或任何私有草稿。

## 内容与发布边界

首篇笔记为原创 Hermes Kanban 研究入口，依据公开官方文档，明确标记未实测。没有个人简介、简历、联系方式、私聊内容或原技术母稿。

上线前由所有者确认公开范围。更多笔记发布前逐篇校验来源、代码、隐私和结论。

## 跨平台

见 `SYNDICATION.md`。当前只提供工作流程，不绑定 X / 小红书账号，不代发，不标记“已同步”。
