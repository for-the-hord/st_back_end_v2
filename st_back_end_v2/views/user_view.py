# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: user_view.py
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
from django.http import JsonResponse, HttpRequest, FileResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.templatetags.static import static

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json, FERNET_KEY


# 获取用户列表
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            # 从请求的 body 中获取 JSON 数据
            json_data = request.body.decode('utf-8')
            j = json.loads(json_data)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', {})

            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                # 这里 用户和角色是一对一关系可以这样分页
                # 如果是 一对多，需要先搜索出分页的用户表，再做角色关联查询
                sql = "select u.id,u.name,u.account,u.unit_name,r.id,r.name  " \
                      "from user u " \
                      "left join user_role ur on u.id = ur.user_id " \
                      "left join role r on ur.role_id = r.id " \
                      "limit %s offset %s"
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                response['data'] = rows
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error
            return JsonResponse(response)


# 添加一个管理员用户
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            account = j.get('account')
            password = '123456'
            unit_name = j.get('unit_name')
            role = j.get('role_id')
            id = create_uuid()

            with conn.cursor() as cur:
                sql = 'insert into user (id, name, password, unit_name, account) values(%s,%s,%s,%s,%s)'
                params = [id, name, password, unit_name, account]
                cur.execute(sql, params)
                conn.commit()
                response['data'] = {'password': '123456'}
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response)


# 修改用户
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()

        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')  # 用户id
            role = j.get('role')  # 字段显示区域
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'update user set name = %s where id = %s'
                cur.execute(sql, [id])
                sql = 'delete from user_role where user_id=%s'
                cur.execute(sql, [id])
                sql = 'insert into user_role (user_id, role_id) values (%s,%s)'
                params = [[id, it] for it in role]
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response, status=200)

        except:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 删除用户
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')  # 用户id

            with conn.cursor() as cur:
                sql = 'delete from user where id=%s'
                params = [id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)
