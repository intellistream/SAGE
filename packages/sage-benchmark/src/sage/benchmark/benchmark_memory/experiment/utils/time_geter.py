from datetime import datetime


def get_time_filename():
    """
    返回格式为 '年月日_时分' 的时间字符串
    例如: '251117_1646' 表示 2025年11月17日 16:46
    """
    # 获取当前时间
    now = datetime.now()

    # 格式化为 'YYMMDD_HHMM' 格式
    # %y: 年份的后两位, %m: 月份, %d: 日期
    # %H: 24小时制的小时, %M: 分钟
    time_str = now.strftime("%y%m%d")

    return time_str
