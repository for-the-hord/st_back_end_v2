# -*- coding: utf-8 -*-
"""
@author: world
@project: st_back_end
@file: field_view.py
@time: 2023/5/28 18:19
@description:
"""

import json
from collections import defaultdict

from django.db import connection as conn
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, DeleteView

from ..tools import  return_msg, create_return_json, rows_as_dict, component_to_json




# 获取模板字段列表
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
            id = j.get('id')  # 模板id
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                sql = 'select tf.field_id,tf.in_box,tf.label as name,tf.type as component_type ' \
                      'from template_fields tf ' \
                      'where template_id=%s'
                cur.execute(sql, [id])
                rows = rows_as_dict(cur)
                result = defaultdict(list)
                for row in rows:
                    result[row['in_box']].append({k: v for k, v in row.items() if k != 'in_box'})

                response['data'] = dict(result)
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
            return JsonResponse(response,status=500)
