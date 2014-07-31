import codecs
import threading
import os
import re
import queue
import shutil
import zipfile

from bs4 import BeautifulSoup
import requests

from global_variable import HAS_QT, SENDER, HEADERS

DOWNLOAD_QUEUE = queue.Queue()


def download_picture():
    """
    download pictures from DOWNLOAD_QUEUE
    """
    while not DOWNLOAD_QUEUE.empty():
        try:
            url, base_path = DOWNLOAD_QUEUE.get()
            path = os.path.join(os.path.join(base_path, 'Images'), url.split('/')[-1])
            if not os.path.exists(path):
                print('downloading:', url)
                if HAS_QT:
                    SENDER.sigChangeStatus.emit('downloading:' + url.split('/')[-1])
                r = requests.get(url, headers=HEADERS, stream=True)
                if r.status_code == requests.codes.ok:
                    tempChunk = r.content
                    with open(path, 'wb') as f:
                        f.write(tempChunk)
        except:
            DOWNLOAD_QUEUE.put((url, base_path))
        finally:
            DOWNLOAD_QUEUE.task_done()


def sortItemref(str):
    m = re.match('\d+', str)
    if m:
        return int(m.group(0))
    else:
        return -1


def file_to_string(file_path):
    """
    read the file as a tring

    Return:
        A string
    """
    with codecs.open(file_path, 'r','utf-8') as f:
        return ''.join(f.readlines())


def create_cover_html(epub):
    cover_name = epub.cover_url.split('/')[-1]
    cover_html = file_to_string('./templates/Cover.html')
    final_cover_html = cover_html.format(cover_name=cover_name, introduction=epub.introduction)
    return final_cover_html


def write_html(text_path, html, file_name):
    with codecs.open(os.path.join(text_path, file_name), 'w', 'utf-8') as f:
        f.write(BeautifulSoup(html).prettify())


def create_chapter_html(epub, base_path):
    chapter_html = file_to_string('./templates/Chapter.html')
    final_chapter_htmls = []
    for chapter in sorted(epub.chapter, key=lambda chapter: chapter[0]):
        content = []
        chapter_name = chapter[1]

        for line in chapter[2]:
            if line.startswith('/illustration/'):
                image_url = 'http://lknovel.lightnovel.cn' + line
                DOWNLOAD_QUEUE.put((image_url, base_path))
                image = '<div class="illust"><img alt="" src="../Images/' + image_url.split('/')[
                    -1] + '" /></div>\n<br/>'
                content.append(image)
            else:
                content.append('<p>' + line + '</p>')
        one_chapter_html = chapter_html.format(chapter_name=chapter_name, content='\n'.join(content))
        final_chapter_htmls.append(one_chapter_html)
    return final_chapter_htmls


def create_title_html(epub):
    title_html = file_to_string('./templates/Title.html')
    final_title_html = title_html.format(book_name=epub.book_name, volume_name=epub.volume_name,
                                         volume_number=epub.volume_number, author=epub.author, illuster=epub.illuster)
    return final_title_html


def create_contents_html(epub):
    contents_html = file_to_string('./templates/Contents.html')
    contents = []
    for i in sorted(epub.chapter, key=lambda chapter: chapter[0]):
        contents.append('<li class="c-rules"><a href="../Text/' + str(i[0]) + '.html">' + i[1] + '</a></li>')
    final_contetns_html = contents_html.format(contents='\n'.join(contents))
    return final_contetns_html


def download_all_pictures():
    th = []
    for i in range(5):
        t = threading.Thread(target=download_picture)
        t.start()
        th.append(t)
    for i in th:
        i.join()


def create_content_opf_html(epub, base_path):
    content_opf_html = file_to_string('./templates/content.opf')
    cover_name = epub.cover_url.split('/')[-1]

    file_paths = []
    for dir_path, dir_names, file_names in os.walk(os.path.join(base_path, 'Text')):
        for file in file_names:
            if file != 'toc.ncx':
                file_paths.append('<item href="Text/' + file + '" id="' + file + '" media-type="application/xhtml+xml" />')
        break

    file_paths.append('<item href="Styles/style.css" id="style.css" media-type="text/css" />')

    for dir_path, dir_names, file_names in os.walk(os.path.join(base_path, 'Images')):
        for file in file_names:
            postfix = file.split('.')[-1]
            postfix= 'jpeg' if postfix =='jpg' else postfix
            file_paths.append(
                '<item href="Images/' + file + '" id="' + file + '" media-type="image/' + postfix + '" />')
        break

    chapter_orders = []

    for dir_path, dir_names, file_names in os.walk(os.path.join(base_path, 'Text')):
        for file in sorted(file_names, key=sortItemref):
            if file not in ('Cover.html', 'Title.html', 'Contents.html'):
                chapter_orders.append('<itemref idref="' + file + '" />')
    final_content_opf_html = content_opf_html.format(book_name=epub.book_name, uuid=epub.uuid,
                                                     cover_name=cover_name,
                                                     author=epub.author, file_paths='\n'.join(file_paths),
                                                     chapter_orders='\n'.join(chapter_orders))
    return final_content_opf_html


