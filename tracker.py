import socket, os, header, struct
from threading import Thread, Lock
from random import randint

tracker_ip_map = {}
map_lock = Lock()

def main():
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host = socket.gethostbyname(socket.gethostname())
	s.bind((host, 0))
	port = s.getsockname()[1]
	print "server start on:", host, port
	s.listen(5)
	while True:
		c, addr = s.accept()
		print "Get connection from ", addr
		thread = Thread(target = handler, args = (c, addr))
		thread.start()

def handler(client, addr):
	print "Handler assigned"
	h = client.recv(header.INT_SIZE) # receive a header to decide what to do
	if struct.unpack('I', h)[0] == header.GET_CHUNK_IP:
		get_chunk_ip_handler(client)
	elif struct.unpack('I', h)[0] == header.PUT_CHUNK_IP:
		put_chunk_ip_handler(client)
	client.close()

def get_chunk_ip_handler(client):
	print "handle get chunk ip request"
	chunk_num = struct.unpack('I', client.recv(header.INT_SIZE))[0]

	for i in range(chunk_num):
		chunk_hash = client.recv(header.SHA1_LEN)
		assert(len(chunk_hash) == header.SHA1_LEN)
		index = randint(0, len(tracker_ip_map[chunk_hash]) - 1)
		map_lock.acquire()
		ip_port = tracker_ip_map[chunk_hash][index]
		map_lock.release()
		print "send ip port:", ip_port
		client.send(ip_port + '\0' * (header.MAX_IP_LEN + 6 - len(ip_port)))
	print "finish get chunk ip request"	

def put_chunk_ip_handler(client):
	print "handle put chunk ip request"
	ip = client.recv(header.MAX_IP_LEN)
	ip = ip.replace('\0', '')
	print "get ip:", ip
	port = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	print "get port:", port
	ip_port = ip + ':' + str(port)
	print "get ip port:", ip_port
	count = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	print "get hash count:", count
	for i in range(count):
		chunk_hash = client.recv(header.SHA1_LEN)
		map_lock.acquire()
		if chunk_hash in tracker_ip_map:
			if ip_port not in tracker_ip_map[chunk_hash]:
				tracker_ip_map[chunk_hash].append(ip_port)
		else:
			tracker_ip_map[chunk_hash] = [ip_port]
		map_lock.release()
	print tracker_ip_map
	print "finish put chunk ip request"	

if __name__ == '__main__':
	main()