#!/usr/bin/env python

from subprocess import Popen,PIPE
from httplib import HTTPConnection
import subprocess
import commands
import socket
import csv
import sys
import re
import time
import urllib
import collections
import optparse
import logging
import time
import StringIO
import HTMLParser
import threading

def print_error(msg):
	print '\033[31m%s\033[0m' %(msg)

def print_color(msg):
	print '\033[32m%s\033[0m' %(msg)	


def get_logger():
	logging.basicConfig(
		level = logging.NOTSET,
		format = '[%(asctime)s][%(levelname)s]  %(message)s'
	)
	
	logger = logging.getLogger(__name__)

	return logger


logger = get_logger()	

def option_parse():
	parser = optparse.OptionParser(usage='%prog [option]', version='1.0')
	parser.add_option('-m', '--mode', type='choice', choices=['r', 'w'], help='select mode,(r: read message,default mode) ,(w: write message)', dest='mode', default='r', metavar='(r|w)')
	parser.add_option('-n','--sn', action='store', type='string', help='device serial number,must needed', dest='sn', metavar='<serial number>')
	options, remains = parser.parse_args()
		
	if not options.sn:
		parser.print_help()
		sys.exit() 
	
	if len(options.sn) != 12:
		logger.error('invalid serial number')
		sys.exit()

	return options	


def usb_location_list():
	mobdev_status, mobdev_cmd = commands.getstatusoutput('which mobdev')

	if mobdev_status != 0:
		logger.error('mobdev command not found')
		return []

	mobdev_list_cmd = '{} list'.format(mobdev_cmd)
	mobdev_output = subprocess.check_output(mobdev_list_cmd, shell=True, bufsize=0, universal_newlines=True)
	usb_location_list = re.findall('.+location ID = (\w+)', mobdev_output, re.M)
	
	if len(usb_location_list) == 0:
		logger.warning('no usb location found,try again')
		mobdev_output = subprocess.check_output(mobdev_list_cmd, shell=True, bufsize=0, universal_newlines=True)
		usb_location_list = re.findall('.+location ID = (\w+)', mobdev_output, re.M)

	return usb_location_list

def usb_device_list():
	usb_status, usb_strings = commands.getstatusoutput('ls -1 /dev/cu.*')
	
	if usb_status != 0:
		logger.error('no usb device found')
		return  []
	usb_list = re.findall('^\/dev\/cu\.(?:usbserial|kanzi).+', usb_strings, re.M)
	
	return usb_list

def nano_cmd():
	nano_status, nano_cmd = commands.getstatusoutput('which nanokdp')
	if nano_status != 0:
		logger.warning('command nanokdp not foudn,try to use nanocom instead')
		nano_status, nano_cmd = commands.getstatusoutput('which nanocom')
		if nano_status != 0:
			logger.error('command nanocom didn\'t existing')
			return False
	
	return nano_cmd

	
def connect_to_device(usb_device_string):
	if nano_cmd():
		cmd = '{} -d {}'.format(nano_cmd(), usb_device_string)
		proc = Popen(cmd, shell=True, bufsize=0, universal_newlines=True, stdin=PIPE, stdout=PIPE, stderr=sys.stderr)
		return proc
	else:
		return False

def device_diags_mode(proc):
	while True:
		output = proc.stdout.readline()
		if output.startswith('Entering recovery mode'):
			logger.info(output)
			proc.stdin.write('diags'+'\n')
			while True:
				output = proc.stdout.readline()
				if output.startswith('script: alias updateroot'):
					logger.info(output)
					break
				else:
					logger.info(output)
			break
		else:
			logger.info(output)


def get_data_from_sfc(sn, datalist = 'mpn region_code'.split()):
	SFC_URL = '172.25.3.167'
	data = {
	'sn':sn,
	'c':'QUERY_RECORD',
	'p': datalist, 
	}
	
	unit = {}
	unit = unit.fromkeys(datalist)
	encoded_data = urllib.urlencode(data, doseq=True)
	headers = {'Content-type':'application/x-www-form-urlencoded', 'Accept':'text/plain'}	
	try:
		connection = HTTPConnection(SFC_URL, timeout=5)
		connection.request('POST', '/fatpd11', encoded_data, headers)
		response = connection.getresponse()
		result_list = response.read().split('\n')
	except socket.error, msg:
		logger.error('Connection SFC Server {} {}.'.format(SFC_URL, msg))
		sys.exit()
	finally:
		connection.close()
	
	is_successful = False	
	for var in result_list:
		if var.endswith('SFC_OK'):
			is_successful = True
			result_list.remove(var)
	else:
		if is_successful:
			for var in result_list:
				for key in unit.iterkeys():
					if var.startswith(key):
						unit[key] = var.split('=')[1]
			else:
				return unit
		else:	
			logger.error('Get SFC Data Failed')
			sys.exit()


