#!/usr/bin/env python3
"""Static-site build using Python-Markdown and its bundled TOC extension."""
from pathlib import Path
from editorial_lint import check_sources, check_html
import html, json, re
ROOT = Path(__file__).resolve().parent
E = html.escape

from markdown_renderer import render
from word_count import count_words

def article_body(text, outline=False):
    body, toc, _ = render(text)
    if not outline:
        return body
    # TOC markup/nesting/IDs are produced by Python-Markdown's bundled toc extension.
    return '<aside class="reader-sidebar"><details class="reader-outline" open><summary aria-label="文章目录"><svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M8 6h12M8 12h12M8 18h12M3 6h1M3 12h1M3 18h1"/></svg></summary><nav aria-label="文章目录">' + toc + '</nav></details></aside><div class="reader-text">' + body + '</div>'

def shell(title, body, prefix='', description='个人学习笔记。记录问题、源码与实验。', style_suffix='?v=markdown-9'):
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{E(description, quote=True)}"><meta name="color-scheme" content="light"><title>{E(title)} · pixel notes</title><link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}style.css{style_suffix}"></head>
<body><a class="skip" href="#main">跳到正文</a><div class="wrap"><header class="header"><a class="brand" href="{prefix}index.html" aria-label="pixel notes 首页"><span class="mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>pixel notes<span style="color:#64686d;font-weight:400">/</span></a><nav class="nav" aria-label="主导航"><a href="{prefix}index.html#notes">笔记</a><a href="{prefix}index.html#research">待研究</a></nav></header>{body}<footer class="footer"><span>pixel notes · 学习笔记</span><span>保留问题，也保留依据。</span></footer></div><script src="{prefix}search.js" defer></script></body></html>'''

check_sources(ROOT)
notes = json.loads((ROOT/'notes.json').read_text())
slugs=set()
for n in notes:
    assert re.fullmatch('[a-z0-9-]+',n['slug']) and n['slug'] not in slugs
    slugs.add(n['slug'])
    source = ROOT/f"{n['slug']}.md"
    (ROOT/f"{n['slug']}.html").write_text(shell(n['title'],f'''<main id="main" class="article-wrap{' reader-mode' if n['slug']=='hermes-memory-skills' else ''}"><a class="back" href="index.html#notes">← 所有笔记</a><header class="article-header"><div class="eyebrow">LEARNING NOTE / {E(n['topic'])}</div><h1>{E(n['title'])}</h1><div class="meta"><time datetime="{n['date']}">{n['date']}</time><span>{E(n['reading'])}</span><span title="按正文可见文字统计：每个汉字计 1，连续英文字母或数字计 1；含小节标题和图注，不含目录、链接地址与标点。">总字数 {count_words(source.read_text()):,}</span><span class="tag">{E(n['status'])}</span></div></header><article class="prose">{article_body(source.read_text(), outline=n['slug']=='hermes-memory-skills')}</article><div class="article-end"><a href="{n['slug']}.md" download>下载 Markdown ↓</a>{'<a href="https://github.com/pixelieee/pixelieee.github.io/blob/main/hermes-memory-skills.md">查看 Markdown（GitHub）</a>' if n['slug']=='hermes-memory-skills' else ''}<a href="index.html#research">继续看待研究问题 →</a></div></main>''','',n['summary'], '?v=markdown-9'))
cards=''.join(f'''<article class="note" data-search="{E(' '.join([n['title'],n['summary'],n['topic'],n['status']]), quote=True)}"><div class="meta"><span>{E(n['topic'])}</span><time datetime="{n['date']}">{n['date']}</time><span class="tag">{E(n['status'])}</span></div><h3><a href="{n['slug']}.html">{E(n['title'])}</a></h3><p style="margin-bottom:0">{E(n['summary'])}</p></article>''' for n in sorted(notes,key=lambda n:n['date'],reverse=True))
home_links=''.join(f'<li><a href="{n["slug"]}.html">{E(n["title"])}</a></li>' for n in sorted(notes,key=lambda n:n['date'],reverse=True))
topics=sorted({n['topic'] for n in notes})
topic_rows=''.join(f'<div class="subject"><span>{E(t)}</span><span>{sum(n["topic"]==t for n in notes):02}</span></div>' for t in topics)
body=f'''<main id="main"><section id="notes" aria-labelledby="notes-title"><div class="toolbar"><h1 id="notes-title">学习笔记 <span class="count" id="result-count" role="status" aria-live="polite">{len(notes)} 篇</span></h1><label class="search"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="搜索笔记、主题…" aria-label="搜索笔记"></label></div><div class="grid"><div>{cards}<p class="empty" id="empty" hidden>没有找到相关笔记。换个关键词试试。</p></div><aside class="aside"><details class="home-outline" open><summary>导航</summary><nav aria-label="主页导航"><a href="#notes">学习笔记</a><ul>{home_links}</ul><a href="#research">待研究问题</a></nav></details><h3>主题</h3>{topic_rows}</aside></div></section><section class="queue" id="research" aria-labelledby="research-title"><div><div class="eyebrow">NEXT QUESTION</div><h2 id="research-title" style="margin-top:8px">多 Agent 如何真正交接工作？</h2><p>从 Hermes Kanban 开始，追一次实现、审查、退回修改的完整流程。</p><a class="read" style="margin-top:16px" href="hermes-kanban.html">查看笔记 <span aria-hidden="true">↗</span></a></div><span class="pill">待研究</span></section></main>'''
(ROOT/'index.html').write_text(shell('学习笔记',body))
check_html(ROOT)
print(f'Built homepage + {len(notes)} note(s).')
