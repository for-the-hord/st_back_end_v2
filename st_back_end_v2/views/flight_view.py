# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: flight_view.py
@time: 2023/4/7 9:23
@description:飞参数据
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
from django.core.files.storage import default_storage

from pypinyin import lazy_pinyin
import pandas as pd

from django.http import FileResponse, HttpResponse, Http404, StreamingHttpResponse
from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from .. import settings
from ..settings import FILE_ROOT, TEMP_ROOT, BACKUP_ROOT, FLIGHT_ROOT
from st_back_end_v2.utils.utils import create_uuid, return_msg, create_response, rows_as_dict, FERNET_KEY, \
    calibration, rename_file_with_uuid, ZipUtils


# 获取所有飞参数据列表接口
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
            with conn.cursor() as cur:
                # 创建临时表 存放树的节点
                sql = 'create TEMPORARY table node(id VARCHAR(32))'
                cur.execute(sql)
                params = [mission_id]
                sql = 'insert into node (id) select id from (with RECURSIVE temp as ' \
                      '(select m.* from mission m where m.id=%s ' \
                      'union all select m.* from mission m ' \
                      'inner join temp on m.parent_id =temp.id)  ' \
                      'select id from temp) as t'

                cur.execute(sql, params)

                # 计算满足条件的 count
                sql = 'select count(distinct f.id) as count ' \
                      'from flight f ' \
                      'left join node n on n.id = f.mission_id ' \
                      'order by f.create_date desc'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                # 查询满足条件的数据
                sql = 'select f.id,f.name,f.create_date ' \
                      'from flight f ' \
                      'left join node n on n.id = f.mission_id ' \
                      'order by f.create_date desc ' \
                      'limit %s offset %s'
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = []
                for row in rows:
                    record = {'id': row['id'], 'name': row['name'],'unit_name':None,
                              'create_date': datetime.fromtimestamp(
                                  0 if (re := row.get('create_date')) is None else re).strftime('%Y-%m-%d %H:%M:%S')}
                    data.append(record)

                # 构造返回数据
                response['data'] = {'records': data, 'title': None, 'total': count}
                return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            print(e)
            return JsonResponse(response, status=500)


# 导入飞参文件
@method_decorator(csrf_exempt, name='dispatch')
class import_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            mission_id = request.POST.get('mission_id')
            files = request.FILES.getlist('files')  # 导入压缩包
            params = []
            create_date = datetime.now().timestamp()
            # 重新命名文件
            for file in files:
                file_name, id = rename_file_with_uuid(file.name)
                params.append([id, file.name, mission_id, file_name, create_date])
                file_path = os.path.join(FLIGHT_ROOT, file_name)
                with default_storage.open(file_path, 'wb') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
            with conn.cursor() as cur:
                sql = 'insert into flight (id,name,mission_id,storage_name,create_date) values (%s,%s,%s,%s,%s)'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            # 删除临时文件和目录
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.illegal_rd
            return JsonResponse(response, status=500)


# 下载飞参数据
@method_decorator(csrf_exempt, name='dispatch')
class export_view(DetailView):
    def get(self, request, *args, **kwargs):
        response = create_response()
        try:
            id = request.GET.get('id')
            with conn.cursor() as cur:
                sql = 'select storage_name,name as file_name from flight where id =%s'
                cur.execute(sql,[id])
                rows = rows_as_dict(cur)
            zip_utils = ZipUtils()
            for file in rows:
                tmp_dl_path = os.path.join(FLIGHT_ROOT, file['storage_name'])
                zip_utils.to_zip(tmp_dl_path, file['storage_name'])
            response = StreamingHttpResponse(zip_utils.zip_file, content_type='application/zip')
            response['Access-Control-Expose-Headers'] = '*'
            response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote("下载")}.zip'
            return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return HttpResponse("error", status=500)


# 批量下载飞参数据
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
            in_clause = ','.join([f'"{it}"' for it in ids])
            with conn.cursor() as cur:
                sql = f'select storage_name,name as file_name from flight where id in ({in_clause})'
                cur.execute(sql)
                rows = rows_as_dict(cur)
            zip_utils = ZipUtils()
            for file in rows:
                tmp_dl_path = os.path.join(FLIGHT_ROOT, file['storage_name'])
                zip_utils.to_zip(tmp_dl_path, file['storage_name'])
            response = StreamingHttpResponse(zip_utils.zip_file, content_type='application/zip')
            response['Access-Control-Expose-Headers'] = '*'
            response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote("下载")}.zip'
            return response
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return HttpResponse("error", status=500)


# 删除飞行数据
@method_decorator(csrf_exempt, name='dispatch')
class delete_view(DetailView):
    def post(self, request, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
        except json.JSONDecodeError:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)
        try:
            ids = j.get('ids')
            with conn.cursor() as cur:
                sql = 'delete from flight where id=%s'
                cur.executemany(sql, ids)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.inner_error
            return HttpResponse("error", status=500)

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
                sql = 'update flight set mission_id=%s where id = %s'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except self.model.DoesNotExist:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_delete
            return JsonResponse(response, status=500)

