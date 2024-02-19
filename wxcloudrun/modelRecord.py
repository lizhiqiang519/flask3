from datetime import datetime

from wxcloudrun import db


# 计数表
class Records(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'Records'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    remark = db.Column(db.TEXT, default=1)
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now())
