# -*- coding: utf-8 -*-
"""
@author: word
@project: ST
@file: tools
@time: 2023/4/3 8:42
@description: 
"""
import os
import uuid
import jwt


from django.db import connection as conn
from django.http import JsonResponse

class MSG:
    S200 = 200  # 成功返回
    S100 = 100  # 失败返回
    S101 = 101
    S401 = 401  # 验证失败
    S400 = 400 #
    bad_request='bad request！'
    succ = '操作成功'
    inner_error = '内部错误，请联系管理员！'
    params_error = '参数错误！'
    row_none = '暂无数据！'
    conflict = '数据冲突'
    token_invalid = '无效的token值'
    token_expired = 'token已过期'
    no_user = '用户不存在'
    exist = '已存在该名称的代码！'
    exist_template = '已存在重复的模板名称！'
    exist_equipment = '已存在重复的装备名称！'
    exist_some = '存在相同指标'
    unaccess = '无权限访问'
    timeout = '验证码已过期！'
    verify_failure = '验证码错误！'
    no_file = '无该文件！'
    exist_doing = '有未完成转学申请，请勿重复申请'
    exist_score = '已存在该同学的成绩！'
    exist_records = '已存在该同学当前方案的选课记录！'
    no_access = '无权限修改他人的考试方案'
    password_error = '输入密码错误！'
    not_in_time = '未到选课时间'
    upload_error = '导入失败！'
    none_update = '无效的更新！'
    no_delete = '无法删除已使用方案'
    no_modify_scheme = '选课方案已被使用！'
    fail_insert = '写入数据失败！'
    fail_update = '更新数据失败！'
    fail_delete = '删除数据失败！'
    exist_unit = '已存在重复的单位名称！'
    illegal_rc = '非法的模板文件！'
    illegal_rd = '非法的数据文件！'
    no_template = '找不到模板数据！'
    data_error = '数据格式错误！'

return_msg = MSG()
def create_uuid():
    """
    创建一个uuid
    Returns:
        uuid:32位字符串
    """
    return str(uuid.uuid1()).replace('-', '')

class Calibration:
    """
    数据清洗校验规则，存放正则的表达式
    """
    # 经纬度正则规则
    _lonlat = [
    r'^(\d{1,3}°\d{1,2}′\d{1,2}″$)', # DDD°MM′SS″
    r'^-?\d{1,3}\.\d*$' # ddd.ddddddd
    ]

    # 时间正则规则
    _date = []

    _di = {'lonlat':_lonlat,'date':_date}

    def get(self,type):
        return self._di.get(type,[])

calibration = Calibration()

