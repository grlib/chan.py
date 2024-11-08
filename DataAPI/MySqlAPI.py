import pymysql
from pymysql import Error
from datetime import datetime
from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit
from .CommonStockAPI import CCommonStockApi

from config import config 

class MySQL_API(CCommonStockApi):
    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=None):
        self.code = code
        self.k_type = k_type
        self.begin_date = begin_date
        self.end_date = end_date
        self.autype = autype
        
        self.columns = [
            'date',
            'closingPrice',    
            'maxPrice',    
            'minPrice',    
            'openingPrice',    
            'changeRate',    
        ]  # 每一列字段
        super(MySQL_API, self).__init__(code, k_type, begin_date, end_date, autype)
        self.db_connection = None

    def connect_to_db(self):
        try:
            db_host = config['database']['host']
            db_name = config['database']['name']
            db_port = config['database']['port']
            db_user = config['database']['user']
            db_password = config['database']['password']
            self.db_connection = pymysql.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                cursorclass=pymysql.cursors.DictCursor  # 使用字典游标
            )
            self.cursor = self.db_connection.cursor()
        except Error as e:
            raise CChanException(f"Error connecting to MySQL database: {e}", ErrCode.DB_CONNECTION_ERROR)

    def disconnect_from_db(self):
        if self.db_connection:
            self.db_connection.close()

    def get_all_stocks(self):
        if self.db_connection is None:
            self.connect_to_db()
        try:
            query = f"SELECT * FROM core_stockmain"
            
            self.cursor.execute(query)
            return  self.cursor.fetchall()
        except Error as e:
            raise CChanException(f"Error fetching data from MySQL: {e}", ErrCode.DB_QUERY_ERROR)
        finally:
            self.disconnect_from_db()
    def get_kl_data(self):
        if self.db_connection is None:
            self.connect_to_db()
        try:
            query = f"SELECT {', '.join(self.columns)} FROM core_dayline WHERE code = %s"
            params = (self.code,)
            
            if self.begin_date is not None:
                query += " AND `date` >= %s"
                params += (self.begin_date,)
            
            if self.end_date is not None:
                query += " AND `date` <= %s"
                params += (self.end_date,)
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            for row in results:
                time_obj = row['date']
                row['time'] = CTime(time_obj.year, time_obj.month, time_obj.day, 0, 0)
                
                kl_dict = {
                    DATA_FIELD.FIELD_TIME: row['time'],
                    DATA_FIELD.FIELD_CLOSE: float(row['closingPrice']),
                    DATA_FIELD.FIELD_OPEN: float(row['openingPrice']),
                    DATA_FIELD.FIELD_HIGH: float(row['maxPrice']),
                    DATA_FIELD.FIELD_LOW: float(row['minPrice']),
                }
                yield CKLine_Unit(kl_dict)
        except Error as e:
            raise CChanException(f"Error fetching data from MySQL: {e}", ErrCode.DB_QUERY_ERROR)
        finally:
            self.disconnect_from_db()

    def SetBasciInfo(self):
        pass

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass

# Helper function to create item dictionary
def create_item_dict(data, column_name):
    print(data, column_name)
    print(len(data))
    for i in range(len(data)):
        data[i] = parse_time_column(data[i]) if column_name[i] == DATA_FIELD.FIELD_TIME else str2float(data[i])
    return dict(zip(column_name, data))

# Helper function to parse time column
def parse_time_column(inp):
    # Your existing parse_time_column function here
    pass