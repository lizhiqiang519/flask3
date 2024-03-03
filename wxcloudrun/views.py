import json
from datetime import datetime
from math import floor
from pathlib import Path

from flask import render_template, request, jsonify
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid, insert_records, \
    insert_questions, insert_file, query_filebycreateby, query_questionsbyapiid, query_filebyfileid, delete_file22, \
    query_wendatisbyapiid, query_fileByApiFileid
from wxcloudrun.model import Counters
from wxcloudrun.modelFile import File
from wxcloudrun.modelQuestions import Questions
from wxcloudrun.modelRecord import Records
from wxcloudrun.modelWendatis import Wendati
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import os
import logging
import requests
from openai import OpenAI
import re
from werkzeug.utils import secure_filename

from urllib.parse import urlparse, unquote

# 配置日志记录
logging.basicConfig(level=logging.INFO)

# 设置您的Moonshot AI API密钥
MOONSHOT_API_KEY = 'sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX'
MOONSHOT_API_URL = 'https://api.moonshot.cn/v1'

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

    client = OpenAI(
        # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
        api_key="sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV",
        base_url="https://api.moonshot.cn/v1",
    )

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
            model="moonshot-v1-32k",
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

        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            api_key="sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV",
            base_url="https://api.moonshot.cn/v1",
        )


        # 暗面AI
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)


        file = File()
        file.file_name = file_object.filename
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = file_object.bytes
        file.api_file_id = file_object.id
        insert_file(file)

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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的前三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的中间三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的后三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
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
                file_name= filename,
                api_file_id= file_object.id,
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


#基础会员使用
# @app.route('/api/pdfV1', methods=['POST'])
# def upload_pdf_v1():
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     # 打印信息到控制台
#     print(f"pdfV1 Download URL: {downloadURL}")
#     print(f"pdfV1 PDF Name: {pdfName}")
#     print(f"pdfV1 用户的openid: {openid}")
#
#     app.logger.info("pdfV1传进来的下载链接= %s,PDF名称= %s", downloadURL, pdfName)
#
#
#     # 当前目录
#     current_path = os.getcwd()
#     app.logger.info('pdfV1当前所在目录:')
#     app.logger.info(current_path)
#
#     # 从请求体获取下载链接
#     if not downloadURL:
#         return jsonify({'error': 'Missing URL'}), 400
#
#     try:
#         # 使用requests下载文件
#         response = requests.get(downloadURL)
#         response.raise_for_status()  # 确保请求成功
#
#         # 解析 URL 并提取文件名
#         parsed_url = urlparse(downloadURL)
#         pdf_filename_with_extension = os.path.basename(parsed_url.path)
#
#         # 对 URL 进行解码，以获取正确的文件名（包括中文等字符）
#         decoded_filename = unquote(pdf_filename_with_extension)
#
#         # 去除文件扩展名，假设扩展名为 .pdf
#         filename = decoded_filename.rsplit('.', 1)[0]
#
#         # 获取当前运行的路径，保存文件
#         current_path = os.getcwd()
#         file_path = os.path.join(current_path, filename)
#
#         # 写入文件
#         with open(file_path, 'wb') as f:
#             f.write(response.content)
#
#         # 暗面AI
#
#         client = OpenAI(
#             # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
#             # 3335
#             api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
#             #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
#             #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
#             base_url="https://api.moonshot.cn/v1",
#         )
#         # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
#         file_object = client.files.create(file=Path(file_path), purpose="file-extract")
#         app.logger.info("pdfV1文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("pdfV1文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
#         app.logger.info("文件ID= %s", file_object.id)
#         app.logger.info("pdfV1文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)
#
#         # 把它放进请求中
#         messages1 = [
#             {
#                 "role": "system",
#                 "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
#             },
#             {
#                 "role": "system",
#                 "content": file_content,
#             },
#             {"role": "user",
#              "content": "你是一个老师，请针对" + filename + ".pdf" + "的前面一半部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
#         ]
#
#         messages2 = [
#             {
#                 "role": "system",
#                 "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
#             },
#             {
#                 "role": "system",
#                 "content": file_content,
#             },
#
#             {"role": "user",
#              "content": "你是一个老师，请针对" + filename + ".pdf" + "的后面一半部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
#         ]
#
#         messages3 = [
#             {
#                 "role": "system",
#                 "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
#             },
#             {
#                 "role": "system",
#                 "content": file_content,
#             },
#             {"role": "user",
#              "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
#         ]
#
#         # 然后调用 chat-completion, 获取 kimi 的回答
#         completion1 = client.chat.completions.create(
#             model="moonshot-v1-128k",
#             messages=messages1,
#             temperature=0.3,
#         )
#         #------------------------1------------------------------
#         #第一次返回的答案
#         text1 = completion1.choices[0].message.content
#
#         record1 = Records()
#         record1.remark = text1
#         record1.remark2 = "v1"
#         record1.created_at = datetime.now()
#         insert_records(record1)
#
#         # 使用正则表达式匹配 ```json 和 ``` 之间的内容
#         pattern = re.compile(r"```json(.*?)```", re.DOTALL)
#         matches = pattern.findall(text1)
#         # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
#         extracted_json1 = '\n\n'.join(matches)
#         #转成list
#         my_list1 = json.loads(extracted_json1)
#
#         #--------------------------2--------------------------------
#
#         #然后调用 chat-completion, 获取 kimi 的回答
#         completion2 = client.chat.completions.create(
#             model="moonshot-v1-128k",
#             messages=messages2,
#             temperature=0.3,
#         )
#         #第一次返回的答案
#         text2 = completion2.choices[0].message.content
#
#         record1 = Records()
#         record1.remark = text2
#         record1.remark2 = "v1"
#         record1.created_at = datetime.now()
#         insert_records(record1)
#
#         # 使用正则表达式匹配 ```json 和 ``` 之间的内容
#         pattern = re.compile(r"```json(.*?)```", re.DOTALL)
#         matches = pattern.findall(text2)
#         # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
#         extracted_json2 = '\n\n'.join(matches)
#         #转成list
#         my_list2 = json.loads(extracted_json2)
#
#         # --------------------------3-------------------------------
#
#         # 然后调用 chat-completion, 获取 kimi 的回答
#         completion3 = client.chat.completions.create(
#             model="moonshot-v1-128k",
#             messages=messages3,
#             temperature=0.3,
#         )
#
#         text3 = completion3.choices[0].message.content;
#         record3 = Records()
#         record3.remark = text3
#         record3.remark2 = "zongjie"
#         record3.created_at = datetime.now()
#         insert_records(record3)
#
#         # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
#         pattern = re.compile(r"```json(.*?)```", re.DOTALL)
#         matches = pattern.findall(text3)
#         # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
#         extracted_json3 = '\n\n'.join(matches)
#
#         # 使用json.loads()将字符串解析为字典
#         extracted_json3333 = json.loads(extracted_json3)
#
#         file = File()
#         file.file_name = pdfName
#         file.download_url = downloadURL
#         file.created_at = datetime.now()
#         file.open = 1
#         file.file_size = floor(file_object.bytes / 1024 )
#         file.api_file_id = file_object.id
#         file.version = "v1"
#         file.create_by = openid
#         file.zongfenjie = extracted_json3
#         file.yijuhua = extracted_json3333.get("zongjie", "")
#         insert_file(file)
#
#         #my_list = my_list1 + my_list2 + my_list3;
#         my_list = my_list1 + my_list2;
#         app.logger.info('v1_my_list:')
#         app.logger.info(my_list)
#
#         """
#         处理问题列表并插入到数据库
#         :param questions_list: 包含多个问题字典的列表
#         """
#         for question_dict in my_list:
#             # 创建 Records 实例，确保字段匹配
#             question_record = Questions(
#                 question=question_dict.get('question', ''),
#                 option_a=question_dict.get('option_a', ''),
#                 option_b=question_dict.get('option_b', ''),
#                 option_c=question_dict.get('option_c', ''),
#                 option_d=question_dict.get('option_d', ''),
#                 answer=question_dict.get('answer', ''),
#                 fenxi=question_dict.get('fenxi', ''),
#                 source=question_dict.get('source', ''),
#                 file_name= pdfName,
#                 api_file_id= file_object.id,
#                 created_at = datetime.now()
#             )
#             # 调用插入方法
#             app.logger.info("question_record888_v11111")
#             insert_questions(question_record)
#
#         # 返回成功消息和文件路径
#         return jsonify({'message': 'successfully'})
#
#     # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
#     except requests.RequestException as e:
#         return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500
#


