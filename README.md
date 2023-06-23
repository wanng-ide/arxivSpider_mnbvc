# arxivSpider_mnbvc

Arxiv Paper Downloader

这是一个用于从Arxiv下载论文的Python脚本。它使用多线程来并行下载论文，并且可以处理网络错误和连接中断。

## 特性

- 使用多线程并行下载论文
- 可以处理网络错误和连接中断
- 使用随机用户代理来防止被Arxiv封锁
- 使用进度条显示下载进度
- 可以选择从不同的URL下载论文

## 依赖

该脚本依赖以下Python库：

- os
- time
- loguru
- traceback
- requests
- random
- jsonlines
- tqdm
- concurrent.futures
- datetime
- argparse
- itertools
- fake_useragent

## 使用

首先，你需要安装所有的依赖。你可以使用以下命令来安装：

```bash
pip install os time loguru traceback requests random jsonlines tqdm concurrent.futures datetime argparse itertools fake_useragent
```

!!!注意!!!

你需要访问[Kaggle](https://www.kaggle.com/datasets/Cornell-University/arxiv)中下载json文件用以替换 arxiv-metadata-oai-snapshot.json。

因为我们提供的json文件是一个subset，只包含了200条。

然后，你可以运行`python main.py`来启动脚本。你可以使用命令行参数来配置脚本的行为。以下是可用的命令行参数：

- `--meta_file`: 存储arxiv论文元信息的文件地址，默认为`./arxiv-metadata-oai-snapshot.json`
- `--retry_times`: 对同一个url最多重试次数，默认为3
- `--log_interval`: 间隔多少篇文章打印一次信息，默认为10
- `--max_workers`: 线程数量，默认为5
- `--max_files`: 调试用，最大论文爬取数量，设置为0时，则全部爬取，默认为100
- `--out_folder`: 下载的文件夹位置，默认为`./download`

例如，如果你想使用10个线程来下载论文，你可以运行`python main.py --max_workers 10`。

你也可以在bash脚本中进行设置，并且直接启动bash脚本


```bash
bash run.sh
```

## 注意

该脚本仅供学习和研究使用，不得用于任何商业用途。请遵守Arxiv的使用条款，并尊重作者的版权。
