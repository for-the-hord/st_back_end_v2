"""st_back_end_v2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from   .views import field_view,template_view,record_view,login_view,view,unit_view,user_view,role_view,module_view

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html")),
    # 登录+用户管理
    path('api/login', login_view.login.as_view()),
    path('api/user/get_unit', login_view.Login_unit_list_view.as_view()),
    path('api/user/login', login_view.login_without.as_view()),
    path('api/update_sys_info', login_view.sys_info_update_view.as_view()),
    path('api/get_router', login_view.get_router.as_view()),

    path('api/get_user_list', user_view.list_view.as_view()),
    path('api/add_user', user_view.create_view.as_view()),
    path('api/update_user',user_view.update_view.as_view()),
    path('api/del_user',user_view.delete_view.as_view()),
    path('api/reset',user_view.reset_view.as_view()),
    path('api/upload', view.upload_file_view.as_view()),
    # 模板管理
    path('api/get_template_list', template_view.list_view.as_view()),
    path('api/get_template',template_view.item.as_view()),
    path('api/add_template', template_view.create_view.as_view()),
    path('api/update_template', template_view.update_view.as_view()),
    path('api/preview_template', template_view.preview_view.as_view()),
    # path('api/load_template', TemplateLoadView2.as_view()),
    path('api/del_template', template_view.delete_view.as_view()),
    path('api/export_template', template_view.export_view.as_view()),
    path('api/import_template', template_view.import_view.as_view()),
    path('api/import_field', template_view.import_field_view.as_view()),
    path('api/export_field', template_view.export_field_view.as_view()),

    path('api/get_field_list', field_view.list_view.as_view()),
    path('api/add_field', field_view.create_view.as_view()),
    path('api/del_field', field_view.delete_view.as_view()),

    # 数据管理
    path('api/get_record_list', record_view.list_view.as_view()),
    path('api/get_record',record_view.item.as_view()),
    path('api/add_record', record_view.create_view.as_view()),
    path('api/update_record', record_view.update_view.as_view()),
    path('api/del_record', record_view.delete_view.as_view()),
    path('api/get_template_by_unit',template_view.list_by_unit_view.as_view()),
    path('api/export_record', record_view.export_view.as_view()),
    path('api/import_record', record_view.import_view.as_view()),

    #单位管理
    path('api/get_unit_list', unit_view.list_view.as_view()),
    # path('api/get_unit', unit_view.item.as_view()),
    path('api/add_unit', unit_view.create_view.as_view()),
    path('api/update_unit', unit_view.update_view.as_view()),
    path('api/del_unit', unit_view.delete_view.as_view()),

    # 角色管理
    path('api/get_role_list', role_view.list_view.as_view()),
    path('api/get_role',role_view.item.as_view()),
    path('api/add_role', role_view.create_view.as_view()),
    path('api/update_role', role_view.update_view.as_view()),
    path('api/del_role', role_view.delete_view.as_view()),

    # 模块
    path('api/get_menu_list', module_view.list_view.as_view()),
]
