import os
import cx_Oracle
import redis
import traceback
from flask import (
    Flask, Blueprint,
    send_from_directory
)
from flask_json import FlaskJSON, as_json
from datetime import datetime


app = Flask(__name__)
FlaskJSON(app)
bpout = Blueprint('out', __name__, url_prefix='/maintain/invtOut', static_folder='static')

username = os.getenv('ORCL_USERNAME') or 'username'
password = os.getenv('ORCL_PASSWORD') or 'password'
dbUrl = os.getenv('ORCL_DBURL') or '127.0.0.1:1521/orcl'
redisHost = os.getenv('REDIS_HOST') or '127.0.0.1'
redisPort = os.getenv('REDIS_PORT') or 6379

redisPool = redis.ConnectionPool(host=redisHost, port=redisPort)
redisConn = redis.Redis(connection_pool=redisPool)

def executeSql(sql, **kw):
    print(sql)
    con = cx_Oracle.connect(username, password, dbUrl)
    cursor = con.cursor()
    result = None
    try:
        cursor.prepare(sql)
        cursor.execute(None, kw)
        result = cursor.fetchall()
        con.commit()
    except Exception:
        traceback.print_exc()
        con.rollback()
    finally:
        cursor.close()
        con.close()
    return result


@bpout.route('/getInvtInfo/<companyCode>/<password>/<logisticsNo>', methods=['GET'])
@as_json
def outInvtInfo(companyCode, password, logisticsNo):
    res = {}
    sql = '''
        select count(1) from user_user t
        where t.login_name = :loginName
        and t.password = :password
    '''
    result = executeSql(sql, loginName=companyCode, password=password)

    if int(result[0][0]) <= 0:
        res['success'] = False
        res['info'] = '企业代码或者密码错误，或者联系电子口岸客服开通清关接口权限!'
        return res

    sql = '''
        select t.order_no, t.logistics_no, t.invt_no, t.bill_no, time_to_char(t.sys_date),
        t.app_status, t.rtn_status, t.rtn_info, time_to_char(t.rtn_time),
        t.cus_status, time_to_char(t.cus_time), t.cop_no
        from ceb3_invt_head t
        where t.logistics_no = :logisticsNo
        and (t.ebc_code = :ebcCode
        or t.ebp_code = :ebpCode
        or t.logistics_code = :logisticsCode
        or t.agent_code = :agentCode)
    '''
    result = executeSql(sql, logisticsNo=logisticsNo, ebcCode=companyCode, ebpCode=companyCode, logisticsCode=companyCode, agentCode=companyCode)

    if result is None or len(result) == 0:
        res['success'] = False
        res['info'] = '未找到运单号对应的清单信息'
        return res
    else:
        res['success'] = True
        res['info'] = '获取清单信息成功!'
        res['data'] = []
        for invt in result:
            invtData = {}
            invtData['orderNo'] = invt[0]
            invtData['logisticsNo'] = invt[1]
            invtData['invtNo'] = invt[2]
            invtData['billNo'] = invt[3]
            invtData['sysDate'] = invt[4]
            invtData['appStatus'] = invt[5]
            invtData['rtnStatus'] = invt[6]
            invtData['rtnInfo'] = invt[7]
            invtData['rtnTime'] = invt[8]
            invtData['cusStatus'] = invt[9]
            invtData['cusTime'] = invt[10]
            invtData['copNo'] = invt[11]
            res['data'].append(invtData)


    return res


@bpout.route('/getInvtInfoByOrderNo/<companyCode>/<password>/<orderNo>', methods=['GET'])
@as_json
def outInvtInfoByOrderNo(companyCode, password, orderNo):
    res = {}
    sql = '''
        select count(1) from user_user t
        where t.login_name = :loginName
        and t.password = :password
    '''
    result = executeSql(sql, loginName=companyCode, password=password)

    if int(result[0][0]) <= 0:
        res['success'] = False
        res['info'] = '企业代码或者密码错误，或者联系电子口岸客服开通清关接口权限!'
        return res

    sql = '''
        select t.order_no, t.logistics_no, t.invt_no, t.bill_no, time_to_char(t.sys_date),
        t.app_status, t.rtn_status, t.rtn_info, time_to_char(t.rtn_time),
        t.cus_status, time_to_char(t.cus_time), t.cop_no
        from ceb3_invt_head t
        where t.order_no = :orderNo
        and (t.ebc_code = :ebcCode
        or t.ebp_code = :ebpCode
        or t.logistics_code = :logisticsCode
        or t.agent_code = :agentCode)
    '''
    result = executeSql(sql, orderNo=orderNo, ebcCode=companyCode, ebpCode=companyCode, logisticsCode=companyCode, agentCode=companyCode)

    if result is None or len(result) == 0:
        res['success'] = False
        res['info'] = '未找订单号对应的清单信息'
        return res
    else:
        res['success'] = True
        res['info'] = '获取清单信息成功!'
        res['data'] = []
        for invt in result:
            invtData = {}
            invtData['orderNo'] = invt[0]
            invtData['logisticsNo'] = invt[1]
            invtData['invtNo'] = invt[2]
            invtData['billNo'] = invt[3]
            invtData['sysDate'] = invt[4]
            invtData['appStatus'] = invt[5]
            invtData['rtnStatus'] = invt[6]
            invtData['rtnInfo'] = invt[7]
            invtData['rtnTime'] = invt[8]
            invtData['cusStatus'] = invt[9]
            invtData['cusTime'] = invt[10]
            invtData['copNo'] = invt[11]
            res['data'].append(invtData)


    return res


@bpout.route('/exportSummaryList/<token>/<billNo>', methods=['GET'])
def exportSummaryList(token, billNo):
    now = datetime.now()
    exportDir = 'export'
    fileName = "{}_{}_summary_list.txt".format(billNo, now.strftime('%Y%m%d%H%M%S'))

    companyCode = redisConn.get(token).decode()

    if companyCode is None:
        with open(os.path.join(exportDir, fileName), 'w', encoding='utf-8') as f:
            f.write('token不存在，请联系管理员，申请开通')
        return send_from_directory(exportDir, fileName, as_attachment=True)

    sql = '''
    select t.invt_no
    from ceb3_invt_head t
    where t.app_status = '899'
    and t.bill_no = :billNo
    and (t.ebc_code = :ebcCode
    or t.ebp_code = :ebpCode
    or t.logistics_code = :logisticsCode
    or t.agent_code = :agentCode
    )
    '''

    result = executeSql(sql, billNo=billNo, ebcCode=companyCode, ebpCode=companyCode, logisticsCode=companyCode, agentCode=companyCode)

    with open(os.path.join(exportDir, fileName), 'w') as f:
        for invt in result:
            f.write(invt[0] + '\n')

    return send_from_directory(exportDir, fileName, as_attachment=True)

app.register_blueprint(bpout)