@app.route('/api/pdfVip', methods=['POST'])
def upload_pdf_vip():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    print(f"Download URL: {downloadURL}")
    print(f"PDF Name: {pdfName}")
    print(f"用户的openid: {openid}")

    app.logger.info("vip传进来的下载链接= %s,PDF名称= %s", downloadURL, pdfName)

    # 返回响应
    # return jsonify({
    #     "message": "Data received",
    #     "downloadURL": downloadURL,
    #     "pdfName": pdfName
    # })

    # 当前目录
    current_path = os.getcwd()
    app.logger.info('vip当前所在目录:')
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

        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            base_url="https://api.moonshot.cn/v1",
        )


        # 暗面AI
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("vip文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("vip文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("vip文件ID= %s", file_object.id)


        file = File()
        file.file_name = file_object.filename
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = file_object.bytes
        file.api_file_id = file_object.id
        file.create_by = openid
        insert_file(file)


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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的前三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的中间三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的后三分之一部分的内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串格式，list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
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
            model="moonshot-v1-128k",
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
            model="moonshot-v1-128k",
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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_vip")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500



@app.route('/files/by_creator', methods=['POST'])
def get_files_by_creator():

    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON or empty payload'}), 400

    openid = data.get('openid')
    if not openid:
        return jsonify({'error': 'Missing openid'}), 400

    app.logger.info("查询PDF入参=%s", openid)

    files = query_filebycreateby(openid)
    files_data = [{
        'id': file.id,
        'file_name': file.file_name,
        'download_url': file.download_url,
        'file_size': file.file_size,
        'open': file.open,
        'created_at': file.created_at,
        'create_by': file.create_by,
        'zongfenjie': file.zongfenjie,
        'yijuhua': file.yijuhua,
        'api_file_id': file.api_file_id,
        'timus': file.timus,
        'version': file.version
    } for file in files]

    return jsonify(files_data), 200


#选择题查询
@app.route('/questions/by_fileid', methods=['POST'])
def get_questions_by_fileid():

    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON or empty payload'}), 400

    api_file_id = data.get('api_file_id')
    if not api_file_id:
        return jsonify({'error': 'Missing openid'}), 400

    app.logger.info("查询问题入参=%s", api_file_id)

    questions = query_questionsbyapiid(api_file_id)
    questions_data = [{
        'id': question.id,
        'question': question.question,
        'option_a': question.option_a,
        'option_b': question.option_b,
        'option_c': question.option_c,
        'option_d': question.option_d,
        'answer': question.answer,
        'fenxi': question.fenxi,
        'file_name': question.file_name,
        'created_at': question.created_at,
        'source': question.source,
        'api_file_id': question.api_file_id
    } for question in questions]

    return jsonify(questions_data), 200


@app.route('/api/calculate-token', methods=['POST'])
def api_pdf_v1():

    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    print(f"api_pdf_v1 Download URL: {downloadURL}")
    print(f"api_pdf_v1 PDF Name: {pdfName}")
    print(f"api_pdf_v1 用户的openid: {openid}")

    app.logger.info("api_pdf_v1传进来的下载链接= %s,PDF名称= %s", downloadURL, pdfName)

    # 当前目录
    current_path = os.getcwd()

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

        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("api_pdf_v1文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("api_pdf_v1文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 上传文件到Moonshot AI
        headers = {
            'Authorization': f'Bearer {MOONSHOT_API_KEY}',
            'Content-Type': 'multipart/form-data'
        }

        # 使用文件内容计算Token
        calculate_token_response = requests.post(
            f'{MOONSHOT_API_URL}/tokenizers/estimate-token-count',
            headers=headers,
            json={'model': 'moonshot-v1-128k', 'messages': [{'role': 'system', 'content': file_content}]}
        )

        app.logger.info("计算token结果 %s", calculate_token_response)
        app.logger.info(calculate_token_response)

        # 检查计算Token响应
        if calculate_token_response.status_code != 200:
            return jsonify({'error': 'Failed to calculate tokens'}), calculate_token_response.status_code

        # 解析计算Token响应
        token_data = calculate_token_response.json()
        total_tokens = token_data.get('data', {}).get('total_tokens')

        app.logger.info("total_tokens %s", total_tokens)
        app.logger.info("token_data %s", token_data)
        app.logger.info(token_data)
        app.logger.info("文件字数 %s", len(file_content))

        app.logger.info(total_tokens)

        # 返回计算结果
        return jsonify({'total_tokens': total_tokens,'file_words': len(file_content)}), 200

        # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to get total_tokens', 'details': str(e)}), 500

@app.route('/file/by_fileid', methods=['POST'])
def get_filedetail_by_fileid():

    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON or empty payload'}), 400

    fileid = data.get('fileid')
    if not fileid:
        return jsonify({'error': 'Missing openid'}), 400

    app.logger.info("查询问题入参=%s", fileid)
    file = query_filebyfileid(fileid)
    if file is None:
        return jsonify({'error': 'File not found'}), 404
    file_detail = {
        'id': file.id,
        'file_name': file.file_name,
        'download_url': file.download_url,
        'file_size': file.file_size,
        'open': file.open,
        'api_file_id': file.api_file_id,
        'created_at': file.created_at,
        'create_by': file.create_by,
        'version': file.version,
        'yijuhua': file.yijuhua,
        'timus': file.timus,
        'zongfenjie': file.zongfenjie

    }
    return jsonify(file_detail), 200


#基础会员使用
@app.route('/api/pdf/v1', methods=['POST'])
def upload_pdf_v1():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
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

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v1"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        text3 = completionZongJie.choices[0].message.content;
        record3 = Records()
        record3.remark = text3
        record3.remark2 = "zongjie"
        record3.created_at = datetime.now()
        insert_records(record3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_json3333 = json.loads(extracted_json3)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "v1"
        file.create_by = openid
        file.zongfenjie = extracted_json3
        file.yijuhua = extracted_json3333.get("zongjie", "")
        file.timus = process_input_string("v1")
        insert_file(file)

        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个专业老师，请针对" + filename + ".pdf" + "的全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda,
            temperature=0.3,
        )

        #插入记录
        textWenda = completionWenda.choices[0].message.content;
        recordWenda = Records()
        recordWenda.remark = textWenda
        recordWenda.remark2 = "wenda"
        recordWenda.created_at = datetime.now()
        insert_records(recordWenda)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda = '\n\n'.join(matches)

        #转成list
        my_listWenda= json.loads(extracted_jsonWenda)

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v11111")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        for question_dict in my_list1:
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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/v2', methods=['POST'])
def upload_pdf_v2():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

        #切割文本
        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
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

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v2"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        #第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v2"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        #----------------------------2-----------------------------------


        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        text3 = completion3.choices[0].message.content;
        record3 = Records()
        record3.remark = text3
        record3.remark2 = "zongjie"
        record3.created_at = datetime.now()
        insert_records(record3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_json3333 = json.loads(extracted_json3)


        #插入文件记录

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "v2"
        file.create_by = openid
        file.zongfenjie = extracted_json3
        file.yijuhua = extracted_json3333.get("zongjie", "")
        file.timus = process_input_string("v2")
        insert_file(file)

        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个专业老师，请针对" + filename + ".pdf" + "的全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda,
            temperature=0.3,
        )

        #插入记录
        textWenda = completionWenda.choices[0].message.content;
        recordWenda = Records()
        recordWenda.remark = textWenda
        recordWenda.remark2 = "wenda"
        recordWenda.created_at = datetime.now()
        insert_records(recordWenda)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda = '\n\n'.join(matches)

        #转成list
        my_listWenda= json.loads(extracted_jsonWenda)

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2;

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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/v3', methods=['POST'])
def upload_pdf_v3():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

        #切割文本
        # 计算每一部分的大致长度，使用整除来确保得到整数
        part_length = len(file_content) // 3
        # 使用字符串切片获取每一部分
        first_part = file_content[:part_length]
        second_part = file_content[part_length:2 * part_length]
        third_part = file_content[2 * part_length:]

        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content2) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content2[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content2[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
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

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v3"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        #第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v3"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        #----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages3,
            temperature=0.3,
        )
        #第3次返回的答案
        text3 = completion2.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "v3"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        #转成list
        my_list3 = json.loads(extracted_json3)


        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie= completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "v3"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v3")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)


        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        #插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        #转成list
        my_listWenda1= json.loads(extracted_jsonWenda1)

        #----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        #插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        #转成list
        my_listWenda2= json.loads(extracted_jsonWenda2)

        my_listWenda = my_listWenda1 + my_listWenda2;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3;

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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500

@app.route('/api/pdf/v4', methods=['POST'])
def upload_pdf_v4():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

        #切割文本
        # 计算每一部分的长度，使用整除确保得到整数
        part_length = len(file_content) // 4
        # 使用字符串切片获取每一部分
        first_part = file_content[:part_length]
        second_part = file_content[part_length:2 * part_length]
        third_part = file_content[2 * part_length:3 * part_length]
        fourth_part = file_content[3 * part_length:]

        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content2) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content2[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content2[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
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

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v4"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        #第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v4"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        #----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages3,
            temperature=0.3,
        )
        #第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "v4"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        #转成list
        my_list3 = json.loads(extracted_json3)


        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages4,
            temperature=0.3,
        )
        #第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "v4"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        #转成list
        my_list4 = json.loads(extracted_json4)


        #-----------------------------------4 结束--------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie= completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "v4"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v4")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)


        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        #插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        #转成list
        my_listWenda1= json.loads(extracted_jsonWenda1)

        #----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2= client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        #插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        #转成list
        my_listWenda2= json.loads(extracted_jsonWenda2)

        my_listWenda = my_listWenda1 + my_listWenda2;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4;

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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/v5', methods=['POST'])
def upload_pdf_v5():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName, openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            # api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            # api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s", file_object.filename, file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename, file_object.bytes / 1024,
                        file_content)

        # 切割文本
        # 获取字符串长度
        total_length = len(file_content)

        # 计算每一部分的长度，注意这里我们不使用整除，因为我们想尽可能均匀地分配字符串
        part_length = total_length / 5

        # 使用字符串切片获取每一部分
        first_part = file_content[:int(part_length)]
        second_part = file_content[int(part_length):int(2 * part_length)]
        third_part = file_content[int(2 * part_length):int(3 * part_length)]
        fourth_part = file_content[int(3 * part_length):int(4 * part_length)]
        fifth_part = file_content[int(4 * part_length):]


        #问答题切割
        # 计算每一部分的大致长度，使用整除来确保得到整数
        wenda_length = len(file_content2) // 3
        # 使用字符串切片获取每一部分
        first_wenda = file_content2[:wenda_length]
        second_wenda = file_content2[wenda_length:2 * wenda_length]
        third_wenda = file_content2[2 * wenda_length:]


        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages5 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fifth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages1,
            temperature=0.3,
        )
        # ------------------------1------------------------------
        # 第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v5"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        # 转成list
        my_list1 = json.loads(extracted_json1)

        # ----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        # 第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v5"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        # 转成list
        my_list2 = json.loads(extracted_json2)

        # ----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages3,
            temperature=0.3,
        )
        # 第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "v5"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages4,
            temperature=0.3,
        )
        # 第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "v5"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text4)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        # 转成list
        my_list4 = json.loads(extracted_json4)

        # -----------------------------------4 结束--- 5开始-----------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completion5 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages5,
            temperature=0.3,
        )
        # 第3次返回的答案
        text5 = completion5.choices[0].message.content

        record5 = Records()
        record5.remark = text5
        record5.remark2 = "v5"
        record5.created_at = datetime.now()
        insert_records(record5)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text5)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json5 = '\n\n'.join(matches)
        # 转成list
        my_list5 = json.loads(extracted_json5)

        # -----------------------------------4 结束--------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie = completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024)
        file.api_file_id = file_object.id
        file.version = "v5"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v5")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)

        # ------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        # 插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        # 转成list
        my_listWenda1 = json.loads(extracted_jsonWenda1)

        # ----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        # 插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda2 = json.loads(extracted_jsonWenda2)

        # ----------------------------------------2问答题----------------------------
        messagesWenda3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda3,
            temperature=0.3,
        )

        # 插入记录
        textWenda3 = completionWenda3.choices[0].message.content;
        recordWenda3 = Records()
        recordWenda3.remark = textWenda3
        recordWenda3.remark2 = "wenda"
        recordWenda3.created_at = datetime.now()
        insert_records(recordWenda3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda3= json.loads(extracted_jsonWenda2)


        #-----------------------------问答题3 结束--------------------------

        my_listWenda = my_listWenda1 + my_listWenda2 + my_listWenda3;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4 + my_list5;

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
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/v6', methods=['POST'])
def upload_pdf_v6():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName, openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            # api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            # api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s", file_object.filename, file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename, file_object.bytes / 1024,
                        file_content)

        # 切割文本
        # 获取字符串长度
        total_length = len(file_content)
        # 计算每一部分的长度，这里我们直接使用浮点数进行计算以保持平均分配
        part_length = total_length / 6
        # 使用字符串切片获取每一部分
        first_part = file_content[:int(part_length)]
        second_part = file_content[int(part_length):int(2 * part_length)]
        third_part = file_content[int(2 * part_length):int(3 * part_length)]
        fourth_part = file_content[int(3 * part_length):int(4 * part_length)]
        fifth_part = file_content[int(4 * part_length):int(5 * part_length)]
        sixth_part = file_content[int(5 * part_length):]

        #问答题切割
        # 计算每一部分的大致长度，使用整除来确保得到整数
        wenda_length = len(file_content2) // 3
        # 使用字符串切片获取每一部分
        first_wenda = file_content2[:wenda_length]
        second_wenda = file_content2[wenda_length:2 * wenda_length]
        third_wenda = file_content2[2 * wenda_length:]


        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages5 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fifth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]


        messages6 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": sixth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages1,
            temperature=0.3,
        )
        # ------------------------1------------------------------
        # 第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v6"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        # 转成list
        my_list1 = json.loads(extracted_json1)

        # ----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages2,
            temperature=0.3,
        )
        # 第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v6"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        # 转成list
        my_list2 = json.loads(extracted_json2)

        # ----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages3,
            temperature=0.3,
        )
        # 第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "v6"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages4,
            temperature=0.3,
        )
        # 第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "v6"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text4)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        # 转成list
        my_list4 = json.loads(extracted_json4)

        # -----------------------------------4 结束--- 5开始-----------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completion5 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages5,
            temperature=0.3,
        )
        # 第3次返回的答案
        text5 = completion5.choices[0].message.content

        record5 = Records()
        record5.remark = text5
        record5.remark2 = "v6"
        record5.created_at = datetime.now()
        insert_records(record5)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text5)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json5 = '\n\n'.join(matches)
        # 转成list
        my_list5 = json.loads(extracted_json5)

        # -----------------------------------5 结束--------------------

        # -----------------------------------5 结束--- 6开始-----------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion6 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messages6,
            temperature=0.3,
        )
        # 第3次返回的答案
        text6= completion6.choices[0].message.content

        record6 = Records()
        record6.remark = text6
        record6.remark2 = "v6"
        record6.created_at = datetime.now()
        insert_records(record6)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text6)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json6 = '\n\n'.join(matches)
        # 转成list
        my_list6 = json.loads(extracted_json6)

        # -----------------------------------6 结束--------------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie = completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024)
        file.api_file_id = file_object.id
        file.version = "v6"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v6")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)

        # ------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        # 插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        # 转成list
        my_listWenda1 = json.loads(extracted_jsonWenda1)

        # ----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        # 插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda2 = json.loads(extracted_jsonWenda2)

        # ----------------------------------------2问答题----------------------------
        messagesWenda3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda3 = client.chat.completions.create(
            model="moonshot-v1-32k",
            messages=messagesWenda3,
            temperature=0.3,
        )

        # 插入记录
        textWenda3 = completionWenda3.choices[0].message.content;
        recordWenda3 = Records()
        recordWenda3.remark = textWenda3
        recordWenda3.remark2 = "wenda"
        recordWenda3.created_at = datetime.now()
        insert_records(recordWenda3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda3= json.loads(extracted_jsonWenda2)


        #-----------------------------问答题3 结束--------------------------

        my_listWenda = my_listWenda1 + my_listWenda2 + my_listWenda3;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4 + my_list5 + my_list6;

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
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500



#VIP会员使用
@app.route('/api/pdf/s1', methods=['POST'])
def upload_pdf_s1():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

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
             "content": "你是一个老师，请针对" + filename + ".pdf" + "的全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        #------------------------1------------------------------
        #第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "s1"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        text3 = completionZongJie.choices[0].message.content;
        record3 = Records()
        record3.remark = text3
        record3.remark2 = "zongjie"
        record3.created_at = datetime.now()
        insert_records(record3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_json3333 = json.loads(extracted_json3)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "s1"
        file.create_by = openid
        file.zongfenjie = extracted_json3
        file.yijuhua = extracted_json3333.get("zongjie", "")
        file.timus = process_input_string("s1")
        insert_file(file)

        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个专业老师，请针对" + filename + ".pdf" + "的全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda= client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda,
            temperature=0.3,
        )

        #插入记录
        textWenda = completionWenda.choices[0].message.content;
        recordWenda = Records()
        recordWenda.remark = textWenda
        recordWenda.remark2 = "wenda"
        recordWenda.created_at = datetime.now()
        insert_records(recordWenda)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda = '\n\n'.join(matches)

        #转成list
        my_listWenda= json.loads(extracted_jsonWenda)

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v11111")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        for question_dict in my_list1:
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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/s2', methods=['POST'])
def upload_pdf_s2():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

        #切割文本
        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        #------------------------1------------------------------
        #第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "s2"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages2,
            temperature=0.3,
        )
        #第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "s2"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        #----------------------------2-----------------------------------


        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        text3 = completion3.choices[0].message.content;
        record3 = Records()
        record3.remark = text3
        record3.remark2 = "zongjie"
        record3.created_at = datetime.now()
        insert_records(record3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_json3333 = json.loads(extracted_json3)


        #插入文件记录
        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 1
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "s2"
        file.create_by = openid
        file.zongfenjie = extracted_json3
        file.yijuhua = extracted_json3333.get("zongjie", "")
        file.timus = process_input_string("v2")
        insert_file(file)

        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个专业老师，请针对" + filename + ".pdf" + "的全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda= client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda,
            temperature=0.3,
        )

        #插入记录
        textWenda = completionWenda.choices[0].message.content;
        recordWenda = Records()
        recordWenda.remark = textWenda
        recordWenda.remark2 = "wenda"
        recordWenda.created_at = datetime.now()
        insert_records(recordWenda)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda = '\n\n'.join(matches)

        #转成list
        my_listWenda= json.loads(extracted_jsonWenda)

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2;

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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/s3', methods=['POST'])
def upload_pdf_s3():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName,openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            #api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            #api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)

        #切割文本
        # 计算每一部分的大致长度，使用整除来确保得到整数
        part_length = len(file_content) // 3
        # 使用字符串切片获取每一部分
        first_part = file_content[:part_length]
        second_part = file_content[part_length:2 * part_length]
        third_part = file_content[2 * part_length:]

        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content2) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content2[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content2[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        #------------------------1------------------------------
        #第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "s3"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        #转成list
        my_list1 = json.loads(extracted_json1)

        #----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages2,
            temperature=0.3,
        )
        #第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "s3"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        #转成list
        my_list2 = json.loads(extracted_json2)

        #----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages3,
            temperature=0.3,
        )
        #第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "s3"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        #转成list
        my_list3 = json.loads(extracted_json3)


        # --------------------------3-------------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie= completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024 )
        file.api_file_id = file_object.id
        file.version = "s3"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v3")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)


        #------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1= client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        #插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        #转成list
        my_listWenda1= json.loads(extracted_jsonWenda1)

        #----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2= client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        #插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        #转成list
        my_listWenda2= json.loads(extracted_jsonWenda2)

        my_listWenda = my_listWenda1 + my_listWenda2;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3;

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
                file_name= pdfName,
                api_file_id= file_object.id,
                created_at = datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/s4', methods=['POST'])
