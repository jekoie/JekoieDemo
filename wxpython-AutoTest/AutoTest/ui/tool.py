#coding:utf-8
import wx
import wx.adv
import ftputil.error
import re
import io
import time
import os
import httplib
import threading
import wx.lib.dialogs
import traceback
import ftfy
import ftputil
import wx.lib.agw.pybusyinfo as PBI
from lxml import etree
import posixpath
import uuid
import pandas as pd
import wx.lib.newevent
import subprocess
import collections
import psutil
import wx.lib.agw.genericmessagedialog as GMD
from config.config import Config, DeviceState
from communicate.communicate import communicate_factory
from oracle import cx_Oracle

def mes_value(value):
    mes_value =  '' if value == None else  ftfy.fix_text( unicode(value) )
    return mes_value

def errorencode(str):
    return unicode(str, encoding='gbk', errors='ignore')

def inttomac(mac_int=0):
    mac_str = '{:0>12X}'.format(int(mac_int))
    return  ':'.join([mac_str[i:i+2] for i in xrange(0,12,2)] )

#调整窗体位置
def adjustpos(win, dlg):
    if Config.autopos:
        posx, posy = win.GetScreenPosition()
        adjust_pos = (posx + Config.posx, posy + Config.posy)
        dlg.SetPosition(adjust_pos)
    else:
        dlg.CentreOnParent()

def macAddrCreator(mac, count=100, prefix='MAC'):
    mac_str = mac.replace(':', '')
    mac_num = int(mac_str, 16)
    mac_dict = collections.OrderedDict()
    for i in range(count):
        mac_str = hex(mac_num+i).upper().strip('0X').strip('L')
        mac_str = '{:0>12}'.format(mac_str)
        mac3_str = mac_str[0:4] + '.' + mac_str[4:8] + '.' + mac_str[8:]
        mac_str = ':'.join([ mac_str[j:j+2] for j in range(0, 12, 2)])
        mac_dict['@{}{}'.format(prefix, i)] = mac_str
        mac_dict['@3{}{}'.format(prefix, i)] = mac3_str
    return mac_dict

def convert_value(value="", flag=[]):
    def convert(value, flag):
        if 'upper' in flag:
            if value != None:
                value = value.upper()

        if 'lower' in flag:
            if value != None:
                value = value.lower()

        if 'lstrip' in flag:
            if value != None:
                value = value.lstrip()

        if 'rstrip' in flag:
            if value != None:
                value = value.rstrip()

        if 'strip' in flag:
            if value != None:
                value = value.strip()

        if "date" in flag:
            t = pd.to_datetime(value, errors='ignore')
            if t.__class__.__name__ == 'Timestamp':
                value = t.strftime('%Y%m%d')

        if 'length' in flag:
            if value != None:
                value = len(value)
        return value

    for f in flag:
        value = convert(value, f.strip() )
    return value

#parse sequence xml file
class ParseSeqXML(object):
    def __init__(self, filepath):
        self.tree = etree.parse(filepath, Config.parser_without_comments)
        self.root = self.tree.getroot()
        self.file = filepath
        self.dir = posixpath.dirname(self.file)
        self._run = 'run'
        self.__options_path = './options'
        self.__options2_path = './options2'
        self.__testtree_path = './testtree'
        self.__testitem_path = './testitem'
        self.__attribute_path = './attribute'
        self.__assignversion_path = './assignversion'
        self.__workstage_path= './workstage'

    def get_workstage_element(self):
        return self.root.find(self.__workstage_path)

    def get_options_element(self):
        return self.root.find(self.__options_path)

    def get_options2_element(self):
        return self.root.find(self.__options2_path)

    def get_testtree_element(self):
        return self.root.find(self.__testtree_path)

    def get_testitem_element(self):
        return self.root.find(self.__testitem_path)

    def get_attribute_element(self):
        return self.root.find(self.__attribute_path)

    def get_assignversion_element(self):
        return self.root.find(self.__assignversion_path)

    def get_run_sequence(self):
        seq = []
        for tree in self.get_testtree_element().getchildren():
            for item in self.get_testitem_element().getchildren():
                if tree.tag == item.tag:
                    seq.append((tree, item))
        return seq

