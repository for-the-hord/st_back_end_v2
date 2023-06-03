# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: unit_view.py
@time: 2023/6/2 13:36
@description: 
"""
# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: template_view.py
@time: 2023/4/7 9:21
@description:
"""
import json
import jwt
from datetime import datetime
from collections import defaultdict
import os
import io
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from cryptography.fernet import Fernet
import pandas as pd
from urllib.parse import quote

from django.http import HttpResponse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest,FileResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.templatetags.static import static

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json,FERNET_KEY

# 获取所有单位列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', {})
            where_clause = '' if len(condition) == 0 else 'where ' + " AND ".join(
                [f"{key} LIKE %s" for key in condition.keys()])
            where_values = ["%" + value + "%" for value in condition.values()]

            with conn.cursor() as cur:
                params = where_values
                sql = f'select count(*) as count,n.name as unit_name from unit n {where_clause}'
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select n.id, n.unit_name,' \
                      't.id as template_id,t.name as template_name ' \
                      f'from (select id,name as unit_name from unit {where_clause} order by id limit %s offset %s) n ' \
                      'left join unit_template ut on n.unit_name=ut.unit_name ' \
                      'left join template t on ut.template_id=t.id '
                params = where_values + [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data_list = [
                    {'id': it.get('id'), 'name': it.get('unit_name'),
                     'formwork_id': it.get('template_id'), 'formwork_name': it.get('template_name')
                     } for it in rows]

            # 使用 defaultdict 创建新的数据结构
            records = defaultdict(lambda: {"id": None, "name": None, "formwork_list": []})
            for record in data_list:
                # 按照 id 分组，每个分组都是一个字典
                group = records[record["id"]]
                group["id"] = record["id"]
                group["name"] = record["name"]
                # 如果 formwork_id 和 formwork_name 不为 None，则加入到 formwork_list 中
                if record["formwork_id"] is not None and record["formwork_name"] is not None:
                    group["formwork_list"].append(
                        {"formwork_id": record["formwork_id"], "formwork_name": record["formwork_name"]})

            # 将字典转换为列表
            records = list(records.values())
            # 构造返回数据
            response['data'] = {'records': records, 'title': None,
                                     'total': count}
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response)


# 获取单个单位信息
@method_decorator(csrf_exempt, name='dispatch')
class item(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            with conn.cursor() as cur:
                sql = 'select t.id as template_id,t.is_file,t.name as template_name,' \
                      'n.id,' \
                      'n.name  ' \
                      'from unit n ' \
                      'left join template t on n.name = t.name ' \
                      'where n.id=%s'
                params = [j.get('id')]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.row_none
                else:
                    response['data'] = {'id': rows[0].get('id'), 'name': rows[0].get('name'),
                                             'formwork_id':rows[0].get('template_id'),
                                             'formwork_name': rows[0].get('template_name')
                                             }
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)


# 添加一个单位接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            id = create_uuid()
            template_ids = j.get('template_ids')
            with conn.cursor() as cur:
                sql ='select count(*) as count from unit u where u.name=%s'
                params = [name]
                cur.execute(sql,params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                if count !=0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.exist_unit
                    return JsonResponse(response)
                sql = 'insert into unit (id,name) values(%s,%s)'
                params = [id, name]
                cur.execute(sql, params)
                sql = 'insert into unit_template (unit_name,template_id) values (%s,%s)'
                params = [[id, it] for it in template_ids]
                cur.executemany(sql, params)
                conn.commit()
                response['data'] = {'id': id}
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response)


# 修改一个单位接口
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            id = j.get('id')
            template_ids = j.get('template_ids')
            with conn.cursor() as cur:
                sql ='select count(*) as count from unit u where u.name=%s and u.id<>%s'
                params = [name,id]
                cur.execute(sql,params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                if count !=0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.exist_unit
                    return JsonResponse(response)
                sql = 'delete from unit_template  where unit_name=%s'
                params = [name]
                cur.execute(sql, params)
                sql = 'insert into unit_template (unit_name,template_id) values (%s,%s)'
                params = [[name, it] for it in template_ids]
                cur.executemany(sql, params)
                conn.commit()

        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response)


# 删除一个或者多个单位接口
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DeleteView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with conn.cursor() as cur:
                place_holders = ','.join(['%s' for _ in range(len(ids))])
                sql = f"SELECT name FROM unit WHERE id IN ({place_holders})"
                cur.execute(sql,tuple(ids))
                rows = rows_as_dict(cur)
                sql = 'delete from unit  where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from unit_template  where unit_name=%s'
                params =[[it['name']] for it in rows]
                cur.executemany(sql, params)
                conn.commit()
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_delete
        return JsonResponse(response)