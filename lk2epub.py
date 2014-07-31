import re
import sys
import threading
import uuid

from bs4 import BeautifulSoup
import requests

from generate_epub import generate_epub
from global_variable import HAS_QT, SENDER, HEADERS, single_thread, retrun_single


class Epub():
    """
    store epub information

    Attributes:
        volume_name: A string represent the volume name
        volume_number: A string represent the volume number
        volume_author: A string represent the author
        volume_illuster: A string represent the illuster
        volume_introduction: A string represent the introduction
        volume_cover_url: A string represent the cover_url
        chapter_links: A string represent the chapter links
        cover_path: A string represent the cover path
        book_namer: A string represent the book name
        uuid: A string represent the book uuid
        chapter: A list represent the chapter

    """
    def __init__(self, volume_name, volume_number, author, illuster, introduction, cover_url, chapter_links,
                 cover_path=None):
        self.volume_name = volume_name
        self.volume_number = volume_number
        self.author = author
        self.illuster = illuster
        self.introduction = introduction
        self.cover_url = cover_url
        self.chapter_links = chapter_links
        self.cover_path = cover_path
        self.book_name = self.volume_name + ' ' + self.volume_number
        self.uuid=str(uuid.uuid1())
        self.chapter = []


    def addChapter(self, chapter):
        """
        add chapter
        chapter structure：a tuple (chapter number,chapter name,content)
        """
        self.chapter.append(chapter)


def get_urls():
    """
    Get urls from input or sys.argv

    Return:
        A string contains urls
    """
    for i in sys.argv[1:]:
        if i.startswith('-u'):
            return i[2:]
    else:
        urls = input('Please input urls（separate with ","）:')
        return urls


def is_single_thread():
    for i in sys.argv[1:]:
        if i.startswith('-s'):
            return True
    else:
        single = input("Single Thread(Y/N)?:")
        return True if single in ['Y', 'y'] else False


def check_url(url):
    """
    check input url

    Args:
        url: A string represent the url which was input by user

    Returns:
        return 'vollist' if the url represent a vollist
        return 'book' if the url represent a book
        return False if the url is neither vollist nor booklist
    """
    vollist = re.compile(r'http://lknovel.lightnovel.cn/main/vollist/(\d+).html')
    book = re.compile(r'http://lknovel.lightnovel.cn/main/book/(\d+).html')
    if vollist.search(url):
        return 'vollist'
    elif book.search(url):
        return 'book'
    else:
        return False


def print_info(info):
    print(info)
    if HAS_QT:
        SENDER.sigChangeStatus.emit(info)


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


def extract_epub_info(soup):
    """
    extract volume's basic info

    Args:
        soup: A parsed page

    Return:
        A dict contains the volume's info
    """
    name_and_number = str(soup.select('h1.ft-24 strong'))[1:-1].replace('</strong>', '').split('\n')
    volume_name = name_and_number[1].strip()
    volume_number = name_and_number[2].strip()
    print_info('volume_name:' + volume_name + '\nvolume_number:' + volume_number)

    temp_author_name = soup.select('table.lk-book-detail td')
    find_author_name = re.compile(r'target="_blank">(.*)</a></td>')
    find_illuster_name = re.compile(r'<td>(.*)</td>')
    author = find_author_name.search(str(temp_author_name[3])).group(1)
    illuster = find_illuster_name.search(str(temp_author_name[5])).group(1)
    print_info('author:' + author + '\nilluster:' + illuster)

    temp_introduction = soup.select(
        'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span10 p')
    find_introduction = re.compile(r'<p style="width:42em; text-indent: 2em;">(.*)</p>')
    introduction = find_introduction.search(str(temp_introduction).replace('\n', '')).group(1)

    temp_cover_url = soup.select(
        'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span2 div.lk-book-cover a')
    find_cover_url = re.compile(r'<img src="(.*)"/>')
    cover_url = 'http://lknovel.lightnovel.cn' + find_cover_url.search(str(temp_cover_url)).group(1)

    chapter_links = find_chapter_links(soup)

    epub_info = {'volume_name': volume_name, 'volume_number': volume_number, 'author': author,
                 'illuster': illuster, 'introduction': introduction, 'cover_url': cover_url,
                 'chapter_links': chapter_links}
    return epub_info


