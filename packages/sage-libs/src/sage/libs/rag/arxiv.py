from typing import Any, List, Literal, Optional, Union
from typing import Any, List, Optional
from urllib.parse import quote
import feedparser
import os
import requests
import time
import json
import fitz
from PIL import Image
from collections import Counter
import json
import re

from sage.core.api.function.map_function import MapFunction



class Paper:
    def __init__(self, path, title='', url='', abs='', authors=[],**kwargs):
        super().__init__(**kwargs)
        # 初始化函数，根据pdf路径初始化Paper对象                
        self.url = url  # 文章链接
        self.path = path  # pdf路径
        self.section_names = []  # 段落标题
        self.section_texts = {}  # 段落内容
        self.abs = abs
        self.title_page = 0
        if title == '':
            self.pdf = fitz.open(self.path)  # pdf文档
            self.title = self.get_title()
            self.parse_pdf()
        else:
            self.title = title
        self.authors = authors
        self.roman_num = ["I", "II", 'III', "IV", "V", "VI", "VII", "VIII", "IIX", "IX", "X"]
        self.digit_num = [str(d + 1) for d in range(10)]
        self.first_image = ''

    def parse_pdf(self):
        self.pdf = fitz.open(self.path)  # pdf文档
        self.text_list = [page.get_text() for page in self.pdf]
        self.all_text = ' '.join(self.text_list)
        self.extract_section_infomation()
        self.section_texts.update({"title": self.title})
        self.pdf.close()

    # 定义一个函数，根据字体的大小，识别每个章节名称，并返回一个列表
    def get_chapter_names(self, ):
        # # 打开一个pdf文件
        doc = fitz.open(self.path)  # pdf文档
        text_list = [page.get_text() for page in doc]
        all_text = ''
        for text in text_list:
            all_text += text
        # # 创建一个空列表，用于存储章节名称
        chapter_names = []
        for line in all_text.split('\n'):
            line_list = line.split(' ')
            if '.' in line:
                point_split_list = line.split('.')
                space_split_list = line.split(' ')
                if 1 < len(space_split_list) < 5:
                    if 1 < len(point_split_list) < 5 and (
                            point_split_list[0] in self.roman_num or point_split_list[0] in self.digit_num):
                        # print("line:", line)
                        chapter_names.append(line)

        return chapter_names

    def get_title(self):
        doc = self.pdf  # 打开pdf文件
        max_font_size = 0  # 初始化最大字体大小为0
        max_string = ""  # 初始化最大字体大小对应的字符串为空
        max_font_sizes = [0]
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block['lines']):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        font_size = block["lines"][0]["spans"][0]["size"]  # 获取第一行第一段文字的字体大小
                        max_font_sizes.append(font_size)
                        if font_size > max_font_size:  # 如果字体大小大于当前最大值
                            max_font_size = font_size  # 更新最大值
                            max_string = block["lines"][0]["spans"][0]["text"]  # 更新最大值对应的字符串
        max_font_sizes.sort()
        # print("max_font_sizes", max_font_sizes[-10:])
        cur_title = ''
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block['lines']):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        cur_string = block["lines"][0]["spans"][0]["text"]  # 更新最大值对应的字符串
                        font_flags = block["lines"][0]["spans"][0]["flags"]  # 获取第一行第一段文字的字体特征
                        font_size = block["lines"][0]["spans"][0]["size"]  # 获取第一行第一段文字的字体大小
                        # print(font_size)
                        if abs(font_size - max_font_sizes[-1]) < 0.3 or abs(font_size - max_font_sizes[-2]) < 0.3:
                            # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags)                            
                            if len(cur_string) > 4 and "arXiv" not in cur_string:
                                # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags) 
                                if cur_title == '':
                                    cur_title += cur_string
                                else:
                                    cur_title += ' ' + cur_string
                                self.title_page = page_index
                                # break
        title = cur_title.replace('\n', ' ')
        return title

    def extract_section_infomation(self):
        doc = fitz.open(self.path)

        # 获取文档中所有字体大小
        font_sizes = []
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if 'lines' not in block:
                    continue
                lines = block["lines"]
                for line in lines:
                    for span in line["spans"]:
                        font_sizes.append(span["size"])
        most_common_size, _ = Counter(font_sizes).most_common(1)[0]

        # 按照最频繁的字体大小确定标题字体大小的阈值
        threshold = most_common_size * 1
        section_dict = {}
        section_dict["Abstract"] = ""
        last_heading = None
        subheadings = []
        heading_font = -1
        # 遍历每一页并查找子标题
        found_abstract = False
        upper_heading = False
        font_heading = False
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if not found_abstract:
                    try:
                        text = json.dumps(block)
                    except:
                        continue
                    if re.search(r"\bAbstract\b", text, re.IGNORECASE):
                        found_abstract = True
                        last_heading = "Abstract"
                if found_abstract:
                    if 'lines' not in block:
                        continue
                    lines = block["lines"]
                    for line in lines:
                        for span in line["spans"]:
                            # 如果当前文本是子标题
                            if not font_heading and span["text"].isupper() and sum(1 for c in span["text"] if c.isupper() and ('A' <= c <='Z')) > 4:  # 针对一些标题大小一样,但是全大写的论文
                                upper_heading = True
                                heading = span["text"].strip()
                                if "References" in heading:  # reference 以后的内容不考虑
                                    self.section_names = subheadings
                                    self.section_texts = section_dict
                                    return
                                subheadings.append(heading)
                                if last_heading is not None:
                                    section_dict[last_heading] = section_dict[last_heading].strip()
                                section_dict[heading] = ""
                                last_heading = heading
                            if not upper_heading and span["size"] > threshold and re.match(  # 正常情况下,通过字体大小判断
                                    r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*",
                                    span["text"].strip()):
                                font_heading = True
                                if heading_font == -1:
                                    heading_font = span["size"]
                                elif heading_font != span["size"]:
                                    continue
                                heading = span["text"].strip()
                                if "References" in heading:  # reference 以后的内容不考虑
                                    self.section_names = subheadings
                                    self.section_texts = section_dict
                                    return
                                subheadings.append(heading)
                                if last_heading is not None:
                                    section_dict[last_heading] = section_dict[last_heading].strip()
                                section_dict[heading] = ""
                                last_heading = heading
                            # 否则将当前文本添加到上一个子标题的文本中
                            elif last_heading is not None:
                                section_dict[last_heading] += " " + span["text"].strip()
        self.section_names = subheadings
        self.section_texts = section_dict

