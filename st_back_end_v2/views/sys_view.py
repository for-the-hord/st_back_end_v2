# -*- coding: utf-8 -*-
"""
@author: jerry
@project: st_back_end_v2
@file: sys_view.py
@time: 23/07/07 14:54
@description: 
"""
# 修改系统名称接口

import json
import os
import configparser

from django.db import connection as conn
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView, DetailView

from st_back_end_v2.utils.utils import create_response, return_msg, rows_as_dict


@method_decorator(csrf_exempt, name='dispatch')
class item_view(DetailView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            with conn.cursor() as cur:
                sql = 'select sys_title from  sys_info limit 1 offset 0'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                data = {'title': '数据填报系统'}
                for row in rows:
                    data = {'title': row['sys_title']}
                response['data'] = data
                return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_update
            return JsonResponse(response, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            name = j.get('title')
            with conn.cursor() as cur:
                sql = 'update sys_info set sys_title=%s where 1=1'
                params = [name]
                cur.execute(sql, params)
                conn.commit()
                return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_update
            return JsonResponse(response, status=500)


# 获取数据库参数
@method_decorator(csrf_exempt, name='dispatch')
class db_item(DetailView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my.cnf')
            config = configparser.ConfigParser()
            config.read(config_path)
            # 通过section和option获取配置文件的值
            host = config.get('client', 'host')
            port = config.get('client', 'port')
            database = config.get('client', 'database')
            user = config.get('client', 'user')
            password = config.get('client', 'password')
            default_character_set = config.get('client', 'default-character-set')
            response['data'] = {'host': host, 'port': port, 'database': database, 'user': user, 'password': password,
                                'default_character_set': default_character_set}
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class update_db_view(UpdateView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            host = j.get('host')
            port = j.get('port')
            database = j.get('database')
            user = j.get('user')
            password = j.get('password')
            default_character_set = j.get('default_character_set')
            # 指定文件路径
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my.cnf')
            # 创建一个configparser对象
            config = configparser.ConfigParser()
            # 读取配置文件
            config.read(config_path)
            # 修改值
            config.set('client', 'host', host)
            config.set('client', 'port', port)
            config.set('client', 'database', database)
            config.set('client', 'user', user)
            config.set('client', 'password', password)
            config.set('client', 'default-character-set',default_character_set)
            # 将修改后的值写入文件
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_update
            return JsonResponse(response, status=500)

# # 获取单个QB信息
# @method_decorator(csrf_exempt, name='dispatch')
# class TemplateItem(DetailView):
#
#     def post(self, request, *args, **kwargs):
#         response_json = create_response()
#         try:
#             j = json.loads(request.body)
#             with connection.cursor() as cur:
#                 sql = 'select i.*, ' \
#                       'fn.id as from_id,fn.name as from_name,fn.ip as from_ip,' \
#                       'tn.id as to_id,tn.name as to_name,tn.ip as to_ip ' \
#                       'from info i ' \
#                       'left join info_node inn on inn.info_id=i.id ' \
#                       'left join node fn on fn.id = inn.from_id ' \
#                       'left join node tn on tn.id = inn.to_id ' \
#                       'where t.id=%s'
#                 params = [j.get('id')]
#                 cur.execute(sql, params)
#                 rows = rows_as_dict(cur)
#                 # 构造返回数据
#                 if len(rows) == 0:
#                     response_json['code'], response_json['msg'] = return_msg.code_100, return_msg.row_none
#                 else:
#                     template = [{'id': it.get('id'),
#                                  'name': it.get('name'),
#                                  'user_name': it.get('user_name'),
#                                  'is_file': it.get('is_file'),
#                                  'equipment_name': it.get('equipment_name'),
#                                  'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
#                                      '%Y-%m-%d %H:%M:%S'),
#                                  'update_date': datetime.fromtimestamp(it.get('update_date')).strftime(
#                                      '%Y-%m-%d %H:%M:%S')
#                                  } for it in rows]
#                     # 使用 defaultdict 创建新的数据结构
#                     records = defaultdict(lambda: {'id': None,
#                                                    'name': None,
#                                                    'user_name': None,
#                                                    'is_file': None,
#                                                    'create_date': 0,
#                                                    'update_date': 0,
#                                                    'equipment_list': []})
#                     for record in template:
#                         # 按照 id 分组，每个分组都是一个字典
#                         group = records[record["id"]]
#                         group["id"] = record["id"]
#                         group["name"] = record["name"]
#                         group["user_name"] = record["user_name"]
#                         group["is_file"] = record["is_file"]
#                         group["create_date"] = record["create_date"]
#                         group["update_date"] = record["update_date"]
#                         # 如果 equipment_id 和 equipment_name 不为 None，则加入到 formwork_list 中
#                         if record["equipment_name"] is not None:
#                             group["equipment_list"].append(
#                                 {"equipment_name": record["equipment_name"]})
#
#                     # 将字典转换为列表
#                     records = list(records.values())
#                     response_json['data'] = records
#         except Exception as e:
#             response_json['code'], response_json['msg'] = return_msg.code_100, return_msg.row_none
#         return JsonResponse(response_json)

# class a(DeleteView):
#     def get(self, request, *args, **kwargs):
#         import random
#         import string
#
#         with conn.cursor() as cur:
#             # 定义 4 种节点类型
#             types = ['type1', 'type2', 'type3', 'type4']
#
#             # 生成 50 条数据
#             for i in range(1, 11):
#                 # 生成随机字符串作为节点名称和 IP 地址
#                 name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
#                 account =  ''.join(random.choices(string.ascii_letters + string.digits, k=10))
#                 ip = '.'.join(str(random.randint(0, 255)) for _ in range(4))
#                 # 从类型列表中随机选择一个节点类型
#                 node_type = random.choice(types)
#                 # 插入数据到表中
#                 cur.execute(f"INSERT INTO seats (id, account,name, ip, type) VALUES ({i},'{account}', '{name}', '{ip}', '{node_type}')")
#
#         return HttpResponse({'ok'})
#
# class b(DetailView):
#     def get(self, request, *args, **kwargs):
#         with conn.cursor() as cur:
#             # 生成包裹 ID 列表
#             package_ids = [str(i) for i in range(1, 11)]
#
#             # 生成地点 ID 列表
#             location_ids = [str(i) for i in range(1, 11)]
#
#             # 生成 1000 条数据
#             data = []
#             for i in range(50):
#                 from_id = random.choice(location_ids)
#                 to_id = random.choice(location_ids)
#                 while to_id == from_id:
#                     to_id = random.choice(location_ids)
#
#                 info_id = random.choice(package_ids)
#
#                 from_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30))
#
#                 to_date = from_date + datetime.timedelta(days=random.randint(1, 10))
#                 from_date =time.mktime(from_date.timetuple())
#                 to_date = time.mktime(to_date.timetuple())
#
#                 # 添加数据到列表
#                 data.append((create_uuid(), from_id, to_id, info_id, from_date, to_date))
#             sql = "INSERT INTO info_seats (id,from_id, to_id, info_id, from_date, to_date) VALUES (%s,%s, %s, %s, %s, %s)"
#             # 使用批量插入将数据插入到数据库表中
#             cur.executemany(sql,data)
#         return HttpResponse({'ok'})
