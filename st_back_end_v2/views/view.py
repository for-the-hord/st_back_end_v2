# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: template_view.py
@time: 2023/4/7 9:21
@description:
"""

import os

from django.core.files.storage import default_storage
from django.db import connection as conn
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


from ..tools import create_uuid, return_msg, create_return_json

# 上传接口
@method_decorator(csrf_exempt, name='dispatch')
class upload_file_view(View):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        if request.method == 'POST':
            file = request.FILES.get('file')
            file_binary = file.read()
            if file:
                try:
                    # 定义文件保存的相对路径
                    relative_path = 'media'
                    file_path = os.path.join(relative_path, file.name)

                    # 使用Django的default_storage保存文件
                    with default_storage.open(file_path, 'wb') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    id = create_uuid()
                    with conn.cursor() as cur:
                        sql = 'insert into file (id,name) values (%s,%s)'
                        # sql = 'update template set file=%s where id=%s'
                        params = [file_binary,id]
                        cur.execute(sql, params)
                    response['data'] = {'id': id, 'name': file.name}
                except Exception as e:
                    print(e)

                return JsonResponse(response)
            else:
                response['code'], response['msg'] = return_msg.S100, return_msg.no_file
                return JsonResponse(response)
        else:
            response['code'], response['msg'] = return_msg.S100, return_msg.params_error
            return JsonResponse(response)
