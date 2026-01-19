from xtquant import xtdata

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def normalize_code(code):
    """标准化股票代码格式为xtdata格式，如000001.SZ"""
    if '.' in code:
        parts = code.split('.')
        if len(parts) == 2:
            market, num = parts
            if market.lower() == 'sz':
                return f"{num}.SZ"
            elif market.lower() == 'sh':
                return f"{num}.SH"
            else:
                return code  # 保持原样
    else:
        # 默认SZ
        return f"{code}.SZ"


def normalize_date(date_str):
    """标准化日期格式为YYYYMMDD"""
    if date_str is None:
        return None
    if '-' in date_str:
        return date_str.replace('-', '')
    else:
        return date_str


def create_item_dict(data, column_name):
    for i in range(len(data)):
        if column_name[i] == DATA_FIELD.FIELD_TIME:
            data[i] = parse_time_column(data[i])
        else:
            data[i] = str2float(data[i])
    return dict(zip(column_name, data))


def parse_time_column(inp):
    # xtdata的时间可能是datetime或timestamp
    if isinstance(inp, str):
        # 处理不同长度的字符串
        if len(inp) == 8:  # YYYYMMDD
            year = int(inp[:4])
            month = int(inp[4:6])
            day = int(inp[6:8])
            hour = minute = 0
        elif len(inp) == 12:  # YYYYMMDDHHMM
            year = int(inp[:4])
            month = int(inp[4:6])
            day = int(inp[6:8])
            hour = int(inp[8:10])
            minute = int(inp[10:12])
        elif len(inp) == 17:  # YYYYMMDDHHMMSSmmm 或类似
            year = int(inp[:4])
            month = int(inp[4:6])
            day = int(inp[6:8])
            hour = int(inp[8:10])
            minute = int(inp[10:12])
        else:
            raise Exception(f"unknown time column from qmt:{inp}")
    else:
        # 如果是datetime
        year = inp.year
        month = inp.month
        day = inp.day
        hour = inp.hour
        minute = inp.minute
    return CTime(year, month, day, hour, minute)


def GetColumnNameFromFieldList(fields: list):
    _dict = {
        "time": DATA_FIELD.FIELD_TIME,
        "date": DATA_FIELD.FIELD_TIME,
        "open": DATA_FIELD.FIELD_OPEN,
        "high": DATA_FIELD.FIELD_HIGH,
        "low": DATA_FIELD.FIELD_LOW,
        "close": DATA_FIELD.FIELD_CLOSE,
        "volume": DATA_FIELD.FIELD_VOLUME,
        "amount": DATA_FIELD.FIELD_TURNOVER,
        "turn": DATA_FIELD.FIELD_TURNRATE,
    }
    return [_dict[x] for x in fields]


class CQMTAPI(CCommonStockApi):
    is_connect = None

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        code = normalize_code(code)
        begin_date = normalize_date(begin_date)
        end_date = normalize_date(end_date)
        super(CQMTAPI, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        # 天级别以上才有详细交易信息
        if kltype_lt_day(self.k_type):
            if not self.is_stock:
                raise Exception("没有获取到数据，注意指数是没有分钟级别数据的！")
            fields = ["time", "open", "high", "low", "close"]
        else:
            fields = ["time", "open", "high", "low", "close", "volume", "amount"]

        period = self.__convert_type()
        dividend_type = self.__convert_autype()

        if not self.end_date:
             self.end_date = ''
        data = xtdata.get_market_data(
            field_list=fields,
            stock_list=[self.code],
            period=period,
            start_time=self.begin_date,
            end_time=self.end_date,
            dividend_type=dividend_type
        )

        if not data or self.code not in data['open'].index:
            raise Exception("没有获取到数据")

        # data is dict of {field: DataFrame}, DataFrame index=stock_list, columns=time_list
        df_open = data['open']
        times = df_open.columns
        for t in times:
            row_data = []
            for field in fields:
                if field == "time":
                    row_data.append(t)
                else:
                    val = data[field].loc[self.code, t]
                    row_data.append(val)
            yield CKLine_Unit(create_item_dict(row_data, GetColumnNameFromFieldList(fields)))

    def SetBasciInfo(self):
        detail = xtdata.get_instrument_detail(self.code)
        if not detail:
            raise Exception(f"无法获取合约信息: {self.code}")
        self.name = detail.get('InstrumentName', '')
        # 判断是否为股票
        inst_type = xtdata.get_instrument_type(self.code)
        self.is_stock = inst_type.get('stock', False)

    @classmethod
    def do_init(cls):
        if not cls.is_connect:
            cls.is_connect = xtdata.connect()

    @classmethod
    def do_close(cls):
        if cls.is_connect:
            xtdata.disconnect()
            cls.is_connect = None

    def __convert_type(self):
        _dict = {
            KL_TYPE.K_DAY: '1d',
            KL_TYPE.K_WEEK: '1w',
            KL_TYPE.K_MON: '1mon',
            KL_TYPE.K_5M: '5m',
            KL_TYPE.K_15M: '15m',
            KL_TYPE.K_30M: '30m',
            KL_TYPE.K_60M: '1h',
        }
        return _dict[self.k_type]

    def __convert_autype(self):
        _dict = {
            AUTYPE.QFQ: 'front',
            AUTYPE.HFQ: 'back',
            AUTYPE.NONE: 'none',
        }
        return _dict[self.autype]