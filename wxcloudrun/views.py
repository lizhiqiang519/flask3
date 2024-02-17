from datetime import datetime
from pathlib import Path

from flask import render_template, request, jsonify
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import os
import logging
import requests
from openai import OpenAI

# 配置日志记录
logging.basicConfig(level=logging.INFO)

client = OpenAI(
    api_key="sk-MLYNp6HXoDRx7kFKiPRxCO8BLoejH9tfzcGq3OANtoY1r1bG",
    base_url="https://api.moonshot.cn/v1",
)

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

        #暗面AI
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 把它放进请求中
        messages = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user", "content": "充分阅读downloaded.pdf，先整理里面的重要的知识点，根据重要知识点提供20道选择题，并且给出对应的答案、解释、答案来源（具体到章节）。最后提供的是MySQL的执行脚本。MySQL数据库表是ask表，表字段分别是：question（问题）、"
                                        + "optio_a(选项A)、option_b(选项B)、option_c(选项C)、option_d(选项D)、answer（答案，单选A或B或C或D）、explain（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节）。"},
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages,
            temperature=0.3,
        )
        app.logger.info(completion.choices[0])
        app.logger.info(completion)

        # 返回成功消息和文件路径
        return jsonify({'message': 'File downloaded successfully', 'zongjie': completion.choices[0].message})

    #return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500