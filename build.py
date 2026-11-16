#!/usr/bin/env python3
"""Zero-dependency build. Trusted author Markdown subset only; HTML is escaped."""
from pathlib import Path
from editorial_lint import check_sources, check_html
import html, json, re
ROOT = Path(__file__).resolve().parent
E = html.escape

def inline(text):
    text = E(text)
    # Only HTTPS links; no raw HTML or javascript URLs.
    text = re.sub(r'\[([^\]]+)\]\((https://[^\s)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

def markdown(text):
    output, paragraph, list_kind, code = [], [], None, None
    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>'); paragraph.clear()
    def close_list():
        nonlocal list_kind
        if list_kind: output.append(f'</{list_kind}>'); list_kind = None
    for line in text.splitlines():
        if line.startswith('```'):
            flush(); close_list()
            if code is None: code = []
            else: output.append('<pre><code>'+E('\n'.join(code))+'</code></pre>'); code=None
            continue
        if code is not None: code.append(line); continue
        if not line.strip(): flush(); close_list(); continue
        if line.startswith('# '): continue # title comes from notes.json
        img = re.fullmatch(r'!\[([^\]]+)\]\(([a-z0-9-]+\.png)\)', line)
        if img:
            flush(); close_list(); output.append(f'<figure style="margin:28px 0"><a href="{img[2]}" target="_blank" rel="noopener"><img src="{img[2]}" alt="{E(img[1],quote=True)}" loading="lazy" style="display:block;width:100%;height:auto"></a><figcaption style="font-size:12px;color:var(--muted);margin-top:8px">{E(img[1])} · 点击查看原图</figcaption></figure>'); continue
        if line.startswith('### '):
            flush(); close_list(); output.append('<h3>'+inline(line[4:])+'</h3>'); continue
        if line.startswith('## '):
            flush(); close_list(); output.append('<h2>'+inline(line[3:])+'</h2>'); continue
        if line.startswith('> '):
            flush(); close_list(); output.append('<blockquote>'+inline(line[2:])+'</blockquote>'); continue
        match = re.match(r'(- |\d+\. )(.*)', line)
        if match:
            flush(); kind = 'ul' if match[1]=='- ' else 'ol'
            if list_kind != kind: close_list(); output.append(f'<{kind}>'); list_kind=kind
            output.append('<li>'+inline(match[2])+'</li>'); continue
        close_list(); paragraph.append(line)
    flush(); close_list()
    if code is not None: raise ValueError('Unclosed code fence')
    return '\n'.join(output)

def article_body(text, outline=False):
    body = markdown(text)
    if not outline:
        return body
    headings = []
    section = sub = 0
    def anchor(match):
        nonlocal section, sub
        level, title = match[1], match[2]
        if level == '2':
            section += 1; sub = 0
            ident = f'section-{section}'
        else:
            sub += 1
            ident = f'section-{section}-{sub}'
        headings.append((level, ident, title))
        return f'<h{level} id="{ident}" tabindex="-1">{title}</h{level}>'
    body = re.sub(r'<h([23])>(.*?)</h\1>', anchor, body)
    items = []
    nested = False
    for level, ident, title in headings:
        if level == '2':
            if nested: items.append('</ul>'); nested = False
            if items: items.append('</li>')
            items.append(f'<li><a href="#{ident}">{title}</a>')
        else:
            if not nested: items.append('<ul>'); nested = True
            items.append(f'<li><a href="#{ident}">{title}</a></li>')
    if nested: items.append('</ul>')
    if items: items.append('</li>')
    toc = '<aside class="reader-sidebar"><details class="reader-outline" open><summary>大纲</summary><nav aria-label="文章大纲"><div class="outline-label" aria-hidden="true">大纲</div><ul>' + ''.join(items) + '</ul></nav></details></aside>'
    return toc + '<div class="reader-text">' + body + '</div>'

def shell(title, body, prefix='', description='个人学习笔记。记录问题、源码与实验。'):
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{E(description, quote=True)}"><meta name="color-scheme" content="light"><title>{E(title)} · pixel notes</title><link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}style.css"></head>
<body><a class="skip" href="#main">跳到正文</a><div class="wrap"><header class="header"><a class="brand" href="{prefix}index.html" aria-label="pixel notes 首页"><span class="mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>pixel notes<span style="color:#64686d;font-weight:400">/</span></a><nav class="nav" aria-label="主导航"><a href="{prefix}index.html#notes">笔记</a><a href="{prefix}index.html#research">待研究</a></nav></header>{body}<footer class="footer"><span>pixel notes · 学习笔记</span><span>保留问题，也保留依据。</span></footer></div><script src="{prefix}search.js" defer></script></body></html>'''

check_sources(ROOT)
notes = json.loads((ROOT/'notes.json').read_text())
slugs=set()
for n in notes:
    assert re.fullmatch('[a-z0-9-]+',n['slug']) and n['slug'] not in slugs
    slugs.add(n['slug'])
    source = ROOT/f"{n['slug']}.md"
    (ROOT/f"{n['slug']}.html").write_text(shell(n['title'],f'''<main id="main" class="article-wrap{' reader-mode' if n['slug']=='hermes-memory-skills' else ''}"><a class="back" href="index.html#notes">← 所有笔记</a><header class="article-header"><div class="eyebrow">LEARNING NOTE / {E(n['topic'])}</div><h1>{E(n['title'])}</h1><div class="meta"><time datetime="{n['date']}">{n['date']}</time><span>{E(n['reading'])}</span><span class="tag">{E(n['status'])}</span></div></header><article class="prose">{article_body(source.read_text(), outline=n['slug']=='hermes-memory-skills')}</article><div class="article-end"><a href="{n['slug']}.md" download>下载 Markdown ↓</a>{'<a href="https://github.com/pixelieee/pixelieee.github.io/blob/main/hermes-memory-skills.md">查看 Markdown（GitHub）</a>' if n['slug']=='hermes-memory-skills' else ''}<a href="index.html#research">继续看待研究问题 →</a></div></main>''','',n['summary']))
cards=''.join(f'''<article class="note" data-search="{E(' '.join([n['title'],n['summary'],n['topic'],n['status']]), quote=True)}"><div class="meta"><span>{E(n['topic'])}</span><time datetime="{n['date']}">{n['date']}</time><span class="tag">{E(n['status'])}</span></div><h3><a href="{n['slug']}.html">{E(n['title'])}</a></h3><p>{E(n['summary'])}</p><a class="read" href="{n['slug']}.html" aria-label="阅读：{E(n['title'],quote=True)}">阅读笔记 <span aria-hidden="true">↗</span></a></article>''' for n in sorted(notes,key=lambda n:n['date'],reverse=True))
topics=sorted({n['topic'] for n in notes})
topic_rows=''.join(f'<div class="subject"><span>{E(t)}</span><span>{sum(n["topic"]==t for n in notes):02}</span></div>' for t in topics)
body=f'''<main id="main"><section class="hero"><div><div class="eyebrow">NOTES ON BUILDING & LEARNING</div><h1>边学，边拆，<br>边做。</h1><p>记录值得追下去的问题、读过的源码，<br>以及动手之后得到的结论。</p></div><div class="annotation"><strong>一份持续更新的学习记录</strong>每篇笔记标明进度，保留原始资料。<br>还没验证的内容，先把问题写清楚。</div></section><section id="notes" aria-labelledby="notes-title"><div class="toolbar"><h2 id="notes-title">学习笔记 <span class="count" id="result-count" role="status" aria-live="polite">{len(notes)} 篇</span></h2><label class="search"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="搜索笔记、主题…" aria-label="搜索笔记"></label></div><div class="grid"><div>{cards}<p class="empty" id="empty" hidden>没有找到相关笔记。换个关键词试试。</p></div><aside class="aside"><h3>主题</h3>{topic_rows}</aside></div></section><section class="queue" id="research" aria-labelledby="research-title"><div><div class="eyebrow">NEXT QUESTION</div><h2 id="research-title" style="margin-top:8px">多 Agent 如何真正交接工作？</h2><p>从 Hermes Kanban 开始，追一次实现、审查、退回修改的完整流程。</p><a class="read" style="margin-top:16px" href="hermes-kanban.html">查看笔记 <span aria-hidden="true">↗</span></a></div><span class="pill">待研究</span></section></main>'''
(ROOT/'index.html').write_text(shell('学习笔记',body))
check_html(ROOT)
print(f'Built homepage + {len(notes)} note(s).')