class AppSettingReader(object):
    __root = None
    __tree = None

    def __init__(self):
        self.path = Config.appfile

    def __enter__(self):
        if self.__class__.__root is None:
            self.__class__.__tree = etree.parse(self.path, Config.parser_without_comments)
            self.__class__.__root = self.__tree.getroot()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass

    def get(self, tag, key):
        node = self.__root.find(".//*[@name='{}']".format(tag))
        return node.attrib.get(key, None)

    def set(self, tag, attr):
        node = self.__root.find(".//*[@name='{}']".format(tag))
        node.attrib.update(attr)
        self.__tree.write(self.path, encoding='utf-8', pretty_print=True, xml_declaration=True)

def update_config_file(ftp_config_base_dir=u"工艺工作文件夹/工艺资料/AutoTest-Config", local_setting_file="./setting/config.xml" ):
    #更新提示信息
    wx.GetApp().Yield()
    config_file = None
    msg, ret_status = '', True
    busy = PBI.PyBusyInfo(u'正在更新配置', None, u'更新')
    basedir = ftp_config_base_dir
    rootElement = etree.Element('root')
    ftp = ftputil.FTPHost("192.168.60.70", "szgy-chenjie", "szgy-chenjie")
    ftp.chdir(basedir.encode("gbk"))
    for dirpath, dirnames, filenames in ftp.walk("."):
        try:
            dirpath_seg = dirpath.split("/")
            dirpath_seg_len = len(dirpath_seg)
            if dirpath_seg_len == 2 and 'config.xml' in filenames:
                config_file = posixpath.join(dirpath, 'config.xml')
                config_file_handle = ftp.open(config_file, encoding="utf-8")
                tree = etree.parse(config_file_handle, Config.parser_without_comments)
                comment = etree.Comment(dirpath_seg[-1])
                rootElement.append(comment)
                for item in tree.xpath('./li'):
                    if len(item) == 0:
                        xml_path = item.get('xml', '')
                        item.attrib['xml'] = xml_path[:2] + dirpath_seg[-1] + '/' + xml_path[2:]
                        etree.SubElement(rootElement, item.tag, item.attrib)
                    else:
                        for subitem in item:
                            xml_path = subitem.get('xml', '')
                            subitem.attrib['xml'] = xml_path[:2] + dirpath_seg[-1] + '/' + xml_path[2:]
                        rootElement.append(item)
        except Exception as e:
            msg += '文件：{} 错误：{}\n'.format(config_file, e.message)
            ret_status = False
            continue

    if ret_status:
        with open(local_setting_file, mode="w",) as f:
            f.write(etree.tostring(rootElement, xml_declaration=True, pretty_print=True, encoding="utf-8"))

        ftp.upload(local_setting_file, "./config.xml")
        ftp.close()

    del busy

    return msg, ret_status

def validate_workjob():
    mes_attr = Config.mes_attr
    sql_workjob = "select distinct workjob_code from DMSNEW.work_workjob where workjob_code='{}' ".format(mes_attr['extern_WJTableName'])
    sql_linecode = "select distinct linecode,line from DMSNEW.workproduce where linecode='{}' ".format(mes_attr['extern_SubLineCode'])
    sql_stationcode = "select distinct code, name from DMSNEW.qa_mantaince_type where code='{}' ".format(mes_attr['extern_StationCode'])

    value_workjob = Config.mes_db.fetchone(sql_workjob)
    value_linecode = Config.mes_db.fetchone(sql_linecode)
    value_stationcode = Config.mes_db.fetchone(sql_stationcode)

    if value_workjob :
        flag_workjob = True
        #特殊评审说明
        sql_review = "select segment33 from dmsnew.work_workjob  where workjob_code='{}' ".format(mes_attr['extern_WJTableName'])
        review_sql_value = Config.mes_db.fetchone(sql_review)
        mes_attr['workjob_review'] = review_sql_value[0] if review_sql_value[0] else str(uuid.uuid4())
        tipmsg = u'1.工单号：{}正确\n'.format(mes_attr['extern_WJTableName'])
    else:
        flag_workjob = False
        tipmsg = u'1.工单号：{}.不存在\n'.format(mes_attr['extern_WJTableName'])

    if value_linecode:
        flag_linecode = True
        tipmsg += u'2.线体：{}正确\n'.format(mes_attr['extern_SubLineCode'])
    else:
        flag_linecode = False
        tipmsg +=  u'2.线体：{}.不存在\n'.format( mes_attr['extern_SubLineCode'])

    if value_stationcode:
        flag_stationcode = True
        mes_attr['extern_StationName'] = value_stationcode[1]
        tipmsg += u'3.工序：{}正确\n'.format(mes_attr['extern_StationCode'])
    else:
        flag_stationcode = False
        tipmsg += u'3.工序：{}.不存在\n'.format( mes_attr['extern_StationCode'])

    return flag_workjob, flag_linecode, flag_stationcode, tipmsg


