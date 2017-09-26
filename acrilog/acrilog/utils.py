'''
Created on Sep 19, 2017

@author: arnon
'''
import socket

LOCAL_HOST = '127.0.0.1'
def get_free_port():
    
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((LOCAL_HOST,0))
    host,port=s.getsockname()
    s.close()
    return port

if __name__ == '__main__':
    print(get_free_port())