def create_epub_instance(url):
    soup = parse_page(url)
    epub_info = extract_epub_info(soup)
    return Epub(**epub_info)


def get_new_chapter_name(soup):
    """
    get the formal chapter name

    Args:
        soup: A parsed page

    Returns:
        A string contain the chapter name
    """
    temp_chapter_name = soup.select('html body div.content div.container ul.breadcrumb li.active')
    find_chapter_name = re.compile(r'<li class="active">(.*)</li>')
    chapter_name = find_chapter_name.search(str(temp_chapter_name)).group(1)
    new_chapter_name = chapter_name[:chapter_name.index('章') + 1] + ' ' + chapter_name[chapter_name.index('章') + 1:]
    return new_chapter_name


def get_content(soup):
    """
    extract contents from each page
    
    Args:
        soup: parsed page
        
    Return:
        A list contain paragraphs of one chapter
    """
    content=[]
    temp_chapter_content=soup.select('div.lk-view-line')
    find_picture_url=re.compile(r'data-cover="(.*)" src="')
    for line in temp_chapter_content:
        if 'lk-view-img' not in str(line):
            content.append(line.get_text().strip())
        else:
            picture_url=find_picture_url.search(str(line)).group(1)
            content.append(picture_url)
    return content


def extract_chapter(url, epub, number):
    """
    add each chapter's content to the Epub instance
    
    Args:
        url: A string represent the chapter url to be added
        epub: A Epub instance
        number: A int represent the chapter's number
    """
    try:
        soup = parse_page(url)

        new_chapter_name = get_new_chapter_name(soup)
        print_info(new_chapter_name)
        content = get_content(soup)

        epub.addChapter((number, new_chapter_name, content))

    except Exception as e:
        if HAS_QT:
            SENDER.sigWarningMessage.emit('错误', str(e) + ('\nat:') + url)
            SENDER.sigButton.emit()
        print(url)
        raise e


def get_chapter_content(epub):
    """
    start extract every chapter in epub

    Args:
        epub: The Epub instance to be created
    """
    th = []

    if not retrun_single():
        for i, link in enumerate(epub.chapter_links):
            t = threading.Thread(target=extract_chapter, args=(link, epub, i))
            t.start()
            th.append(t)
        for t in th:
            t.join()
    else:
        for i, link in enumerate(epub.chapter_links):
            extract_chapter(link, epub, i)


def grab_volume(url, epub_file_path=None, cover_path=None):
    """
    grab volume
    
    Args:
        url: A string represent the url which was input by user
        epub_file_path: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    try:
        print_info('Getting:' + url)
        epub = create_epub_instance(url)

        if cover_path:
            epub.cover_path = cover_path

        get_chapter_content(epub)
        print_info('网页获取完成\n开始生成Epub')

        generate_epub(epub, epub_file_path)

    except Exception as e:
        if HAS_QT:
            SENDER.sigWarningMessage.emit('错误', str(e) + '\nat:' + url)
            SENDER.sigButton.emit()
        print(url)
        raise e


def grab_booklist(url, epub_file_path=None, cover_path=None):
    """
    grab each volume in the booklist

    Args:
        url: A string represent the booklist
        epub_file_path: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    soup = parse_page(url)
    temp_volume_link = soup.select('body div.content div.container dl dd.row div.inline h2.ft-24 strong a')
    find_lolume_link = re.compile(r'<a href="(.*)">')
    for i in temp_volume_link:
        volume_link = find_lolume_link.search(str(i)).group(1)
        grab_volume(volume_link, epub_file_path, cover_path)


def start(urls, epub_file_path=None, cover_path=None):
    """
    start the job using url

    Args:
        urls: A string represent the urls which was input by user
        epub_file_path: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    for url in urls.split(','):
        check_result = check_url(url)
        if check_result == 'book':
            grab_volume(url, epub_file_path, cover_path)
        elif check_result == 'vollist':
            grab_booklist(url, epub_file_path, cover_path)
        else:
            print(
                '请输入正确的网址，例如：\nhttp://lknovel.lightnovel.cn/main/vollist/726.html' +
                '\nhttp://lknovel.lightnovel.cn/main/book/2664.html')


def main():
    urls = get_urls()
    if is_single_thread():
        single_thread()

    start(urls)


if __name__ == '__main__':
    main()
