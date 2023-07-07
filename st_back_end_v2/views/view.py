# -*- coding: utf-8 -*-
"""
@author: user
@project: ST
@file: template_view.py
@time: 2023/4/7 9:21
@description:
"""

import os
from urllib.parse import quote

from django.core.files.storage import default_storage
from django.http import JsonResponse, FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..settings import FILE_ROOT
from ..tools import return_msg, create_return_json, rename_file_with_uuid


# 上传接口
@method_decorator(csrf_exempt, name='dispatch')
class upload_file_view(View):
    def post(self, request, *args, **kwargs):
        response = create_return_json()
        try:
            file = request.FILES.get('file')
        # 重新命名文件
            file_name,id = rename_file_with_uuid(file.name)
            file_path = os.path.join(FILE_ROOT, file_name)
            with default_storage.open(file_path, 'wb') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            response['data'] = {'id': file_name,'name':file.name}
            return JsonResponse(response, status=200)
        except Exception as e:
            response['code'], response['msg'] = return_msg.S100, return_msg.inner_error
            return JsonResponse(response, status=500)

# 下载附件接口
@method_decorator(csrf_exempt, name='dispatch')
class download_file_view(View):
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id')
        name = request.GET.get('name')
        # 定义文件保存的相对路径,这里为了确保文件不会被覆盖，将上传的文件名换成id，同时数据库做id和name的存储

        file_path = os.path.join(FILE_ROOT, id)
        if os.path.exists(file_path):
            file_name = quote(name)
            # 直接在FileResponse内部打开文件
            response = FileResponse(open(file_path, 'rb'),content_type="application/octet-stream")
            response['Access-Control-Expose-Headers'] = '*'
            response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(file_name)
            return response
        else:
            return  Http404