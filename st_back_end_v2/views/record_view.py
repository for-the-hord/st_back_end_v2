# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: record_view.py
@time: 2023/4/7 9:23
@description:数据管理
"""

import glob
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
import io
from urllib.parse import quote
from cryptography.fernet import Fernet
from itertools import groupby

from pypinyin import lazy_pinyin
import pandas as pd

from django.http import FileResponse, HttpResponse, Http404
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from .. import settings
from ..settings import FILE_ROOT, TEMP_ROOT, BACKUP_ROOT
from st_back_end_v2.utils.utils import create_uuid, return_msg, create_response, rows_as_dict, FERNET_KEY, \
    calibration


# 获取所有数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except json.JSONDecodeError:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            mission_id = j.get('mission_id')
            condition = {} if (re := j.get('condition')) is None else re
            # {'unit_name':[],'template_id','equipment_name':[],'data_info':''}
            sort = j.get('sort', {})
            # {'record_date':'desc'}
            # 排序
            params = []

            def convert_key(orginal):
                """
                将前端传递的参数转成数据库字段
                Args:
                    orginal:

                Returns:

                """
                if orginal == 'unit_name':
                    k = 'n.name'
                elif orginal == 'template_id':
                    k = 't.id'
                elif orginal == 'equipment_name':
                    k = 'te.equipment_name'
                elif orginal == 'data_info':
                    k = 'rf.field_value'
                elif orginal == 'record_date':
                    k = 'r.record_date'
                else:
                    k = None
                return k

            def dict_to_query_str(d: dict):
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

            sort_clause = f'order by {sort_sql}' if (sort_sql := convert_key(sort)) else 'order by r.record_date desc'
            with conn.cursor() as cur:
                # 创建临时表 存放树的节点
                sql = 'create TEMPORARY table node(id VARCHAR(32))'
                cur.execute(sql)
                sql = 'insert into node (id) select id from (with RECURSIVE temp as ' \
                      '(select m.* from mission m where m.id=%s ' \
                      'union all select m.* from mission m ' \
                      'inner join temp on m.parent_id =temp.id)  ' \
                      'select id from temp) as t'

                cur.execute(sql, [mission_id])

                # 计算满足条件的 count
                sql = 'select count(distinct r.id) as count ' \
                      'from record r ' \
                      'join node on node.id = r.mission_id ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} ' \
                      f'{sort_clause}'

                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                # 查询满足条件的数据
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.record_date,' \
                      't.is_file,t.name as template_name,' \
                      'r.unit_name,' \
                      'r.equipment_name ' \
                      'from (select distinct r.id,r.record_date ' \
                      'from record r ' \
                      'join node on node.id = r.mission_id ' \
                      'left join record_fields rf on r.id = rf.record_id ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join unit n on n.name=r.unit_name ' \
                      'left join tp_equipment te ' \
                      'on t.id = te.template_id and te.equipment_name=r.equipment_name ' \
                      f'{where_clause} {sort_clause} )u  ' \
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
                              'template_name': row['template_name'],
                              'record_date': datetime.fromtimestamp(
                                  0 if (re := row.get('record_date')) is None else re).strftime(
                                  '%Y-%m-%d %H:%M:%S'),
                              'update_date': datetime.fromtimestamp(row.get('update_date')).strftime(
                                  '%Y-%m-%d %H:%M:%S'), 'unit_name': row['unit_name'],
                              'equipment_name': row['equipment_name']}
                    data.append(record)

                # 构造返回数据
                response['data'] = {'records': data, 'title': None, 'total': count}
                return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            print(e)
            return JsonResponse(response, status=500)


# 拉取单位列表
@method_decorator(csrf_exempt, name='dispatch')
class unit_search(ListView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            with conn.cursor() as cur:
                sql = 'select distinct n.id,n.name ' \
                      'from  unit n '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                response['data'] = rows
                return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return JsonResponse(response, status=500)


# 获取模板
@method_decorator(csrf_exempt, name='dispatch')
class template_search(ListView):

    def post(self, request, *args, **kwargs):
        response = create_response()

        try:
            with conn.cursor() as cur:
                sql = 'select distinct t.id as id,t.name  ' \
                      'from template t '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                response['data'] = rows
                return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return JsonResponse(response, status=500)


# 获取装备列表
@method_decorator(csrf_exempt, name='dispatch')
class equipment_search(ListView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            with conn.cursor() as cur:
                sql = 'select distinct te.equipment_name as name,' \
                      'te.equipment_name as name ' \
                      'from  tp_equipment te '
                cur.execute(sql)
                rows = rows_as_dict(cur)
                response['data'] = rows
                return JsonResponse(response)

        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return JsonResponse(response, status=500)


# 获取单个数据信息
@method_decorator(csrf_exempt, name='dispatch')
class item(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')

            with conn.cursor() as cur:
                data = {}
                # 获取填报数据
                sql = 'select r.id,r.name,t.name as template_name,t.id as template_id,' \
                      'r.record_date,r.update_date,r.unit_name,r.equipment_name,r.attachment,' \
                      'rf.field_id,rf.field_value,rf.serial_no ' \
                      'from record r ' \
                      'left join template t on r.template_id = t.id ' \
                      'left join template_fields tf on t.id = tf.template_id ' \
                      'left join record_fields rf on r.id = rf.record_id and rf.field_id=tf.field_id ' \
                      'where r.id=%s order by rf.serial_no'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                    return JsonResponse(response, status=100)
                else:
                    info_box = {}
                    data_box = []
                    template_id = rows[0].get('template_id')
                    try:
                        attachment = json.loads(rows[0]['attachment'])
                    except:
                        attachment = []
                    rd_data = {'id': rows[0].get('id'),
                               'template_id': rows[0].get('template_id'),
                               'template_name': rows[0].get('template_name'),
                               'attachment': attachment,
                               'info_box': info_box,
                               'data_box': data_box,
                               'equipment_name': rows[0]['equipment_name'],
                               'unit_name': rows[0].get('unit_name'),
                               'record_date': '' if (re := rows[0].get('record_date')) is None else
                               datetime.fromtimestamp(re).strftime(
                                   '%Y-%m-%d %H:%M:%S'),
                               'update_date': datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                   '%Y-%m-%d %H:%M:%S')
                               }
                # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段

                for row in rows:
                    if row['field_id'] == None:
                        continue
                    if row['serial_no'] == -1:
                        info_box[row['field_id']] = row['field_value']
                    else:
                        if len(data_box) <= row['serial_no']:
                            data_box.append({})
                        data_box[row['serial_no']][row['field_id']] = row['field_value']
                data['record'] = rd_data
                # 获取模板数据
                sql = 'select t.id,t.name,t.is_file,te.equipment_name,ut.unit_name ' \
                      'from template t ' \
                      'left join unit_template ut on t.id = ut.template_id ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [template_id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows) == 0:
                    response['msg'], response['code'] = return_msg.no_template, return_msg.code_100
                    return JsonResponse(response, status=400)
                equipment = []
                unit = []
                tp_data = {'id': rows[0]['id'], 'name': rows[0]['name'],
                           'feature': [{'prop': 'equipment_name', 'label': '装备名称', 'value': equipment},
                                       {'prop': 'unit_name', 'label': '单位名称', 'value': unit}],
                           'info_box': [],
                           'data_box': []}
                for row in rows:
                    if row['equipment_name'] is not None and row['equipment_name'] not in equipment:
                        equipment.append(row['equipment_name'])
                    if row['unit_name'] is not None and row['unit_name'] not in unit:
                        unit.append(row['unit_name'])

                sql = 'select tf.in_box,tf.component,tf.label,tf.default,tf.type,tf.field_id ' \
                      'from template t ' \
                      'left join template_fields tf on tf.template_id =t.id ' \
                      'where t.id=%s'
                params = [template_id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 通过不同的区域来分组 每个组件
                for row in rows:
                    # 先取出组件数据
                    name = row['label']
                    type = row['type']
                    default = row['default']
                    box_name = row['in_box']
                    key = row['field_id']
                    if box_name in tp_data:
                        tp_data[box_name].append({'key': key, 'name': name, 'type': type, 'default': default})
                data['template'] = tp_data
                response['data'] = data
            return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return JsonResponse(response, status=500)


# 获取单个数据信息,在新建前调用，载入最近一次填报
@method_decorator(csrf_exempt, name='dispatch')
class load_his(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            template_id = j.get('template_id')

            with conn.cursor() as cur:
                data = {}
                # 获取某个模板的最近填报数据
                sql = 'select r.id from record r left join template t on r.template_id = t.id ' \
                      'where t.id=%s order by r.create_date desc limit 1 offset 0'
                params = [template_id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows) == 0:
                    response['data'] = None
                    return JsonResponse(response)
                else:
                    id = rows[0]['id']
                    sql = 'select r.id,r.name,t.name as template_name,t.id as template_id,' \
                          'r.record_date,r.update_date,r.unit_name,r.equipment_name,r.attachment,' \
                          'rf.field_id,rf.field_value,rf.serial_no ' \
                          'from record r ' \
                          'left join template t on r.template_id = t.id ' \
                          'left join template_fields tf on t.id = tf.template_id ' \
                          'left join record_fields rf on r.id = rf.record_id and rf.field_id=tf.field_id ' \
                          'where r.id=%s order by rf.serial_no'
                    params = [id]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    # 构造返回数据
                    if len(rows) == 0:
                        response['data'] = None
                        return JsonResponse(response)
                    else:
                        info_box = {}
                        data_box = []
                        rd_data = {'template_id': rows[0].get('template_id'),
                                   'template_name': rows[0].get('template_name'),
                                   'info_box': info_box,
                                   'data_box': data_box,
                                   'equipment_name': rows[0]['equipment_name'],
                                   'unit_name': rows[0].get('unit_name'),
                                   'record_date': datetime.fromtimestamp(rows[0].get('record_date')).strftime(
                                       '%Y-%m-%d %H:%M:%S'),
                                   'update_date': datetime.fromtimestamp(rows[0].get('update_date')).strftime(
                                       '%Y-%m-%d %H:%M:%S')
                                   }
                    # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段

                    for row in rows:
                        if row['field_id'] == None:
                            continue
                        if row['serial_no'] == -1:
                            info_box[row['field_id']] = row['field_value']
                        else:
                            if len(data_box) <= row['serial_no']:
                                data_box.append({})
                            data_box[row['serial_no']][row['field_id']] = row['field_value']
                    data['record'] = rd_data
                    # 获取模板数据
                    sql = 'select t.id,t.name,t.is_file,te.equipment_name,ut.unit_name ' \
                          'from template t ' \
                          'left join unit_template ut on t.id = ut.template_id ' \
                          'left join tp_equipment te on t.id = te.template_id ' \
                          'where t.id=%s'
                    params = [template_id]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    if len(rows) == 0:
                        response['msg'], response['code'] = return_msg.no_template, return_msg.code_100
                        return JsonResponse(response, status=400)
                    equipment = []
                    unit = []
                    tp_data = {'name': rows[0]['name'],
                               'feature': [{'prop': 'equipment_name', 'label': '装备名称', 'value': equipment},
                                           {'prop': 'unit_name', 'label': '单位名称', 'value': unit}],
                               'info_box': [],
                               'data_box': []}
                    for row in rows:
                        if row['equipment_name'] is not None and row['equipment_name'] not in equipment:
                            equipment.append(row['equipment_name'])
                        if row['unit_name'] is not None and row['unit_name'] not in unit:
                            unit.append(row['unit_name'])

                    sql = 'select tf.in_box,tf.label,tf.default,tf.type,tf.field_id ' \
                          'from template t ' \
                          'left join template_fields tf on tf.template_id =t.id ' \
                          'where t.id=%s'
                    params = [template_id]
                    cur.execute(sql, params)
                    rows = rows_as_dict(cur)
                    # 通过不同的区域来分组 每个组件
                    for row in rows:
                        # 先取出组件数据
                        name = row['label']
                        type = row['type']
                        default = row['default']
                        box_name = row['in_box']
                        key = row['field_id']
                        if box_name in tp_data:
                            tp_data[box_name].append({'key': key, 'name': name, 'type': type, 'default': default})
                    data['template'] = tp_data
                    response['data'] = data
                return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return JsonResponse(response, status=500)


# 数据清洗校验
class calibrate_data:

    def value_in_range(self, type, value, range):
        '''
        判断值是否在范围内
        Returns:

        '''
        if type == 'number':
            range = range.split('~')
            if value in range:
                return True, []
            else:
                return False, range
        else:
            return True, []

    def convert_to_standardisation(self, type, value, re):
        '''
        将不同数据格式的时间、经纬度转成统一的数据格式
        Args:
            type:
            value:
            re:

        Returns:

        '''
        if type == 'date':
            try:
                value, date_format = calibration.get_date_rex(value, re)
                timestamp = datetime.strptime(value, date_format)
                new_value = int(timestamp.timestamp())
            except Exception as e:
                new_value = value
        elif type == 'lonlat':
            new_value = value
        else:
            new_value = value
        return new_value

    def calibration(self, data):
        """
        data:[{'key':value,'key':value},{'key':value,'key':value}]
        Args:
            data:

        Returns:

        """
        error = []
        new_data = []
        if len(data) > 0:
            di = dict(data[0])
            keys = di.keys()
            regex_dict = []  # [{'id1':[rex,rex,rex,rex],'type':'','default':''},...]
            if keys:
                with conn.cursor() as cur:
                    placeholders = ', '.join(f'"{key}"' for key in keys)
                    sql = f'''select tf.field_id,tf.label,tf.type,tf.`default` 
                              from template_fields tf 
                              where tf.field_id in ({placeholders})'''
                    cur.execute(sql)
                    rows = rows_as_dict(cur)

                    def find_regx(type):
                        return calibration.get(type)

                    for row in rows:
                        record = {}
                        key = row['field_id']
                        type = row['type']
                        record[key] = find_regx(type)
                        record['type'] = type
                        record['default'] = row['default']
                        regex_dict.append(record)

            df = pd.DataFrame(data)
            for row in range(df.shape[0]):
                for col in range(df.shape[1]):
                    value = df.iloc[row, col]
                    value = str(value)  # 接收数据需要转成字符串
                    key = df.columns[col]
                    record = {'key': key, 'value': value, 'standards_value': value}
                    if any(key in d for d in regex_dict):  # 数据格式校验
                        di = next((d for d in regex_dict if key in d), {})
                        # 对于 key 对应的每个正则表达式
                        is_regx = 0
                        for regex in di[key]:
                            # 如果 value 符合正则表达式
                            if re.match(regex, value):
                                new_value = self.convert_to_standardisation(di['type'], value, regex)
                                record['standards_value'] = new_value
                                is_regx = 1
                                break  # 匹配成功，不需要继续检查其他正则表达式
                            else:
                                is_regx = -1
                        if is_regx == -1:
                            error.append({'rowIndex': row, 'columnIndex': col,'tips':'数据格式错误！'})
                    else:  # 无数据格式的进行范围校验
                        in_range, value_range = self.value_in_range(di['type'], value, di['default'])
                        error.append({'rowIndex': row, 'columnIndex': col, 'tips': 'error'})
                    new_data.append(record)
        return error, new_data


# 添加一个数据列表接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView, calibrate_data):
    # 校验数据

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            # name = j.get('name')
            mission_id = j.get('mission_id')
            template_id = j.get('template_id')
            equipment_name = j.get('equipment_name')
            unit_name = j.get('unit_name')
            attachment = j.get('attachment', [{'id', 'name'}])  # 附件名称的数组[]
            try:
                attachment = json.dumps(attachment)
            except:
                attachment = "[]"
            info_box = j.get('info_box', {})
            data_box = j.get('data_box')
            error, new_data_box = self.calibration(data_box)
            if len(error) != 0:  # 数据校验有错误 返回
                response['code'], response['msg'] = return_msg.code_101, return_msg.data_error
                response['data'] = error
                return JsonResponse(response, status=200)
            record_date = int(datetime.now().timestamp())
            id = create_uuid()
            val = []
            for k, v in info_box.items():
                val.append([id, k, v, -1, v])

            for i, it in enumerate(new_data_box):
                val.append([id, it.get('key'), it.get('value'), i, it.get('standards_value')])

            with conn.cursor() as cur:
                create_date = datetime.now().timestamp()
                sql = 'insert into record (id,template_id,unit_name,equipment_name,create_date,' \
                      'update_date,record_date,attachment,mission_id) ' \
                      'values(%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                params = [id, template_id, unit_name, equipment_name, create_date, create_date, record_date, attachment,mission_id]

                cur.execute(sql, params)
                sql = 'insert into record_fields (record_id, field_id, field_value, serial_no,std_value) ' \
                      'values (%s,%s,%s,%s,%s)'
                params = val
                cur.executemany(sql, params)
                conn.commit()
                response['data'] = error
                return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)


# 修改一个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView, calibrate_data):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            equipment_name = j.get('equipment_name')
            unit_name = j.get('unit_name')
            info_box = j.get('info_box', {})
            attachment = j.get('attachment', [{'id', 'name'}])  # 附件名称的数组[]
            try:
                attachment = json.dumps(attachment)
            except:
                attachment = "[]"
            data_box = j.get('data_box')

            error, new_data_box = self.calibration(data_box)
            if len(error) != 0:
                response['code'], response['msg'] = return_msg.code_101, return_msg.data_error
                response['data'] = error
                return JsonResponse(response, status=200)
            record_date = int(datetime.now().timestamp())
            val = []
            for k, v in info_box.items():
                val.append([id, k, v, -1, v])

            for i, it in enumerate(new_data_box):
                val.append([id, it.get('key'), it.get('value'), i, it.get('standards_value')])

            with conn.cursor() as cur:
                # 更新主表
                sql = 'update record set unit_name=%s,equipment_name=%s,attachment=%s,record_date=%s where id=%s'
                params = [unit_name, equipment_name, attachment, record_date, id]
                cur.execute(sql, params)
                # 删除关系表 然后再写入
                sql = 'delete from record_fields where record_id=%s'
                params = [id]
                cur.execute(sql, params)
                sql = 'insert into record_fields (record_id, field_id, field_value, serial_no,std_value) ' \
                      'values (%s,%s,%s,%s,%s)'
                params = val
                cur.executemany(sql, params)
                conn.commit()
                response['data'] = error
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 删除一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DeleteView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
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
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_delete
            return JsonResponse(response, status=500)


# 移至一个或者多个数据信息接口
@method_decorator(csrf_exempt, name='dispatch')
class move_view(DeleteView):

    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            ids = j.get('ids')
            mission_id = j.get('mission_id')
            params = [[mission_id,it] for it in ids]
            with conn.cursor() as cur:
                sql = 'update record set mission_id=%s where id = %s'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except self.model.DoesNotExist:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_delete
            return JsonResponse(response, status=500)


# 导出数据文件，数据格式跟priview_template数据一致，加密生成rd文件并于附件一同压缩到zip文件
@method_decorator(csrf_exempt, name='dispatch')
class export_view(DetailView):
    def get(self, request, *args, **kwargs):
        response = create_response()
        try:
            id = request.GET.get('id')  # 数据id
            with conn.cursor() as cur:
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.unit_name,r.equipment_name,' \
                      'r.attachment,' \
                      'rf.field_id,rf.field_value,rf.serial_no,rf.std_value,' \
                      't.name as template_name  ' \
                      'from record r ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join template_fields tf on t.id = tf.template_id ' \
                      'left join record_fields rf on r.id = rf.record_id and rf.field_id=tf.field_id ' \
                      'where r.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 构造返回数据
                if len(rows) == 0:
                    response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                    return Http404
                else:
                    try:
                        attachment = json.loads(rows[0]['attachment'])
                    except:
                        attachment = []
                    data = {'id': rows[0].get('id'),
                            'name': rows[0].get('name'),
                            'template_id': rows[0].get('template_id'),
                            'template_name': rows[0].get('template_name'),
                            'attachement': attachment,
                            'records': [],
                            'equipment_name': rows[0]['equipment_name'],
                            'unit_name': rows[0].get('unit_name'),
                            'create_date': rows[0].get('create_date'),
                            'record_date': rows[0].get('record_date'),
                            'update_date': rows[0].get('update_date')
                            }

                    for row in rows:
                        if row['field_id'] is None:
                            continue
                        data['records'].append(
                            {'field_id': row['field_id'],
                             'field_value': row['field_value'],
                             'serial_no': row['serial_no'],
                             'std_value': row['std_value']})

                    cipher_suite = Fernet(FERNET_KEY)
                    # 对数据进行加密
                    json_str = json.dumps(data)
                    cipher_text = cipher_suite.encrypt(json_str.encode())
                    # 生成文件名称
                    record_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                    equipment_name = data['equipment_name']  # 装备名称
                    template_name = data['template_name']  # 填报模板
                    unit_name = data['unit_name']  # 填报单位
                    file_name = f'{unit_name}-{equipment_name}-{template_name}-{record_time}'

                    # 压缩数据文件格式
                    file = io.BytesIO()
                    zf = zipfile.ZipFile(file, 'w')
                    zf.writestr(f'{file_name}.rd', cipher_text)

                    # 第一个参数是文件的路径，第二个参数是在zip文件中的文件名
                    for it in attachment:
                        try:
                            id = it.get('id')
                            file_path = os.path.join(FILE_ROOT, id)
                            zf.write(file_path, f'/attachment/{id}')
                        except:
                            continue
                    # 关闭ZipFile对象
                    zf.close()
                    # 将BytesIO对象的位置设置回到开始处，以便于读取其内容
                    file.seek(0)

                    # 创建一个FileResponse对象，这个对象可以直接返回给客户端
                    response = FileResponse(file, content_type='application/zip')
                    response['Access-Control-Expose-Headers'] = '*'
                    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}.zip'
                    return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return Http404


# 批量导出数据文件，数据格式跟priview_template数据一致，加密生成rd文件并于附件一同压缩到zip文件
@method_decorator(csrf_exempt, name='dispatch')
class export_batch_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except json.JSONDecodeError:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            ids = j.get('ids')
            in_clause = ','.join(['%s' for _ in range(len(ids))])
            with conn.cursor() as cur:
                sql = 'select r.id,r.name,r.template_id,r.create_date,r.update_date,r.unit_name,r.equipment_name,' \
                      'r.attachment,' \
                      'rf.field_id,rf.field_value,rf.serial_no,rf.std_value,' \
                      't.name as template_name  ' \
                      'from record r ' \
                      'left join template t on t.id=r.template_id ' \
                      'left join template_fields tf on t.id = tf.template_id ' \
                      'left join record_fields rf on r.id = rf.record_id and rf.field_id=tf.field_id ' \
                      f'where r.id in ({in_clause})'
                params = tuple(ids)
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 根据id将同一id值的数据进行分组
                group_rows = {}
                for key, group in groupby(rows, key=lambda x: x['id']):
                    group_rows[key] = list(group)

                file = io.BytesIO()
                zf = zipfile.ZipFile(file, 'w')
                # 构造返回数据
                for record_id, it in group_rows.items():
                    try:
                        attachment = json.loads(it[0]['attachment'])
                    except:
                        attachment = []
                    data = {'id': record_id,
                            'name': it[0].get('name'),
                            'template_id': it[0].get('template_id'),
                            'template_name': it[0].get('template_name'),
                            'attachement': attachment,
                            'records': [],
                            'equipment_name': it[0]['equipment_name'],
                            'unit_name': it[0].get('unit_name'),
                            'create_date': it[0].get('create_date'),
                            'record_date': it[0].get('record_date'),
                            'update_date': it[0].get('update_date')
                            }
                    # 使用一个字典存储'serial_no'的值作为键，字典的值作为值，用来收集每一个'serial_no'对应的字段
                    for row in it:
                        if row['field_id'] is None:
                            continue
                        data['records'].append(
                            {'field_id': row['field_id'],
                             'field_value': row['field_value'],
                             'serial_no': row['serial_no'],
                             'std_value': row['std_value']
                             })

                    cipher_suite = Fernet(FERNET_KEY)
                    # 对数据进行加密
                    json_str = json.dumps(data)
                    cipher_text = cipher_suite.encrypt(json_str.encode())
                    # 生成文件名称
                    record_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                    equipment_name = data['equipment_name']  # 装备名称
                    template_name = data['template_name']  # 填报模板
                    unit_name = data['unit_name']  # 填报单位
                    file_name = f'{unit_name}-{equipment_name}-{template_name}-{record_time}'

                    # 压缩数据文件格式

                    zf.writestr(f'{file_name}.rd', cipher_text)

                    # 第一个参数是文件的路径，第二个参数是在zip文件中的文件名
                    for it in attachment:
                        try:
                            id = it.get('id')
                            file_path = os.path.join(FILE_ROOT, id)
                            zf.write(file_path, f'/attachment/{id}')
                        except:
                            continue
                    # 关闭ZipFile对象
                zf.close()
                # 将BytesIO对象的位置设置回到开始处，以便于读取其内容
                file.seek(0)

                # 创建一个FileResponse对象，这个对象可以直接返回给客户端
                response = FileResponse(file, content_type='application/zip')
                response['Access-Control-Expose-Headers'] = '*'
                response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}.zip'
                return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
            return Http404


# 导入单份数据文件
@method_decorator(csrf_exempt, name='dispatch')
class import_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            mission_id = request.POST.get('mission_id')
            file = request.FILES.get('file')  # 导入压缩包
            #  创建一个临时文件存放zip解压缩文件
            if os.path.exists(TEMP_ROOT):
                shutil.rmtree(TEMP_ROOT)
            else:
                os.mkdir(TEMP_ROOT)
            # 保存文件到服务器临时目录
            file_path = os.path.join(BACKUP_ROOT, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            try:
                # 解压文件
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(TEMP_ROOT)
            except:
                response['code'], response['msg'] = return_msg.code_100, return_msg.zip_error
                return JsonResponse(response, status=200)

            # 移动attachment文件夹下的文件到项目的files/attachment目录下
            src_dir = os.path.join(TEMP_ROOT, 'attachment')
            for file_name in os.listdir(src_dir):
                shutil.copyfile(os.path.join(src_dir, file_name), os.path.join(FILE_ROOT, file_name))

            li = glob.glob(os.path.join(TEMP_ROOT, '*.rd'))
            if len(li) > 0:
                json_file = li[0]
            else:
                # 删除临时文件和目录
                shutil.rmtree(TEMP_ROOT)
                response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
                return JsonResponse(response, status=200)
            # 解析json文件并保存到数据库
            with open(json_file, 'r') as rd_file:
                file_binary = rd_file.read()
                # 解密数据
                cipher_suite = Fernet(FERNET_KEY)
                json_str = cipher_suite.decrypt(file_binary).decode()
                data = json.loads(json_str)  # data数据格式参照export数据
                if len(data) == 0:
                    response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                    return JsonResponse(response, status=400)
                record_id = data.get('id')
                if record_id is None:
                    response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
                    return JsonResponse(response, status=200)

                try:
                    with conn.cursor() as cur:
                        # 覆盖已有的数据
                        sql = 'delete from record r where r.id=%s'
                        cur.execute(sql, [record_id])
                        sql = 'delete from record_fields rf where rf.record_id=%s'
                        cur.execute(sql, [record_id])
                        # 从文件中读取用户填报数据
                        # 写入到sql
                        sql = 'insert into record (id, template_id, name, unit_name, equipment_name, create_date, ' \
                              'update_date,attachment,record_date,mission_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                        params = [record_id,
                                  data.get('template_id'),
                                  data.get('name'),
                                  data.get('unit_name'),
                                  data.get('equipment_name'), data.get('create_date'),
                                  data.get('update_date'), json.dumps(data.get('attachment')),
                                  data.get('record_date'), mission_id]
                        cur.execute(sql, params)
                        sql = 'insert into record_fields (record_id, field_id, field_value, serial_no,std_value) ' \
                              'values (%s,%s,%s,%s,%s)'
                        params = [[record_id, it['field_id'], it['field_value'], it['serial_no'], it['std_value']] for
                                  it in
                                  data['records']]
                        cur.executemany(sql, params)
                        conn.commit()
                        # 删除临时文件和目录
                except Exception as e:
                    # 删除临时文件和目录
                    shutil.rmtree(TEMP_ROOT)
                    conn.rollback()
                    response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
                    return JsonResponse(response, status=500)
            shutil.rmtree(TEMP_ROOT)
            return JsonResponse(response)
        except Exception as e:
            # 删除临时文件和目录
            shutil.rmtree(TEMP_ROOT)
            response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
            return JsonResponse(response, status=500)


# 批量导入数据文件
@method_decorator(csrf_exempt, name='dispatch')
class import_batch_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            mission_id = request.POST.get('mission_id')
            file = request.FILES.get('files')  # 导入压缩包
            #  创建一个临时文件存放zip解压缩文件
            if os.path.exists(TEMP_ROOT):
                shutil.rmtree(TEMP_ROOT)
            else:
                os.mkdir(TEMP_ROOT)
            # 保存文件到服务器临时目录
            file_path = os.path.join(BACKUP_ROOT, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            try:
                # 解压文件
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(TEMP_ROOT)
            except:
                response['code'], response['msg'] = return_msg.code_100, return_msg.zip_error
                return JsonResponse(response, status=200)

            # 移动attachment文件夹下的文件到项目的files/attachment目录下
            src_dir = os.path.join(TEMP_ROOT, 'attachment')
            for file_name in os.listdir(src_dir):
                shutil.copyfile(os.path.join(src_dir, file_name), os.path.join(FILE_ROOT, file_name))

            # 解析rd数据文件
            li = glob.glob(os.path.join(TEMP_ROOT, '*.rd'))
            if len(li) == 0:  # zip里不含有rd文件
                # 删除临时文件和目录
                shutil.rmtree(TEMP_ROOT)
                response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
                return JsonResponse(response, status=200)
            else:
                for it in li:
                    # 解析json文件并保存到数据库
                    with open(it, 'r') as rd_file:
                        file_binary = rd_file.read()
                        # 解密数据
                        cipher_suite = Fernet(FERNET_KEY)
                        json_str = cipher_suite.decrypt(file_binary).decode()
                        data = json.loads(json_str)  # data数据格式参照export数据
                        if len(data) == 0:
                            response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                            return JsonResponse(response, status=400)
                        record_id = data.get('id')
                        if record_id is None:
                            response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
                            return JsonResponse(response, status=200)

                        try:
                            with conn.cursor() as cur:
                                # 覆盖已有的数据
                                sql = 'delete from record r where r.id=%s'
                                cur.execute(sql, [record_id])
                                sql = 'delete from record_fields rf where rf.record_id=%s'
                                cur.execute(sql, [record_id])
                                # 从文件中读取用户填报数据
                                # 写入到sql
                                sql = 'insert into record (id, template_id, name, unit_name, equipment_name, ' \
                                      'create_date, update_date,attachment,record_date,mission_id) ' \
                                      'values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                                params = [record_id,
                                          data.get('template_id'),
                                          data.get('name'),
                                          data.get('unit_name'),
                                          data.get('equipment_name'), data.get('create_date'),
                                          data.get('update_date'), json.dumps(data.get('attachment')),
                                          data.get('record_date'), mission_id]
                                cur.execute(sql, params)
                                sql = 'insert into record_fields (record_id, field_id, field_value, serial_no,std_value) ' \
                                      'values (%s,%s,%s,%s,%s)'
                                params = [[record_id, it['field_id'], it['field_value'], it['serial_no'],
                                          it['std_value']] for it in data['records']]
                                cur.executemany(sql, params)
                                conn.commit()
                                # 删除临时文件和目录
                        except Exception as e:
                            # 删除临时文件和目录
                            shutil.rmtree(TEMP_ROOT)
                            conn.rollback()
                            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
                            return JsonResponse(response, status=500)
                shutil.rmtree(TEMP_ROOT)
            return JsonResponse(response)
        except Exception as e:
            # 删除临时文件和目录
            shutil.rmtree(TEMP_ROOT)
            response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
            return JsonResponse(response, status=500)


# 下载数据采集要素
@method_decorator(csrf_exempt, name='dispatch')
class export_field_view(DetailView):
    def get(self, request, *args, **kwargs):
        response = create_response()
        try:
            type = request.GET.get('type')
            if type == 'info':  # 下载要素模板
                file_path = os.path.join(settings.FILE_ROOT, '要素模板.xlsx')
                if os.path.exists(file_path):
                    file_name = quote('要素模板.xlsx')
                    # 直接在FileResponse内部打开文件
                    response = FileResponse(open(file_path, 'rb'))
                    response['content_type'] = "application/vnd.ms-excel"
                    response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'{}'.format(file_name)
                    return response
            elif type == 'data':  # 下载数据采集要素模板
                file_path = os.path.join(settings.FILE_ROOT, '数据采集要素模板.xlsx')
                if os.path.exists(file_path):
                    file_name = quote('数据采集模板.xlsx')
                    # 直接在FileResponse内部打开文件
                    response = FileResponse(open(file_path, 'rb'))
                    response['content_type'] = "application/vnd.ms-excel"
                    response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'{}'.format(file_name)
                    return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return HttpResponse("error", status=500)


# 导入数据采集要素
@method_decorator(csrf_exempt, name='dispatch')
class import_field_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            template_id = request.GET.get('template_id')
            box = request.GET.get('box')
            file = request.FILES.get('file')

            def convert_to_english(label):
                """
                这里将lable转成一个唯一的key
                采用拼音+UUID
                Args:
                    label:

                Returns:

                """
                pinyin_list = lazy_pinyin(label)
                name = ''.join(pinyin_list)
                name = f'{name}_{create_uuid()}'
                return name

            if box == 'data_box':
                # 使用 header=None 选项读取 Excel 文件，这样 pandas 不会将第一行视为列名
                df = pd.read_excel(file, header=None)
                # 将 DataFrame 转换为转置形式，使每一列对应一个字段（'label', 'type', 'default'）
                df = df.head(1)
                df = df.transpose()

                # 设置 DataFrame 的列名
                df.columns = ['name']

                # 添加一个新的列 'No'，用来表示每一列的序号
                df['No'] = range(1, len(df) + 1)

                # 添加一个新的列 'key'，用来表示 'label' 字段的英文名

                df['key'] = df['name'].apply(convert_to_english)
                # 将 DataFrame 转换为字典列表
                data = df.to_dict('records')
                response['data'] = data
                return JsonResponse(response, status=200)
            elif box == 'info_box':
                # 使用 header=None 选项读取 Excel 文件，这样 pandas 不会将第一行视为列名
                df = pd.read_excel(file, header=None)
                # 将 DataFrame 转换为转置形式，使每一列对应一个字段（'label', 'type', 'default'）
                df = df.head(3)
                df = df.transpose()

                # 设置 DataFrame 的列名
                df.columns = ['name', 'component_type', 'default_value']

                # 添加一个新的列 'No'，用来表示每一列的序号
                df['No'] = range(1, len(df) + 1)

                df['key'] = df['name'].apply(convert_to_english)
                # 将 DataFrame 转换为字典列表
                data = df.to_dict('records')
                for it in data:
                    it['template_id'] = template_id
                    it['box'] = box
                response['data'] = data
                return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return JsonResponse(response, status=500)