class QCR_HTMLParser(HTMLParser.HTMLParser):
	
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self)
		self.data_list = []

	def handle_data(self, data):
		self.data_list.append(data)
	
	def get_data(self):
		return self.data_list

	def get_ecid(self):
		ecid_count = self.data_list.count('ECID')
		
		if ecid_count == 0:
			return None		
		while ecid_count > 1:
			self.data_list.remove('ECID')
			ecid_count = self.data_list.count('ECID')		
		else:
			ecid_index = self.data_list.index('ECID')
			ecid_value = self.data_list[ecid_index + 4]
			
			if ecid_value.startswith('0x') and len(ecid_value) == 18:
				return ecid_value
			else:
				return None		


	def get_key(self, key):
		product_keys = ['MLBSN']
		attr_keys = [
				'BACK NVM BARCODE', 'BASEBANDGOLDCERTID', 'BATTERY_SN', 'BB_FIRMWARE_VERSION', 'BT_MAC_ADDR', 'BUILD_EVENT', 'CG_SN', 'CHIPID',
				'DEVICE_ID', 'DIAG_VERSION', 'DIEID', 'ECID', 'FUSEID', 'IMEI', 'MOPED', 'MPN', 'NANDCS', 'NANDID', 'REGION_CODE', 'S_BUILD',
				'UDID', 'UNIT#', 'WIFI/BT VENDOR', 'WIFI_MAC_ADDR',
			]
				
		key_count = self.data_list.count(key)
		
		if key in product_keys:
			offset = 5
		elif key in attr_keys:
			offset = 4
		else:
			offset = 4

		if key_count == 0:
			return None		
		while key_count > 1:
			self.data_list.remove(key)
			key_count = self.data_list.count(key)		
		else:
			key_index = self.data_list.index(key)
			key_value = self.data_list[key_index + offset]
			key_value = key_value.strip()
			return key_value
		
def get_page_from_qcr(sn):
	QCR_URL = '10.172.5.131'
	relm =  '/cgi-bin/WebObjects/QCR.woa/1/wo/KfbIxGOtjHIK9Ho4rJU7D0/2.1.5.5.29'
	
	L = relm.split('/')
	L.reverse()
	wosid = L[1]	
	
	data = {
		'1.5.5.29.1':sn,
		'1.5.5.29.3':'Search',
		'wosid':wosid,
	}
	
	encoded_data = urllib.urlencode(data, doseq=False)
	headers = {'Content-type':'application/x-www-form-urlencoded', 'Accept':'text/plain'}

	try:
		connection = HTTPConnection(QCR_URL, timeout=5)
		connection.request('POST', relm, encoded_data, headers)
		response = connection.getresponse()
	except socket.error, msg:
		logger.error('Connection QCR Server {} {}.'.format(QCR_URL, msg))
		return ''
	finally:
		connection.close()

	return response.read()

def get_key_from_qcr(sn, key):
	
	the_page = get_page_from_qcr(sn)
	if the_page:
		page_parser = QCR_HTMLParser()
		page_parser.feed(the_page)
		key_value = page_parser.get_key(key)
		page_parser.close()
		return key_value
	else:
		return -1

def is_iboot():
	status, output = commands.getstatusoutput('usbterm -list')
	if status == 0 and output.find('CPID') != -1:
		return True
	elif status > 0:
		logging.error('usbterm command not found')
		return False
	else:
		return False

def is_os():
	
	mobdev_list_cmd = 'mobdev list'
	mobdev_output = subprocess.check_output(mobdev_list_cmd, shell=True, bufsize=0, universal_newlines=True)
	usb_location_list = re.findall('.+location ID = (\w+)', mobdev_output, re.M)
	
	if len(usb_location_list) == 0:
		logger.warning('no usb location string found,try again')
		mobdev_output = subprocess.check_output(mobdev_list_cmd, shell=True, bufsize=0, universal_newlines=True)
		usb_location_list = re.findall('.+location ID = (\w+)', mobdev_output, re.M)

	if len(usb_location_list) == 0:
		return False
	else:
		return True

def force_to_recovery(usb_location_string):
	mobdev_cmd = 'mobdev -l {} recovery'.format(usb_location_string)
	subprocess.check_call(mobdev_cmd, shell=True)

def interrupt_to_iboot(proc):
	start_time = time.time()
	while True:
		output = proc.stdout.readline()
		end_time = time.time()
		diff_time = end_time - start_time
		logger.info(output)

		if output.startswith('Boot Failure') and diff_time < 15:
			proc.stdin.write('\n')
			return True
		elif diff_time > 15:
			return False

