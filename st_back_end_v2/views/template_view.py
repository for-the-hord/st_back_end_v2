# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: template_view.py
@time: 2023/4/7 9:21
@description:
"""
import json
import os
from datetime import datetime
import io
from cryptography.fernet import Fernet
from urllib.parse import quote
import pandas as pd
from pypinyin import lazy_pinyin

from django.db import connection as conn
from django.http import JsonResponse, HttpRequest, FileResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from .. import settings
from ..settings import TEMPLATE_ROOT
from ..tools import create_uuid, return_msg, create_return_json, rows_as_dict, component_to_json, FERNET_KEY


# 获取模板列表
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
            condition = j.get('condition', {})

            def convert_key(orginal):
                if orginal == 'template_name':
                    k = 't.name'
                else:
                    k = None
                return k

            limit_clause = '' if page_size == 0 and page_index == 0 else 'limit %s offset %s'
            where_clause = '' if len(condition) == 0 else 'where ' + " AND ".join(
                [f"{convert_key(key)} LIKE %s" for key in condition.keys()])
            where_values = ["%" + value + "%" for value in condition.values()]
            with conn.cursor() as cur:
                params = where_values
                sql = f'select count(*) as count from template t {where_clause}'
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                count = rows[0]['count']
                sql = 'select t.id,t.name as template_name,t.is_file,' \
                      't.create_date,t.update_date ' \
                      'from template t  ' \
                      f'{where_clause} ' \
                      f'order by t.update_date desc {limit_clause}'
                params = where_values + [page_size, (page_index - 1) * page_size] \
                    if limit_clause != '' else where_values
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                template_list = [
                    {'id': it.get('id'), 'name': it.get('template_name'),
                     'is_file': it.get('is_fle'),
                     'create_date': datetime.fromtimestamp(it.get('create_date')).strftime(
                         '%Y-%m-%d %H:%M:%S'),
                     'update_date': datetime.fromtimestamp(0 if (re := it.get('update_date')) is None else re).strftime(
                         '%Y-%m-%d %H:%M:%S')} for it in rows]

            # 构造返回数据
            response['data'] = {'records': template_list, 'title': None,
                                'total': count}
            return JsonResponse(response)
        except Exception as e:
            print(e)
            return JsonResponse(response, status=500)


# 获取单个模板信息(填报数据时候，选择模板调用)
@method_decorator(csrf_exempt, name='dispatch')
class item(DetailView):

    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,te.equipment_name,ut.unit_name ' \
                      'from template t ' \
                      'left join unit_template ut on t.id = ut.template_id ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows) == 0:
                    response['msg'], response['code'] = return_msg.no_template, return_msg.S100
                    return JsonResponse(response, status=400)
                equipment = []
                data = {'id': rows[0]['id'], 'name': rows[0]['name'],
                        'equipment_name': equipment,
                        'info_box': [],
                        'data_box': []}
                for row in rows:
                    if row['equipment_name'] is not None and row['equipment_name'] not in equipment:
                        equipment.append(row['equipment_name'])

                sql = 'select tf.in_box,tf.component,tf.label,tf.default,tf.type ' \
                      'from template t ' \
                      'left join template_fields tf on tf.template_id =t.id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 通过不同的区域来分组 每个组件
                for row in rows:
                    # 先取出组件数据
                    name = row['label']
                    type = row['type']
                    default = row['default']
                    # 判断box的区域位置
                    box_name = row['in_box']
                    if box_name  in data:
                        data[box_name].append({'name': name, 'type': type, 'default': default})
                response['data'] = data
                return JsonResponse(response)
        except Exception as e:
            print(e)
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
            return JsonResponse(response, status=500)


# 搜索模板by 单位名称
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(check_token, name='dispatch')
class list_by_unit_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
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
            print(e)
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response)


# 添加一个模板接口
@method_decorator(csrf_exempt, name='dispatch')
class create_view(CreateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            id = create_uuid()  # 模板id
            name = j.get('name')  # 模板名称
            create_date = int(datetime.now().timestamp())
            is_file = j.get('is_file')
            equipment_name = j.get('equipment_name')
            info_box = j.get('info_box')  # 字段显示区域  # 基本信息 采集信息 [{'name':,'type':,'default':,'box'}]
            data_box = j.get('data_box')
            with conn.cursor() as cur:
                sql = 'insert into template (id,name,is_file,create_date,update_date) ' \
                      'values(%s,%s,%s,%s,%s)'
                params = [id, name, is_file, create_date, create_date]
                cur.execute(sql, params)
                params = [[id, it] for it in equipment_name]
                sql = 'insert into tp_equipment (template_id,equipment_name) values (%s,%s)'
                cur.executemany(sql, params)

                feature = [{'box': 'info_box', **d} for d in info_box] + [{'box': 'data_box', **d} for d in data_box]
                params = []
                for it in feature:
                    label = it.get('name')  # 字段组件标签
                    type = it.get('type')  # 字段类型
                    default = it.get('default')  # 字段选项
                    box = it.get('box')
                    key =create_uuid()
                    #component = component_to_json(type=type, default=default, label=label)  # 字段组件json
                    params.append((id, key, box, None, label, type,default))

            # 执行原生 SQL 查询
                sql = 'insert into template_fields (template_id, field_id, in_box,component, label,type,`default`) ' \
                      'values (%s,%s,%s,%s,%s,%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_insert
            return JsonResponse(response, status=500)


# 更新模板接口
@method_decorator(csrf_exempt, name='dispatch')
class update_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
            # 从请求的 body 中获取 JSON 数据
            id = j.get('id')  # 模板id
            name = j.get('name')
            equipment_name = j.get('equipment_name')
            info_box = j.get('info_box')  # 字段显示区域  # 基本信息 采集信息 [{'name':,'type':,'default':,'box'}]
            data_box = j.get('data_box')
            feature = [{'box': 'info_box', **d} for d in info_box] + [{'box': 'data_box', **d} for d in data_box]

            params = []
            for it in feature:
                label = it.get('name')  # 字段组件标签
                type = it.get('type')  # 字段类型
                default = it.get('default')  # 字段选项
                box = it.get('box')
                params.append((id, create_uuid(), box, label, type,default))

            var = [[id,it] for it in equipment_name]
            # 执行原生 SQL 查询
            with conn.cursor() as cur:
                # 修改主表
                sql = 'update template set name=%s where id=%s'
                cur.execute(sql,[name,id])
                # 修改模板装备表
                sql = 'delete from tp_equipment where template_id=%s'
                cur.execute(sql,[id])
                sql = 'insert into tp_equipment (template_id, equipment_name) values (%s,%s)'
                # 修改模板要素表
                cur.executemany(sql,var)
                sql = 'delete from template_fields where template_id=%s'
                cur.execute(sql,[id])
                sql = 'insert into template_fields (template_id, field_id, in_box, label,type,`default`) ' \
                      'values (%s,%s,%s,%s,%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response, status=200)
        except Exception as e:
            conn.rollback()
            return JsonResponse({'error': str(e)}, status=500)


# 与load_template数据格式不同
# preview数据格式是ngform格式，不做box的区分
@method_decorator(csrf_exempt, name='dispatch')
class preview_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,te.equipment_name,ut.unit_name ' \
                      'from template t ' \
                      'left join unit_template ut on t.id = ut.template_id ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows) == 0:
                    response['msg'], response['code'] = return_msg.no_template, return_msg.S100
                    return JsonResponse(response, status=400)
                equipment = []
                unit = []
                data = {'id': rows[0]['id'], 'name': rows[0]['name'],
                        'feature': [{'prop': 'equipment_name', 'label': '装备名称', 'value': equipment},
                                    {'prop': 'unit_name', 'label': '单位名称', 'value': unit},
                                    {'prop': 'attechment', 'label': '附件', 'value': None}],
                        'info_box':[],
                        'data_box':[]}
                for row in rows:
                    if row['equipment_name'] is not None and row['equipment_name'] not in equipment:
                        equipment.append(row['equipment_name'])
                    if row['unit_name'] is not None and row['unit_name'] not in unit:
                        unit.append(row['unit_name'])

                sql = 'select tf.in_box,tf.component,tf.label,tf.default,tf.type,tf.field_id ' \
                      'from template t ' \
                      'left join template_fields tf on tf.template_id =t.id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                # 通过不同的区域来分组 每个组件
                for row in rows:
                    # 先取出组件数据
                    name = row['label']
                    type = row['type']
                    default = row['default']
                    box_name = row['in_box']
                    key=row['field_id']
                    if box_name in data:
                        data[box_name] .append({'key':key,'name': name, 'type': type, 'default': default})
                response['data'] = data
                return JsonResponse(response)
        except Exception as e:
            print(e)
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
            return JsonResponse(response, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class delete_view(UpdateView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
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
            return JsonResponse(response)
        except self.model.DoesNotExist:
            conn.rollback()
            response['code'], response['msg'] = return_msg.S100, return_msg.fail_delete
            return JsonResponse(response, status=500)


# 导出模板文件，数据格式跟priview_template数据一致，加密生成rc文件
@method_decorator(csrf_exempt, name='dispatch')
class export_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = return_msg.bad_request, return_msg.S400
            return JsonResponse(response, status=400)
        try:
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select t.id,t.name,t.is_file,te.equipment_name,ut.unit_name ' \
                      'from template t ' \
                      'left join tp_equipment te on t.id = te.template_id ' \
                      'left join unit_template ut on t.id = ut.template_id ' \
                      'where t.id=%s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = {'id': rows[0]['id'], 'name': rows[0]['name'], 'equipment_name': [], 'unit_name': []}
                for row in rows:
                    data['equipment_name'].append(row['equipment_name'])
                    data['unit_name'].append(row['unit_name'])
                data['equipment_name'] = list(set(data['equipment_name']))
                data['unit_name'] = list(set(data['unit_name']))
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
                if 'data_box' in data:
                    data['data_box']['list'].append(table)
                response['data'] = data

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
                response['Access-Control-Expose-Headers'] = '*'
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(file_name)}'
                return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.row_none
            print(e)
            return JsonResponse(response, status=500)


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
                return JsonResponse(response, status=200)
            except:
                response['code'], response['msg'] = return_msg.S100, return_msg.illegal_rc
                return JsonResponse(response, status=500)
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)


# 下载模板采集要素
@method_decorator(csrf_exempt, name='dispatch')
class export_field_view(DetailView):
    def get(self, request, *args, **kwargs):
        response = create_return_json()
        try:

            file_path = os.path.join(TEMPLATE_ROOT, '模板文件.xlsx')
            if os.path.exists(file_path):
                file_name = quote('模板文件.xlsx')
                # 直接在FileResponse内部打开文件
                response = FileResponse(open(file_path, 'rb'))
                response['content_type'] = "application/vnd.ms-excel"
                response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'{}'.format(file_name)
                return response

            # type = request.GET.get('type')
            # if type == 'info':  # 下载要素模板
            #     file_path = os.path.join(settings.FILE_ROOT, '要素模板.xlsx')
            #     if os.path.exists(file_path):
            #         file_name = quote('要素模板.xlsx')
            #         # 直接在FileResponse内部打开文件
            #         response = FileResponse(open(file_path, 'rb'))
            #         response['content_type'] = "application/vnd.ms-excel"
            #         response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'{}'.format(file_name)
            #         return response
            # elif type == 'data':  # 下载数据采集要素模板
            #     file_path = os.path.join(settings.FILE_ROOT, '数据采集要素模板.xlsx')
            #     if os.path.exists(file_path):
            #         file_name = quote('数据采集模板.xlsx')
            #         # 直接在FileResponse内部打开文件
            #         response = FileResponse(open(file_path, 'rb'))
            #         response['content_type'] = "application/vnd.ms-excel"
            #         response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'{}'.format(file_name)
            #         return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return HttpResponse("error", status=500)


# 导入模板采集要素
@method_decorator(csrf_exempt, name='dispatch')
class import_field_view(DetailView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_return_json()
        try:
            template_id = request.GET.get('template_id')
            box = request.GET.get('box')
            file = request.FILES.get('file')
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

                # 添加一个新的列 'key'，用来表示 'label' 字段的英文名
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

                df['key'] = df['name'].apply(convert_to_english)
                # 将 DataFrame 转换为字典列表
                data = df.to_dict('records')
                for it in data:
                    it['template_id'] = template_id
                    it['box'] = box
                response['data'] = data
                return JsonResponse(response, status=200)


        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)
