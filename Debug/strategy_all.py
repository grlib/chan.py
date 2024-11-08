import logging
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from DataAPI.MySqlAPI import MySQL_API

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_within_days(dt, days=10):
    # 将输入的日期字符串转换为 datetime 对象
    # 获取当前日期
    current_date = datetime.now()
    
    # 计算给定日期和当前日期之间的差异
    delta = current_date - dt
    
    # 检查差异是否不超过两天
    return abs(delta.days) <= days

def calc_bsp_list(code):
    begin_time = "2024-01-01"
    end_time = None
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": False,
        "divergence_rate": 0.8,
        "min_zs_cnt": 1,
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src='custom:MySqlAPI.MySQL_API',
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )
    
    bsp_list = chan.get_bsp()  # 获取买卖点列表
    if not bsp_list:  # 为空
        return
    last_bsp = bsp_list[-1]  # 最后一个买卖点
    
    if not last_bsp.is_buy:
        return

    logger.info(f'{code}')
    if is_within_days(last_bsp.klu.time.toDateTime()):
        logger.info(f"code={code},last_bsp.type={last_bsp.type},last_bsp.klu.time.toDateTime()={last_bsp.klu.time.toDateTime()}")
    
if __name__ == "__main__":
  
    data_src = MySQL_API('all')
    
    stocks = data_src.get_all_stocks()
    total = len(stocks)
    i = 0
    for stock in stocks:
        code = stock['code']
        i += 1
        logger.info(f'({i}/{total}) {code}')
        try:
            calc_bsp_list(code)
        except:
            pass
        