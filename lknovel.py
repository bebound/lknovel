# !/usr/bin/env python3
"""lknovel

Usage:
    lknovel.py
    lknovel.py <url>... [-s] [-o | --output=<output_dir>] [-c | --cover=<cover_path>]
    lknovel.py -h | --help
    lknovel.py -v | --version

Arguments:
    <url>                                      Novel url

Options:
    -s                                         Single thread
    -o=<output_dir> --output=<output_dir>      Output folder
    -c=<cover_path> --cover=<cover_path>       Cover path
    -h --help                                  Show this screen
    -v --version                               Show version

Examples:
    lknovel.py http://lknovel.lightnovel.cn/main/vollist/492.html -s
    lknovel.py http://lknovel.lightnovel.cn/main/book/1578.html -o d:/
"""
import re
import sys

from bs4 import BeautifulSoup
from docopt import docopt
import requests

from epub import Epub
from global_variable import HAS_QT, HEADERS
from novel import Novel

if HAS_QT:
    from global_variable import SENDER

SINGLE_THREAD = False


def is_single_thread():
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


def grab_volume(url, output_dir, cover_path):
    """
    grab volume
    
    Args:
        url: A string represent the url which was input by user
        output_dir: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    try:
        print_info('Getting:' + url)
        novel = Novel(url=url, single_thread=SINGLE_THREAD)
        novel.get_novel_information()
        epub = Epub(output_dir=output_dir, cover_path=cover_path, **novel.novel_information())
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


def grab_booklist(url, output_dir, cover_path):
    """
    grab each volume in the booklist

    Args:
        url: A string represent the booklist
        output_dir: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    soup = parse_page(url)
    temp_volume_link = soup.select('body div.content div.container dl dd.row div.inline h2.ft-24 strong a')
    find_lolume_link = re.compile(r'<a href="(.*)">')
    for i in temp_volume_link:
        volume_link = find_lolume_link.search(str(i)).group(1)
        grab_volume(volume_link, output_dir, cover_path)


def start(urls, output_dir=None, cover_path=None):
    """
    start the job using url

    Args:
        urls: A string represent the urls which was input by user
        output_dir: A string represent the path of the output EPUB file
        cover_file: A string represent the path of the EPUB cover
    """
    for url in urls:
        check_result = check_url(url)
        if check_result == 'book':
            grab_volume(url, output_dir, cover_path)
        elif check_result == 'vollist':
            grab_booklist(url, output_dir, cover_path)
        else:
            print('请输入正确的网址，例如：\nhttp://lknovel.lightnovel.cn/main/vollist/492.html'
                  '\nhttp://lknovel.lightnovel.cn/main/book/1578.html')


def main():
    global SINGLE_THREAD
    if len(sys.argv) > 1:
        urls = arguments['<url>']
        SINGLE_THREAD = arguments['-s']
        output_dir = None if not arguments['--output'] else arguments['--output'][0]
        cover_path = None if not arguments['--cover'] else arguments['--cover'][0]
    else:
        urls = input('Please input urls（separate with space）:').split()
        if is_single_thread():
            SINGLE_THREAD = True
        output_dir = None
        cover_path = None

    start(urls, output_dir, cover_path)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Lknovel 1.0')
    sys.exit(main())
