import os
import time
import logging
import traceback

import requests
import jsonlines
import threading

def crawl(url, headers=None):
    # 发送请求，如果失败，重复最多3次
    resp = requests.get(url, timeout=30)
    for i in range(retry_times):
        if resp.status_code == 200: break
        resp = requests.get(url, timeout=30)
    return resp

def download_files(j, out_folder=None):
    global done_set
    pid = j['id']
    if pid in done_set:
        return

    if out_folder is None:
        out_folder = "download"

    source_url = 'https://arxiv.org/e-print/' + pid
    pdf_url = 'https://arxiv.org/pdf/' + pid
    page_url = 'https://arxiv.org/abs/' + pid

    # 生成输出目录
    pdf_out_folder = os.path.join(out_folder, pid.replace('/', '_'),'pdf')          # 带有replace的部分是因为有的pid里存在 '/' 符号
    source_out_folder = os.path.join(out_folder, pid.replace('/','_'), 'source')  
    pdf_out_path = os.path.join(pdf_out_folder, pid.replace('/','_')+'.pdf')
    # ↓↓↓↓↓↓↓↓↓↓↓↓↓ ABOUT SOURCE FILE ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓:
    source_out_path = os.path.join(source_out_folder, pid.replace('/','_'))
    #   Delivered as a gzipped tar (.tar.gz) file if there are multiple files, 
    #   otherwise as a PDF file, or a gzipped TeX, DVI, PostScript or HTML (
    #   .gz, .dvi.gz, .ps.gz or .html.gz) file depending on submission format.

    # 下载pdf文件
    pdf_resp = crawl(pdf_url)
    pdf_status = pdf_resp.status_code

    # 下载source文件
    source_resp = crawl(source_url)
    source_status = source_resp.status_code

    # 保存文件
    if pdf_status == 200:
        os.makedirs(pdf_out_folder, exist_ok=True)
        with open(pdf_out_path, 'wb')as wb: wb.write(pdf_resp.content)
    else: pdf_out_path = ""
    if source_status == 200:
        os.makedirs(source_out_folder, exist_ok=True)
        with open(source_out_path, 'wb')as wb: wb.write(source_resp.content)
    else: source_out_path = ""

    if pdf_out_path == '' or source_out_path == '':
        logging.warning(f'{pid} {pdf_status} {source_status}')

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

def worker(obj):
    # global t_counter
    try:
        download_files(obj)
    except ConnectionResetError:
        print(obj['id'], 'err1--------------------------------------')
        print('connection reset error')
        logging.error(f"connection reset error: {obj['id']}")
    except requests.exceptions.ProxyError:
        print(obj['id'], 'err2--------------------------------------')
        print('requests proxy error')
        logging.error(f"requests proxy error: {obj['id']}")
    except Exception as e:
        # TODO: 异常处理
        print(obj['id'], 'err3--------------------------------------')
        logging.error(f"other exception: {obj['id']}\n\t{e}\n\t{traceback.format_exc()}")
    # finally:
    #     t_counter -= 1

def main():
    # global t_counter
    # t_counter = 0
    all_counter = 0

    if not os.path.exists(meta_file):
        print('没有找到arxiv论文元信息文件')
        return

    read_iter = iter(jsonlines.open(meta_file))
    
    for obj in read_iter:
        if obj['id'] in done_set:
            print(obj['id'], 'pass')
            continue
        worker(obj)
        all_counter += 1 
        if all_counter % log_interval == 0:
            print(time.strftime('%Y-%m-%d %H:%M:%S'), '已获取', all_counter, '篇论文。')
            logging.info(f"已获取{all_counter}篇论文。")

    # while True:
    #     if t_counter < max_processes:
    #         try:
    #             obj = next(read_iter)
    #             if obj['id'] in done_set:
    #                 print(obj['id'], 'pass')
    #                 continue
    #         except StopIteration:
    #             print('StopIteration')
    #             logging.info(f"所有元信息全部遍历完成。")
    #             break
    #     
    #         th = threading.Thread(target=worker, args=(obj,))
    #         th.start()
    #         t_counter += 1
    #         all_counter += 1
    #         # if all_counter >= 100:          #########
    #         #     print('all_counter >= 100') #######  测试用
    #         #     break                       #########
    #         if all_counter % log_interval == 0:
    #             print(time.strftime('%Y-%m-%d %H:%M:%S'), '已获取', all_counter, '篇论文。')
    #             logging.info(f"已获取{all_counter}篇论文。")
    #     

if __name__ == '__main__':
    log_file = 'spider_log.jsonl'                    # 记录爬取信息的文件路径
    error_log_file = './error_log.log'               # 记录爬取过程异常信息的文件路径
    max_processes = 5                                # 最大线程数
    meta_file = './arxiv-metadata-oai-snapshot.json' # 存储arxiv论文元信息的文件地址
    retry_times = 3                                  # 对同一个url最多重试次数
    log_interval = 10                                # 间隔多少篇文章打印一次信息

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(filename)s %(levelname)s\n%(message)s',
        datefmt='%a %d %b %Y %H:%M:%S',
        filename=error_log_file,
    )

    done_set = set()
    # 检查已经爬取过的文件，避免重复爬取
    if os.path.exists(log_file):
        with jsonlines.open(log_file)as reader:
            for obj in reader:
                done_set.add(obj['id'])
    
    main()
