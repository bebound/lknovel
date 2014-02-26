import re
import os
import codecs
import threading
import shutil
import queue
import uuid
import zipfile
import requests
import sys
from bs4 import BeautifulSoup
from PyQt4 import QtCore

debug = 1
downloadQueue = queue.Queue()


class SenderObject(QtCore.QObject):
    sigChangeStatus = QtCore.pyqtSignal(str)
    sigWarningMessage = QtCore.pyqtSignal(str, str)
    sigInformationMessage = QtCore.pyqtSignal(str, str)
    sigButton=QtCore.pyqtSignal()


sender = SenderObject()


#从volist中提取每一卷的网址
def parseList(url, epubFilePath='', coverPath=''):
    r = requests.get(url)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text)
    tempVolumeLink = soup.select('body div.content div.container dl dd.row div.inline h2.ft-24 strong a')
    findVolumeLink = re.compile(r'<a href="(.*)">')
    for i in tempVolumeLink:
        volumeLink = findVolumeLink.search(str(i)).group(1)
        parseVolume(volumeLink, epubFilePath, coverPath)


#提取每卷信息
def parseVolume(url, epubFilePath='', coverPath=''):
    try:
        print('getting:', url)
        sender.sigChangeStatus.emit('getting:' + url)
        r = requests.get(url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text)
        tempvolumeName = str(soup.select(
            'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span10 h1.ft-24')).split(
            '\n')
        tempChapterLink = soup.select(
            'body div.content div.container div.row-fluid div.span9 div.well div.row-fluid ul.lk-chapter-list li')
        findChapterLink = re.compile(r'<a href="(.*)">')
        volumeName = tempvolumeName[2].strip()
        volumeNumber = tempvolumeName[3].strip()
        print('volumeName:', volumeName, '\nvolumeNumber:', volumeNumber)
        sender.sigChangeStatus.emit('volumeName:' + volumeName + '\nvolumeNumber:' + volumeNumber)
        chapterLink = []
        for i in tempChapterLink:
            chapterLink.append(findChapterLink.search(str(i)).group(1))
        tempAuthorName = soup.select('table.lk-book-detail td')
        findAuthorName = re.compile(r'target="_blank">(.*)</a></td>')
        findIllusterName = re.compile(r'<td> (.*)</td>')
        authorName = findAuthorName.search(str(tempAuthorName[3])).group(1)
        illusterName = findIllusterName.search(str(tempAuthorName[5])).group(1)
        print('authorName:', authorName, '\nillusterName:', illusterName)
        sender.sigChangeStatus.emit('authorName:' + authorName)
        sender.sigChangeStatus.emit('illusterName:' + illusterName)
        tempIntroduction = soup.select(
            'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span10 p')
        findIntroduction = re.compile(r'<p style="width:42em; text-indent: 2em;">(.*)</p>')
        introduction = findIntroduction.search(str(tempIntroduction).replace('\n', '')).group(1)
        #print('introduction:',introduction)
        tempCoverUrl = soup.select(
            'html body div.content div.container div.row-fluid div.span9 div.well div.row-fluid div.span2 div.lk-book-cover a')
        findCoverUrl = re.compile(r'<img src="(.*)"/>')
        coverUrl = findCoverUrl.search(str(tempCoverUrl)).group(1) if not coverPath else coverPath
        newEpub = Epub(volumeName, volumeNumber, authorName, illusterName, introduction, coverUrl)
        th = []
        for i, link in enumerate(chapterLink):
            t = threading.Thread(target=parseChapter, args=(link, newEpub, i))
            t.start()
            th.append(t)
        for t in th:
            t.join()

        print('网页获取完成\n开始生成epub')
        sender.sigChangeStatus.emit('网页获取完成,开始生成epub')
        createEpub(newEpub, epubFilePath, coverPath)

    except Exception as e:
        sender.sigWarningMessage.emit('错误', str(e))
        sender.sigButton.emit()
        raise e


class Epub():
    def __init__(self, volumeName, volumeNumber, authorName, illusterName, introduction, coverUrl):
        self.volumeName = volumeName
        self.volumeNumber = volumeNumber
        self.authorName = authorName
        self.illusterName = illusterName
        self.introduction = introduction
        self.coverUrl = coverUrl
        self.bookName = self.volumeName + ' ' + self.volumeNumber
        self.chapter = []

    #tempChapter结构：章节序号、章节名、内容
    def addChapter(self, tempChapter):
        self.chapter.append(tempChapter)


