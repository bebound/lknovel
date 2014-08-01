import codecs
import threading
import os
import re
import queue
import shutil
import uuid
import zipfile

from bs4 import BeautifulSoup
import requests

from global_variable import HAS_QT, SENDER, HEADERS

DOWNLOAD_QUEUE = queue.Queue()


class Epub():
    """
    deal with epub

    Attributes:
        volume_name: A string represent the volume name
        volume_number: A string represent the volume number
        volume_author: A string represent the author
        volume_illuster: A string represent the illuster
        volume_introduction: A string represent the introduction
        volume_cover_url: A string represent the cover_url
        chapter_links: A string represent the chapter links
        epub_file_path: A stirng represent the epub save path
        cover_path: A string represent the cover path
        book_namer: A string represent the book name
        uuid: A string represent the book uuid
        chapter: A list represent the chapter
        base_path: A string represent the epub temp path

    """
    def __init__(self, url, epub_file_path='', cover_path='', single_thread=False):
        self.url = url
        self.epub_file_path = epub_file_path
        self.cover_path = cover_path
        self.single_thread = single_thread

        self.uuid = str(uuid.uuid1())

        self.chapter = []
        self.volume_name = ''
        self.volume_number = ''
        self.author = ''
        self.illuster = ''
        self.introduction = ''
        self.cover_url = ''
        self.chapter_links = ''
        self.book_name = ''
        self.base_path = ''

    @staticmethod
    def parse_page(url):
        """
        parse page with BeautifulSoup

        Args:
            url: A string represent the url to be parsed

        Return:
            A BeatifulSoup element
        """
        r = requests.get(url, headers=HEADERS)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text)

    @staticmethod
    def find_chapter_links(soup):
        """
        extract chapter links from page

        Args:
            soup: A parsed page

        Returns:
            a list contains the book's chapter links
        """
        temp_chapter_links = soup.select(
            'body div.content div.container div.row-fluid div.span9 div.well div.row-fluid ul.lk-chapter-list li')
        find_chapter_links = re.compile(r'<a href="(.*)">')
        chapter_links = []
        for i in temp_chapter_links:
            chapter_links.append(find_chapter_links.search(str(i)).group(1))
        return chapter_links

    def find_volume_name_number(self, soup):
        name_and_number = str(soup.select('h1.ft-24 strong'))[1:-1].replace('</strong>', '').split('\n')
        self.volume_name = name_and_number[1].strip()
        self.volume_number = name_and_number[2].strip()
        self.book_name = self.volume_name + ' ' + self.volume_number
        self.print_info('Volume_name:' + self.volume_name + ',Volume_number:' + self.volume_number)

    def find_author_illuster(self, soup):
        temp_author_name = soup.select('table.lk-book-detail td')
        find_author_name = re.compile(r'target="_blank">(.*)</a></td>')
        find_illuster_name = re.compile(r'<td>(.*)</td>')
        self.author = find_author_name.search(str(temp_author_name[3])).group(1)
        self.illuster = find_illuster_name.search(str(temp_author_name[5])).group(1)
        self.print_info('Author:' + self.author + '\nIlluster:' + self.illuster)

    def find_introduction(self, soup):
        temp_introduction = soup.select(
            'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span10 p')
        find_introduction = re.compile(r'<p style="width:42em; text-indent: 2em;">(.*)</p>')
        self.introduction = find_introduction.search(str(temp_introduction).replace('\n', '')).group(1)

    def find_cover_url(self, soup):
        temp_cover_url = soup.select(
            'div.container div.row-fluid div.span9 div.well div.row-fluid div.span2 div.lk-book-cover a')
        find_cover_url = re.compile(r'<img src="(.*)"/>')
        self.cover_url = 'http://lknovel.lightnovel.cn' + find_cover_url.search(str(temp_cover_url)).group(1)

    def extract_epub_info(self):
        """
        extract volume's basic info

        Args:
            soup: A parsed page

        Return:
            A dict contains the volume's info
        """
        soup = self.parse_page(self.url)

        self.find_volume_name_number(soup)
        self.find_author_illuster(soup)
        self.find_introduction(soup)
        self.find_cover_url(soup)
        self.chapter_links = self.find_chapter_links(soup)

    @staticmethod
    def get_new_chapter_name(soup):
        """
        get the formal chapter name

        Args:
            soup: A parsed page

        Returns:
            A string contain the chapter name
        """
        chapter_name = soup.select('h3.ft-20')[0].get_text()
        new_chapter_name = chapter_name[:chapter_name.index('章') + 1] + ' ' + chapter_name[chapter_name.index('章') + 1:]
        return new_chapter_name

    @staticmethod
    def print_info(info):
        print(info)
        if HAS_QT:
            SENDER.sigChangeStatus.emit(info)

    @staticmethod
    def get_content(soup):
        """
        extract contents from each page

        Args:
            soup: parsed page

        Return:
            A list contain paragraphs of one chapter
        """
        content = []
        temp_chapter_content = soup.select('div.lk-view-line')
        find_picture_url = re.compile(r'data-cover="(.*)" src="')
        for line in temp_chapter_content:
            if 'lk-view-img' not in str(line):
                content.append(line.get_text().strip())
            else:
                picture_url = find_picture_url.search(str(line)).group(1)
                content.append(picture_url)
        return content

    def add_chapter(self, chapter):
        """
        add chapter
        chapter structure：a tuple (chapter number,chapter name,content)
        """
        self.chapter.append(chapter)

    def extract_chapter(self, url, number):
        """
        add each chapter's content to the Epub instance

        Args:
            url: A string represent the chapter url to be added
            epub: A Epub instance
            number: A int represent the chapter's number
        """
        try:
            soup = self.parse_page(url)

            new_chapter_name = self.get_new_chapter_name(soup)
            self.print_info(new_chapter_name)
            content = self.get_content(soup)
            self.add_chapter((number, new_chapter_name, content))

        except Exception as e:
            if HAS_QT:
                SENDER.sigWarningMessage.emit('错误', str(e) + '\nat:' + url)
                SENDER.sigButton.emit()
            print(self.url)
            raise e

    def get_chapter_content(self):
        """
        start extract every chapter in epub

        Args:
            epub: The Epub instance to be created
        """
        th = []

        if not self.single_thread:
            for i, link in enumerate(self.chapter_links):
                t = threading.Thread(target=self.extract_chapter, args=(link, i))
                t.start()
                th.append(t)
            for t in th:
                t.join()
        else:
            for i, link in enumerate(self.chapter_links):
                self.extract_chapter(link, i)

    def create_folders(self):
        if not os.path.exists(self.base_path):
            os.mkdir(self.base_path)
        if not os.path.exists(os.path.join(self.base_path, 'Text')):
            os.mkdir(os.path.join(os.path.join(self.base_path, 'Text')))
        if not os.path.exists(os.path.join(self.base_path, 'Styles')):
            os.mkdir(os.path.join(os.path.join(self.base_path, 'Styles')))
        if not os.path.exists(os.path.join(self.base_path, 'Images')):
            os.mkdir(os.path.join(os.path.join(self.base_path, 'Images')))
        shutil.copy2('./templates/style.css', os.path.join(os.path.join(self.base_path, 'Styles')))

    def move_or_download_cover(self):
        if not self.cover_path:
            DOWNLOAD_QUEUE.put(self.cover_url)
        else:
            temp_cover_path = os.path.join(os.path.join(self.base_path, 'Images'), self.cover_path.split('/')[-1])
            shutil.copyfile(self.cover_path, temp_cover_path)

    def download_picture(self):
        """
        download pictures from DOWNLOAD_QUEUE
        """
        while not DOWNLOAD_QUEUE.empty():
            try:
                url = DOWNLOAD_QUEUE.get()
                path = os.path.join(os.path.join(self.base_path, 'Images'), url.split('/')[-1])
                if not os.path.exists(path):
                    print('downloading:', url)
                    if HAS_QT:
                        SENDER.sigChangeStatus.emit('downloading:' + url.split('/')[-1])
                    r = requests.get(url, headers=HEADERS, stream=True)
                    if r.status_code == requests.codes.ok:
                        temp_chunk = r.content
                        with open(path, 'wb') as f:
                            f.write(temp_chunk)
            except:
                DOWNLOAD_QUEUE.put(url)
            finally:
                DOWNLOAD_QUEUE.task_done()

    @staticmethod
    def sort_itemref(file_name):
        m = re.match('\d+', file_name)
        if m:
            return int(m.group(0))
        else:
            return -1

    @staticmethod
    def file_to_string(file_path):
        """
        read the file as a tring

        Return:
            A string
        """
        with codecs.open(file_path, 'r', 'utf-8') as f:
            return ''.join(f.readlines())

    def create_cover_html(self):
        cover_name = self.cover_url.split('/')[-1]
        cover_html = self.file_to_string('./templates/Cover.html')
        final_cover_html = cover_html.format(cover_name=cover_name, introduction=self.introduction)
        return final_cover_html

    @staticmethod
    def write_html(html, file_path):
        with codecs.open(file_path, 'w', 'utf-8') as f:
            f.write(BeautifulSoup(html).prettify())

    def create_chapter_html(self):
        chapter_html = self.file_to_string('./templates/Chapter.html')
        final_chapter_htmls = []
        for chapter in sorted(self.chapter, key=lambda x: x[0]):
            content = []
            chapter_name = chapter[1]

            for line in chapter[2]:
                if line.startswith('/illustration/'):
                    image_url = 'http://lknovel.lightnovel.cn' + line
                    DOWNLOAD_QUEUE.put(image_url)
                    image = '<div class="illust"><img alt="" src="../Images/' + image_url.split('/')[
                        -1] + '" /></div>\n<br/>'
                    content.append(image)
                else:
                    content.append('<p>' + line + '</p>')
            one_chapter_html = chapter_html.format(chapter_name=chapter_name, content='\n'.join(content))
            final_chapter_htmls.append(one_chapter_html)
        return final_chapter_htmls

    def create_title_html(self):
        title_html = self.file_to_string('./templates/Title.html')
        final_title_html = title_html.format(book_name=self.book_name, volume_name=self.volume_name,
                                             volume_number=self.volume_number, author=self.author,
                                             illuster=self.illuster)
        return final_title_html

    def create_contents_html(self):
        contents_html = self.file_to_string('./templates/Contents.html')
        contents = []
        for i in sorted(self.chapter, key=lambda chapter: chapter[0]):
            contents.append('<li class="c-rules"><a href="../Text/' + str(i[0]) + '.html">' + i[1] + '</a></li>')
        final_contetns_html = contents_html.format(contents='\n'.join(contents))
        return final_contetns_html

    def download_all_pictures(self):
        th = []
        for i in range(5):
            t = threading.Thread(target=self.download_picture)
            t.start()
            th.append(t)
        for i in th:
            i.join()

    def create_content_opf_html(self):
        content_opf_html = self.file_to_string('./templates/content.opf')
        cover_name = self.cover_url.split('/')[-1]

        file_paths = []
        for dir_path, dir_names, file_names in os.walk(os.path.join(self.base_path, 'Text')):
            for file in file_names:
                if file != 'toc.ncx':
                    file_paths.append(
                        '<item href="Text/' + file + '" id="' + file + '" media-type="application/xhtml+xml" />')
            break

        file_paths.append('<item href="Styles/style.css" id="style.css" media-type="text/css" />')

        for dir_path, dir_names, file_names in os.walk(os.path.join(self.base_path, 'Images')):
            for file in file_names:
                postfix = file.split('.')[-1]
                postfix = 'jpeg' if postfix == 'jpg' else postfix
                file_paths.append(
                    '<item href="Images/' + file + '" id="' + file + '" media-type="image/' + postfix + '" />')
            break

        chapter_orders = []

        for dir_path, dir_names, file_names in os.walk(os.path.join(self.base_path, 'Text')):
            for file in sorted(file_names, key=self.sort_itemref):
                if file not in ('Cover.html', 'Title.html', 'Contents.html'):
                    chapter_orders.append('<itemref idref="' + file + '" />')
        final_content_opf_html = content_opf_html.format(book_name=self.book_name, uuid=self.uuid,
                                                         cover_name=cover_name,
                                                         author=self.author, file_paths='\n'.join(file_paths),
                                                         chapter_orders='\n'.join(chapter_orders))
        return final_content_opf_html

    def create_toc_html(self):
        toc_html = self.file_to_string('./templates/toc.ncx')
        nav = []
        playorder = 4
        for i in sorted(self.chapter, key=lambda chapter: chapter[0]):
            nav.append(
                '<navPoint id="' + str(i[0]) + '" playOrder="' + str(playorder) + '">\n<navLabel>\n<text>' + i[
                    1] + '</text>\n</navLabel>\n<content src="Text/' + str(i[0]) + '.html"/>\n</navPoint>')
            playorder += 1
        final_toc_html = toc_html.format(uuid=self.uuid, book_name=self.book_name, author=self.author,
                                         nav='\n'.join(nav))
        return final_toc_html

    def create_html(self):
        """
        create the html file for epub
        """
        html_path = os.path.join(self.base_path, 'Text')

        cover_html = self.create_cover_html()
        self.write_html(cover_html, os.path.join(html_path, 'Cover.html'))

        chapter_htmls = self.create_chapter_html()
        for i, chapter_html in enumerate(chapter_htmls):
            self.write_html(chapter_html, os.path.join(html_path, str(i) + '.html'))

        title_html = self.create_title_html()
        self.write_html(title_html, os.path.join(html_path, 'Title.html'))

        contents_html = self.create_contents_html()
        self.write_html(contents_html, os.path.join(html_path, 'Contents.html'))

        os.path.join(html_path, 'Contents.html')

        self.download_all_pictures()

        content_opf_html = self.create_content_opf_html()
        self.write_html(content_opf_html, os.path.join(self.base_path, 'content.opf'))

        toc_html = self.create_toc_html()
        self.write_html(toc_html, os.path.join(self.base_path, 'toc.ncx'))

    def zip_files(self):
        folder_name = os.path.basename(self.base_path)
        with zipfile.ZipFile(folder_name + '.epub', 'w', zipfile.ZIP_DEFLATED) as z:
            for dir_path, dir_names, file_names in os.walk(self.base_path):
                for file in file_names:
                    f = os.path.join(dir_path, file)
                    z.write(f, 'OEBPS//' + f[len(self.base_path) + 1:])
            z.write('./files/container.xml', 'META-INF//container.xml')
            z.write('./files/mimetype', 'mimetype')

    def move_epub_file(self):
        folder_name = os.path.basename(self.base_path)
        if os.path.exists(os.path.join(self.epub_file_path, folder_name + '.epub')):
            if HAS_QT:
                SENDER.sigWarningMessage.emit('文件名已存在', 'epub保存在lknovel文件夹')
                SENDER.sigButton.emit()
        else:
            shutil.move(folder_name + '.epub', self.epub_file_path)
            if HAS_QT:
                SENDER.sigInformationMessage.emit('已生成', folder_name + '.epub')
                SENDER.sigButton.emit()

    def generate_epub(self):
        """
        generate epub file by the Epub instance

        Args:
            epub: A Epub instance
            epub_file_path: A string represent the path of the output EPUB file
        """
        self.extract_epub_info()
        self.get_chapter_content()
        self.print_info('网页获取完成\n开始生成Epub')

        folder_name = re.sub(r'[<>:"/\\|\?\*]', '_', self.book_name)
        self.base_path = os.path.abspath(folder_name)
        self.create_folders()
        self.move_or_download_cover()

        self.create_html()

        self.zip_files()
        print('已生成：', self.book_name + '.epub\n\n')

        # delete temp file
        shutil.rmtree(self.base_path)

        # move file
        if self.epub_file_path:
            self.move_epub_file()