def get_mes_attr():
    mes_attr = Config.mes_attr
    extern_WJTableName = mes_attr['extern_WJTableName']
    extern_StationCode = mes_attr['extern_StationCode']

    sql = "select serial_number,sub_attempter_code,attempter_code,order_code,class," + \
          " to_char(attemper_begin_date,'yyyy-mm-dd hh24:mi:ss') attemper_begin_date,to_char(attemper_end_date,'yyyy-mm-dd hh24:mi:ss') attemper_end_date," + \
          "worksubsequence_code,workshop,work_code,line_code,worksations,persons, number1,number2,ympk,yinum,oddscan,work_code2,testposition," + \
          "decode(bug_num,0,'否',1,'是','是') bug_num,TOTALSENDNUM from DMSNEW.mtl_sub_attemper where  state in('已调度' , '已开工') "
    sql += " and  order_code='{}' and TESTPOSITION in ( select name from DMSNEW.qa_mantaince_type  where code='{}' )".format(extern_WJTableName, extern_StationCode)

    sql_value = Config.mes_db.fetchall(sql)

    if len(sql_value) == 0:
        return False, u'此调度单为空'

    mes_attr['extern_SerialNumber'] = mes_value(sql_value[0][0])
    mes_attr['extern_SubAttemperCode'] = mes_value(sql_value[0][1])
    mes_attr['extern_AttempterCode'] = mes_value(sql_value[0][2])
    mes_attr['extern_strympk'] = mes_value(sql_value[0][15])
    mes_attr['extern_Num1'] = mes_value(sql_value[0][16])
    mes_attr['extern_SubTestPosition'] = mes_value(sql_value[0][19])
    mes_attr['extern_strWorkCode2'] = mes_value(sql_value[0][18])
    # mes_attr['op_workers'] = mes_value(sql_value[0][21])
    mes_attr['extern_strmpk'] = '0'

    sql = "select item_code,item_version,item_type ,item_memo, lotno, segment17,segment11,mytype,item_num  from dmsnew.work_workjob where workjob_code='{}'".format(extern_WJTableName)
    sql_value = Config.mes_db.fetchall(sql)
    # 产品编码
    mes_attr['extern_stritemcode'] = mes_attr['extern_productcode'] = mes_value(sql_value[0][0])
    # 产品版本
    mes_attr['extern_stritemversion'] = mes_attr['extern_productversion'] = mes_value(sql_value[0][1])
    # 规格型号
    mes_attr['extern_stritemtype'] = mes_attr['extern_producttype'] = mes_value(sql_value[0][2])
    # 产品名称
    mes_attr['extern_stritemmemo'] = mes_attr['extern_productname'] = mes_value(sql_value[0][3])
    # 计划模式
    mes_attr['extern_plan_mode'] = mes_value(sql_value[0][6])
    # 客户产品型号
    mes_attr['extern_mytype'] = mes_value(sql_value[0][7])
    mes_attr['extern_lotno'] = mes_value(sql_value[0][4])
    mes_attr['extern_bomcode'] = mes_value(sql_value[0][5])
    #item_num任务单 SN数量
    mes_attr['extern_Num1'] = mes_attr['extern_item_num'] = mes_value(sql_value[0][8])

    extern_SubLineCode = mes_attr['extern_SubLineCode']
    sql = "select line,workshopname,biglinename from dmsnew.workproduce where linecode='{}' ".format(extern_SubLineCode)
    sql_value = Config.mes_db.fetchall(sql)
    mes_attr['extern_SubLine'] = mes_value(sql_value[0][0])
    mes_attr['extern_workshopname'] = mes_value(sql_value[0][1])
    mes_attr['extern_biglinename'] = mes_value(sql_value[0][2])

    #获取MES变量
    mes_attr['@MES_PRODUCTTYPE'] = mes_attr['extern_stritemtype']
    mes_attr['@MES_LOTNO'] = mes_attr['extern_lotno']
    mes_attr['@MES_CUSTOMER_PRODUCTNAME'] = mes_attr['extern_mytype']
    mes_attr['@MES_PRODUCTNAME'] = mes_attr['extern_stritemmemo']
    return True, ''

