# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end
@file: field_view.py
@time: 2023/5/28 18:19
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
from django.http import JsonResponse, HttpRequest,Http404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.templatetags.static import static

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json


# def check_token(view_func):
#     def wrapped(request, *args, **kwargs):
#         # 获取前端传过来的token
#         response = create_return_json()
#         token = request.headers.get('AUTHORIZATION', '').split(' ')
#         if len(token) > 1:
#             token = token[1]
#         else:
#             return JsonResponse({'error': 'Token error'}, status=401)
#         try:
#             # 解码token
#             payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
#
#             # 根据payload中的user_id进行用户认证
#             user_id = payload['user_id']
#             with connection.cursor() as cur:
#                 sql = 'select name from user u ' \
#                       'where u.id=%s'
#                 params = [user_id]
#                 cur.execute(sql, params)
#                 rows = rows_as_dict(cur)
#             user = User.objects.get(id=user_id)
#
#             # 将user添加到请求中，方便视图函数中使用
#             request.user = user
#
#             return view_func(request, *args, **kwargs)
#
#         except jwt.ExpiredSignatureError:
#             # token过期
#             response['code'], response['msg'] = return_msg.S401, return_msg.token_expired
#             return JsonResponse(response, status=401)
#
#         except jwt.InvalidSignatureError:
#             # token无效
#             response['code'], response['msg'] = return_msg.S401, return_msg.token_invalid
#             return JsonResponse(response, status=401)
#
#         except User.DoesNotExist:
#             # 用户不存在
#             response['code'], response['msg'] = return_msg.S401, return_msg.no_user
#             return JsonResponse(response, status=401)
#
#     return wrapped

# 添加字段接口

@method_decorator(csrf_exempt, name='dispatch')
class list_view(ListView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            id = j.get('template_id')  # 模板id
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'select tf.field_id,tf.in_box,tf.label,tf.type ' \
                      'from template_fields tf ' \
                      'where template_id=%s'
                cur.execute(sql, [id])
                rows = rows_as_dict(cur)
                response['data'] = rows
            return JsonResponse(response, status=200)
        except Exception as e:
            print(e)
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


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
            id = j.get('template_id')  # 模板id
            in_box = j.get('box')  # 字段显示区域
            label = j.get('name')  # 字段组件标签
            component_type = j.get('component_type')  # 字段类型
            options = j.get('options')  # 字段选项
            component = component_to_json(type=component_type, options=options,label = label)  # 字段组件json
            params=[id, component['key'], in_box, json.dumps(component), label, component_type]

            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'insert into template_fields (template_id, field_id, in_box,component, label,type) ' \
                      'values (%s,%s,%s,%s,%s,%s)'
                cur.execute(sql, params)
                conn.commit()
                response['data'] = {'template_id':id,'field_id':component['key'],'name':label,'component_type':component_type,'box':in_box}
            return JsonResponse(response, status=200)

        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)

# 删除字段接口
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DeleteView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response,status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            tempalate_id = j.get('template_id')
            field_id = j.get('field_id')

            with conn.cursor() as cur:
                sql = 'delete from template_fields where template_id=%s and field_id = %s'
                params = [tempalate_id,field_id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response,status=200)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response,status==500)
