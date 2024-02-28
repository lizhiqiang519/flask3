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
# #查询
#
# @app.route('/files/by_creator', methods=['POST'])
# def get_files_by_creator():
#
#     if not request.is_json:
#         return jsonify({'error': 'Missing JSON in request'}), 400
#
#     data = request.get_json(silent=True)
#     if data is None:
#         return jsonify({'error': 'Invalid JSON or empty payload'}), 400
#
#     openid = data.get('openid')
#     if not openid:
#         return jsonify({'error': 'Missing openid'}), 400
#
#     app.logger.info("查询PDF入参=%s", openid)
#
#     files = query_filebycreateby(openid)
#     files_data = [{
#         'id': file.id,
#         'file_name': file.file_name,
#         'download_url': file.download_url,
#         'file_size': file.file_size,
#         'open': file.open,
#         'created_at': file.created_at,
#         'create_by': file.create_by,
#         'zongfenjie': file.zongfenjie,
#         'yijuhua': file.yijuhua,
#         'api_file_id': file.api_file_id,
#         'version': file.version
#     } for file in files]
#
#     return jsonify(files_data), 200
#
#
#
# @app.route('/questions/by_fileid', methods=['POST'])
# def get_questions_by_fileid():
#
#     if not request.is_json:
#         return jsonify({'error': 'Missing JSON in request'}), 400
#
#     data = request.get_json(silent=True)
#     if data is None:
#         return jsonify({'error': 'Invalid JSON or empty payload'}), 400
#
#     api_file_id = data.get('api_file_id')
#     if not api_file_id:
#         return jsonify({'error': 'Missing openid'}), 400
#
#     app.logger.info("查询问题入参=%s", api_file_id)
#
#     questions = query_questionsbyapiid(api_file_id)
#     questions_data = [{
#         'id': question.id,
#         'question': question.question,
#         'option_a': question.option_a,
#         'option_b': question.option_b,
#         'option_c': question.option_c,
#         'option_d': question.option_d,
#         'answer': question.answer,
#         'fenxi': question.fenxi,
#         'file_name': question.file_name,
#         'created_at': question.created_at,
#         'source': question.source,
#         'api_file_id': question.api_file_id
#     } for question in questions]
#
#     return jsonify(questions_data), 200
#
#
# @app.route('/api/calculate-token', methods=['POST'])
# def api_pdf_v1():
#
#     # 解析请求数据
#     data = request.get_json()
#     downloadURL = data.get('downloadURL')
#     pdfName = data.get('pdfName')
#     openid = data.get('openid')
#
#     # 打印信息到控制台
#     print(f"api_pdf_v1 Download URL: {downloadURL}")
#     print(f"api_pdf_v1 PDF Name: {pdfName}")
#     print(f"api_pdf_v1 用户的openid: {openid}")
#
#     app.logger.info("api_pdf_v1传进来的下载链接= %s,PDF名称= %s", downloadURL, pdfName)
#
#     # 当前目录
#     current_path = os.getcwd()
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
#         app.logger.info("api_pdf_v1文件名称= %s,文件ID= %s",file_object.filename,file_object.id)
#         app.logger.info("api_pdf_v1文件路径= %s,文件大小= %s kb", file_path, file_object.bytes / 1024)
#
#         # 获取结果
#         # file_content = client.files.retrieve_content(file_id=file_object.id)
#         # 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
#         # 如果是旧版本，可以用 retrieve_content
#         file_content = client.files.content(file_id=file_object.id).text
#
#         # 上传文件到Moonshot AI
#         headers = {
#             'Authorization': f'Bearer {MOONSHOT_API_KEY}',
#             'Content-Type': 'multipart/form-data'
#         }
#
#         # 使用文件内容计算Token
#         calculate_token_response = requests.post(
#             f'{MOONSHOT_API_URL}/tokenizers/estimate-token-count',
#             headers=headers,
#             json={'model': 'moonshot-v1-128k', 'messages': [{'role': 'system', 'content': file_content}]}
#         )
#
#         app.logger.info("计算token结果 %s", calculate_token_response)
#         app.logger.info(calculate_token_response)
#
#         # 检查计算Token响应
#         if calculate_token_response.status_code != 200:
#             return jsonify({'error': 'Failed to calculate tokens'}), calculate_token_response.status_code
#
#         # 解析计算Token响应
#         token_data = calculate_token_response.json()
#         total_tokens = token_data.get('data', {}).get('total_tokens')
#
#         app.logger.info("total_tokens %s", total_tokens)
#         app.logger.info("token_data %s", token_data)
#         app.logger.info(token_data)
#         app.logger.info("文件字数 %s", len(file_content))
#
#         app.logger.info(total_tokens)
#
#         # 返回计算结果
#         return jsonify({'total_tokens': total_tokens,'file_words': len(file_content)}), 200
#
#         # return make_succ_response(0) if counter is None else make_succ_response(counter.count)
#     except requests.RequestException as e:
#         return jsonify({'error': 'Failed to get total_tokens', 'details': str(e)}), 500
#
# @app.route('/file/by_fileid', methods=['POST'])
# def get_filedetail_by_fileid():
#
#     if not request.is_json:
#         return jsonify({'error': 'Missing JSON in request'}), 400
#
#     data = request.get_json(silent=True)
#     if data is None:
#         return jsonify({'error': 'Invalid JSON or empty payload'}), 400
#
#     fileid = data.get('fileid')
#     if not fileid:
#         return jsonify({'error': 'Missing openid'}), 400
#
#     app.logger.info("查询问题入参=%s", fileid)
#     file = query_filebyfileid(fileid)
#     if file is None:
#         return jsonify({'error': 'File not found'}), 404
#     file_detail = {
#         'id': file.id,
#         'file_name': file.file_name,
#         'download_url': file.download_url,
#         'file_size': file.file_size,
#         'open': file.open,
#         'api_file_id': file.api_file_id,
#         'created_at': file.created_at,
#         'create_by': file.create_by,
#         'version': file.version,
#         'yijuhua': file.yijuhua,
#         'zongfenjie': file.zongfenjie
#
#     }
#     return jsonify(file_detail), 200
