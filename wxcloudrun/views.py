import json
from datetime import datetime
from pathlib import Path

from flask import render_template, request, jsonify
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid, insert_records, \
    insert_questions
from wxcloudrun.model import Counters
from wxcloudrun.modelQuestions import Questions
from wxcloudrun.modelRecord import Records
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import os
import logging
import requests
from openai import OpenAI
import re

from urllib.parse import urlparse, unquote

# 配置日志记录
logging.basicConfig(level=logging.INFO)

client = OpenAI(
    # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
    api_key="sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV",
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

        # 暗面AI
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小

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
            {"role": "user",
             "content": "充分阅读downloaded.pdf，先整理里面的重要的知识点，根据重要知识点提供20道选择题，并且给出对应的答案、解释、答案来源（具体到章节）。最后提供的是MySQL的执行脚本。MySQL数据库表是ask表，表字段分别是：question（问题）、"
                        + "optio_a(选项A)、option_b(选项B)、option_c(选项C)、option_d(选项D)、answer（答案，单选A或B或C或D）、explain（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节）。并且提供给表添加选择题的记录的sql脚本"},
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

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf', methods=['POST'])
def upload_pdf():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')

    # 打印信息到控制台
    print(f"Download URL: {downloadURL}")
    print(f"PDF Name: {pdfName}")

    app.logger.info("传进来的下载链接= %s,PDF名称= %s", downloadURL, pdfName)

    # 返回响应
    # return jsonify({
    #     "message": "Data received",
    #     "downloadURL": downloadURL,
    #     "pdfName": pdfName
    # })

    # 当前目录
    current_path = os.getcwd()
    app.logger.info('当前所在目录:')
    app.logger.info(current_path)

    # 从请求体获取下载链接
    if not downloadURL:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        # 使用requests下载文件
        response = requests.get(downloadURL)
        response.raise_for_status()  # 确保请求成功

        # 解析 URL 并提取文件名
        parsed_url = urlparse(downloadURL)
        pdf_filename_with_extension = os.path.basename(parsed_url.path)

        # 对 URL 进行解码，以获取正确的文件名（包括中文等字符）
        decoded_filename = unquote(pdf_filename_with_extension)

        # 去除文件扩展名，假设扩展名为 .pdf
        filename = decoded_filename.rsplit('.', 1)[0]

        # 获取当前运行的路径，保存文件
        current_path = os.getcwd()
        file_path = os.path.join(current_path, filename)

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(response.content)

        # 暗面AI
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s,文件内容= %s", file_object.id, file_content)

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的前三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A)、option_b(选项B)、option_c(选项C)、option_d(选项D)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },

            {"role": "user",
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的中间三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A)、option_b(选项B)、option_c(选项C)、option_d(选项D)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的后三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A)、option_b(选项B)、option_c(选项C)、option_d(选项D)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages1,
            temperature=0.3,
        )
        #------------------------1------------------------------
        #第一次返回的答案
        text1 = completion1.choices[0].message.content
        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #--------------------------2--------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        #第一次返回的答案
        text2 = completion2.choices[0].message.content
        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages3,
            temperature=0.3,
        )
        # 第一次返回的答案
        text3 = completion3.choices[0].message.content
        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        my_list = my_list1 + my_list2+ my_list3;
        app.logger.info('my_list:')
        app.logger.info(my_list)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        for question_dict in my_list:
            # 创建 Records 实例，确保字段匹配
            question_record = Questions(
                question=question_dict.get('question', ''),
                option_a=question_dict.get('option_a', ''),
                option_b=question_dict.get('option_b', ''),
                option_c=question_dict.get('option_c', ''),
                option_d=question_dict.get('option_d', ''),
                answer=question_dict.get('answer', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500
