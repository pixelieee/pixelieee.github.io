# pixel notes

源码级 Agent 工程学习笔记。Astro + MDX，纯静态输出。

```bash
npm install
npm run dev      # 本地预览
npm run build    # 输出到 dist/
```

## 写笔记

在 `src/content/notes/` 新建 `.mdx`，frontmatter 字段见 `src/content.config.ts`。
`status`：`published`（已完成）、`draft`（写作中）、`todo`（待研究）。
源码引用用 `<Src p="path/in/repo.py" l="10-20" />`，固定到笔记所用的提交。

## 部署

GitHub Pages 的来源需要设为 **GitHub Actions**（Settings → Pages → Source），推送 `main` 后由 `.github/workflows/deploy.yml` 构建并发布。