#记录MES查询记录
def record_mes_query():
    try:
        mes_attr = Config.mes_attr
        workjob_code = mes_attr['extern_WJTableName']
        item_code = mes_attr['extern_productcode']
        item_type = mes_attr['extern_producttype']
        line_code = mes_attr['extern_SubLine']
        testposition = mes_attr['extern_SubTestPosition']
        item_num = mes_attr['extern_item_num']
        describe = mes_attr['extern_SubAttemperCode']
        item_version = mes_attr['extern_productversion']
        item_memo = mes_attr['extern_stritemmemo']
        workshop = mes_attr['extern_workshopname']
        daline = mes_attr['extern_biglinename']
        segment1 = '8'
        segemnt2 = ''
        segment3 = Config.wn + Config.wnname + '[AutoTest]'
        sql = "insert into dmsnew.todayworkjob(workjob_code,item_code,item_type,line_code,testposition,item_num, " \
              "describe,item_version,item_memo,WORKSHOP,DALINE_CODE,SEGMENT1,SEGMENT2,SEGMENT3) " \
              "values('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}')".format(
            workjob_code, item_code, item_type, line_code, testposition, item_num, describe, item_version, item_memo,
            workshop, daline, segment1, segemnt2, segment3)

        Config.mes_db.execute(sql)
        Config.mes_db.commit()
    except Exception as e:
        Config.logger.error(errorencode(traceback.format_exc()))
        Config.mes_db.rollback()

def getSNValue(window):
    # sn verify
    sn_value = None
    devwin = Config.getdevwin(window)
    sn_dlg = wx.TextEntryDialog(devwin, '请输入产品SN', '{}:SN'.format(window.GetName()))
    adjustpos(devwin, sn_dlg)
    while True:
        if sn_dlg.ShowModal() == wx.ID_OK:
            sn_value = sn_dlg.GetValue().strip().upper()
            if re.match(r'^[A-Z0-9-_]+', sn_value, re.I):
                sn_dlg.Destroy()
                return True, sn_value
            else:
                for childwin in sn_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            sn_dlg.Destroy()
            return False, sn_value

def getMacValue(window):
    # mac address verify
    mac_value = None
    devwin = Config.getdevwin(window)
    mac_dlg = wx.TextEntryDialog(devwin, '请输入产品MAC地址', '{}:MAC Address'.format(window.GetName()))
    adjustpos(devwin, mac_dlg)
    while True:
        if mac_dlg.ShowModal() == wx.ID_OK:
            mac_value = mac_dlg.GetValue().strip().upper()
            if re.match(r'^([A-F\d]{2}:){5}([A-F\d]{2})$', mac_value, re.I):
                mac_dlg.Destroy()
                return True, mac_value
            else:
                for childwin in mac_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        childwin.SetLabelText('产品MAC地址输入有误，请重新输入')
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            mac_dlg.Destroy()
            return  False, mac_value

def getWorkstage(window, xml):
    msg = ''
    candidate_value_list = []
    workstage_ele = xml.root.find('.//workstage')
    if workstage_ele is None: return True, None
    for child in workstage_ele.iterchildren():
        msg += child.get('name', '') + '\n'
        candidate_value_list.append(child.get('value', 'unchoosed'))
    devwin = Config.getdevwin(window)
    workstage_dlg = wx.TextEntryDialog(devwin, '{}'.format(msg.rstrip()), '{}:工序选择'.format(window.GetName()))
    adjustpos(devwin, workstage_dlg)
    while True:
        if workstage_dlg.ShowModal() == wx.ID_OK:
            workstage_value = workstage_dlg.GetValue().strip()
            if workstage_value in candidate_value_list:
                workstage_dlg.Destroy()
                return True, workstage_value
            else:
                for childwin in workstage_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        workstage_dlg.SetTitle('工序选择错误' )
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            workstage_dlg.Destroy()
            return False, None

