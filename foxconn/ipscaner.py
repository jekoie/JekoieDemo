import pexpect
import os
import sys
import time
import commands
import threading
import re

def printcolor(cstr, color='g'):
	if color == 'g':
		print '\033[32m%s\033[0m' %(cstr)
	elif color == 'r':
		print '\033[31m%s\033[0m' %(cstr)
	elif color == 'br':
		print '\033[33m%s\033[0m' %(cstr)
	elif color == 'pr':
		print '\033[34m%s\033[0m' %(cstr)
	elif color == 'mh':
		print '\033[35m%s\033[0m' %(cstr)
	elif color == 'cy':
		print '\033[36m%s\033[0m' %(cstr)

def host_reachable(ip):
	status = commands.getstatusoutput('ping -c 1 -t 1 -q {}'.format(ip))[0]
	if status == 0:
		printcolor('Host {} reachable'.format(ip))
		return True
	else:
		printcolor('Host {} unreachable'.format(ip))
		return False

def ssh_connect(user, ip, passwd):
	ssh_cmd = 'ssh {}@{}'.format(user, ip)
	p = pexpect.spawn(ssh_cmd)
	index = p.expect(['(yes/no)', '(?i)password', '(?i)last login', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
	
	if index == 0:
		p.sendline('yes')
		index = p.expect([r'(?i)password', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
		if index == 0:
			p.sendline(passwd)
		else:
			printcolor('Connection host failed')
			return False
	elif index == 1:
		p.sendline(passwd)
	elif index == 2:
		pass
	else:
		return False
	
	p.setecho('False')
	p.sendline('echo')
	index = p.expect(['(?i)password|Permission denied', 'gdlocal', pexpect.TIMEOUT])
	if index == 0 or index == 2:
		printcolor('Password for host is invalid')
		return False		
	
	return p

def ssh_keygen(passphrase='JettChen', comment='jett chen make'):
	ssh_path = os.path.expanduser('~/.ssh')
	if not os.path.exists(ssh_path):	
		os.makedirs(ssh_path, mode=0600)
		
	rsa_private_key = os.path.expanduser('~/.ssh/id_rsa')
	output = commands.getoutput('ssh-keygen -B -f {}'.format(rsa_private_key))
	
	if output.find('jett chen') != -1:
		printcolor('Private key already existing')	
		return

	ssh_keygen_cmd = 'ssh-keygen -t rsa -N \'{}\' -C \'{}\' -f {}'.format(passphrase, comment, rsa_private_key)
	p = pexpect.spawn(ssh_keygen_cmd)
	index = p.expect(['(?i)overwrite', pexpect.EOF])	
	
	if index == 0:
		p.sendline('y')
	else:
		pass
	
	p.expect(pexpect.EOF)
	printcolor('Generate private key successful.')
	p.close()

def pub_key():
	pub_key = os.path.expanduser('~/.ssh/id_rsa.pub')
	
	with open(pub_key, 'r') as f:
		key_str = f.read()

	return key_str

def ssh_add(passphrase='JettChen'):
	rsa_private_key = os.path.expanduser('~/.ssh/id_rsa')
	ssh_add_cmd = 'ssh-add {}'.format(rsa_private_key)
	p = pexpect.spawn(ssh_add_cmd)
	index = p.expect(['(?i)enter passphrase', pexpect.EOF])
	
	if index == 0:
		p.sendline(passphrase)	
	else:
		pass
		return 

	p.expect(pexpect.EOF)
	printcolor('Add private key to agent successful')
	p.close()

def ident_purge():
	commands.getoutput('ssh-add -D')	
	printcolor('Remove localhost identify successful')

def gh_info(p):
	restore_info = '/vault/data_collection/test_station_config/gh_station_info.json'
	printcolor('Try to get info from {}'.format(restore_info))
	cmd = 'cat {}'.format(restore_info)
	p.sendline(cmd)
	p.sendline('echo')
		
	p.expect('gdlocal')
	index = p.expect(['gdlocal', 'No such file'])
	if index == 1:
		printcolor('Get info from {} failed'.format(restore_info))
		return False	
		
	printcolor('Get info from {} successful'.format(restore_info))
	return p.before

def host_info(gh_msg):
		
	info = {}
	prn = re.compile(r'"(?:STATION_ID|STATION_OVERLAY|BUILD_STAGE|PRODUCT|STATION_IP)"\s:\s".+"', re.M)
	info_list = prn.findall(gh_msg)
	for var in info_list:
		var = var.translate(None, '" ')
		var = var.split(':')
		info[var[0]] = var[1]

	return info	

def config_write(host_info):
	
	if len(host_info) == 0:
		printcolor('{} is invaild, failed to write'.format(host_info))
		return False
	
	config_path = os.path.expanduser('~/.ssh/config')
	if not os.path.exists(config_path):
		with open(config_path, 'w') as f:
			os.fchmod(f.fileno(), 0644)

	f = open(config_path, 'r')
	config_text = f.read()
	ret = config_text.find(host_info['STATION_ID'])
	if ret != -1:
		f.close()
		printcolor('Host info already existing at {}, failed to write'.format(config_path))
		return False
	
	with open(config_path, 'a')  as f:
		
		mutex = threading.RLock()
		mutex.acquire()
		try:
			f.write('Host {}\n'.format(host_info['STATION_ID']))
			f.write('\tHostName {}\n'.format(host_info['STATION_IP']))
			f.write('\tUser {}\n'.format('gdlocal'))
			f.write('\t#PRODUCT={}\n'.format(host_info['PRODUCT']))
			f.write('\t#BUILD_STAGE={}\n'.format(host_info['BUILD_STAGE']))
		
			f.write('\t#STATION_OVERLAY={}\n'.format(host_info['STATION_OVERLAY']))
		except KeyError:
			pass
		mutex.release()
	
	printcolor('Write host info {} successful'.format(config_path))
	return True

def pubkey2host(p, pub_key_str):
	auth_key = '~/.ssh/authorized_keys'
	cmd = 'echo \'{}\' >> {}'.format(pub_key_str, auth_key)
	cmd = cmd.translate(None, '\n')
	p.sendline(cmd)
	p.sendline('')	
	printcolor('Add pub key to remote successful')

def host_scan(ip, pubkey):
	
	if not host_reachable(ip):
		return	

	ssh = ssh_connect('gdlocal', ip, 'gdlocal')
	if not ssh:
		return

	host_gh_info = gh_info(ssh)
	
	if not host_gh_info:
		return
	host_station_info = host_info(host_gh_info)	
	print host_station_info
	config_write(host_station_info)
	pubkey2host(ssh, pub_key())
	ssh.close()

if __name__ == '__main__':

	ident_purge()
	ssh_keygen()
	ssh_add()
	
#	host_scan('192.168.3.15', pub_key())
#	'''
	for i in xrange(22, 256):
		for j in xrange(1, 256):
			ip = '192.168.{}.{}'.format(i, j)
			host_scan(ip, pub_key())
#	'''
	'''
	user = 'gdlocal'
	passwd = 'gdlocal'
	ip = '192.168.9.17'	
	ssh_keygen()
	ssh_add()
	ident_purge()
	ssh = ssh_connect(user, ip, passwd)
	if not ssh:
		print ssh
		sys.exit()
	pub_key_str = pub_key()
	#pubkey2host(ssh, pub_key_str)
	gh_info = gh_info(ssh)
	info = host_info(gh_info)
	print info
	config_write(info)
	pubkey2host(ssh, pub_key_str)
	ssh.close()
	'''