def upload_pdf_s4():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName, openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            # api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            # api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s", file_object.filename, file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename, file_object.bytes / 1024,
                        file_content)

        # 切割文本
        # 计算每一部分的长度，使用整除确保得到整数
        part_length = len(file_content) // 4
        # 使用字符串切片获取每一部分
        first_part = file_content[:part_length]
        second_part = file_content[part_length:2 * part_length]
        third_part = file_content[2 * part_length:3 * part_length]
        fourth_part = file_content[3 * part_length:]

        # 计算字符串的长度，并整除2得到中间位置
        mid_point = len(file_content2) // 2
        # 使用字符串切片获取前半部分
        first_half = file_content2[:mid_point]
        # 使用字符串切片获取后半部分
        second_half = file_content2[mid_point:]

        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        # ------------------------1------------------------------
        # 第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "v4"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        # 转成list
        my_list1 = json.loads(extracted_json1)

        # ----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages2,
            temperature=0.3,
        )
        # 第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "v4"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        # 转成list
        my_list2 = json.loads(extracted_json2)

        # ----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages3,
            temperature=0.3,
        )
        # 第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "v4"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages4,
            temperature=0.3,
        )
        # 第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "v4"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        # 转成list
        my_list4 = json.loads(extracted_json4)

        # -----------------------------------4 结束--------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie = completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024)
        file.api_file_id = file_object.id
        file.version = "v4"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v4")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)

        # ------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        # 插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        # 转成list
        my_listWenda1 = json.loads(extracted_jsonWenda1)

        # ----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_half,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        # 插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda2 = json.loads(extracted_jsonWenda2)

        my_listWenda = my_listWenda1 + my_listWenda2;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4;

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
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500



