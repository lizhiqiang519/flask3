from datetime import datetime

from wxcloudrun import db


# 计数表
class File(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'File'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.TEXT, default="")
    download_url = db.Column(db.TEXT, default="")
    file_size = db.Column(db.Integer, default="")
    open = db.Column(db.Integer, default="")
    api_file_id = db.Column(db.TEXT, default="")
    created_at = db.Column('created_at', db.TIMESTAMP, nullable=False, default=datetime.now())
    create_by = db.Column(db.TEXT, default="")
    #版本号
    version = db.Column(db.TEXT, default="")
    yijuhua = db.Column(db.TEXT, default="")
    zongfenjie= db.Column(db.TEXT, default="")
    #题目数量
    timus = db.Column(db.Integer, default="")
    #文件字数
    file_words = db.Column(db.Integer, default="")
    #操作类型：1、上传文件；2、上传文本
    operation_type = db.Column(db.Integer, default=1)