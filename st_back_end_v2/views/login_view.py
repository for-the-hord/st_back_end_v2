# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: view.py
@time: 2023/3/30 11:30
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

from django.http import HttpResponse
import pandas as pd

from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest, Http404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.templatetags.static import static

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, list_to_tree


# 登录
class login(View):

    def post(self, request: HttpRequest):
        response = create_return_json()

        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)

        if j is not None:
            account = str(j.get('account', None)).replace(' ', '')
            password = str(j.get('password', None)).replace(' ', '')
            with conn.cursor() as cur:
                sql = 'select u.id,n.name as unit_name,u.name ,s.sys_title ' \
                      'from user u left join unit n on u.unit_name=n.name ' \
                      'left join sys_info s on 1=1 ' \
                      'where u.account= %s and u.password=%s'
                params = [account, password]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
            if len(rows) != 0:
                user = rows[0]
                payload = {'user_id': user.get('id')}
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                response['msg'], response['data'] = '登陆成功！', {'token_id': token,
                                                              'user_name': user.get('name'),
                                                              'user_id': user.get('id'),
                                                              'unit_name': user.get('unit_name'),
                                                              'sys_title': user.get('sys_title')}
                return JsonResponse(response, status=200)
            else:
                response['msg'], response['code'] = '账户或密码错误！', return_msg.S100
                return JsonResponse(response ,status=400)
        else:
            return JsonResponse(response,status=400)

# 获取单位列表
@method_decorator(csrf_exempt, name='dispatch')
class Login_unit_list_view(View):
    def post(self, request: HttpRequest):
        response = create_return_json()
        with conn.cursor() as cur:
            sql = 'select n.id,n.name from  unit n '
            cur.execute(sql)
            rows = rows_as_dict(cur)
            response['data'] = rows
        return JsonResponse(response)

# 登录
class login_without(View):
    def post(self, request: HttpRequest):
        response = create_return_json()
        if (get_json := json.loads(request.body)) is not None:
            unit_name = get_json.get('unit_name', None)
            report_date = get_json.get('date')
            response['data'] = {'unit_name': unit_name}
        else:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error
        return JsonResponse(response)


# 修改系统名称接口
@method_decorator(csrf_exempt, name='dispatch')
class sys_info_update_view(UpdateView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            name = j.get('sys_title')
            with conn.cursor() as cur:
                sql = 'update sys_info set sys_title=%s'
                params = [name]
                cur.execute(sql, params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response)



# 获取用户菜单
@method_decorator(csrf_exempt, name='dispatch')
class get_router(UpdateView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            user_id = j.get('user_id')
            with conn.cursor() as cur:
                sql = 'select m.id,m.title,m.path,m.parent_id from module m ' \
                      'left join role_module rm on m.id = rm.module_id ' \
                      'left join role r on rm.role_id = r.id ' \
                      'left join user_role ur on r.id = ur.role_id ' \
                      'where ur.user_id=%s'
                params = [user_id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = list_to_tree(rows,id_key='id',parent_key='parent_id',parent_value='0')
                response['data'] = data
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response)