@app.route('/api/pdf/s5', methods=['POST'])
def upload_pdf_s5():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName, openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            # api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            # api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s", file_object.filename, file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename, file_object.bytes / 1024,
                        file_content)

        # 切割文本
        # 获取字符串长度
        total_length = len(file_content)

        # 计算每一部分的长度，注意这里我们不使用整除，因为我们想尽可能均匀地分配字符串
        part_length = total_length / 5

        # 使用字符串切片获取每一部分
        first_part = file_content[:int(part_length)]
        second_part = file_content[int(part_length):int(2 * part_length)]
        third_part = file_content[int(2 * part_length):int(3 * part_length)]
        fourth_part = file_content[int(3 * part_length):int(4 * part_length)]
        fifth_part = file_content[int(4 * part_length):]


        #问答题切割
        # 计算每一部分的大致长度，使用整除来确保得到整数
        wenda_length = len(file_content2) // 3
        # 使用字符串切片获取每一部分
        first_wenda = file_content2[:wenda_length]
        second_wenda = file_content2[wenda_length:2 * wenda_length]
        third_wenda = file_content2[2 * wenda_length:]


        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages5 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fifth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        # ------------------------1------------------------------
        # 第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "s5"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        # 转成list
        my_list1 = json.loads(extracted_json1)

        # ----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages2,
            temperature=0.3,
        )
        # 第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "s5"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        # 转成list
        my_list2 = json.loads(extracted_json2)

        # ----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages3,
            temperature=0.3,
        )
        # 第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "s5"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages4,
            temperature=0.3,
        )
        # 第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "s5"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text4)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        # 转成list
        my_list4 = json.loads(extracted_json4)

        # -----------------------------------4 结束--- 5开始-----------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completion5 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages5,
            temperature=0.3,
        )
        # 第3次返回的答案
        text5 = completion5.choices[0].message.content

        record5 = Records()
        record5.remark = text5
        record5.remark2 = "s5"
        record5.created_at = datetime.now()
        insert_records(record5)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text5)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json5 = '\n\n'.join(matches)
        # 转成list
        my_list5 = json.loads(extracted_json5)

        # -----------------------------------4 结束--------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie = completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024)
        file.api_file_id = file_object.id
        file.version = "s5"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v5")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)

        # ------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        # 插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        # 转成list
        my_listWenda1 = json.loads(extracted_jsonWenda1)

        # ----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        # 插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda2 = json.loads(extracted_jsonWenda2)

        # ----------------------------------------2问答题----------------------------
        messagesWenda3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda3,
            temperature=0.3,
        )

        # 插入记录
        textWenda3 = completionWenda3.choices[0].message.content;
        recordWenda3 = Records()
        recordWenda3.remark = textWenda3
        recordWenda3.remark2 = "wenda"
        recordWenda3.created_at = datetime.now()
        insert_records(recordWenda3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda3= json.loads(extracted_jsonWenda2)


        #-----------------------------问答题3 结束--------------------------

        my_listWenda = my_listWenda1 + my_listWenda2 + my_listWenda3;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4 + my_list5;

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
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


@app.route('/api/pdf/s6', methods=['POST'])
def upload_pdf_s6():
    # 解析请求数据
    data = request.get_json()
    downloadURL = data.get('downloadURL')
    pdfName = data.get('pdfName')
    openid = data.get('openid')

    # 打印信息到控制台
    app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s", downloadURL, pdfName, openid)

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
        client = OpenAI(
            # api_key="sk-nFhPcpNc2oBTxAMn7XP5KuL8ldxAKq9SFCky7xeCJzwqwkLV",sk-vdjbCMxXv762YrwrVxdZFWtC2DxrjE3BMOuVtEczmX5afvgV
            # 3335
            api_key="sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX",
            # api_key = "sk-gpbNCX3bxCQX8fUOQu1KUXj97SVKQQoJuxJSym7eXMMnqWHe",  # 8061
            # api_key = "sk-fvcU5LTOezeeBcbbFSiXiwWTudu6v3p7uhAblYucKbGg0a1W",  #7077
            base_url="https://api.moonshot.cn/v1",
        )
        # xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 等格式, 目前暂不提供ocr相关能力
        file_object = client.files.create(file=Path(file_path), purpose="file-extract")
        app.logger.info("文件名称= %s,文件ID= %s", file_object.filename, file_object.id)
        app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)

        # 获取结果
        # file_content = client.files.retrieve_content(file_id=file_object.id)
        # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
        # 如果是旧版本，可以用 retrieve_content
        file_content = client.files.content(file_id=file_object.id).text
        file_content2 = client.files.content(file_id=file_object.id).text

        # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
        app.logger.info("文件ID= %s", file_object.id)
        app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename, file_object.bytes / 1024,
                        file_content)

        # 切割文本
        # 获取字符串长度
        total_length = len(file_content)
        # 计算每一部分的长度，这里我们直接使用浮点数进行计算以保持平均分配
        part_length = total_length / 6
        # 使用字符串切片获取每一部分
        first_part = file_content[:int(part_length)]
        second_part = file_content[int(part_length):int(2 * part_length)]
        third_part = file_content[int(2 * part_length):int(3 * part_length)]
        fourth_part = file_content[int(3 * part_length):int(4 * part_length)]
        fifth_part = file_content[int(4 * part_length):int(5 * part_length)]
        sixth_part = file_content[int(5 * part_length):]

        #问答题切割
        # 计算每一部分的大致长度，使用整除来确保得到整数
        wenda_length = len(file_content2) // 3
        # 使用字符串切片获取每一部分
        first_wenda = file_content2[:wenda_length]
        second_wenda = file_content2[wenda_length:2 * wenda_length]
        third_wenda = file_content2[2 * wenda_length:]


        # 把它放进请求中
        messages1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages4 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fourth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messages5 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": fifth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]


        messages6 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": sixth_part,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        messagesZongJie = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": file_content,
            },
            {"role": "user",
             "content": "你是一个老师，请认真阅读" + filename + ".pdf" + "的全部内容，最终返回的是json的字符串（用```json和```包围起来）。先从专业的角度总结该文档的内容（返回字段是zongjie），然后从专业的角度分点详细总结出各个完整的知识点（返回的字段是fendian,fendian是一个list结构，里面是map，map包含的key有title（知识点标题）、content（知识点内容））"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages1,
            temperature=0.3,
        )
        # ------------------------1------------------------------
        # 第一次返回的答案
        text1 = completion1.choices[0].message.content

        record1 = Records()
        record1.remark = text1
        record1.remark2 = "s6"
        record1.created_at = datetime.now()
        insert_records(record1)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json1 = '\n\n'.join(matches)
        # 转成list
        my_list1 = json.loads(extracted_json1)

        # ----------------------------2-----------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages2,
            temperature=0.3,
        )
        # 第2次返回的答案
        text2 = completion2.choices[0].message.content

        record2 = Records()
        record2.remark = text2
        record2.remark2 = "s6"
        record2.created_at = datetime.now()
        insert_records(record2)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json2 = '\n\n'.join(matches)
        # 转成list
        my_list2 = json.loads(extracted_json2)

        # ----------------------------2-结束---------------------------------
        # 然后调用 chat-completion, 获取 kimi 的回答
        completion3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages3,
            temperature=0.3,
        )
        # 第3次返回的答案
        text3 = completion3.choices[0].message.content

        record3 = Records()
        record3.remark = text3
        record3.remark2 = "s6"
        record3.created_at = datetime.now()
        insert_records(record3)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json3 = '\n\n'.join(matches)
        # 转成list
        my_list3 = json.loads(extracted_json3)

        # --------------------------3--结束----4开始------------------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion4 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages4,
            temperature=0.3,
        )
        # 第3次返回的答案
        text4 = completion4.choices[0].message.content

        record4 = Records()
        record4.remark = text4
        record4.remark2 = "s6"
        record4.created_at = datetime.now()
        insert_records(record4)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text4)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json4 = '\n\n'.join(matches)
        # 转成list
        my_list4 = json.loads(extracted_json4)

        # -----------------------------------4 结束--- 5开始-----------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completion5 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages5,
            temperature=0.3,
        )
        # 第3次返回的答案
        text5 = completion5.choices[0].message.content

        record5 = Records()
        record5.remark = text5
        record5.remark2 = "s6"
        record5.created_at = datetime.now()
        insert_records(record5)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text5)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json5 = '\n\n'.join(matches)
        # 转成list
        my_list5 = json.loads(extracted_json5)

        # -----------------------------------5 结束--------------------

        # -----------------------------------5 结束--- 6开始-----------------

        # 然后调用 chat-completion, 获取 kimi 的回答
        completion6 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages6,
            temperature=0.3,
        )
        # 第3次返回的答案
        text6= completion6.choices[0].message.content

        record6 = Records()
        record6.remark = text6
        record6.remark2 = "s6"
        record6.created_at = datetime.now()
        insert_records(record6)

        # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(text6)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_json6 = '\n\n'.join(matches)
        # 转成list
        my_list6 = json.loads(extracted_json6)

        # -----------------------------------6 结束--------------------


        # 然后调用 chat-completion, 获取 kimi 的回答
        completionZongJie = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesZongJie,
            temperature=0.3,
        )

        textZongJie = completionZongJie.choices[0].message.content;
        recordZongJie = Records()
        recordZongJie.remark = textZongJie
        recordZongJie.remark2 = "zongjie"
        recordZongJie.created_at = datetime.now()
        insert_records(recordZongJie)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textZongJie)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonZongJie = '\n\n'.join(matches)

        # 使用json.loads()将字符串解析为字典
        extracted_jsonZongJie22 = json.loads(extracted_jsonZongJie)

        file = File()
        file.file_name = pdfName
        file.download_url = downloadURL
        file.created_at = datetime.now()
        file.open = 0
        file.file_size = floor(file_object.bytes / 1024)
        file.api_file_id = file_object.id
        file.version = "s6"
        file.create_by = openid
        file.zongfenjie = extracted_jsonZongJie
        file.yijuhua = extracted_jsonZongJie22.get("zongjie", "")
        file.timus = process_input_string("v6")
        insert_file(file)
        app.logger.info("添加文件 文件名称= %s", file_object.filename)

        # ------------------------------------------问答题-----------------------------------------------------------
        messagesWenda1 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": first_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda1 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda1,
            temperature=0.3,
        )

        # 插入记录
        textWenda1 = completionWenda1.choices[0].message.content;
        recordWenda1 = Records()
        recordWenda1.remark = textWenda1
        recordWenda1.remark2 = "wenda"
        recordWenda1.created_at = datetime.now()
        insert_records(recordWenda1)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda1)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda1 = '\n\n'.join(matches)
        # 转成list
        my_listWenda1 = json.loads(extracted_jsonWenda1)

        # ----------------------------------------2问答题----------------------------
        messagesWenda2 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": second_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda2 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda2,
            temperature=0.3,
        )

        # 插入记录
        textWenda2 = completionWenda2.choices[0].message.content;
        recordWenda2 = Records()
        recordWenda2.remark = textWenda2
        recordWenda2.remark2 = "wenda"
        recordWenda2.created_at = datetime.now()
        insert_records(recordWenda2)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda2)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda2 = json.loads(extracted_jsonWenda2)

        # ----------------------------------------2问答题----------------------------
        messagesWenda3 = [
            {
                "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
            },
            {
                "role": "system",
                "content": third_wenda,
            },
            {"role": "user",
             "content": "你是一个专业老师，请认真阅读全部内容，提供6道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
        ]

        # 然后调用 chat-completion, 获取 kimi 的回答
        completionWenda3 = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messagesWenda3,
            temperature=0.3,
        )

        # 插入记录
        textWenda3 = completionWenda3.choices[0].message.content;
        recordWenda3 = Records()
        recordWenda3.remark = textWenda3
        recordWenda3.remark2 = "wenda"
        recordWenda3.created_at = datetime.now()
        insert_records(recordWenda3)

        # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = pattern.findall(textWenda3)
        # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
        extracted_jsonWenda2 = '\n\n'.join(matches)

        # 转成list
        my_listWenda3= json.loads(extracted_jsonWenda2)


        #-----------------------------问答题3 结束--------------------------

        my_listWenda = my_listWenda1 + my_listWenda2 + my_listWenda3;

        for question_dict in my_listWenda:
            # 创建 Records 实例，确保字段匹配
            question_wenda = Wendati(
                question=question_dict.get('question', ''),
                fenxi=question_dict.get('fenxi', ''),
                source=question_dict.get('source', ''),
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("extracted_jsonWenda_v22222")
            insert_questions(question_wenda)
        # ------------------------------------------问答题-----------------------------------------------------------
        app.logger.info('my_list1:')
        app.logger.info(my_list1)

        """
        处理问题列表并插入到数据库
        :param questions_list: 包含多个问题字典的列表
        """
        my_list = my_list1 + my_list2 + my_list3 + my_list4 + my_list5 + my_list6;

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
                file_name=pdfName,
                api_file_id=file_object.id,
                created_at=datetime.now()
            )
            # 调用插入方法
            app.logger.info("question_record888_v11111")
            insert_questions(question_record)

        # 返回成功消息和文件路径
        return jsonify({'message': 'successfully'})

    # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to download the file', 'details': str(e)}), 500


