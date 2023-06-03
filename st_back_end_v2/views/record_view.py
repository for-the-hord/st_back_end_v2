# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: record_view.py
@time: 2023/4/7 9:23
@description:
"""
import collections
import json
import jwt
from datetime import datetime
from collections import defaultdict
import os
import io
import openpyxl
from cryptography.fernet import Fernet
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment

from django.http import HttpResponse, FileResponse
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

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json, FERNET_KEY


# 获取所有数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = j.get('condition')
            # {'unit_name':[],'formwork_id','equipment_name':[],'data_info':''}
            params = []

            def dict_to_query_str(d: dict):
                def convert_key(orginal):
                    if orginal == 'unit_name':
                        k = 'n.name'
                    elif orginal == 'formwork_id':
                        k = 't.id'
                    elif orginal == 'equipment_name':
                        k = 'te.equipment_name'
                    elif orginal == 'data_info':
                        k = 'd.data'
                    else:
                        k = None
                    return k

                conditions = []
                for key, value in d.items():
                    if k := convert_key(key):
                        if key == 'data_info':
                            if value:
                                conditions.append(f"{k} like  %s ")
                                params.append(f'%{value}%')
                        else:
                            if value:  # 如果数组不为空
                                conditions.append(f"{k} IN ({','.join(['%s' for i in range(len(value))])})")
                                params.extend(value)
                return ' and '.join(conditions)

            where_clause = '' if (where_sql := dict_to_query_str(condition)) == '' else 'where ' + where_sql
            with conn.cursor() as cur:
                sql = 'select count(distinct r.id) as count ' \
                      'from record r ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} ' \
                      'order by t.id  '
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,' \
                      't.is_file,t.name as template_name,' \
                      'r.unit_name,' \
                      'r.equipment_name ' \
                      'from record r ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te ' \
                      'on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} ' \
                      'order by t.update_date desc ' \
                      'limit %s offset %s'
                params += [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = []
                for row in rows:
                    record = {'id':row['id'],'name':row['name'],'template_id':row['template_id'],
                              'create_date': datetime.fromtimestamp(row.get('create_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'),
                              'update_date':datetime.fromtimestamp(row.get('update_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'),'unit_name':row['unit_name'],'equipment_name':row['equipment_name']}
                    data.append(record)

                # 构造返回数据
                response['data'] = {'records': data, 'title': None,'total': count}
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error

        return JsonResponse(response)


# 获取单个数据信息
@method_decorator(csrf_exempt, name='dispatch')
class item(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.unit_name,r.equipment_name,' \
                      'rf.field_id,rf.field_value,rf.serial_no ' \
                      'from record r ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'where r.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.row_none
                else:
                    response['data'] = {'id': rows[0].get('id'),
                                        'name': rows[0].get('name'),
                                        'template_id': rows[0].get('template_id'),
                                        'records': [],
                                        'equipment_name': rows[0]['equipment_name'],
                                        'unit_name': rows[0].get('unit_name'),
                                        'create_date': datetime.fromtimestamp(rows[0].get('create_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'),
                                        'update_date':datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S')
                                        }
                # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段
                records = {}
                data_box = []
                for row in rows:
                    if row['serial_no'] == -1:
                        records[row['field_id']] = row['field_value']
                    else:
                        if len(data_box) <= row['serial_no']:
                            data_box.append({})
                        data_box[row['serial_no']][row['field_id']] = row['field_value']

                records["data_box"] = data_box

                response['data']['records']=records

        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)


# 添加一个数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            name = j.get('name')
            template_id = j.get('template_id')
            equipment_name = j.get('equipment_name')
            unit_name = j.get('unit_name')
            id = create_uuid()
            with conn.cursor() as cur:
                create_date = datetime.now().timestamp()
                sql = 'insert into record (id,name,template_id,unit_name,equipment_name,create_date,' \
                      'update_date) ' \
                      'values(%s,%s,%s,%s,%s,%s,%s)'
                params = [id, name, template_id, unit_name, equipment_name, create_date, create_date]
                cur.execute(sql, params)
                conn.commit()
                response['data'] = {'id': id}
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
        return JsonResponse(response)


# 修改一个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            records = j.get('records')
            params = []
            for k, v in records.items():
                # 这里是判断data_box的动态tbale格式
                # 判断条件是为数组 这里不是很严谨
                if type(v) is list:
                    for i, obj in enumerate(v):
                        for obj_k, obj_v in obj.items():
                            params.append([id, i, obj_k, obj_v])
                else:
                    params.append([id, -1, k, v])

            with conn.cursor() as cur:
                sql = 'delete from record_fields where record_id=%s'
                cur.execute(sql,[id])
                sql = 'insert into record_fields (record_id,serial_no,field_id,field_value) ' \
                      'values (%s,%s,%s,%s)'
                cur.executemany(sql, params)
                conn.commit()

        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_update
        return JsonResponse(response)


# 删除一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DeleteView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with conn.cursor() as cur:
                # 先删除从表
                # 后删除主表
                sql = 'delete from record_fields  where record_id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)

                sql = 'delete from record  where id = %s'
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
            id = j.get('id') # 数据id
            with conn.cursor() as cur:
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.unit_name,r.equipment_name,' \
                      'rf.field_id,rf.field_value,rf.serial_no ' \
                      'from record r ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'where r.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.row_none
                else:
                    data= {'id': rows[0].get('id'),
                                        'name': rows[0].get('name'),
                                        'template_id': rows[0].get('template_id'),
                                        'records': [],
                                        'equipment_name': rows[0]['equipment_name'],
                                        'unit_name': rows[0].get('unit_name'),
                                        'create_date': datetime.fromtimestamp(rows[0].get('create_date')).strftime(
                                            '%Y-%m-%d %H:%M:%S'),
                                        'update_date': datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                            '%Y-%m-%d %H:%M:%S')
                                        }
                # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段
                records = {}
                data_box = []
                for row in rows:
                    if row['serial_no'] == -1:
                        records[row['field_id']] = row['field_value']
                    else:
                        if len(data_box) <= row['serial_no']:
                            data_box.append({})
                        data_box[row['serial_no']][row['field_id']] = row['field_value']

                records["data_box"] = data_box

                data['records'] = records

                cipher_suite = Fernet(FERNET_KEY)

                # 对数据进行加密
                json_str = json.dumps(data)
                cipher_text = cipher_suite.encrypt(json_str.encode())

                # 创建一个 BytesIO 对象并写入加密后的数据
                file = io.BytesIO()
                file.write(cipher_text)
                file.seek(0)

                # file_name = f'{data["name"]}.rc'
                # 创建一个 HttpResponse 对象，并设置 Content-Disposition 头，使其作为文件下载

                response = FileResponse(file)
                response['Access-Control-Expose-Headers']='*'
                response['Content-Type']='application/octet-stream'
                # response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}'
                return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
        return JsonResponse(response)

# 导入数据文件
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
