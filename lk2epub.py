import re
import sys

from bs4 import BeautifulSoup
import requests

from epub import Epub
from global_variable import HAS_QT, SENDER, HEADERS


SINGLE_THREAD = False


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


def grab_volume(url, epub_file_path, cover_path):
    """
    grab volume
    
    Args:
        url: A string represent the url which was input by user
        epub_file_path: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    try:
        print_info('Getting:' + url)
        epub = Epub(url=url, epub_file_path=epub_file_path, cover_path=cover_path, single_thread=SINGLE_THREAD)

        epub.generate_epub()

    except Exception as e:
        if HAS_QT:
            SENDER.sigWarningMessage.emit('错误', str(e) + '\nat:' + url)
            SENDER.sigButton.emit()
        print(url)
        raise e


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


def grab_booklist(url, epub_file_path, cover_path):
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
        global SINGLE_THREAD
        SINGLE_THREAD = True

    start(urls)


if __name__ == '__main__':
    main()