#文件与用户id绑定
@app.route('/user/bind/pdf', methods=['POST'])
def user_bind_pdf():

    # 解析请求数据
    data = request.get_json()
    file_name = data.get('file_name')
    download_url = data.get('download_url')
    file_size = data.get('file_size')
    create_by = data.get('create_by')
    api_file_id = data.get('api_file_id')
    version = data.get('version')
    yijuhua = data.get('yijuhua')
    zongfenjie = data.get('zongfenjie')

    app.logger.info("文件与用户id绑定 download_url= %s,PDF名称= %s", download_url, file_name)

    file = File()
    file.file_name = file_name
    file.download_url = download_url
    file.created_at = datetime.now()
    file.open = 2
    file.file_size = file_size
    file.api_file_id = api_file_id
    file.version = version
    file.create_by = create_by
    file.zongfenjie = zongfenjie
    file.yijuhua = yijuhua
    file.timus = process_input_string(version)
    insert_file(file)

    return jsonify({'message': '绑定成功'})


@app.route('/user/unbind/pdf', methods=['POST'])
def user_unbind_pdf():

    # 解析请求数据
    data = request.get_json()
    api_file_id = data.get('api_file_id')
    create_by = data.get('create_by')

    app.logger.info("文件与用户id取消绑定 api_file_id= %s,create_by= %s", api_file_id, create_by)

    success, message = delete_file22(api_file_id, create_by)  # 使用新的 delete_file 方法
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400 if "未找到文件或权限不足" in message else 500


