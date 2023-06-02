# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: role_view.py
@time: 2023/6/2 13:45
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

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json, FERNET_KEY, \
    list_to_tree


# 获取角色列表
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', {})

            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = "select u.id,u.name,m.id,m.parent_id,m.parent_id,m.path,m.title " \
                      "from (select r.id,r.name from role r limit %s offset %s) u " \
                      "left join role_module rm on u.id=rm.role_id " \
                      "left join  module m on rm.module_id = m.id "
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                rows = list_to_tree(rows,id_key='id',parent_key='parent_id')

                response['data'] = rows
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse(response, status=500)


# 获取单个角色
@method_decorator(csrf_exempt, name='dispatch')
class item(DetailView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,' \
                      't.create_date as create_date,' \
                      't.update_date as update_date,' \
                      'te.equipment_name,' \
                      'ut.unit_name ' \
                      'from template t ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'left join unit_template ut on t.id = ut.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.row_none
                else:
                    data = {
                        'id': id,
                        'name': rows[0]['name'],
                        'unit_name': [],
                        'equipment_name': []
                    }
                    for row in rows:
                        unit_name = row['unit_name']
                        equipment_name = row['equipment_name']

                        if unit_name is not None:
                            data['unit_name'].append(unit_name)

                        if equipment_name is not None:
                            data['equipment_name'].append(equipment_name)

                    response['data'] = data
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)

# 新建角色接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            id = create_uuid()  # 模板id
            name = j.get('name')  # 模板名称
            module = j.get('module')
            with conn.cursor() as cur:
                sql = 'insert into role (id,name) ' \
                      'values(%s,%s)'
                params = [id, name]
                cur.execute(sql, params)
                params = [[id, it] for it in module]
                sql = 'insert into role_module (role_id,module_id) values (%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
                response['data'] = {'id': id}
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
            JsonResponse(response,status=500)


# 修改角色接口
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()

        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            id = j.get('id')  # 模板id
            name = j.get('name')  # 字段显示区域
            module = j.get('module')
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'update role set name = %s where id = %s'
                cur.execute(sql,[id,name])
                sql = 'delete from role_module where role_id=%s'
                cur.execute(sql, [id])
                sql = 'insert into role_module (role_id, module_id) values (%s,%s)'
                params = [[id,it] for it in module]
                cur.executemany(sql,params)
                conn.commit()
            return JsonResponse(response, status=200)

        except :
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 删除角色
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'delete from role  where id=%s'
                cur.execute(sql, [id])
                sql = 'delete from role_module where role_id=%s'
                cur.execute(sql, [id])
                conn.commit()
            return JsonResponse(response)
        except :
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)