def parseChapter(url, newEpub, number):
    try:
        r = requests.get(url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text)
        tempChapterName = soup.select('html body div.content div.container ul.breadcrumb li.active')
        findChapterName = re.compile(r'<li class="active">(.*)</li>')
        chapterName = findChapterName.search(str(tempChapterName)).group(1)
        newChapterName = chapterName[:chapterName.index('章') + 1] + ' ' + chapterName[chapterName.index('章') + 1:]
        print(newChapterName)
        sender.sigChangeStatus.emit(newChapterName)
        tempChapterContent = soup.select('div#J_view')
        findContent = re.compile(r'">(.*)<br/>')
        content = []
        for i in str(tempChapterContent).split('\n')[4:-1]:
            content.append(findContent.search(i).group(1))
        newEpub.addChapter((number, newChapterName, content))
    except Exception as e:
        sender.sigWarningMessage.emit('错误', str(e))
        sender.sigButton.emit()
        raise e


#建文件夹 下cover 生成单章节 目录 打包zip
def createEpub(newEpub, epubFilePath='', coverPath=''):
    coverUrl = 'http://lknovel.lightnovel.cn' + newEpub.coverUrl

    #创建需要的文件夹
    if not os.path.exists(newEpub.bookName):
        os.mkdir(newEpub.bookName)
    basePath = os.path.abspath(newEpub.bookName)
    if not os.path.exists(os.path.join(basePath, 'Text')):
        os.mkdir(os.path.join(os.path.join(basePath, 'Text')))
    if not os.path.exists(os.path.join(basePath, 'Styles')):
        os.mkdir(os.path.join(os.path.join(basePath, 'Styles')))
    if not os.path.exists(os.path.join(basePath, 'Images')):
        os.mkdir(os.path.join(os.path.join(basePath, 'Images')))
    shutil.copy2('./files/style.css', os.path.join(os.path.join(basePath, 'Styles')))
    if not coverPath:
        downloadQueue.put((coverUrl, basePath))
    else:
        tempCoverPath = os.path.join(os.path.join(basePath, 'Images'), coverUrl.split('/')[-1])
        print(coverPath, tempCoverPath)
        shutil.copyfile(coverPath, tempCoverPath)
    createText(newEpub, os.path.join(os.path.join(basePath, 'Text')), basePath)

    #打包epub文件
    with zipfile.ZipFile(newEpub.bookName + '.epub', 'w', zipfile.ZIP_DEFLATED) as zip:
        for dirPath, dirNames, fileNames in os.walk(basePath):
            for file in fileNames:
                f = os.path.join(dirPath, file)
                zip.write(f, 'OEBPS//' + f[len(basePath) + 1:])
        zip.write('./files/container.xml', 'META-INF//container.xml')
        zip.write('./files/mimetype', 'mimetype')
    print('已生成：', newEpub.bookName + '.epub\n\n')

    #删除临时文件
    shutil.rmtree(basePath)

    #是否移动文件
    if epubFilePath:
        if os.path.exists(epubFilePath + '/' + newEpub.bookName + '.epub'):
            sender.sigWarningMessage.emit('文件名已存在', 'epub保存在lknovel文件夹')
            sender.sigButton.emit()
        else:
            shutil.move(newEpub.bookName + '.epub', epubFilePath)
            sender.sigInformationMessage.emit('已生成', newEpub.bookName + '.epub')
            sender.sigButton.emit()


#下载图片专用
def download():
    while not downloadQueue.empty():
        url, basePath = downloadQueue.get()
        path = os.path.join(os.path.join(basePath, 'Images'), url.split('/')[-1])
        if not os.path.exists(path):
            print('downloading:', url)
            sender.sigChangeStatus.emit('downloading:' + url.split('/')[-1])
            r = requests.get(url, stream=True)
            if r.status_code == requests.codes.ok:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(256 * 1024):
                        f.write(chunk)
        downloadQueue.task_done()


def sortItemref(str):
    m = re.match('\d+', str)
    if m:
        return int(m.group(0))
    else:
        return -1


