# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: user_view.py
@time: 2023/6/2 13:45
@description:
"""

import json

from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView

from st_back_end_v2.utils.utils import create_uuid, return_msg, create_response, rows_as_dict


# 获取用户列表
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response,status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition', {})

            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = f'select count(*) as count from user '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                # 这里 用户和角色是一对一关系可以这样分页
                # 如果是 一对多，需要先搜索出分页的用户表，再做角色关联查询
                sql = "select u.id,u.name,u.account,u.unit_name,r.id as role_id,r.name as role_name  " \
                      "from user u " \
                      "left join user_role ur on u.id = ur.user_id " \
                      "left join role r on ur.role_id = r.id " \
                      "limit %s offset %s"
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                response['data'] = {'records': rows, 'title': None, 'total': count}
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response)


# 添加一个管理员用户
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response,status=400)
        try:
            name = j.get('name')
            account = j.get('account')
            password = j.get('password')
            unit_name = j.get('unit_name')
            role_id = j.get('role_id')
            id = create_uuid()

            with conn.cursor() as cur:
                sql = 'insert into user (id, name, password, unit_name, account) values(%s,%s,%s,%s,%s)'
                params = [id, name, password, unit_name, account]
                cur.execute(sql, params)
                sql  = 'insert into user_role (user_id, role_id) values (%s,%s)'
                params = [id,role_id]
                cur.execute(sql,params)
                conn.commit()
                response['data'] = {'password': '123456'}
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
        return JsonResponse(response)


# 修改用户
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_response()

        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')  # 用户id
            password = j.get('password')
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'update user set password = %s where id = %s'
                cur.execute(sql, [password,id])
                conn.commit()
            return JsonResponse(response, status=200)

        except:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 删除用户
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')  # 用户id

            with conn.cursor() as cur:
                sql = 'delete from user where id=%s'
                params = [id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)

# 重置密码
@method_decorator(csrf_exempt, name='dispatch')
class reset_view(CreateView):

    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')  # 用户id

            with conn.cursor() as cur:
                sql = 'update  user  set password="123456" where id=%s'
                params = [id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)
