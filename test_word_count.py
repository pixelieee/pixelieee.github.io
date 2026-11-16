import unittest
from word_count import count_words
class WordCountTests(unittest.TestCase):
    def test_chinese_and_english(self):
        self.assertEqual(count_words('中文 English 123，。'), 4)
    def test_visible_link_label_only(self):
        self.assertEqual(count_words('[源码](https://example.com/very/long/destination)'), 2)
    def test_headings_not_toc_or_title(self):
        self.assertEqual(count_words('# Page title\n\n## 小节\n\n正文'), 4)
    def test_inline_formatting(self):
        self.assertEqual(count_words('**中文** `memory_tool` A**B**'), 5)
    def test_caption_once_not_img_attributes(self):
        self.assertEqual(count_words('![流程](figure.png)'), 8)
if __name__=='__main__': unittest.main()
