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
                sql = "select id, name, create_date, update_date from  template limit %s offset %s"
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = []
                for row in rows:
                    record = {'id': row['id'], 'name': row['name'],
                              'create_date': datetime.fromtimestamp(row.get('create_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'),
                              'update_date': datetime.fromtimestamp(row.get('update_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S')}
                    data.append(record)
                response['data'] = data
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse(response, status=500)


# 获取单个模板信息(填报数据时候，选择模板调用)
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


@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_by_unit_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)

            with conn.cursor() as cur:
                if 'unit_name' in j:
                    unit_name = j.get('unit_name')
                    params = [unit_name]
                    sql = 'select distinct t.id as id,t.name  ' \
                          'from template t ' \
                          'left join unit_template ut on t.id = ut.template_id ' \
                          'where ut.unit_name=%s'
                    cur.execute(sql, params)
                else:
                    sql = 'select distinct t.id as id,t.name  ' \
                          'from template t '
                    cur.execute(sql)

                rows = rows_as_dict(cur)
                response['data'] = rows
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse(response, status=500)


# 添加一个模板接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            # 从请求的 body 中获取 JSON 数据
            json_data = request.body.decode('utf-8')
            j = json.loads(json_data)
            id = create_uuid()  # 模板id
            label = j.get('label')  # 模板名称
            equipment_name = j.get('equipment_name')
            create_date = int(datetime.now().timestamp())
            is_file = j.get('is_file')
            with conn.cursor() as cur:
                sql = 'insert into template (id,name,is_file,create_date,update_date) ' \
                      'values(%s,%s,%s,%s,%s)'
                params = [id, label, is_file, create_date, create_date]
                cur.execute(sql, params)
                params = [[id, it] for it in equipment_name]
                sql = 'insert into tp_equipment (template_id,equipment_name) values (%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
                response['data'] = {'id': id}
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        if request.method == 'POST':
            try:
                # 从请求的 body 中获取 JSON 数据
                json_data = request.body.decode('utf-8')
                j = json.loads(json_data)
                id = j.get('template_id')  # 模板id

                box = j.get('box')  # 字段显示区域

                params = []
                for in_box in box:
                    componets = j.get(in_box, [])
                    for it in componets:
                        label = it.get('name')  # 字段组件标签
                        component_type = it.get('component_type')  # 字段类型
                        options = it.get('options')  # 字段选项
                        component = component_to_json(type=component_type, options=options, label=label)  # 字段组件json
                        params.append((id, component['key'], in_box, json.dumps(component), label, component_type))

                # 执行原生 SQL 查询
                with conn.cursor() as cur:
                    sql = 'insert into template_fields (template_id, field_id, in_box,component, label,type) ' \
                          'values (%s,%s,%s,%s,%s,%s)'
                    cur.executemany(sql, params)
                    conn.commit()
                return JsonResponse(response, status=200)

            except Exception as e:
                conn.rollback()
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Invalid request method'}, status=405)

# 与load_template数据格式不同
# preview数据格式是ngform格式，不做box的区分
@method_decorator(csrf_exempt, name='dispatch')
class preview_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,te.equipment_name ' \
                      'from template t ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = {'id': rows[0]['id'], 'name': rows[0]['name'], 'equipment_name': []}
                for row in rows:
                    data['equipment_name'].append(row['equipment_name'])

                sql = 'select tf.in_box,tf.component ' \
                      'from template t ' \
                      'left join template_fields tf on tf.template_id =t.id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 动态table的ngform格式
                table = {
                    "type": "batch",
                    "label": "动态表格",
                    "list": [],
                    "options": {
                        "scrollY": 0,
                        "disabled": False,
                        "hidden": False,
                        "showLabel": False,
                        "hideSequence": False,
                        "labelWidth": "100",
                        "labelPosition": "left",
                        "customStyle": "",
                        "customClass": "",
                        "showItem": [
                        ],
                        "colWidth": {},
                        "width": "100%",
                        "dynamicHide": False,
                        "dynamicHideValue": ""
                    },
                    "model": "data_box",
                    "key": "data_box"
                }
                # 通过不同的区域来分组 每个组件
                for row in rows:
                    # 先取出组件数据
                    try:
                        component = json.loads(row['component'])
                    except:
                        component = None
                    if component is None:
                        continue
                    # 判断box的区域位置
                    box_name = row['in_box']
                    if box_name not in data:
                        data[box_name] = {'list': [],'config': {
                            'labelPosition': "left",
                            'labelWidth': 100,
                            'size': "mini",
                            'outputHidden': True,
                            'hideRequiredMark': False,
                            'syncLabelRequired': False,
                            'customStyle': "",
                        }}
                    # data_box是动态table格式，需要特殊处理
                    if box_name == 'data_box' :
                        table['list'].append(component)
                    else:
                        data[box_name]['list'].append(component)
                data['data_box']['list'].append(table)
                response['data'] = data
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)