COMPONENT = {
    'input': {
        "type": "input",
        "label": "输入框",
        "options": {
            "type": "text",
            "width": "100%",
            "defaultValue": "",
            "placeholder": "请输入",
            "clearable": False,
            "maxLength": 0,
            "prepend": "",
            "append": "",
            "tooptip": "",
            "hidden": False,
            "disabled": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "input_1685102799060",
        "key": "input_1685102799060",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "blur"
                ]
            }
        ]
    },

    'select': {
        "type": "select",
        "label": "下拉选择器",
        "options": {
            "width": "100%",
            "multiple": True,
            "disabled": False,
            "clearable": False,
            "hidden": False,
            "placeholder": "请选择",
            "valueKey": "value",
            "tooptip": "",
            "dynamic": 0,
            "remoteFunc": "",
            "dataPath": "",
            "remoteValue": "",
            "remoteLabel": "",
            "dictType": "",
            "linkage": False,
            "options": [
                {
                    "value": "1",
                    "label": "下拉框1"
                }
            ],
            "showSearch": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "select_1685102771054",
        "key": "select_1685102771054",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "change",
                    "blur"
                ]
            }
        ]
    },

    'number': {
        "type": "number",
        "label": "数字输入框",
        "options": {
            "width": "100%",
            "defaultValue": 0,
            "min": 0,
            "max": 100,
            "precision": 0,
            "tooptip": "",
            "prepend": "",
            "append": "",
            "step": 1,
            "hidden": False,
            "disabled": False,
            "placeholder": "请输入",
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "number_1685102509062",
        "key": "number_1685102509062",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "change",
                    "blur"
                ]
            }
        ]
    },

    'textarea': {
        "type": "textarea",
        "label": "文本框",
        "options": {
            "width": "100%",
            "maxLength": 0,
            "defaultValue": "",
            "rows": 4,
            "clearable": False,
            "tooptip": "",
            "hidden": False,
            "disabled": False,
            "placeholder": "请输入",
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "textarea_1685102515274",
        "key": "textarea_1685102515274",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "blur"
                ]
            }
        ]
    },

    'text': {
        "type": "text",
        "label": "标签",
        "options": {
            "textAlign": "left",
            "tooptip": "",
            "hidden": False,
            "showRequiredMark": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "key": "text_1685102509063",
        "model": "text_1685102509063"
    },

    'radio': {
        "type": "radio",
        "label": "单选框",
        "options": {
            "disabled": False,
            "hidden": False,
            "defaultValue": "",
            "dynamic": 0,
            "tooptip": "",
            "remoteFunc": "",
            "dataPath": "",
            "remoteValue": "",
            "remoteLabel": "",
            "linkage": False,
            "dictType": "",
            "options": [
            ],
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "radio_1685102509062",
        "key": "radio_1685102509062",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "change",
                    "blur"
                ]
            }
        ]
    },

    'label': {
        "type": "text",
        "label": "",
        "options": {
            "textAlign": "center",
            "tooptip": "",
            "hidden": False,
            "showRequiredMark": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "key": ""
    },

    'datePicker':	{
			"type": "datePicker",
			"label": "日期时间选择框",
			"options": {
				"width": "100%",
				"defaultValue": "",
				"rangeDefaultValue": [],
				"range": False,
				"disabled": False,
				"hidden": False,
				"clearable": False,
				"placeholder": "请选择",
				"tooptip": "",
				"rangeStartPlaceholder": "开始时间",
				"rangeEndPlaceholder": "结束时间",
				"format": "yyyy-MM-dd HH:mm:ss",
				"dynamicHide": False,
				"dynamicHideValue": "",
				"labelWidth": -1
			},
			"model": "",
			"key": "",
			"rules": [
				{
					"required": False,
					"message": "必填项",
					"trigger": [
						"change",
						"blur"
					]
				}
			]
		},

    'date': {
        "type": "input",
        "label": "输入框",
        "options": {
            "type": "text",
            "width": "100%",
            "defaultValue": "",
            "placeholder": "请输入时间",
            "clearable": False,
            "maxLength": 0,
            "prepend": "",
            "append": "",
            "tooptip": "",
            "hidden": False,
            "disabled": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "input_1685102799060",
        "key": "input_1685102799060",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "blur"
                ]
            }
        ]
    },

    'lonlat': {
        "type": "input",
        "label": "输入框",
        "options": {
            "type": "text",
            "width": "100%",
            "defaultValue": "",
            "placeholder": "请输入经纬度",
            "clearable": False,
            "maxLength": 0,
            "prepend": "",
            "append": "",
            "tooptip": "",
            "hidden": False,
            "disabled": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "model": "input_1685102799060",
        "key": "input_1685102799060",
        "rules": [
            {
                "required": False,
                "message": "必填项",
                "trigger": [
                    "blur"
                ]
            }
        ]
    },
}

FERNET_KEY = '59XHlCAzuZZatGHt1feL82B8ZxOhclwdPsd4dW2r920='


def create_return_json():
    """
    创建一个返回json
    Returns:

    """
    # return json
    return {
        'code': return_msg.S200,
        'msg': return_msg.succ,
        'data': None
    }


def rows_as_dict(cursor):
    """
    查询结果集转字典
    Args:
        cursor:

    Returns:

    """
    col_names = [i[0].lower() for i in cursor.description]
    return [dict(zip(col_names, row)) for row in cursor]


