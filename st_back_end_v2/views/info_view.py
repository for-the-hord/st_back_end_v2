# -*- coding: utf-8 -*-
"""
@author: jerry
@project: st_back_end_v2
@file: info_view.py
@time: 23/07/10 16:26
@description: 情报线
"""

import json
import random
import time
from datetime import datetime
import uuid

from django.db import connection as conn
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from django.views.generic import ListView, CreateView, DetailView


from st_back_end_v2.utils.utils import create_uuid, return_msg, create_response, rows_as_dict


# 获取情报流转关系
class chart_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            with conn.cursor() as cur:
                sql = 'select n.id,n.name as text,n.ip,n.type from seats n'
                cur.execute(sql)
                nodes = rows_as_dict(cur)

                sql = '''select  o.to_id 'to',n.name as to_name ,o.from_id as 'from',no.name as from_name,
                     o.to_date,o.from_date,i.id,i.id as 'text'  
                     from info_seats o 
                     left join info i on i.id=o.info_id 
                     left join seats n on  o.to_id=n.id 
                     left join seats no on no.id=o.from_id'''

                cur.execute(sql)
                lines = rows_as_dict(cur)
            node_color = {}
            for item in nodes:
                # 如果当前 id 没有对应的颜色，就生成一个新的颜色
                if item['type'] not in node_color:
                    color = '#{:06x}'.format(random.randint(0, 256 ** 3 - 1))  # 生成随机颜色
                    node_color[item['type']] = color  # 保存 id 和对应的颜色

                # 在 item 字典中添加颜色属性
                item['color'] = node_color[item['type']]

            color_map = {}
            for item in lines:
                # 如果当前 id 没有对应的颜色，就生成一个新的颜色
                if item['id'] not in color_map:
                    color = '#{:06x}'.format(random.randint(0, 256 ** 3 - 1))  # 生成随机颜色
                    color_map[item['id']] = color  # 保存 id 和对应的颜色

                # 在 item 字典中添加颜色属性
                item['color'] = color_map[item['id']]
            # 构造返回数据
            response['data'] = {'rootId': nodes[0]['id'] if len(nodes) != 0 else None, 'nodes': nodes, 'lines': lines}
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 获取情报线列表
class list_line_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition =j.get('condition')
            with conn.cursor() as cur:
                sql = 'select count(*) as count from info_seats'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                sql = 'select o.to_id ,n.name as to_name ,o.from_id,o.id,no.name as from_name,' \
                      ' o.to_date,o.from_date,i.id as info_id,i.code  ' \
                      'from info_seats o ' \
                      'left join info i on i.id=o.info_id ' \
                      'left join seats n on  o.to_id=n.id ' \
                      'left join seats no on no.id=o.from_id ' \
                      'limit %s offset %s'
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = rows
            # 构造返回数据
                response['data'] = {'records': data, 'title': None, 'total': count}
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 获取单个线
class line_item(DetailView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select from_id, to_id, info_id, from_date, to_date from info_seats  where id = %s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows):
                    response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                    return JsonResponse(response, status=100)
                else:
                    data = rows[0]
                    response['data'] = data
                    return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 添加情报线
class create_line_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            from_id = j.get('from_id')
            to_id = j.get('to_id')
            to_date = j.get('to_date')
            from_date = j.get('from_date')
            info_id = j.get('info_id')
            with conn.cursor() as cur:

                line_id = create_uuid()
                sql = 'insert into info_seats (id,from_id, to_id, info_id, from_date, to_date) values (%s,%s,%s,%s,%s,%s)'
                params = [line_id,from_id,to_id,info_id,from_date,to_date]
                cur.execute(sql,params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)


