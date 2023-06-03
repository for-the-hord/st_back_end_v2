# -*- coding: utf-8 -*-
"""
@author: word
@project: ST
@file: tools
@time: 2023/4/3 8:42
@description: 
"""
import uuid


class MSG:
    S200 = 200  # 成功返回
    S100 = 100  # 失败返回
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


def create_uuid():
    """
    创建一个uuid
    Returns:
        uuid:32位字符串
    """
    return str(uuid.uuid1()).replace('-', '')


return_msg = MSG()

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
            "multiple": False,
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
        "label": "标签",
        "options": {
            "textAlign": "center",
            "tooptip": "",
            "hidden": False,
            "showRequiredMark": False,
            "dynamicHide": False,
            "dynamicHideValue": "",
            "labelWidth": -1
        },
        "key": "text_1685259188567"
    }
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


def process_input(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['defaultValue'] = options.get('default_value', None)
    json['options']['maxLength'] = options.get('max_length', None)


def process_select(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['valueKey'] = 'value'
    # select 组件 default为数组
    li = [{'value': it, 'label': it} for it in options.get('list')]
    json['options']['options'] = li
    json['defaultValue'] = options.get('default_value')


def process_number(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['defaultValue'] = options.get('default_value', None)
    json['options']['min'] = options.get('min', None)
    json['options']['max'] = options.get('max', None)
    json['options']['precision'] = options.get('precision')


def process_textarea(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['rows'] = options.get('rows', 9)


def process_radio(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['model'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['options']['valueKey'] = 'value'
    # radio 组件 default为数组
    li = [{'value': it, 'label': it} for it in options.get('default_value')]
    json['options']['options'] = li


def process_label(json, options):
    type = json['type']
    json['key'] = f'{type}_{str(uuid.uuid4().hex)}'
    json['label'] = options.get('default_value')


def process_default(json, options):
    pass


# 使用字典映射处理函数
type_handlers = {
    'input': process_input,
    'select': process_select,
    'number': process_number,
    'textarea': process_textarea,
    'radio': process_radio,
    'label': process_label
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
        options = kwargs.get('options')
        handler(json, options)
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