(() => {
  const root = document.documentElement;
  const saved = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const store = (key,value) => { try { localStorage.setItem(key,value); } catch {} };
  const media = matchMedia('(prefers-color-scheme: dark)');
  let theme = saved('pixel-theme');
  const applyTheme = () => {
    const dark = theme ? theme === 'dark' : media.matches;
    root.dataset.theme = dark ? 'dark' : 'light';
    const button = document.querySelector('#theme-toggle');
    if (button) { button.textContent = dark ? '☀' : '☾'; button.setAttribute('aria-label',root.lang === 'en' ? (dark?'Use light theme':'Use dark theme') : (dark?'切换浅色模式':'切换深色模式')); button.title=button.getAttribute('aria-label'); }
  };
  applyTheme();
  media.addEventListener('change', () => { if (!theme) applyTheme(); });
  document.addEventListener('DOMContentLoaded', () => {
    const toggle=document.querySelector('#theme-toggle'), language=document.querySelector('#language-toggle');
    const translations=[
      ['.skip','跳到正文','Skip to content'],['.nav a[href$="#notes"]','笔记','Notes'],['.nav a[href$="#research"]','待研究','Research'],
      ['.back','← 所有笔记','← All notes'],['.article-end a[download]','下载 Markdown ↓','Download Markdown ↓'],['.article-end a[href*="github.com"]','查看 Markdown（GitHub）','View Markdown on GitHub'],['.article-end a[href$="#research"]','继续看待研究问题 →','Explore research questions →'],
      ['.footer span','pixel notes · 学习笔记','pixel notes · Learning notes'],['.home-outline summary','导航','Navigation'],['.home-outline nav>a[href="#notes"]','学习笔记','Learning notes'],['.home-outline nav>a[href="#research"]','待研究问题','Research questions'],['.aside>h3','主题','Topics'],['.queue .read','查看笔记 ↗','View note ↗'],['#empty','没有找到相关笔记。换个关键词试试。','No notes found. Try another keyword.']
    ];
    const originalTags=new Map([...document.querySelectorAll('.tag,.pill')].map(e=>[e,e.textContent]));
    const applyLanguage = () => {
      const english=root.lang==='en';
      for (const [selector,zh,en] of translations) document.querySelectorAll(selector).forEach(e=>e.textContent=english?en:zh);
      const heading=document.querySelector('#notes-title');if(heading)heading.firstChild.textContent=english?'Learning notes ':'学习笔记 ';
      document.querySelectorAll('.subject span:first-child,.note .meta>span:first-child').forEach(e=>{if(['Agent 工程','Agent engineering'].includes(e.textContent))e.textContent=english?'Agent engineering':'Agent 工程';});
      const search=document.querySelector('#search');if(search){search.placeholder=english?'Search notes…':'搜索笔记、主题…';search.setAttribute('aria-label',english?'Search notes':'搜索笔记');search.dispatchEvent(new Event('input'));}
      for(const [e,text] of originalTags)e.textContent=english?({'源码解读':'Source walkthrough','待研究':'To explore'}[text]||text):text;
      document.querySelectorAll('.content-language').forEach(e=>{e.hidden=!english;e.textContent='Chinese original';});
      document.querySelectorAll('.article-header .meta [title]').forEach(e=>{const n=e.textContent.match(/[\d,]+/);if(n)e.textContent=(english?'Word count ':'总字数 ')+n[0];e.title=english?'Visible article text: each Han character or English/alphanumeric word counts as one. Headings and captions included; navigation, URLs and punctuation excluded.':'按正文可见文字统计：每个汉字计 1，连续英文字母或数字计 1；含小节标题和图注，不含目录、链接地址与标点。';});
      const reading=document.querySelector('.article-header .meta time+span');if(reading){const n=reading.textContent.match(/\d+/);if(n)reading.textContent=english?`${n[0]} min read`:(n[0]==='20'?'约 20 分钟':`${n[0]} 分钟`);}
      const nav=document.querySelector('.reader-outline nav');if(nav)nav.setAttribute('aria-label',english?'Article contents':'文章目录');
      const summary=document.querySelector('.reader-outline summary');if(summary)summary.setAttribute('aria-label',english?'Article contents':'文章目录');
      language.textContent=english?'中文':'EN';language.setAttribute('aria-label',english?'切换中文界面':'Switch interface to English');language.title=english?'Article text remains in Chinese':'切换界面语言，文章保留中文原文';
      applyTheme();
    };
    root.lang=saved('pixel-language')==='en'?'en':'zh-CN';
    toggle.addEventListener('click',()=>{theme=root.dataset.theme==='dark'?'light':'dark';store('pixel-theme',theme);applyTheme();});
    language.addEventListener('click',()=>{root.lang=root.lang==='en'?'zh-CN':'en';store('pixel-language',root.lang);applyLanguage();});
    applyLanguage();
  });
})();
