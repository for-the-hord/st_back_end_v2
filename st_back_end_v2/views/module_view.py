# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end_v2
@file: module_view.py
@time: 2023/6/3 20:54
@description: 
"""
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from ..tools import   create_return_json, rows_as_dict, list_to_tree

# 获取系统菜单模块列表
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = "select m.id,m.parent_id,m.title as label from module m"
                cur.execute(sql)
                rows = rows_as_dict(cur)
                data = list_to_tree(rows, id_key='id',parent_value='0', parent_key='parent_id')
                response['data'] = data
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse(response, status=500)
