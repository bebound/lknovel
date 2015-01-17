#lknovel

Generate epub from http://lknovel.lightnovel.cn/

![iPhone截图](https://raw.github.com/bebound/lknovel/master/screenShot/total.png)

##Requirements

- [python3](http://www.python.org/getit/ "python3")
- [requests](http://docs.python-requests.org/en/latest/ "requests")
- [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/ "BeautifulSoup4")

##Quick start

###lk2epub

`python3 lk2epub.py -uhttp://lknovel.lightnovel.cn/main/book/2664.html,http://lknovel.lightnovel.cn/main/book/2666.html`

Separate urls with `,`

add `-s` parameter to use single thread

![lk2epub截图](https://raw.github.com/bebound/lknovel/master/screenShot/1.PNG)

###GUIVersion

1. Url: Input urls, separate with '\n' ：

    `http://lknovel.lightnovel.cn/main/book/2664.html`

    `http://lknovel.lightnovel.cn/main/vollist/726.html`

2. Cover: You can use your own cover for each epub file.

    This script can batch download covers from bookwalker:[bookwalker.py](https://github.com/bebound/scripts)



3. Sava path: Default is desktop

![GUIVersion截图](https://raw.github.com/bebound/lknovel/master/screenShot/3.png)


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/bebound/lknovel/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

