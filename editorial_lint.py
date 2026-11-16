"""Check public note copy before build. No external dependencies."""
from pathlib import Path
from html.parser import HTMLParser
import json, re, sys
RULES = {
 'editorial-placeholder': r'先记下这个研究入口|这些问题先保留[，,]跑过实验后再补结论|查看研究入口',
 'cross-post-plan': r'完整笔记留在这里[。.]\s*短观点和图解[，,]\s*另整理成适合\s*X[、/]\s*小红书的版本',
}
class VisibleText(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]; self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t in ('br','p','div','section'):self.parts.append(' ')
 def handle_endtag(self,t):
  if t in ('script','style') and self.skip:self.skip-=1
  if t in ('p','div','section'):self.parts.append(' ')
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
def violations(text):
 return [name for name,pattern in RULES.items() if re.search(pattern,text)]
def check(text,path):
 hits=violations(text)
 if hits:raise ValueError(f'{path}: '+', '.join(hits))
def check_sources(root):
 notes=json.loads((root/'notes.json').read_text())
 for n in notes:
  for field in ('title','summary','research_question'):
   check(n.get(field,''),f'notes.json:{n["slug"]}:{field}')
  f=root/f'{n["slug"]}.md';check(f.read_text(),f.name)
def check_html(root):
 notes=json.loads((root/'notes.json').read_text())
 for name in ['index.html']+[f'{n["slug"]}.html' for n in notes]:
  p=VisibleText();p.feed((root/name).read_text());check(''.join(p.parts),name)
def self_test():
 bad=['Hermes 自带 Kanban：先记下这个研究入口','完整笔记留在这里。短观点和图解，另整理成适合 X、小红书的版本。','这些问题先保留，跑过实验后再补结论。']
 good=['Hermes Kanban：多 Agent 任务派发与交接','待验证问题','根据官方文档整理，尚未完成实际运行验证。','X 与小红书的 API 权限差异']
 assert all(violations(x) for x in bad)
 assert not any(violations(x) for x in good)
 p=VisibleText();p.feed('<p>完整笔记留在这里。<br>短观点和图解，另整理成适合<br>X、小红书的版本。</p>');assert violations(''.join(p.parts))
 print('Editorial lint fixtures passed')
if __name__=='__main__':
 try:
  if '--self-test' in sys.argv:self_test()
  elif '--text' in sys.argv:check(sys.argv[sys.argv.index('--text')+1],'text')
  else:root=Path(__file__).resolve().parent;check_sources(root);check_html(root);print('Editorial lint passed')
 except ValueError as e:print(str(e),file=sys.stderr);sys.exit(1)
