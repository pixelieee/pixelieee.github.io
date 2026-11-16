"""Count Chinese characters and English/alphanumeric words in rendered article text."""
from html.parser import HTMLParser
import re
from markdown_renderer import render

TOKEN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]|[A-Za-z0-9]+')
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in {'p','div','li','h2','h3','h4','h5','h6','pre','blockquote','figure','figcaption','br'}:
            self.parts.append('\n')
    def handle_endtag(self, tag):
        self.handle_starttag(tag, [])

def count_words(markdown_source):
    body, _, _ = render(markdown_source)
    parser = VisibleText()
    parser.feed(body)
    return len(TOKEN.findall(''.join(parser.parts)))
