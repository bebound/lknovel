#lknovel

Generate epub from http://lknovel.lightnovel.cn/

![iPhone截图](https://raw.github.com/bebound/lknovel/master/screenShot/total.png)

##Requirements

- [Python3](http://www.python.org/getit/)
- [requests](http://docs.python-requests.org/en/latest/)
- [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/)
- [docopt](https://github.com/docopt/docopt)

##Quick start

###lknovel
`pip install -r requirements.txt`

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
    

![lknovel截图](https://raw.github.com/bebound/lknovel/master/screenShot/1.PNG)

###GUIVersion

1. Url: Input urls, separate with '\n' ：

    `http://lknovel.lightnovel.cn/main/book/1578.html`

    `http://lknovel.lightnovel.cn/main/vollist/492.html`

2. Cover: You can use your own cover for each epub file.

    This script can batch download covers from bookwalker:[bookwalker.py](https://github.com/bebound/scripts)



3. Sava path: Default is desktop

![GUIVersion截图](https://raw.github.com/bebound/lknovel/master/screenShot/3.png)


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/bebound/lknovel/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