class ArxivPDFDownloader(MapFunction):
    def __init__(self, config):
        super().__init__()
        config = config["ArxivPDFDownloader"]
        self.max_results = config.get("max_results", 5)
        self.save_dir = config.get("save_dir", "arxiv_pdfs")
        os.makedirs(self.save_dir, exist_ok=True)

    def execute(self, data: str) -> List[str]:
        self.query = data
        base_url = 'http://export.arxiv.org/api/query?'
        encoded_query = quote(self.query)
        query = f'search_query={encoded_query}&start=0&max_results={self.max_results}&sortBy=submittedDate&sortOrder=descending'
        url = base_url + query
        feed = feedparser.parse(url)

        pdf_paths = []

        print(feed)
        for entry in feed.entries:
            arxiv_id = entry.id.split('/abs/')[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            pdf_path = os.path.join(self.save_dir, f"{arxiv_id}.pdf")

            if not os.path.exists(pdf_path):
                try:
                    resp = requests.get(pdf_url, timeout=15)
                    if resp.status_code == 200:
                        with open(pdf_path, 'wb') as f:
                            f.write(resp.content)
                        pdf_paths.append(pdf_path)
                        self.logger.info(f"Downloaded: {pdf_path}")
                    else:
                        self.logger.error(f"HTTP {resp.status_code} for {pdf_url}")
                except Exception as e:
                    self.logger.error(f"Failed to download {pdf_url}: {e}")
            else:
                self.logger.info(f"File already exists: {pdf_path}")
                pdf_paths.append(pdf_path)

            time.sleep(1)  # 防止请求过快

        return pdf_paths


class ArxivPDFParser(MapFunction):
    def __init__(self, config):
        super().__init__()
        config = config["ArxivPDFParser"]
        print(config)
        self.output_dir = config.get("output_dir", "arxiv_structured_json")
        os.makedirs(self.output_dir, exist_ok=True)

    def execute(self, data: str) -> List[str]:

        pdf_paths = data
        output_paths = []

        for pdf_path in pdf_paths:

            filename = os.path.basename(pdf_path).replace('.pdf', '.json')
            json_path = os.path.join(self.output_dir, filename)

            if not os.path.exists(json_path):
                try:
                    paper = Paper(pdf_path)
                    paper.parse_pdf()
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            "title": paper.title,
                            "authors": paper.authors,
                            "abs": paper.abs,
                            "sections": paper.section_texts
                        }, f, ensure_ascii=False, indent=4)
                    output_paths.append(json_path)
                    self.logger.info(f"Parsed and saved: {json_path}")
                except Exception as e:
                    self.logger.error(f"Failed to parse {pdf_path}: {e}")
            else:
                self.logger.info(f"JSON already exists: {json_path}")
                output_paths.append(json_path)

        return output_paths