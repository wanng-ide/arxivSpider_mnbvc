import os
import time
from loguru import logger
import traceback
import requests
import random
import jsonlines
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import argparse
import itertools
from fake_useragent import UserAgent
from concurrent.futures import as_completed

# 创建一个用户代理池
ua = UserAgent()

# 创建一个Session对象
session = requests.Session()

# 创建一个URL列表
url_list = ['http://cn.arxiv.org/', 'http://export.arxiv.org/']

def crawl(url, headers=None):
    headers = {'User-Agent': ua.random}
    try:
        # 使用Session对象发送请求
        resp = session.get(url, timeout=30)
        for i in range(retry_times):
            if resp.status_code == 200: break
            resp = session.get(url, headers=headers, timeout=30)
            time.sleep(3) # 如果爬太快被反爬，就把这一行的注释去掉
        return resp
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return None

def download_files(j, out_folder):
    global done_set
    pid = j['id']
    if pid in done_set:
        return
    if out_folder is None:
        out_folder = "download"
    # source_url = 'https://arxiv.org/e-print/' + pid
    # pdf_url = 'https://arxiv.org/pdf/' + pid
    # page_url = 'https://arxiv.org/abs/' + pid
    
    # 随机选择一个URL
    base_url = random.choice(url_list)
    source_url = base_url + 'e-print/' + pid
    pdf_url = base_url + 'pdf/' + pid
    page_url = base_url + 'abs/' + pid
    
    # 生成输出目录
    pdf_out_folder = os.path.join(out_folder, pid.replace('/', '_'),'pdf') # 带有replace的部分是因为有的pid里存在 '/' 符号
    source_out_folder = os.path.join(out_folder, pid.replace('/','_'), 'source') 
    pdf_out_path = os.path.join(pdf_out_folder, pid.replace('/','_')+'.pdf')
    # ↓↓↓↓↓↓↓↓↓↓↓↓↓ ABOUT SOURCE FILE ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓:
    source_out_path = os.path.join(source_out_folder, pid.replace('/','_'))
    # Delivered as a gzipped tar (.tar.gz) file if there are multiple files, 
    # otherwise as a PDF file, or a gzipped TeX, DVI, PostScript or HTML (
    # .gz, .dvi.gz, .ps.gz or .html.gz) file depending on submission format.
    # 检查文件是否已经下载
    if os.path.exists(pdf_out_path) and os.path.exists(source_out_path):
        logger.info(f'Files {pid} already downloaded, skip.')
        return
    
    # 下载pdf文件
    logger.info(f'Downloading PDF file {pid}')
    pdf_resp = crawl(pdf_url)
    pdf_status = pdf_resp.status_code if pdf_resp else None
    # pdf_status = pdf_resp.status_code
    # 下载source文件
    logger.info(f'Downloading source file {pid}')
    source_resp = crawl(source_url)
    # source_status = source_resp.status_code
    source_status = source_resp.status_code if source_resp else None
    
    # 保存文件
    if pdf_status == 200:
        os.makedirs(pdf_out_folder, exist_ok=True)
        with open(pdf_out_path, 'wb')as wb: wb.write(pdf_resp.content)
    else: 
        pdf_out_path = ""
        logger.error(f"Failed to download PDF file {pid}")
    if source_status == 200:
        os.makedirs(source_out_folder, exist_ok=True)
        with open(source_out_path, 'wb')as wb: wb.write(source_resp.content)
    else: 
        source_out_path = ""
        logger.error(f"Failed to download source file {pid}")

    if pdf_out_path == '' or source_out_path == '':
        logger.warning(f'{pid} {pdf_status} {source_status}')

    # 保存下载记录
    save_info = dict()
    save_info['id'] = pid
    save_info['arxiv_url'] = page_url
    save_info['title'] = j['title']
    save_info['autorhs'] = j.get('authors_parsed', False) or j['authors']
    save_info['paper_time'] = j['update_date']
    save_info['download_time'] = time.strftime('%Y-%m-%d')
    save_info['pdf_path'] = pdf_out_path
    save_info['source_path'] = source_out_path
    save_info['pdf_status'] = pdf_status
    save_info['source_status'] = source_status
    with jsonlines.open(log_file, mode='a') as writer:
        writer.write(save_info)
    done_set.add(pid)

def worker(obj, out_folder):
    try:
        download_files(obj, out_folder)
    except ConnectionResetError:
        logger.error(f"Connection reset error: {obj['id']}")
    except requests.exceptions.ProxyError:
        logger.error(f"Requests proxy error: {obj['id']}")
    except Exception as e:
        logger.error(f"Other exception: {obj['id']}\n\t{e}\n\t{traceback.format_exc()}")
    # finally:
    #     t_counter -= 1

def main():
    all_counter = 0
    if not os.path.exists(meta_file):
        logger.error('没有找到arxiv论文元信息文件')
        return
    read_iter = iter(jsonlines.open(meta_file))
    
    if max_files > 0:
        # 只读取前100个元数据，调试用
        read_iter = itertools.islice(read_iter, max_files)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:  
        # 创建一个线程池，最大线程数为max_workers
        futures = set()
        for obj in tqdm(read_iter, ncols=100, desc='提交进度'):
            if obj['id'] not in done_set:
                future = executor.submit(worker, obj, out_folder)
                futures.add(future)
        for future in tqdm(as_completed(futures), total=len(futures), ncols=100, desc='完成进度'):
            all_counter += 1 
            if all_counter % log_interval == 0:
                logger.info(f'已获取{all_counter}篇论文。')
        # for obj in tqdm(read_iter, ncols=100):
        #     if obj['id'] in done_set:
        #         logger.info(f"{obj['id']} pass")
        #         continue
        #     executor.submit(worker, obj, out_folder)  # 提交任务到线程池
        #     all_counter += 1 
        #     if all_counter % log_interval == 0:
        #         logger.info(f'已获取{all_counter}篇论文。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--meta_file', default='./arxiv-metadata-oai-snapshot.json', help='存储arxiv论文元信息的文件地址')
    parser.add_argument('--retry_times', type=int, default=3, help='对同一个url最多重试次数')
    parser.add_argument('--log_interval', type=int, default=10, help='间隔多少篇文章打印一次信息')
    parser.add_argument('--max_workers', type=int, default=5, help='线程数量')
    parser.add_argument('--max_files', type=int, default=100, help='调试用，最大论文爬取数量，设置为0时，则全部爬取。')
    parser.add_argument('--out_folder', default='./download', help='下载的文件夹位置')
    args = parser.parse_args()
    
    log_dir = './log'  # log文件夹的路径
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    log_file = f'./{log_dir}/spider_log.jsonl'  
    # log_file = f'./{log_dir}/spider_log_{timestamp}.jsonl'  
    error_log_file = f'./{log_dir}/error_log_{timestamp}.log'  
    
    meta_file = args.meta_file  # 存储arxiv论文元信息的文件地址
    retry_times = args.retry_times  # 对同一个url最多重试次数
    log_interval = args.log_interval  # 间隔多少篇文章打印一次信息
    max_workers = args.max_workers  # 线程数量
    max_files = args.max_files  # 调试用，最大论文爬取数量，设置为0时，则全部爬取。
    out_folder = args.out_folder  # 下载的文件夹位置
    
    logger.add(error_log_file, rotation="500 MB")  # 使用loguru记录日志
    
    done_set = set()
    # 检查已经爬取过的文件，避免重复爬取
    if os.path.exists(log_file):
        with jsonlines.open(log_file)as reader:
            for obj in reader:
                done_set.add(obj['id'])
    
    main()
