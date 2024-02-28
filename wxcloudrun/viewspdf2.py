# import json
# from datetime import datetime
# from math import floor
# from pathlib import Path
#
# from flask import render_template, request, jsonify
# from run import app
# from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid, insert_records, \
#     insert_questions, insert_file, query_filebycreateby, query_questionsbyapiid, query_filebyfileid
# from wxcloudrun.model import Counters
# from wxcloudrun.modelFile import File
# from wxcloudrun.modelQuestions import Questions
# from wxcloudrun.modelRecord import Records
# from wxcloudrun.modelWendatis import Wendati
# from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
# import os
# import logging
# import requests
# from openai import OpenAI
# import re
# from werkzeug.utils import secure_filename
#
# from urllib.parse import urlparse, unquote
#
# # 配置日志记录
# logging.basicConfig(level=logging.INFO)
#
# # 设置您的Moonshot AI API密钥
# MOONSHOT_API_KEY = 'sk-IaFmuC7stQNyYEh63CJVeo94aqwrD2FozqOvRGTLlwPFLOsX'
# MOONSHOT_API_URL = 'https://api.moonshot.cn/v1'
#
#
# #基础会员使用
# @app.route('/api/v2/pdf', methods=['POST'])
# def upload_pdf_v2():
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     #获取接口：v开头是普通会员，s开头是vip会员；v或s后面接的数字代表是要生成多少组题目
#     member = data.get('member')
#
#     # 打印信息到控制台
#     app.logger.info("upload_pdf_v2传进来的下载链接= %s,PDF名称= %s,用户的openid=%s,选择的接口=%s", downloadURL, pdfName,openid,member)
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
#         app.logger.info("upload_pdf_v2文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("upload_pdf_v2文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
#         app.logger.info("文件ID= %s", file_object.id)
#         app.logger.info("upload_pdf_v2文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)
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
#         messagesZongJie = [
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
#             messages=messagesZongJie,
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
#
#
# #基础会员使用
# @app.route('/api/pdf/v1', methods=['POST'])
# def upload_pdf_v1():
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     # 打印信息到控制台
#     app.logger.info("传进来的下载链接= %s,PDF名称= %s,用户的openid=%s,选择的接口=%s", downloadURL, pdfName,openid)
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
#         app.logger.info("文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
#         app.logger.info("文件ID= %s", file_object.id)
#         app.logger.info("文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)
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
#              "content": "你是一个老师，请针对" + filename + ".pdf" + "的全部内容，提供5道书中重要知识点相关的选择题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、option_a(选项A,内容开头含A.)、option_b(选项B,内容开头含B.)、option_c(选项C,内容开头含C.)、option_d(选项D,内容开头含D.)、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
#         ]
#
#         messagesZongJie = [
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
#             model="moonshot-v1-32k",
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
#         # --------------------------3-------------------------------
#
#         # 然后调用 chat-completion, 获取 kimi 的回答
#         completion3 = client.chat.completions.create(
#             model="moonshot-v1-32k",
#             messages=messagesZongJie,
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
#         #------------------------------------------问答题-----------------------------------------------------------
#         messagesWenda = [
#             {
#                 "role": "system",
#                 "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一些涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
#             },
#             {
#                 "role": "system",
#                 "content": file_content,
#             },
#             {"role": "user",
#              "content": "你是一个专业老师，请针对" + filename + ".pdf" + "的全部内容，提供5道文档中重要知识点相关的问答题，返回的格式要求：list的json字符串，其中list里面包含map，每个map包含这些属性：question（问题）、answer（答案，单选A或B或C或D）、fenxi（答案分析解释、知识点复述）、source（答案来源，具体到哪一章哪一节或目录标题，不包含pdf文件名）"}
#         ]
#
#         # 然后调用 chat-completion, 获取 kimi 的回答
#         completionWenda= client.chat.completions.create(
#             model="moonshot-v1-32k",
#             messages=messagesWenda,
#             temperature=0.3,
#         )
#
#         #插入记录
#         textWenda = completionWenda.choices[0].message.content;
#         recordWenda = Records()
#         recordWenda.remark = textWenda
#         recordWenda.remark2 = "wenda"
#         recordWenda.created_at = datetime.now()
#         insert_records(recordWenda)
#
#         # # # 使用正则表达式匹配 ```json 和 ``` 之间的内容
#         pattern = re.compile(r"```json(.*?)```", re.DOTALL)
#         matches = pattern.findall(textWenda)
#         # 将所有匹配的内容连接成一个字符串，每个匹配项之间用两个换行符分隔
#         extracted_jsonWenda = '\n\n'.join(matches)
#
#         #转成list
#         my_listWenda= json.loads(extracted_jsonWenda)
#
#         for question_dict in my_listWenda:
#             # 创建 Records 实例，确保字段匹配
#             question_wenda = Wendati(
#                 question=question_dict.get('question', ''),
#                 answer=question_dict.get('answer', ''),
#                 fenxi=question_dict.get('fenxi', ''),
#                 source=question_dict.get('source', ''),
#                 file_name= pdfName,
#                 api_file_id= file_object.id,
#                 created_at = datetime.now()
#             )
#             # 调用插入方法
#             app.logger.info("extracted_jsonWenda_v11111")
#             insert_questions(question_wenda)
#
#
#
#
#
#
#
#         # ------------------------------------------问答题-----------------------------------------------------------
#         app.logger.info('my_list1:')
#         app.logger.info(my_list1)
#
#         """
#         处理问题列表并插入到数据库
#         :param questions_list: 包含多个问题字典的列表
#         """
#         for question_dict in my_list1:
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
#
#
#
# #基础会员使用
# @app.route('/api/pdf/v2', methods=['POST'])
# def upload_pdf_v2():
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     #获取接口：v开头是普通会员，s开头是vip会员；v或s后面接的数字代表是要生成多少组题目
#     member = data.get('member')
#
#     # 打印信息到控制台
#     app.logger.info("upload_pdf_v2传进来的下载链接= %s,PDF名称= %s,用户的openid=%s,选择的接口=%s", downloadURL, pdfName,openid,member)
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
#         app.logger.info("upload_pdf_v2文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("upload_pdf_v2文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
#         app.logger.info("文件ID= %s", file_object.id)
#         app.logger.info("upload_pdf_v2文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)
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
#         messagesZongJie = [
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
#             messages=messagesZongJie,
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
#
# #基础会员使用
# @app.route('/api/pdf/v3', methods=['POST'])
# def upload_pdf_v3():
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     #获取接口：v开头是普通会员，s开头是vip会员；v或s后面接的数字代表是要生成多少组题目
#     member = data.get('member')
#
#     # 打印信息到控制台
#     app.logger.info("upload_pdf_v2传进来的下载链接= %s,PDF名称= %s,用户的openid=%s,选择的接口=%s", downloadURL, pdfName,openid,member)
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
#         app.logger.info("upload_pdf_v2文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("upload_pdf_v2文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 保存：fileID、原来文件名、下载链接、pdf封面URL、大小
#         app.logger.info("文件ID= %s", file_object.id)
#         app.logger.info("upload_pdf_v2文件名称= %s,文件大小= %s kb, 文件对象= %s ", file_object.filename,file_object.bytes / 1024,file_content)
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
#         messagesZongJie = [
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
#             messages=messagesZongJie,
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
#