#查询可用SN记录
def get_available_sn():
    extern_WJTableName =  Config.mes_attr['extern_WJTableName']
    extern_SerialNumber = Config.mes_attr['extern_SerialNumber']
    sql = "select barcode from ((select barcode from  dmsnew.{worktable}  where scan_position='L' and" \
          " qulity_flag ='no' and scan_type='正常生产' and segment13 ='no'  and subid =({extern_SerialNumber}-1)) minus " \
          "(select barcode from dmsnew.{worktable} where scan_position='L' and  qulity_flag ='no' and scan_type ='正常生产' " \
          "and segment13 ='no' and subid={extern_SerialNumber} ))".format(worktable=extern_WJTableName, extern_SerialNumber=extern_SerialNumber)

    sql_value = Config.mes_db.fetchall(sql)
    available_sn_list = []
    for available_sn in sql_value:
        available_sn_list.append(available_sn[0])

    return available_sn_list

def getWorkstageMsgBox(window, item):
    msg, caption = item.get('msg', ''), item.get('caption', '')
    initial_value, type = item.get('initial_value', ''),  item.get('type', 'msgbox')
    name, show = item.get('name', '@WORKSTAGE_MSGBOX'), item.get('show', 'True')
    flag = item.get('flag', '').split('|')
    if show not in "True":
        return True, {name: initial_value}

    devwin = Config.getdevwin(window)
    dlg = wx.TextEntryDialog(devwin, msg, '{}:{}'.format(window.GetName(), caption), initial_value, style=wx.OK|wx.CANCEL|wx.CENTER)
    adjustpos(devwin, dlg)
    if type in 'msgbox':
        while True:
            if dlg.ShowModal() == wx.ID_OK and dlg.GetValue() != '':
                value = convert_value(dlg.GetValue(), flag)
                dlg.Destroy()
                if 'mac' in flag:
                    return True, macAddrCreator(value, prefix=name.replace('@', ''))
                return True, {name:value}
            else:
                dlg.Destroy()
                return False, {name: ''}

def getMessageDialog(window, msg, caption, style, data):
    devwin = Config.getdevwin(window)
    topwin = wx.Window.FindWindowByName('MainFrame')
    win = devwin if Config.autopos else topwin
    dlg = GMD.GenericMessageDialog(win, msg, caption, style)
    okcancel_label = data.get('okcancel', '')
    adjustpos(win, dlg)
    if okcancel_label:
        dlg.SetOKCancelLabels(okcancel_label[0], okcancel_label[1])

    if dlg.ShowModal() == wx.ID_OK:
        dlg.Destroy()
        return True
    else:
        dlg.Destroy()
        return False


def getProductXML(ftp_base_dir_anonymous="ftp://192.168.60.70/AutoTest-Config/", subproduct="", sn=''):
    config_xml_path = posixpath.join(ftp_base_dir_anonymous, "config.xml")
    comfig_tree = etree.parse(config_xml_path, Config.parser_without_comments)
    config_xml_root = comfig_tree.getroot()
    for item in config_xml_root.getchildren():
        sn_stigma = item.get('bom', '')
        if sn_stigma.upper() == sn[:len(sn_stigma)].upper():
            if len(item) == 0:
                xml_path_list = item.get('xml', '').split('/')[1:]
                xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                product_name = item.get('product')
                return ParseSeqXML(xml_path), product_name
            else:
                default_value = review_value = None
                for subitem in item:
                    if subitem.get('review', str(uuid.uuid4()) ) in subproduct:
                        xml_path_list = subitem.get('xml', '').split('/')[1:]
                        xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                        product_name = subitem.get('product', '')
                        review_value = ParseSeqXML(xml_path), product_name
                        break
                    elif 'default' in subitem.get('review', uuid.uuid4()):
                        xml_path_list = subitem.get('xml', '').split('/')[1:]
                        xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                        product_name = subitem.get('product', '')
                        default_value = ParseSeqXML(xml_path), product_name

                if review_value is not None:
                    return  review_value
                elif default_value is not None:
                    return  default_value
                else:
                    return None, None
    return None, None

def get_bind_info_by_barcode(sn_value):
    #(103002027500S17C28S0010D, C8:50:E9:6E:40:86, C8:50:E9:6E:40:87,  客户SN)
    extern_WJTableName = Config.mes_attr['extern_WJTableName']
    sql = "select distinct barcode, macma, macma2, waima from dmsnew.{} where macma is not null and barcode = '{}' ".format(extern_WJTableName, sn_value)
    sql_value = Config.mes_db.fetchone(sql)
    return sql_value

def get_customer_sn_value(bind_info):
    if bind_info is not None:
        if bind_info[3] is not None:
            customer_sn_value = bind_info[3]
        else:
            customer_sn_value = 'NOT FOUND'
    else:
        customer_sn_value = 'NOT FOUND'

    return customer_sn_value