def process_input(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['defaultValue'] = default


def process_select(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['valueKey'] = 'value'
    # select 组件 default为数组
    if default is not None:
        re_default = default.replace('；', ';')
        # 使用 split() 函数将字符串按英文逗号分割
        options = re_default.split(';')
        li = [{'value': it, 'label': it} for it in options]
    else:
        li=[]
    json['options']['options'] = li


def process_number(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['defaultValue'] = default


def process_textarea(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['rows'] = 8


def process_radio(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['valueKey'] = 'value'
    json['defaultValue'] = default
    # radio 组件 default为数组
    if default is not None:
        re_default = default.replace('；', ';')
        # 使用 split() 函数将字符串按英文逗号分割
        options = re_default.split(';')
        li = [{'value': it, 'label': it} for it in options]
    else:
        li=[]
    json['options']['options'] = li


def process_label(json, default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['label'] = default

def process_datepicker(json,default):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['defaultValue'] = default

def process_default(json, options):
    pass


# 使用字典映射处理函数
type_handlers = {
    'input': process_input,
    'select': process_select,
    'number': process_number,
    'textarea': process_textarea,
    'radio': process_radio,
    'label': process_label,
    'datePicker':process_datepicker,
    'date':process_input,
    'lonlat':process_input,
}


def component_to_json(**kwargs):
    """
    根据组件不同，生成组件的json，包含生成一个唯一key
    :param type:
    :return:
    """
    type = kwargs.get('type', None)
    json = COMPONENT.get(type, None)
    json['label'] = kwargs.get('label')
    if json is not None:
        handler = type_handlers.get(type, process_default)
        default = kwargs.get('default')
        handler(json, default)
    return json

def list_to_tree(data, **kwargs):
    """
    list数据转成tree结构
    Args:
        data: lis数据

    Returns:

    """
    root = []
    node = []

    root_tmp = ()
    if (kwargs.get('parent_value') is None) and (kwargs.get('id_value') is None):
        #  不知道根节点的情况，寻找根节点
        parent_li = []
        id_li = []
        for row in data:
            parent_li.append(row[kwargs.get('parent_key', None)])
            id_li.append(row[kwargs.get('id_key', None)])
        root_tmp = set(parent_li) - set(id_li)
    # 初始化数据，获取根节点和其他子节点list
    for d in data:
        if (kwargs.get('parent_value') is None) and (kwargs.get('id_value') is None):
            #  不知道根节点的情况，寻找根节点
            if d.get(kwargs['parent_key']) in root_tmp:
                root.append(d)
            else:
                node.append(d)
        elif kwargs.get('parent_value') is not None:
            # 知道根节点的父节点
            if d.get(kwargs['parent_key']) == kwargs['parent_value']:
                root.append(d)
            else:
                node.append(d)
        elif kwargs.get('id_value') is not None:
            # 知道根节点的id
            if d.get(kwargs['id_key']) == kwargs['id_value']:
                root.append(d)
            else:
                node.append(d)

    # 排序
    if sort_id := kwargs.get('sort_key', None):
        root = sorted(root, key=lambda x: x[sort_id])
    # 查找子节点
    for p in root:
        add_node(p, node, **kwargs)

    if kwargs.get('label_key'):
        for p in root:
            root_label = p.get(kwargs['label_key'])
            # p['root'] = root_label
            if p['children']:
                find_parent(root_label, p['children'])

    # 无子节点
    if len(root) == 0:
        return node

    return root

def add_node(p, node, **kwargs):
    # 子节点list
    # args = args['args']
    p["children"] = []
    for n in node:
        if n.get(kwargs['parent_key']) == p.get(kwargs['id_key']):
            # n['root'] = p.get(kwargs['label_key'])
            p["children"].append(n)

    # 递归子节点，查找子节点的节点
    for t in p["children"]:
        if not t.get("children"):
            t["children"] = []
        t["children"].append(add_node(t, node, **kwargs))

    if sort_id := kwargs.get('sort_key', None):
        p['children'] = sorted(p['children'], key=lambda x: x[sort_id])
    # 退出递归的条件
    if len(p["children"]) == 0:
        p.pop('children')
        # p['children'] = None
        return


def find_parent(root, node):
    for p in node:
        p['root_label'] = root
        if p['children']:
            find_parent(root, p['children'])


def check_token(view_func):
    def wrapped(request, *args, **kwargs):
        # 获取前端传过来的token
        response = create_return_json()
        token = request.headers.get('AUTHORIZATION', '').split(' ')
        if len(token) > 1:
            token = token[1]
        else:
            return JsonResponse(response, status=401)
        try:
            # 解码token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            # 根据payload中的user_id进行用户认证
            user_id = payload['user_id']
            with conn.cursor() as cur:
                sql = 'select name from user u ' \
                      'where u.id=%s'
                params = [user_id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
            user = User.objects.get(id=user_id)

            # 将user添加到请求中，方便视图函数中使用
            request.user = user

            return view_func(request, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            # token过期
            response['code'], response['msg'] = return_msg.S401, return_msg.token_expired
            return JsonResponse(response, status=401)

        except jwt.InvalidSignatureError:
            # token无效
            response['code'], response['msg'] = return_msg.S401, return_msg.token_invalid
            return JsonResponse(response, status=401)

        except :
            # 用户不存在
            response['code'], response['msg'] = return_msg.S401, return_msg.no_user
            return JsonResponse(response, status=401)

    return wrapped

def rename_file_with_uuid(original_file_name):

    uuid_str = str(uuid.uuid4())
    # 使用os.path.splitext函数获取文件的扩展名
    _, file_extension = os.path.splitext(original_file_name)

    new_file_name = uuid_str + file_extension
    return new_file_name,uuid_str