def createText(newEpub, textPath, basePath):
    #生成Cover.html
    htmlContent = []
    htmlHead1 = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<link href="../Styles/style.css" rel="stylesheet" type="text/css" />\n<title>封面</title>\n</head>\n<body>'
    htmlContent.append(htmlHead1)
    htmlContent.append(
        '<div class="cover"><img alt="" class="bb" src="../Images/' + newEpub.coverUrl.split('/')[-1] + '" /></div>')
    htmlContent.append('<h4>简介</h4>')
    htmlContent.append('<p>' + newEpub.introduction + '</p>')
    htmlContent.append('</body>\n</html>')
    tempContent = ''
    for line in htmlContent:
        tempContent += line
    with codecs.open(os.path.join(textPath, 'Cover.html'), 'w', 'utf-8') as f:
        f.write(BeautifulSoup(tempContent).prettify())


    #生成单章节html
    for i in sorted(newEpub.chapter, key=lambda chapter: chapter[0]):
        htmlContent = []
        print('正在生成', i[1])
        sender.sigChangeStatus.emit('正在生成' + i[1])
        htmlHead1 = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">\n<head>\n<link href="../Styles/style.css" rel="stylesheet" type="text/css" />\n<title>'
        htmlHead2 = '</title>\n</head>\n<body>\n<div>'
        htmlContent.append(htmlHead1 + i[1] + htmlHead2)
        htmlContent.append('<h4>' + i[1] + '</h4>')
        for line in i[2]:
            if line.startswith('<div class="lk-view-img">'):
                findImagesUrl = re.compile(r'data-cover="(.*)" src="')
                imageUrl = findImagesUrl.search(line).group(1)
                if not imageUrl.startswith('http://'):
                    imageUrl = 'http://lknovel.lightnovel.cn' + imageUrl
                downloadQueue.put((imageUrl, basePath))
                imageP = '<div class="illus"><img alt="" src="../Images/' + imageUrl.split('/')[
                    -1] + '" /></div>\n<br/>'
                htmlContent.append(imageP)
            else:
                htmlContent.append('<p>' + line + '</p>')
        htmlHead3 = '</div>\n</body>\n</html>'
        htmlContent.append(htmlHead3)
        tempContent = ''
        for line in htmlContent:
            tempContent += line
        with codecs.open(os.path.join(textPath, str(i[0]) + '.html'), 'w', 'utf-8') as f:
            f.write(BeautifulSoup(tempContent).prettify())

    #生成Title.html
    htmlContent = []
    htmlHead1 = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">\n<head>\n<link href="../Styles/style.css" rel="stylesheet" type="text/css" />\n<title>'
    htmlHead2 = '</title>\n</head>\n<body>\n<div class="title">'
    htmlContent.append(htmlHead1 + newEpub.volumeName + htmlHead2)
    htmlContent.append('<h1>' + newEpub.volumeName + '</h1>')
    htmlContent.append('<h2>' + newEpub.volumeNumber + '</h2>')
    htmlContent.append('<div>\n<br />\n</div>')
    htmlContent.append('<h3>作者：' + newEpub.authorName + '</h3>')
    htmlContent.append('<h3>插画：' + newEpub.illusterName + '</h3>')
    htmlContent.append('<h3>制作：<a target="_blank" href="http://www.github.com/bebound/lknovel">lknovel</a></h3>')
    htmlContent.append('</div>\n</body>\n</html>')
    tempContent = ''
    for line in htmlContent:
        tempContent += line
    with codecs.open(os.path.join(textPath, 'Title.html'), 'w', 'utf-8') as f:
        f.write(BeautifulSoup(tempContent).prettify())

    #生成Contents.html
    htmlContent = []
    htmlContent.append(
        '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<link href="../Styles/style.css" rel="stylesheet" type="text/css" />\n<title>目录</title>\n</head>')
    htmlContent.append('<body>\n<div>\n<p class="cont">目录</p>\n<hr class="line-index" />\n<ul class="contents">\n')
    for i in sorted(newEpub.chapter, key=lambda chapter: chapter[0]):
        htmlContent.append('<li class="c-rules"><a href="../Text/' + str(i[0]) + '.html">' + i[1] + '</a></li>')
    htmlContent.append('</ul>\n</div>\n</body>\n</html>')
    tempContent = ''
    for line in htmlContent:
        tempContent += line
    with codecs.open(os.path.join(textPath, 'Contents.html'), 'w', 'utf-8') as f:
        f.write(BeautifulSoup(tempContent).prettify())


    #下载相关图片
    th = []
    for i in range(5):
        t = threading.Thread(target=download)
        t.start()
        th.append(t)
    for i in th:
        i.join()

    #生成content.opf
    htmlContent = []
    htmlContent.append(
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">')
    htmlContent.append(
        '<dc:identifier id="BookId" opf:scheme="UUID">urn:uuid:' + str(uuid.uuid1()) + '</dc:identifier>')
    htmlContent.append('<dc:title>' + newEpub.bookName + '</dc:title>')
    htmlContent.append(
        '<dc:creator opf:file-as="' + newEpub.authorName + '" opf:role="aut">' + newEpub.authorName + '</dc:creator>')
    htmlContent.append('<dc:language>zh</dc:language>')
    htmlContent.append('<dc:source>http://www.lightnovel.cn</dc:source>')
    htmlContent.append('<dc:description>由https://github.com/bebound/lknovel/生成</dc:description>')
    htmlContent.append('<meta content="' + newEpub.coverUrl.split('/')[-1] + '" name="cover" />')
    htmlContent.append('</metadata>')
    htmlContent.append('<manifest>\n<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml" />')
    for dirPath, dirNames, fileNames in os.walk(os.path.join(basePath, 'Text')):
        for file in fileNames:
            htmlContent.append('<item href="Text/' + file + '" id="' + file + '" media-type="application/xhtml+xml" />')
    htmlContent.append('<item href="Styles/style.css" id="style.css" media-type="text/css" />')
    for dirPath, dirNames, fileNames in os.walk(os.path.join(basePath, 'Images')):
        for file in fileNames:
            if file.split('.')[-1] == 'jpg':
                htmlContent.append('<item href="Images/' + file + '" id="' + file + '" media-type="image/jpeg" />')
            else:
                htmlContent.append('<item href="Images/' + file + '" id="' + file + '" media-type="image/png" />')
    htmlContent.append('</manifest>')
    htmlContent.append('<spine toc="ncx">')
    htmlContent.append(
        '<itemref idref="Cover.html" />\n<itemref idref="Title.html" />\n<itemref idref="Contents.html" />\n')
    for dirPath, dirNames, fileNames in os.walk(os.path.join(basePath, 'Text')):
        for file in sorted(fileNames, key=sortItemref):
            if file not in ('Cover.html', 'Title.html', 'Contents.html'):
                htmlContent.append('<itemref idref="' + file + '" />')
    htmlContent.append('</spine>')
    htmlContent.append(
        '<guide>\n<reference href="Text/Contents.html" title="Table Of Contents" type="toc" />')
    htmlContent.append(
        '<reference href="Text/Cover.html" title="Cover" type="cover"/>\n</guide>')
    htmlContent.append('</package>')
    with codecs.open(os.path.join(basePath, 'content.opf'), 'w', 'utf-8') as f:
        for line in htmlContent:
            f.write(line + '\n')

    #生成toc.ncx
    htmlContent = []
    htmlContent.append(
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"\n"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n<head>\n<meta content="0" name="dtb:depth"/>\n<meta content="0" name="dtb:totalPageCount"/>\n<meta content="0" name="dtb:maxPageNumber"/>\n</head>\n<docTitle>\n<text>' + newEpub.bookName + '</text>\n</docTitle>')
    htmlContent.append('<docAuthor>\n<text>' + newEpub.authorName + '</text>\n</docAuthor>\n<navMap>')
    htmlContent.append(
        '<navPoint id="Contents" playOrder="1">\n<navLabel>\n<text>封面</text>\n</navLabel>\n<content src="Text/Cover.html"/>\n</navPoint>')
    htmlContent.append(
        '<navPoint id="Contents" playOrder="2">\n<navLabel>\n<text>标题</text>\n</navLabel>\n<content src="Text/Title.html"/>\n</navPoint>')
    htmlContent.append(
        '<navPoint id="Contents" playOrder="3">\n<navLabel>\n<text>目录</text>\n</navLabel>\n<content src="Text/Contents.html"/>\n</navPoint>')
    playorder = 4
    for i in sorted(newEpub.chapter, key=lambda chapter: chapter[0]):
        htmlContent.append(
            '<navPoint id="' + str(i[0]) + '" playOrder="' + str(playorder) + '">\n<navLabel>\n<text>' + i[
                1] + '</text>\n</navLabel>\n<content src="Text/' + str(i[0]) + '.html"/>\n</navPoint>')
        playorder += 1
    htmlContent.append('</navMap>\n</ncx>')

    with codecs.open(os.path.join(basePath, 'toc.ncx'), 'w', 'utf-8') as f:
        for line in htmlContent:
            f.write(line + '\n')


def main():
    if len(sys.argv) < 2:
        url = input("输入网址:")
    else:
        url = sys.argv[1]
    ok = 0
    check = re.compile(r'http://lknovel.lightnovel.cn/main/vollist/(\d+).html')
    check2 = re.compile(r'http://lknovel.lightnovel.cn/main/book/(\d+).html')
    if check.search(url) or check2.search(url):
        ok = 1
    if ok:
        if url.split('/')[-2] == 'book':
            parseVolume(url)
        else:
            parseList(url)
    else:
        print(
            '请输入正确的网址，例如：\nhttp://lknovel.lightnovel.cn/main/vollist/726.html\nhttp://lknovel.lightnovel.cn/main/book/2664.html')


if __name__ == '__main__':
    main()