#find substr in s, and return it's position
def find_pos(sub, s, slice):
    sub_count = slice.count(sub)
    if sub_count == 0: return [(0, 0)]
    pos_list, s_length = [], len(s)

    start_pos_list, start_pos = [], 0
    slice_count = s.count(slice)
    for i in range(slice_count):
        start_pos =  s.find(slice, start_pos, s_length)
        start_pos_list.append(start_pos)
        start_pos += len(slice)

    for start_pos in start_pos_list:
        for i in range(sub_count):
            start_pos = s.find(sub, start_pos, s_length)
            end_pos = start_pos + len(sub)
            pos_list.append((start_pos, end_pos))
            start_pos = end_pos
    return  pos_list

def assignMesAttrBySN(sn, store={} ):
    try:
        MES_ATTR = Config.mes_attr
        strBarCode = store['extern_SN'] = sn
        extern_WJTableName = MES_ATTR['extern_WJTableName']
        WJTableName = 'DMSNEW.' + extern_WJTableName
        extern_AttempterCode = MES_ATTR['extern_AttempterCode']
        sql = "select repair, repair1, subid, qulity_flag, testposition, scan_type,scan_position  from " + \
              WJTableName + " where scan_time=(select max(scan_time) from " + \
              WJTableName + " where  barcode='" + strBarCode + "') and barcode='" + \
              strBarCode + "' order by scan_position desc,scan_type desc  ,subid desc"

        sql_value = Config.mes_db.fetchall(sql)
    except KeyError:
        Config.logger.error(errorencode(traceback.format_exc()))
        return False, '工单为输入'
    except cx_Oracle.DatabaseError as e:
        Config.logger.error(errorencode(traceback.format_exc()))
        return False, '工单号不存在'

    if len(sql_value) != 0:
        store['extern_QualityFlag'] = mes_value(sql_value[0][3])
        store['extern_SubID'] = mes_value( sql_value[0][2])
        store['extern_ScanType'] = mes_value(sql_value[0][5])
        store['extern_repair'] = mes_value( sql_value[0][0])
        store['extern_repair1'] = mes_value(sql_value[0][1])
        store['extern_sn_testposition'] = mes_value(sql_value[0][4])
    else:
        store['extern_QualityFlag'] = 'no'
        store['extern_SubID'] = 0
        store['extern_ScanType'] = u'正常生产'
        store['extern_repair'] = u'未维修'
        store['extern_sn_testposition'] = u'未投产'

    work_done_status_sql = "select count(*) from dmsnew.mtl_sub_attemper where state <> '已完工' and attempter_code='{}' ".format(extern_AttempterCode)  # outer

    sql_value = Config.mes_db.fetchone(work_done_status_sql)
    store['extern_work_done_status'] = mes_value( sql_value[0] )

    sql = "select sendno, sendmpk from dmsnew.work_main_barcode where barcode='{}'".format(strBarCode)
    sql_value = Config.mes_db.fetchone(sql)
    if  sql_value is None or  len(sql_value) == 0:
        store['extern_CompSendno'] = ''
        store['extern_CompSendmpk'] = ''
    else:
        store['extern_CompSendno'] = mes_value(sql_value[0])
        store['extern_CompSendmpk'] = mes_value(sql_value[1])

    return True, ''

def sn_in_repaire(mes_attr):
    if mes_attr['extern_QualityFlag'] == 'yes':
        return False, u'此设备在维修状态'
    return True, ''

def sn_in_procedurce(sn_value, mes_attr={}):
    extern_SubID = mes_attr['extern_SubID']
    extern_SerialNumber = mes_attr['extern_SerialNumber']
    extern_ScanType = mes_attr['extern_ScanType']
    extern_sn_testposition = mes_attr['extern_sn_testposition']
    equalNum = int(extern_SubID) - int(extern_SerialNumber)
    if equalNum >= 0 and extern_ScanType == u'正常生产':
        return False, 'AfterStatin', u'该条码不在测试工序，该条码已过工序{}({})'.format(extern_SubID, extern_sn_testposition)
    elif equalNum < 0 and equalNum != -1:
        return False, 'BeforeStation',u'该条码不在测试工序，该条码已过工序{}({})'.format(extern_SubID, extern_sn_testposition)
    elif sn_value not in get_available_sn():
        return False, 'NoList' ,u'该条码{}不在测试列表中'.format(sn_value)
    else:
        sql = "select numr from dmsnew.work_main_barcode where barcode='{}'".format(sn_value)
        sql_value = Config.mes_db.fetchone(sql)
        if sql_value:
            odevity = sql_value[0]
            if odevity % 2 == 1:
                return False, 'Odd', u'该条码扫描次数为奇数{}'.format(odevity)
        return True, 'OK', ''