# 更新情报线
class update_line_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            info_id = j.get('id')
            from_id = j.get('from_id')
            to_id = j.get('to_id')
            to_date = j.get('to_date')
            from_date = j.get('from_date')

            with conn.cursor() as cur:
                sql = 'update info_seats set from_id=%s, to_id=%s, info_id=%s, from_date=%s, to_date=%s where id=%s'
                params = [from_id, to_id, info_id, from_date, to_date,id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 删除情报线
class delete_line_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with conn.cursor() as cur:
                # 这里删除情报线，并不删除情报本身
                sql = 'delete from info_seats where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)


# 获取情报线列表
class list_view(ListView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            page_size = j.get('page_size')
            page_index = j.get('page_index')
            condition =j.get('condition')
            with conn.cursor() as cur:
                sql = 'select count(*) as count from info'
                cur.execute(sql)
                rows = rows_as_dict(cur)
                count = rows[0]['count']

                sql = 'select * ' \
                      'from info i  ' \
                      'limit %s offset %s'
                params = [page_size, (page_index - 1) * page_size]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                data = rows
            # 构造返回数据
                response['data'] = {'records': data, 'title': None, 'total': count}
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 获取单个线
class item(DetailView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            with conn.cursor() as cur:
                sql = 'select * from info i where i.id = %s'
                params = [id]
                cur.execute(sql, params)
                rows = rows_as_dict(cur)
                if len(rows):
                    response['code'], response['msg'] = return_msg.code_100, return_msg.row_none
                    return JsonResponse(response, status=100)
                else:
                    data = rows[0]
                    response['data'] = data
                    return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

# 添加情报线
class create_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            target_name = j.get('target_name')
            target_location =j.get('target_location')
            target_info= j.get('target_info')
            unit_name= j.get('unit_name')
            training_date= j.get('unit_name')
            batch_no= j.get('batch_no')
            scout_platform= j.get('scout_platform')
            troop_name= j.get('troop_name')
            scout_no= j.get('scout_no')
            scout_type= j.get('scout_type')
            scout_date= j.get('scout_date')
            scout_lat= j.get('scout_lat')
            scout_lon= j.get('scout_lon')
            scout_alt= j.get('scout_alt')
            target_report_date= j.get('target_report_date')
            with conn.cursor() as cur:
                id = create_uuid()
                sql = 'insert into info (id, target_name, target_location, target_info, unit_name, ' \
                      'training_date, batch_no, scout_platform, troop_name, scout_no, scout_type, ' \
                      'scout_date, scout_lat, scout_lon, scout_alt, target_report_date) values ' \
                      '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                params = [id,target_name, target_location, target_info, unit_name,
                      training_date, batch_no, scout_platform, troop_name, scout_no, scout_type,
                      scout_date, scout_lat, scout_lon, scout_alt, target_report_date]
                cur.execute(sql,params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)


# 更新情报线
class update_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            id = j.get('id')
            target_name = j.get('target_name')
            target_location =j.get('target_location')
            target_info= j.get('target_info')
            unit_name= j.get('unit_name')
            training_date= j.get('unit_name')
            batch_no= j.get('batch_no')
            scout_platform= j.get('scout_platform')
            troop_name= j.get('troop_name')
            scout_no= j.get('scout_no')
            scout_type= j.get('scout_type')
            scout_date= j.get('scout_date')
            scout_lat= j.get('scout_lat')
            scout_lon= j.get('scout_lon')
            scout_alt= j.get('scout_alt')
            target_report_date= j.get('target_report_date')

            with conn.cursor() as cur:
                sql = 'update info set target_name=%s, target_location=%s, target_info=%s, unit_name=%s, ' \
                      'training_date=%s, batch_no=%s, scout_platform=%s, troop_name=%s, scout_no=%s, scout_type=%s, ' \
                      'scout_date=%s, scout_lat=%s, scout_lon=%s, scout_alt=%s, target_report_date=%s where id=%s'
                params = [target_name, target_location, target_info, unit_name,
                      training_date, batch_no, scout_platform, troop_name, scout_no, scout_type,
                      scout_date, scout_lat, scout_lon, scout_alt, target_report_date,id]
                cur.execute(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)


# 删除情报线
class delete_view(CreateView):
    def post(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        try:
            j = json.loads(request.body)
            ids = j.get('ids')
            with conn.cursor() as cur:
                # 删除情报本身
                sql = 'delete from info where id=%s'
                params = [[it] for it in ids]
                cur.executemany(sql, params)
                # 删除情报线
                sql = 'delete from info_seats where info_id =%s'
                cur.executemany(sql, params)
                conn.commit()
            return JsonResponse(response)
        except Exception as e:
            response['code'], response['msg'] = return_msg.code_100, return_msg.params_error
            return JsonResponse(response, status=500)

class time_offset(DetailView):
    def get(self, request: HttpRequest, *args, **kwargs):
        response = create_response()
        current_time = int(round(time.time()*1000))
        #current_time = time.mktime(current_time.timetuple())
        response['data'] = {'current_time':current_time }
        return JsonResponse(response)



@method_decorator(csrf_exempt, name='dispatch') # 获取目标列表
class get_target_list(View):
    def post(self,  request: HttpRequest):
        response = create_response()

        with conn.cursor() as cur:
            sql = "select distinct(target_name) from info"

            cur.execute(sql)
            rows = sorted([x['target_name'] for x in rows_as_dict(cur)])
        response['data'] = rows
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch') # 获取成果列表
class get_info_list(View):
    def post(self,  request: HttpRequest):
        response = create_response()

        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        with conn.cursor() as cur:
            sql = "select id, target_info, target_report_date  from info where target_name = %s"
            cur.execute(sql,[j.get('target_name')])
            rows = rows_as_dict(cur)
            data = {}
            for x in rows:
                if x.get('target_report_date') not in data:
                    data[x.get('target_report_date')] = {'id':[]}
                data[x.get('target_report_date')]['id'].append({'id':x.get('id'), 'name': x.get('target_info')})
            max_length = max([len(data[x]['id']) for x in data])
            names = ['line'+str(x) for x in range(max_length)]
            line_x = [datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S") for x in data]
            new_values = []
            for i in range(max_length):
                line = []
                for x in data:

                    if len(data[x]['id']) > i:
                        line.append({"id":data[x]['id'][i]['id'], "value":10 + 10 * i, "name":data[x]['id'][i]['name']})
                    else:
                        line.append({"id":0,"value":'-', 'name':''})
                new_values.append(line)
        data = {"names":names, "new_values":new_values, "line_x":line_x}

        response['data'] = data
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch') # 获取成果详情及可选择的来报
class get_info_details(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        with conn.cursor() as cur:
            sql = """
            select i.*,  r.id as report_id, r.report_name , r.report_time, ir.id as relation_id
            from info i left join report r on i.target_name = r.target_name
            left join info_report ir on r.id = ir.report_id and i.id = ir.info_id
            where i.id = %s;
            """
            cur.execute(sql,[j.get('id')])
            rows = rows_as_dict(cur)
        data = []
        for x in rows:
            if x['report_time']:
                if x['report_time'] <= x['target_report_date']:
                    data.append(x)
        other_key = ['report_id', 'report_name', 'relation_id', 'report_time']

        info_details = [{'key':x, 'value':rows[0][x]} for x in rows[0] if x not in other_key]


        check_box = [{'id':x['report_id'], 'value':x['report_name'], 'report_time':x['report_time'],'checked':True if x['relation_id'] else False} for x in data if x['report_id']]

        data = {'info_details':info_details, 'check_box':check_box}

        response['data'] = data
        return JsonResponse(response)



@method_decorator(csrf_exempt, name='dispatch') # 勾选来报记录关系
class select_report(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        info_id = j.get('info_id')
        report_id = j.get('report_id')
        val = []
        for x in report_id:
            val.append([str(uuid.uuid4()), info_id, x])

        try:
            with conn.cursor() as cur:
                sql = "delete from info_report where info_id = %s"
                cur.execute(sql, info_id)


                sql = "insert into info_report (id, info_id, report_id) values (%s,%s,%s);"
                params = val
                cur.executemany(sql, params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)
        response['data'] = True
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch') # 获取来报详情
class get_report_details(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        with conn.cursor() as cur:
            sql = "select * from report where id = %s;"
            cur.execute(sql, [j.get('id')])
            rows = rows_as_dict(cur)
        data = [{'key': x, 'value': rows[0][x]} for x in rows[0]]
        response['data'] = data
        return JsonResponse(response)







# 前端没写


@method_decorator(csrf_exempt, name='dispatch') # 获取成果详情key，新建成果之前请求
class get_info_key(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        with conn.cursor() as cur:
            sql = 'select * from info limit 1'
            cur.execute(sql)
            rows = rows_as_dict(cur)

        data = [{'key':x, "value":""} for x in rows if x != 'id']
        response['data'] = data
        return JsonResponse(response)



@method_decorator(csrf_exempt, name='dispatch') # 新建成果
class add_info(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        try:
            with conn.cursor() as cur:
                key =  "id," + ','.join(j.get('report').keys())
                value = str(uuid.uuid4()) + ',' + ','.join(j.get('report').values())
                sql = "insert into info(%s) values (%s);"
                cur.execute(sql, [key, value])
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)
        response['data'] = True
        return JsonResponse(response)




# @method_decorator(csrf_exempt, name='dispatch')
# class update_info(View):
#     def post(self,  request: HttpRequest):
#         response = create_response()
#         try:
#             j = json.loads(request.body)
#         except:
#             response['msg'], response['code'] = 'bad request！', return_msg.code_400
#             return JsonResponse(response, status=400)
#
#         try:
#             with conn.cursor() as cur:
#                 update_query = ','.join(["{}={}".format(x, list(j.get('report').values())[index]) for index, x in enumerate(list(j.get('report').keys()))])
#                 sql = "update info set %s where id = %s;"
#                 cur.execute(sql, [update_query, j.get('id')])
#                 conn.commit()
#         except Exception as e:
#             conn.rollback()
#             response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
#             return JsonResponse(response, status=500)
#         response['data'] = True
#         return JsonResponse(response)



@method_decorator(csrf_exempt, name='dispatch') # 删除成果，目前没处理有关联来报
class delete_info(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)


        try:
            with conn.cursor() as cur:

                sql = "delete from info where id = %s;"
                cur.execute(sql, [j.get('id')])
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)
        response['data'] = True
        return JsonResponse(response)




@method_decorator(csrf_exempt, name='dispatch') # 获取来报数据的key，新建来报之前请求
class get_report_key(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        with conn.cursor() as cur:
            sql = 'select * from report limit 1'
            cur.execute(sql)
            rows = rows_as_dict(cur)

        data = [{'key':x, "value":""} for x in rows if x != 'id']
        response['data'] = data
        return JsonResponse(response)



@method_decorator(csrf_exempt, name='dispatch') # 新建来报
class add_report(View):
    def post(self,  request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        try:
            with conn.cursor() as cur:
                key =  "id," + ','.join(j.get('report').keys())
                value = str(uuid.uuid4()) + ',' + ','.join(j.get('report').values())
                sql = "insert into report(%s) values (%s);"
                cur.execute(sql, [key, value])
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)
        response['data'] = True
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch')  # 删除来报，目前没处理和成果关联
class delete_report(View):
    def post(self, request: HttpRequest):
        response = create_response()
        try:
            j = json.loads(request.body)
        except:
            response['msg'], response['code'] = 'bad request！', return_msg.code_400
            return JsonResponse(response, status=400)

        try:
            with conn.cursor() as cur:

                sql = "delete from report where id = %s;"
                cur.execute(sql, [j.get('id')])
                conn.commit()
        except Exception as e:
            conn.rollback()
            response['code'], response['msg'] = return_msg.code_100, return_msg.fail_insert
            return JsonResponse(response, status=500)
        response['data'] = True
        return JsonResponse(response)