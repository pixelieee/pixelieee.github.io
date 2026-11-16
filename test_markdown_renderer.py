import unittest,re
from pathlib import Path
from markdown_renderer import render, LEGACY
class RendererTests(unittest.TestCase):
 def test_current_article(self):
  body,toc,tokens=render(Path('hermes-memory-skills.md').read_text())
  ids=re.findall(r'<h[23] id="([^"]+)"',body)
  self.assertEqual(set(ids),set(LEGACY.values()))
  self.assertEqual(len(ids),12)
  self.assertEqual(re.findall(r'href="#([^"]+)"',toc),ids)
  self.assertEqual(len(tokens),5)
  self.assertEqual(body.count('<figure'),4)
  self.assertNotIn('<h1',body)
  self.assertEqual(body.count('style="text-align:center"'),1)
  self.assertIn('<figcaption style="text-align:center">图 3：Hermes Skills 与 curator',body)
 def test_library_nesting_duplicates_and_code(self):
  body,toc,tokens=render('# Title\n\n## 标题\n\n### Sub `code`\n\n## 标题\n\n```\n## not a heading\n```')
  self.assertEqual([t['id'] for t in tokens],['标题','标题_1'])
  self.assertEqual(tokens[0]['children'][0]['name'],'Sub code')
  self.assertNotIn('not a heading',toc)
 def test_raw_html_and_unsafe_link(self):
  body,_,_=render('<script>alert(1)</script>')
  self.assertNotIn('<script>',body)
  with self.assertRaises(ValueError):render('[bad](javascript:alert)')
 def test_markdown(self):
  body,_,_=render('## H\n\n*emphasis* and **bold**\n\n1. One\n2. Two')
  self.assertIn('<em>emphasis</em>',body)
  self.assertEqual(body.count('<li>'),2)
if __name__=='__main__':unittest.main()
