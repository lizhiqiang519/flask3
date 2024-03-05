import logging

from sqlalchemy import desc
from sqlalchemy.exc import OperationalError

from wxcloudrun import db
from wxcloudrun.model import Counters
from wxcloudrun.modelFile import File
from wxcloudrun.modelQuestions import Questions
from wxcloudrun.modelWendatis import Wendati

# 初始化日志
logger = logging.getLogger('log')


def query_counterbyid(id):
    """
    根据ID查询Counter实体
    :param id: Counter的ID
    :return: Counter实体
    """
    try:
        return Counters.query.filter(Counters.id == id).first()
    except OperationalError as e:
        logger.info("query_counterbyid errorMsg= {} ".format(e))
        return None


def delete_counterbyid(id):
    """
    根据ID删除Counter实体
    :param id: Counter的ID
    """
    try:
        counter = Counters.query.get(id)
        if counter is None:
            return
        db.session.delete(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("delete_counterbyid errorMsg= {} ".format(e))


def insert_counter(counter):
    """
    插入一个Counter实体
    :param counter: Counters实体
    """
    try:
        db.session.add(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_counter errorMsg= {} ".format(e))


def update_counterbyid(counter):
    """
    根据ID更新counter的值
    :param counter实体
    """
    try:
        counter = query_counterbyid(counter.id)
        if counter is None:
            return
        db.session.flush()
        db.session.commit()
    except OperationalError as e:
        logger.info("update_counterbyid errorMsg= {} ".format(e))


def insert_records(records):
    """
    插入一个Counter实体
    :param counter: Counters实体
    """
    try:
        db.session.add(records)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_records errorMsg= {} ".format(e))

def insert_questions(questions):
    """
    插入一个questions实体
    :param questions: Questions实体
    """
    try:
        db.session.add(questions)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_questions errorMsg= {} ".format(e))

def insert_file(file):
    """
    插入一个questions实体
    :param questions: Questions实体
    """
    try:
        db.session.add(file)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_file errorMsg= {} ".format(e))

def query_filebycreateby(create_by):
    """
    查书
    """
    try:
        return File.query.filter(File.create_by == create_by).order_by(desc(File.created_at)).all()
    except OperationalError as e:
        logger.info("query_filebycreateby errorMsg= {} ".format(e))
        return None

def query_questionsbyapiid(api_file_id):
    """
    Questions
    """
    try:
        return Questions.query.filter(Questions.api_file_id == api_file_id).all()
    except OperationalError as e:
        logger.info("query_Questions errorMsg= {} ".format(e))
        return None

#获取单条问题
def get_one_questionsbyQid(qid):
    """
    Questions
    """
    try:
        return Questions.query.filter(Questions.id == qid).first()
    except OperationalError as e:
        logger.info("get_one_questionsbyQid errorMsg= {} ".format(e))
        return None



def query_filebyfileid(id):
    """
    查书
    """
    try:
        return File.query.filter(File.id == id).first()
    except OperationalError as e:
        logger.info("query_filebycreateby errorMsg= {} ".format(e))
        return None

def query_fileByApiFileid(id):
    """
    查书
    """
    try:
        return File.query.filter(File.api_file_id == id).first()
    except OperationalError as e:
        logger.info("query_fapi_file_id errorMsg= {} ".format(e))
        return None


def insert_wendatis(wendati):
    """
    插入一个questions实体
    :param questions: Questions实体
    """
    try:
        db.session.add(wendati)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_wendati errorMsg= {} ".format(e))


#删除文件
def delete_file22(api_file_id, create_by):
    try:
        # 查找匹配的文件记录
        file = File.query.filter_by(api_file_id=api_file_id, create_by=create_by).first()
        if file:
            db.session.delete(file)  # 删除该记录
            db.session.commit()  # 提交更改
            return True, "文件删除成功"
        else:
            return False, "未找到文件或权限不足"
    except Exception as e:
        db.session.rollback()  # 错误时回滚
        return False, f"删除文件时发生错误: {str(e)}"


def query_wendatisbyapiid(api_file_id):
    """
    Wendatis
    """
    try:
        return Wendati.query.filter(Wendati.api_file_id == api_file_id).all()
    except OperationalError as e:
        logger.info("query_Wendati errorMsg= {} ".format(e))
        return None