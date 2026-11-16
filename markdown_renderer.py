"""Python-Markdown parses Markdown and its bundled toc builds heading IDs and TOC."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import markdown
from markdown.extensions import Extension
from markdown.extensions.toc import slugify_unicode
from markdown.treeprocessors import Treeprocessor

LEGACY = json.loads(Path(__file__).with_name('legacy-anchors.json').read_text())
def stable_slug(title, separator):
    return LEGACY.get(title, slugify_unicode(title, separator))

class ReadingElements(Treeprocessor):
    def run(self, root):
        # The page template owns the H1. This does not parse headings or construct a TOC.
        for node in list(root):
            if node.tag == 'h1': root.remove(node)
        for node in root.iter():
            if node.tag in ('h2', 'h3'): node.set('tabindex', '-1')
            if node.tag == 'a':
                scheme = urlsplit(node.get('href','')).scheme
                if scheme and scheme != 'https': raise ValueError('Only HTTPS external links supported')
        for parent in list(root.iter()):
            for node in list(parent):
                if node.tag != 'p' or len(node) != 1 or node[0].tag != 'img': continue
                img = node[0]; src = img.get('src','')
                if '/' in src or not src.endswith('.png'): raise ValueError('Expected local PNG image')
                node.tag = 'figure'; node.set('class','note-figure'); node.remove(img)
                a = ET.SubElement(node,'a',{'href':src,'target':'_blank','rel':'noopener'})
                img.set('loading','lazy'); a.append(img)
                caption = ET.SubElement(node,'figcaption')
                caption.text = img.get('alt','') + ' · 点击查看原图'
                if src == 'hermes-skills-curator.png':
                    caption.set('style', 'text-align:center')
        return root

class ReadingExtension(Extension):
    def extendMarkdown(self, md):
        # Author Markdown only, raw HTML is not interpreted.
        md.preprocessors.deregister('html_block')
        md.inlinePatterns.deregister('html')
        md.treeprocessors.register(ReadingElements(md), 'reading_elements', 6)

def render(text):
    md = markdown.Markdown(extensions=['toc', 'fenced_code', ReadingExtension()], extension_configs={
        'toc': {'marker':'', 'toc_depth':'2-3', 'slugify':stable_slug},
    })
    body = md.convert(text)
    return body, md.toc, md.toc_tokens
