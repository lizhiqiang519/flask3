from datetime import datetime

from wxcloudrun import db


# 计数表
class Wendati(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'Wendati'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.TEXT, default="")
    fenxi = db.Column(db.TEXT, default="")
    source = db.Column(db.TEXT, default="")
    file_name = db.Column(db.TEXT, default="")
    api_file_id = db.Column(db.TEXT, default="")
    created_at = db.Column('created_at', db.TIMESTAMP, nullable=False, default=datetime.now())