# # 与preview_template数据格式不同
# # load数据格式是做box的区分,每个box的内容是ngform格式
# @method_decorator(csrf_exempt, name='dispatch')
# class TemplateLoadView(DetailView):
#     def post(self, request, *args, **kwargs):
#         response = create_return_json()
#         try:
#             j = json.loads(request.body)
#             id = j.get('id')
#             with conn.cursor() as cur:
#
#                 sql = 'select tf.in_box,tf.component ' \
#                       'from template t ' \
#                       'left join template_fields tf on tf.template_id =t.id ' \
#                       'where t.id=%s'
#                 params = [id]
#                 cur.execute(sql, params)
#                 rows = rows_as_dict(cur)
#                 data = {}
#                 # 通过不同的区域来分组 每个组件
#                 for row in rows:
#                     box_name = row['in_box']
#                     if box_name not in data:
#                         data[box_name] = {'list': [],'config': {
#                             'labelPosition': "left",
#                             'labelWidth': 100,
#                             'size': "mini",
#                             'outputHidden': True,
#                             'hideRequiredMark': False,
#                             'syncLabelRequired': False,
#                             'customStyle': "",
#                         }}
#                     data[box_name]['list'].append(json.loads(row['component']))
#                 response['data'] = data
#         except Exception as e:
#             response['code'], response['msg'] = return_msg.S100, return_msg.row_none
#         return JsonResponse(response)
#

@method_decorator(csrf_exempt, name='dispatch')
class delete_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with conn.cursor() as cur:
                sql = 'delete from template  where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from unit_template where template_id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from tp_equipment where template_id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                sql = 'delete from template_fields where template_id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                conn.commit()

        except self.model.DoesNotExist:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_delete

        return JsonResponse(response)

# 导出模板文件，数据格式跟priview_template数据一致，
# 加密生成rc文件
@method_decorator(csrf_exempt, name='dispatch')
class export_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,te.equipment_name ' \
                      'from template t ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = {'id': rows[0]['id'], 'name': rows[0]['name'], 'equipment_name': []}
                for row in rows:
                    data['equipment_name'].append(row['equipment_name'])

                sql = 'select tf.in_box,tf.component ' \
                      'from template t ' \
                      'left join template_fields tf on tf.template_id =t.id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 动态table的ngform格式
                table = {
                    "type": "batch",
                    "label": "动态表格",
                    "list": [],
                    "options": {
                        "scrollY": 0,
                        "disabled": False,
                        "hidden": False,
                        "showLabel": False,
                        "hideSequence": False,
                        "labelWidth": "100",
                        "labelPosition": "left",
                        "customStyle": "",
                        "customClass": "",
                        "showItem": [
                        ],
                        "colWidth": {},
                        "width": "100%",
                        "dynamicHide": False,
                        "dynamicHideValue": ""
                    },
                    "model": "data_box",
                    "key": "data_box"
                }
                # 通过不同的区域来分组 每个组件
                for row in rows:
                    # 先取出组件数据
                    try:
                        component = json.loads(row['component'])
                    except:
                        component = None
                    if component is None:
                        continue
                    # 判断box的区域位置
                    box_name = row['in_box']
                    if box_name not in data:
                        data[box_name] = {'list': [], 'config': {
                            'labelPosition': "left",
                            'labelWidth': 100,
                            'size': "mini",
                            'outputHidden': True,
                            'hideRequiredMark': False,
                            'syncLabelRequired': False,
                            'customStyle': "",
                        }}
                    # data_box是动态table格式，需要特殊处理
                    if box_name == 'data_box':
                        table['list'].append(component)
                    else:
                        data[box_name]['list'].append(component)
                data['data_box']['list'].append(table)

                cipher_suite = Fernet(FERNET_KEY)

                # 对数据进行加密
                json_str = json.dumps(data)
                cipher_text = cipher_suite.encrypt(json_str.encode())

                # 创建一个 BytesIO 对象并写入加密后的数据
                file = io.BytesIO()
                file.write(cipher_text)
                file.seek(0)

                file_name = f'{data["name"]}.rc'
                # 创建一个 HttpResponse 对象，并设置 Content-Disposition 头，使其作为文件下载

                response = FileResponse(file)
                response['Access-Control-Expose-Headers']='*'
                response['Content-Type']='application/octet-stream'
                #response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}'
                return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)

# 导入模板文件
@method_decorator(csrf_exempt, name='dispatch')
class import_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            file = request.FILES.get('file')
            file_binary = file.read()
            # 解密数据
            cipher_suite = Fernet(FERNET_KEY)
            json_str = cipher_suite.decrypt(file_binary).decode()
            try:
                response['data'] = json.loads(json_str)
            except:
                response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)