def get_assign_version(product_dict, xml):
    assignversion_ele = xml.get_assignversion_element()
    if assignversion_ele is None: return True, ''
    try:
        extern_WJTableName = Config.mes_attr['extern_WJTableName']
        extern_StationName = Config.mes_attr['extern_StationName']
        sql = "select filename from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' " \
              "and w.createdate = (SELECT MAX(CREATEDATE) FROM DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' " \
              "and w.realtestposition ='{}')".format( extern_WJTableName, extern_StationName, extern_WJTableName, extern_StationName)
        filenams_list = Config.mes_db.fetchall(sql)
        df = pd.DataFrame(filenams_list, columns=['filename'])
        for child in assignversion_ele.iterchildren():
            for filename in df.values:
                match = re.search(child.get('regex', ''), filename[0])
                if match and len(match.groups()) > 0:
                    product_dict[child.get('assign', 'NULL')] = match.groups()[0]
                    break
                product_dict[child.get('assign', 'NULL')] = child.get('default', 'NULL')
    except KeyError:
        return False, '未输入工单号，不能获取工单信息'
    return True, ''

def create_device(device_settings, page_idx, fail_skip=False):
    pagewin = None
    try:
        if Config.mode['mode'] == 'single':
            pagewin = Config.windows.values()[page_idx][0]
        else:
            m, s = divmod(page_idx, 2)
            pagewin = Config.windows.values()[m][s]
    except Exception:
        pass

    try:
        device = communicate_factory(device_settings['protocol'], **device_settings)
        device.connect()
        if Config.mode['mode'] == 'single':
            device_dict = {'master': [device, DeviceState.foreground], 'slave': [None, None]}
            Config.devices[page_idx].update(device_dict)
        else:
            m, s = divmod(page_idx, 2)
            if s:
                device_dict = {'slave': [device, DeviceState.foreground]}
            else:
                device_dict = {'master': [device, DeviceState.foreground]}

            Config.devices[m].update(device_dict)
    except Exception:
        if not fail_skip:
            pagewin.section_area.AppendText('{}创建失败\n'.format(device_settings['name']))
    else:
        pagewin.section_area.AppendText('{}创建成功\n'.format(device_settings['name']))

def time_sync():
    try:
        def set_time(date_str):
            gmt_time_struct = time.strptime(date_str[5:25], "%d %b %Y %H:%M:%S")
            ltime = time.localtime(time.mktime(gmt_time_struct) + 8 * 60 * 60)
            date_cmd = 'date {}-{}-{}'.format(ltime.tm_year, ltime.tm_mon, ltime.tm_mday)
            time_cmd = 'time {}:{}:{}'.format(ltime.tm_hour, ltime.tm_min, ltime.tm_sec)
            os.system(date_cmd)
            os.system(time_cmd)

        host = '192.168.60.70'
        conn = httplib.HTTPConnection(host=host, timeout=3)
        conn.request('GET', '/')
        resp = conn.getresponse()
        date_str = resp.getheader('date')
        threading.Thread(target=set_time, args=(date_str,)).start()
        return True
    except Exception as e:
        return False

def back_remove(s):
        while '\x08' in s:
            s = re.sub('[^\x08]\x08', '', s)
        return s

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

#crc密码生产器
def crc_passwd(mac):
    exe_path = Config.crcfile
    hex_str = mac.upper() + time.strftime('%Y%m%d', time.localtime())
    hex_str = str(hex_str).translate(None, ': ').upper()
    if len(hex_str)%2 == 0:
        hex_str_list = [ hex_str[i:i+2] for i in range(0, len(hex_str), 2) ]
    else:
        hex_str_list = ['00']

    output = subprocess.check_output([exe_path] + hex_str_list, shell=True, universal_newlines=True)
    match = re.search(r'pwd\s*is\s*:\s*(\w+)', output)
    passwd = match.groups()[0]
    return passwd




