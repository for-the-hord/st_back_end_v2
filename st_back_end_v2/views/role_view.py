# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: role_view.py
@time: 2023/6/2 13:45
@description: 
"""
import json
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict


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
            return JsonResponse(response, status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            limit_clause = '' if page_size == 0 and page_index == 0 else 'limit %s offset %s'
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'select count(*) as count from role '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                sql = f'select r.id,r.name from role r {limit_clause} '
                params = [page_size, (page_index - 1) * page_size] \
                    if limit_clause != '' else []
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                response['data'] = {'records': rows, 'title': None, 'total': count}
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
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:

                sql = 'select r.id,r.name,' \
                      'm.id as module_id,m.parent_id, m.title, m.type, m.path, m.icon '\
                      'from role r ' \
                      'left join role_module rm on r.id = rm.role_id ' \
                      'left join module m on rm.module_id = m.id ' \
                      'where r.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = {'id':rows[0]['id'],'name':rows[0]['name'],'menu':[]}
                data['menu'] = [it['module_id'] for it in rows]
                response['data'] = data
                return JsonResponse(response, status=200)
        except Exception as e:
            print(e)
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 新建角色接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
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
            JsonResponse(response, status=500)


# 修改角色接口
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
            id = j.get('id')  # 模板id
            name = j.get('name')  # 字段显示区域
            module = j.get('module')
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'update role set name = %s where id = %s'
                cur.execute(sql, [name,id])
                sql = 'delete from role_module where role_id=%s'
                cur.execute(sql, [id])
                sql = 'insert into role_module (role_id, module_id) values (%s,%s)'
                params = [[id, it] for it in module]
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response, status=200)

        except:
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
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'delete from role  where id=%s'
                cur.execute(sql, [id])
                sql = 'delete from role_module where role_id=%s'
                cur.execute(sql, [id])
                conn.commit()
            return JsonResponse(response)
        except:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)