def create_toc_html(epub, base_path):
    toc_html = file_to_string('./templates/toc.ncx')
    nav = []
    playorder = 4
    for i in sorted(epub.chapter, key=lambda chapter: chapter[0]):
        nav.append(
            '<navPoint id="' + str(i[0]) + '" playOrder="' + str(playorder) + '">\n<navLabel>\n<text>' + i[
                1] + '</text>\n</navLabel>\n<content src="Text/' + str(i[0]) + '.html"/>\n</navPoint>')
        playorder += 1
    final_toc_html = toc_html.format(uuid=epub.uuid,book_name=epub.book_name, author=epub.author, nav='\n'.join(nav))
    return final_toc_html


def create_html(epub, base_path):
    """
    create the html file for epub
    """
    html_path = os.path.join(base_path, 'Text')

    cover_html = create_cover_html(epub)
    write_html(html_path, cover_html, 'Cover.html')

    chapter_htmls = create_chapter_html(epub, base_path)
    for i, chapter_html in enumerate(chapter_htmls):
        write_html(html_path, chapter_html, str(i) + '.html')

    title_html = create_title_html(epub)
    write_html(html_path, title_html, 'Title.html')

    contents_html = create_contents_html(epub)
    write_html(html_path, contents_html, 'Contents.html')

    download_all_pictures()

    content_opf_html = create_content_opf_html(epub, base_path)
    with codecs.open(os.path.join(base_path, 'content.opf'), 'w', 'utf-8') as f:
        f.write(content_opf_html)

    toc_html = create_toc_html(epub, base_path)
    with codecs.open(os.path.join(base_path, 'toc.ncx'), 'w', 'utf-8') as f:
        f.write(toc_html)


def create_folders(folder_name, base_path):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    base_path = os.path.abspath(folder_name)
    if not os.path.exists(os.path.join(base_path, 'Text')):
        os.mkdir(os.path.join(os.path.join(base_path, 'Text')))
    if not os.path.exists(os.path.join(base_path, 'Styles')):
        os.mkdir(os.path.join(os.path.join(base_path, 'Styles')))
    if not os.path.exists(os.path.join(base_path, 'Images')):
        os.mkdir(os.path.join(os.path.join(base_path, 'Images')))
    shutil.copy2('./templates/style.css', os.path.join(os.path.join(base_path, 'Styles')))


def move_or_download_cover(epub, base_path):
    if not epub.cover_path:
        DOWNLOAD_QUEUE.put((epub.cover_url, base_path))
    else:
        tempCover_path = os.path.join(os.path.join(base_path, 'Images'), epub.cover_path.split('/')[-1])
        shutil.copyfile(epub.cover_path, tempCover_path)


def zip_files(folder_name, base_path):
    with zipfile.ZipFile(folder_name + '.epub', 'w', zipfile.ZIP_DEFLATED) as zip:
        for dir_path, dir_names, file_names in os.walk(base_path):
            for file in file_names:
                f = os.path.join(dir_path, file)
                zip.write(f, 'OEBPS//' + f[len(base_path) + 1:])
        zip.write('./files/container.xml', 'META-INF//container.xml')
        zip.write('./files/mimetype', 'mimetype')


def move_epub_file(epub_file_path, folder_name):
    if os.path.exists(epub_file_path + '/' + folder_name + '.epub'):
        if HAS_QT:
            SENDER.sigWarningMessage.emit('文件名已存在', 'epub保存在lknovel文件夹')
            SENDER.sigButton.emit()
    else:
        shutil.move(folder_name + '.epub', epub_file_path)
        if HAS_QT:
            SENDER.sigInformationMessage.emit('已生成', folder_name + '.epub')
            SENDER.sigButton.emit()


def generate_epub(epub, epub_file_path):
    """
    generate epub file by the Epub instance

    Args:
        epub: A Epub instance
        epub_file_path: A string represent the path of the output EPUB file
    """
    folder_name = re.sub(r'[<>:"/\\|\?\*]', '_', epub.book_name)
    base_path = os.path.abspath(folder_name)
    create_folders(folder_name, base_path)

    move_or_download_cover(epub, base_path)

    create_html(epub, base_path)

    zip_files(folder_name, base_path)
    print('已生成：', epub.book_name + '.epub\n\n')

    # delete temp file
    shutil.rmtree(base_path)

    # move file
    if epub_file_path:
        move_epub_file(epub_file_path, folder_name)