def iboot_to_diags(proc):
	proc.stdin.write('diags'+'\n')
	start_time = time.time()	
	while True:
		output = proc.stdout.readline()
		end_time = time.time()
		logger.info(output)
		diff_time = end_time - start_time

		if output.startswith('script: alias updateroot') and diff_time < 15:
			return True
		elif diff_time > 15:
			return False
			
def write_data_to_device(proc, unit):
	print_color(str(unit))
	if unit['mpn'] == 'null' or unit['region_code'] == 'null':
		logger.error('mpn or region_code invalide.write failed')
		sys.exit()

	proc.stdin.write('syscfg add SrNm {}'.format(unit['sn'])+'\n' )
	proc.stdin.write('syscfg add Regn {}'.format(unit['region_code'])+'\n')
	proc.stdin.write('syscfg add Mod# {}'.format(unit['mpn'])+ '\n')
	proc.stdin.write('system'+'\n')
	proc.stdin.write('res'+'\n')
	

if __name__ == '__main__':
	

	#print query_data('C39RN00VH96L', datalist='mpn region_code imei mlbsn goo ecid'.split())	
	
	option = option_parse()
	
	if option.mode == 'r':
		unit = get_data_from_sfc(option.sn)
		print_color(str(unit))
	elif option.mode == 'w':

		unit = get_data_from_sfc(option.sn)
		unit['sn'] = option.sn
		if is_iboot():
			usb_device_list = usb_device_list()
			proc = connect_to_device(usb_device_list[0])
			if iboot_to_diags(proc):
				write_data_to_device(proc, unit)
				proc_stdout,proc_stderr = proc.communicate()
				for line in proc_stdout.split('\n'):
					logger.info(line)
		
				print_color('write successful.')
		elif is_os():
			usb_location_list  = usb_location_list()
			usb_device_list = usb_device_list()
			proc = connect_to_device(usb_device_list[0])
			force_to_recovery(usb_location_list[0])
			interrupt_to_iboot(proc)
			iboot_to_diags(proc)
			write_data_to_device(proc, unit)
			proc_stdout,proc_stderr = proc.communicate()
			for line in proc_stdout.split('\n'):
				logger.info(line)
		
				print_color('write successful.')
		else:
			usb_device_list = usb_device_list()
			proc = connect_to_device(usb_device_list[0])
			write_data_to_device(proc, unit)
			proc_stdout,proc_stderr = proc.communicate()
			for line in proc_stdout.split('\n'):
				logger.info(line)
			print_color('write successful.')		
			
	

	'''
	mlbsn_list, flag = [], 0
	def read_ecid(usb_device, dict_writer, csv_file):

		while True:
			print_color('connect to {}'.format(usb_device))
			proc = connect_to_device(usb_device)
			output = proc.communicate(input='diags\nsyscfg print MLB#\n'+'\n')[0]
			mlb_ecid_list, D = [], {'MLBSN':None, 'ECID':None}
			for line in iter(output.split('\n')):
				line_strip = line.strip()
				if line_strip:
					if len(line_strip) == 16:	
						D['MLBSN'] = line_strip

				if line_strip.startswith('[') and line_strip.endswith(':-)'):
					ecid_value = line_strip.translate(None, '[]:-)')
					ecid_value = '{}{}'.format('0x', ecid_value)
					D['ECID'] = ecid_value
			
			mlb_ecid_list.append(D)
		
			if (D['MLBSN'] in mlbsn_list and flag == 1) or not D['MLBSN']:
				continue		
		
			lock = threading.Lock()
			lock.acquire()
			dict_writer.writerows(mlb_ecid_list)
			lock.release()
			mlbsn_list.append(D['MLBSN'])
			prev_mlbsn = D['MLBSN']
			flag = 1
			csv_file.flush()
			print_color('read {} successful'.format(D))

	
	usb_device_list = usb_device_list()
	mlbsn_ecid_file = open('mlbsn_ecid.csv', 'a+')
	fieldnames = ['MLBSN', 'ECID']
	
	dict_writer = csv.DictWriter(mlbsn_ecid_file, fieldnames=fieldnames)

	
	for usb_device in usb_device_list:
		t = threading.Thread(target=read_ecid, args=(usb_device, dict_writer, mlbsn_ecid_file))
		t.start()

	'''

	'''
	usb_device_list = usb_device_list()
	usb_location_list = usb_location_list()

	proc = connect_to_device(usb_device_list[0])
	
	force_to_recovery(usb_location_list[0])
	
	interrupt_to_iboot(proc)
	
	iboot_to_diags(proc)
	'''


