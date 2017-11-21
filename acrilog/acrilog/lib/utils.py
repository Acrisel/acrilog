'''
Created on Sep 19, 2017

@author: arnon
'''
import socket
from copy import deepcopy

LOCAL_HOST = '127.0.0.1'
def get_free_port():
    
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((LOCAL_HOST,0))
    host,port=s.getsockname()
    s.close()
    return port


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
    except OSError:
        address = 'localhost'
    else:
        address = s.getsockname()[0]
    s.close()
    return address


def get_hostname(full=False):
    ip = get_ip_address()
    if full == False:
        try:
            name = socket.gethostbyaddr(ip)[0]
        except:
            name = ip
    else:
        name = socket.getfqdn(ip)
    return name


def hostname_resolves(hostname):
    try:
        socket.gethostbyname(hostname)
        return 1
    except socket.error:
        return 0



if __name__ == '__main__':
    print(get_free_port())