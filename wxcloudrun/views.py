from datetime import datetime
from flask import render_template, request, jsonify
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import os
import logging
import requests

# 配置日志记录
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    current_path = os.getcwd()
    app.logger.info('12323111')
    app.logger.info(current_path)


    # 从请求体获取下载链接
    url = "https://7064-pdf-8g1671jo5043b0ee-1306680641.tcb.qcloud.la/pdf/1707709258291.pdf?sign=085fac18606ee7a956561d760473410f&t=1708064004"
    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        # 使用requests下载文件
        response = requests.get(url)
        response.raise_for_status()  # 确保请求成功

        # 从URL或内容中提取文件名，或自定义文件名
        # 以下为简化示例，直接命名为'downloaded.pdf'
        filename = 'downloaded.pdf'

        # 获取当前运行的路径，保存文件
        current_path = os.getcwd()
        file_path = os.path.join(current_path, filename)

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(response.content)

        # 返回成功消息和文件路径
        return jsonify({'message': 'File downloaded successfully', 'path': file_path})

    #return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500