# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: record_view.py
@time: 2023/4/7 9:23
@description:
"""

import json
from datetime import datetime
import io

from cryptography.fernet import Fernet

from django.http import FileResponse

from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, FERNET_KEY


# 获取所有数据列表接口
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
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition = {} if (re := j.get('condition')) is None else re
            # {'unit_name':[],'template_id','equipment_name':[],'data_info':''}
            params = []

            def dict_to_query_str(d: dict):
                def convert_key(orginal):
                    if orginal == 'unit_name':
                        k = 'n.name'
                    elif orginal == 'template_id':
                        k = 't.id'
                    elif orginal == 'equipment_name':
                        k = 'te.equipment_name'
                    elif orginal == 'data_info':
                        k = 'rf.field_value'
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
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} ' \
                      'order by r.update_date desc  '
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,' \
                      't.is_file,t.name as template_name,' \
                      'r.unit_name,' \
                      'r.equipment_name ' \
                      'from (select distinct r.id ' \
                      'from record r ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te ' \
                      'on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} )u  ' \
                      'left join record r on r.id=u.id ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te ' \
                      'on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      'order by r.update_date desc ' \
                      'limit %s offset %s'
                params += [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = []
                for row in rows:
                    record = {'id': row['id'], 'name': row['name'], 'template_id': row['template_id'],
                              'create_date': datetime.fromtimestamp(row.get('create_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'),
                              'update_date': datetime.fromtimestamp(row.get('update_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'), 'unit_name': row['unit_name'],
                              'equipment_name': row['equipment_name']}
                    data.append(record)

                # 构造返回数据
                response['data'] = {'records': data, 'title': None, 'total': count}
                return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error
            print(e)
            return JsonResponse(response, status=500)


# 获取单个数据信息
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
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.unit_name,r.equipment_name,' \
                      'rf.field_id,rf.field_value,rf.serial_no ' \
                      'from record r ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'where r.id=%s order by rf.serial_no'
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
                                        'update_date': datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                            '%Y-%m-%d %H:%M:%S')
                                        }
                # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段
                records = {}
                data_box = []
                for row in rows:
                    if row['field_id'] == None:
                        continue
                    if row['serial_no'] == -1:
                        records[row['field_id']] = row['field_value']
                    else:
                        if len(data_box) <= row['serial_no']:
                            data_box.append({})
                        data_box[row['serial_no']][row['field_id']] = row['field_value']

                records["data_box"] = data_box
                response['data']['records'] = records
            return JsonResponse(response, status=200)
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
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
        try:
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
                return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
            return JsonResponse(response, status=500)


# 修改一个数据信息接口
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
                cur.execute(sql, [id])
                sql = 'insert into record_fields (record_id,serial_no,field_id,field_value) ' \
                      'values (%s,%s,%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 删除一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DeleteView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
        try:
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
            return JsonResponse(response)
        except self.model.DoesNotExist:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_delete
            return JsonResponse(response, status=500)


# 导出数据文件，数据格式跟priview_template数据一致，
# 加密生成rd文件
@method_decorator(csrf_exempt, name='dispatch')
class export_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')  # 数据id
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
                    return JsonResponse(response, status=200)
                else:
                    data = {'id': rows[0].get('id'),
                            'name': rows[0].get('name'),
                            'template_id': rows[0].get('template_id'),
                            'records': [],
                            'equipment_name': rows[0]['equipment_name'],
                            'unit_name': rows[0].get('unit_name'),
                            'create_date': rows[0].get('create_date'),
                            'update_date': rows[0].get('update_date')
                            }
                    # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段
                    for row in rows:
                        if row['field_id'] == None:
                            continue
                        data['records'].append(
                            {'field_id': row['field_id'], 'field_value': row['field_value'],
                             'serial_no': row['serial_no']})

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
                    response['Access-Control-Expose-Headers'] = '*'
                    response['Content-Type'] = 'application/octet-stream'
                    # response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}'
                    return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
            return JsonResponse(response, status=500)


# 导入数据文件
@method_decorator(csrf_exempt, name='dispatch')
class import_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            file = request.FILES.get('file')
            file_binary = file.read()
            # 解密数据
            try:
                cipher_suite = Fernet(FERNET_KEY)
                json_str = cipher_suite.decrypt(file_binary).decode()
                data = json.loads(json_str)  # data数据格式参照export数据
                if len(data) == 0:
                    response['code'], response['msg'] = return_msg.S100, return_msg.row_none
                    return JsonResponse(response, status=400)
                id = data.get('id')
                if id == None:
                    response['code'], response['msg'] = return_msg.S100, return_msg.illegal_rd
                    return JsonResponse(response, status=200)
            except Exception as e:
                print(e)
                response['code'], response['msg'] = return_msg.S100, return_msg.illegal_rd
                return JsonResponse(response, status=200)
            with conn.cursor() as cur:
                # 覆盖已有的数据
                sql = 'delete from record r where r.id=%s'
                cur.execute(sql, [id])
                sql = 'delete from record_fields rf where rf.record_id=%s'
                cur.execute(sql,[id])
                # 从文件中读取用户填报数据
                # 写入到sql
                sql = 'insert into record (id, template_id, name, unit_name, equipment_name, create_date, ' \
                      'update_date) values (%s,%s,%s,%s,%s,%s,%s)'
                params = [id, data.get('template_id'), data.get('name'),
                          data.get('unit_name'),
                          data.get('equipment_name'), data.get('create_date'), data.get('update_date')]
                cur.execute(sql, params)
                sql = 'insert into record_fields (record_id, field_id, field_value, serial_no) values (%s,%s,%s,%s)'
                params = [[id, it['field_id'], it['field_value'], it['serial_no']] for it in data['records']]
                cur.executemany(sql, params)
                conn.commit()
                return JsonResponse(response)
        except Exception as e:
            print(e)
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)

