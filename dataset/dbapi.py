﻿import tejapi
import pandas
import numpy
import requests
import json
api_key = ''

# 取得該使用者能存取的所有table的資訊
def get_info():

    tejapi.ApiConfig.api_key = api_key
    info = tejapi.ApiConfig.info()
    print_info = [
                  '使用者名稱：'+str(info.get('user').get('name'))+'('+str(info.get('user').get('shortName'))+')',
                  '使用權限日期：'+str(info.get('user').get('subscritionStartDate'))+'/'+str(info.get('user').get('subscritionEndDate')),
                  '日連線次數狀態：'+str(info.get('todayReqCount'))+'/'+str(info.get('reqDayLimit')),
                  '日查詢資料量狀態：'+str(info.get('todayRows'))+'/'+str(info.get('rowsDayLimit')),
                  '月查詢資料量狀態：'+str(info.get('monthRows'))+'/'+str(info.get('rowsMonthLimit')),
                  ]
        
    print(print_info)
    return info  

# 取得按照索引目錄分層的完整資料表清單
def set_tablelist(tables:list):
        
    api_tables = {}
    for table_name in tables:
        name_list = table_name.split('/')
        market = name_list[0]
        table = name_list[1]
        if api_tables.get(market) is None:
            api_tables[market] = [table]
        else:
            api_tables[market].append(table)

    return api_tables

# 查詢所有的國別的資料庫資訊  
def get_market():

    db_names = ('https://api.tej.com.tw/info/database/list?api_key='
                +api_key)
    response = requests.get(db_names)
    data = json.loads(response.text)['result']
    market_list = data
    return market_list

# 查詢所有資料分類的資料庫    
def get_category():
       
    list_names = ('https://api.tej.com.tw/info/category/list?api_key='
                  +api_key)
    response = requests.get(list_names)
    data = json.loads(response.text)['result']
    category_list = { data[k].get('categoryId'):data[k] for k in data}
    return category_list

# 查詢按國別分類的資料表完整清單   
# 查詢所有資料表資訊內容
def get_tables():

    table_names = ('https://api.tej.com.tw/info/tables/list?api_key='
                   +api_key)
    response = requests.get(table_names)
    data = json.loads(response.text)['result']
    table_list = {}
    for market_code in data.keys():
        this_market_table = {}
        for table_attr in data.get(market_code):
            this_market_table[table_attr['tableCode']] = table_attr  
          
        for table in this_market_table:
            this_table = this_market_table.get(table)
            table_des = this_table.get('description').split('<br />')
            data_freq = 'U'
            for des_col in table_des:
                if '資料頻率' in des_col:
                    data_freq = 'N'
                    if '日' in des_col:
                        data_freq = 'D'
                    if '週' in des_col:
                        data_freq = 'W'
                    if '月' in des_col:
                        data_freq = 'M'
                    if '季' in des_col:
                        data_freq = 'S'
                    if '年' in des_col:
                        data_freq = 'Y'
                    break
            this_table['frequency'] = data_freq
            this_market_table[table] = this_table
        table_list[market_code] = this_market_table
    return table_list

# 根據索引目錄的資料表清單構造，回傳 dataframe方便檢視
def get_tables_info(*, market:str = 'TWN', table_list:list = {}):            
    df = None
    
    # 把所有國別資料表都回傳
    if market is None:            
        for market in table_list:
            if df is None:
                df = pandas.DataFrame.from_dict(table_list.get(market),
                                                orient='index')
            else:
                df = df.append(
                        pandas.DataFrame.from_dict(
                                table_list.get(market),
                                            orient='index'),sort=False)
        return df 
    
    # 僅回傳指定國別
    else:
        df = pandas.DataFrame.from_dict(table_list.get(market),orient='index')
         
    return df.rename(columns={'id':'資料集名稱', 'dbCode':'國別碼',
                              'tableCode':'資料表代碼', 'name':'名稱',
                              'description':'描述', 'enabled':'存取權限',
                              'frequency':'頻率'})


# 根據已知的table名稱，查詢 mapping到別的國家的資料表清單
def get_table_mapping(table_name:str = 'TWN/AIND',*,
                      category_list:list = None):
    market = table_name.split('/')[0]

    if category_list is None:
        category_list = get_category()
    
    for catefory_index in category_list:
        for tableMap in category_list[catefory_index]['subs']:
            for table in tableMap.get('tableMap'):
                if (market in table.get('dbCode') and
                    table_name in table.get('tableId')):
                    return tableMap
                
# 使用tejapi.search_table進行交集或聯集查詢
# 輸入要搜尋的關鍵字，並且產出完整會計科目的中文名稱                    
def search_column(*, market:str = 'TWN', keyword:str = '報酬率',
                    condition:str = 'and', current_market=True):

    tejapi.ApiConfig.api_key = api_key
    k_name_list = keyword.split(' ')
    k_name = k_name_list[0]
    
    # 先查出第一個關鍵字的搜尋結果
    match_dict = { search['tableId']:search for search in tejapi.search_table(k_name)}
    match_outcome = []
    if len(match_dict) > 0:
        # 逐個搜索結果表單檢查
        for match_table in match_dict:
            # 逐欄進行名稱檢查
            for columns in match_dict.get(match_table).get('columns'):
                cname = columns.get('cname')
                # 第一個關鍵字有在裡面
                if k_name in cname:
                    match_table_code = match_table.split('/')[1]
                    match_table_market = match_table.split('/')[0]
                    # 除非current_market=False，否則市場必須完全一致
                    # 但GLOBAL例外，GLOBAL適用別的查詢機制
                    if current_market is False or match_table_market==market:
                        match_outcome.append([cname,
                                              match_dict.get(match_table).get('tableName'),
                                              match_table])

    match_df = pandas.DataFrame(match_outcome,
                                columns=['cname','tableName','tableCode'])
    if condition =='and':
        for i in range(1, len(k_name_list)):
            if len(match_df) > 0:
                for j, row in match_df.iterrows():
                    if k_name_list[i] not in match_df.loc[j,'cname']:
                        match_df.loc[j,'tableCode'] = None
    match_df = match_df.dropna().reset_index(drop=True)
    current_market
    return match_df
    
# 取得指定資料庫的完整資料庫欄位表
def get_table_columns(*, table_name:str = 'TWN/AAPRCDA') -> list:

    tejapi.ApiConfig.api_key = api_key
    columns_name = []
    table_info = tejapi.table_info(table_name)
    pk = table_info.get('primaryKey')
    columns = table_info.get('columns')
    for col in columns:
        if columns.get(col).get('name') not in pk:
            columns_name.append(columns.get(col).get('cname'))
    return columns_name