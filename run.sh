#!/bin/bash

# 设置参数
META_FILE="./arxiv-metadata-oai-snapshot.json"
RETRY_TIMES=5
LOG_INTERVAL=10
MAX_FILES=10000
OUT_FOLDER="./download"

# 运行Python脚本
python3 single-arxivSpider.py --meta_file $META_FILE --retry_times $RETRY_TIMES \
                    --log_interval $LOG_INTERVAL --max_files $MAX_FILES --out_folder $OUT_FOLDER