@app.route('/wendati/by_fileid', methods=['POST'])
def get_wendatis_by_fileid():

    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON or empty payload'}), 400

    api_file_id = data.get('api_file_id')
    if not api_file_id:
        return jsonify({'error': 'Missing openid'}), 400

    app.logger.info("查询问答题入参=%s", api_file_id)

    wendatissss = query_wendatisbyapiid(api_file_id)
    wendati_data = [{
        'id': wendati.id,
        'question': wendati.question,
        'fenxi': wendati.fenxi,
        'file_name': wendati.file_name,
        'created_at': wendati.created_at,
        'source': wendati.source,
        'api_file_id': wendati.api_file_id
    } for wendati in wendatissss]

    return jsonify(wendati_data), 200


def process_input_string(input_string):

    mapping = {
        '1': 11,
        '2': 16,
        '3': 27,
        '4': 32,
        '5': 43,
        '6': 48,
    }

    # 遍历字典，检查输入字符串中是否包含特定字符
    for char, value in mapping.items():
        if char in input_string:
            return value

    # 如果输入字符串不包含任何指定字符，则返回错误信息或特定值
    return 0

@app.route('/file/by_api_fileid', methods=['POST'])
def get_filedetail_by_api_fileid():

    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON or empty payload'}), 400

    fileid = data.get('fileid')
    if not fileid:
        return jsonify({'error': 'Missing openid'}), 400

    app.logger.info("查询问题入参=%s", fileid)
    file = query_fileByApiFileid(fileid)
    if file is None:
        return jsonify({'error': 'File not found'}), 404
    file_detail = {
        'id': file.id,
        'file_name': file.file_name,
        'download_url': file.download_url,
        'file_size': file.file_size,
        'open': file.open,
        'api_file_id': file.api_file_id,
        'created_at': file.created_at,
        'create_by': file.create_by,
        'version': file.version,
        'yijuhua': file.yijuhua,
        'timus': file.timus,
        'zongfenjie': file.zongfenjie
    }
    return jsonify(file_detail), 200


@app.route('/user/chushihua/pdf', methods=['POST'])
def user_chushihua_pdf():

    # 解析请求数据
    data = request.get_json()
    openid = data.get('openid')
    app.logger.info("初始化 = %s", openid)
    file1 = query_fileByApiFileid("cni6e1cudu62fberilog")
    file1.create_by= openid
    insert_file(file1)
    app.logger.info("初始化file1 = %s", file1)

    file2 = query_fileByApiFileid("cni5p72lnl9cetc8kqr0")
    file2.create_by= openid
    insert_file(file2)
    app.logger.info("初始化file2 = %s", file2)

    file3 = query_fileByApiFileid("cni5a02lnl91mfbctqg0")
    file3.create_by= openid
    insert_file(file3)
    app.logger.info("初始化file3 = %s", file3)

    return jsonify({'message': '初始化成功'})
