import socket, header, struct, os, hashlib, sys
from threading import Thread, Lock

class chunk_record():
	def __init__(self, f_path, offset):
		self.f_path = f_path
		self.offset = offset

class downloading_record():
	def __init__(self, f_size):
		self.f_size = f_size
		self.current_size = 0
		self.r_lock = Lock()

	def lock(self):
		self.r_lock.acquire()

	def unlock(self):
		self.r_lock.release()

class Peer():
	torrents_download_path = './download_torrents'
	files_download_path = './download_files'
	hash_map = {}
	downloading_files = {}
	server_ip = "192.168.1.100"
	server_port = 60291
	tracker_ip = "192.168.1.100"
	tracker_port = 60187
	peer_host = ""
	peer_port = 0

	def start(self):
		thread = Thread(target = self.download_request_handler, args = ())
		thread.start()
		# self.server_ip = raw_input("Input server ip: ")
		# self.server_port = int(raw_input("Input server port: "))
		# self.tracker_ip = raw_input("Input tracker ip: ")
		# self.tracker_port = int(raw_input("Input tracker port: "))

		if not os.path.exists(self.files_download_path):
			os.makedirs(self.files_download_path)
		if not os.path.exists(self.torrents_download_path):
			os.makedirs(self.torrents_download_path)

		# while True:
		# 	operation = raw_input("input operation num: ")
		# 	if operation == str(0):
		# 		print "1: request torrent list\n2: download torrent\n3: download file\n4:upload file"
		# 	elif operation == str(1):
		# 		self.request_torrent_list()
		# 	elif operation == str(2):
		# 		self.download_torrent()
		# 	elif operation == str(3):
		# 		self.download_file()
		# 	elif operation == str(4):
		# 		self.upload_file()	

	def request_torrent_list(self):
		s = socket.socket()
		s.connect((self.server_ip, self.server_port))
		s.send(struct.pack('I', header.GET_TORRENT_LIST))

		f_num = struct.unpack('I', s.recv(header.INT_SIZE))[0]
		f_list = []
		print "total file num:", f_num
		for i in range(int(f_num)):
			t_name = s.recv(header.MAX_FILENAME_LEN).replace('\0', '')
			f_name = s.recv(header.MAX_FILENAME_LEN).replace('\0', '')
			f_size = struct.unpack('I', s.recv(header.INT_SIZE))[0]
			record = (t_name, f_name, f_size)
			f_list.append(record)
		print "torrent files are: ", f_list
		s.close()
		return f_list

	def download_torrent(self):
		s = socket.socket()
		s.connect((self.server_ip, self.server_port))
		s.send(struct.pack('I', header.DOWNLOAD_TORRENT))
		
		f_name = raw_input("Input file name: ")
		s.send(f_name + '\0' * (header.MAX_FILENAME_LEN - len(f_name)))

		f = open(self.torrents_download_path + '/' + f_name, 'wb+')
		f_size = struct.unpack('I', s.recv(header.INT_SIZE))[0]
		print "file size is:", f_size

		pos = 0
		while pos < f_size:
			data = s.recv(header.FILE_BUF_LEN)
			f.write(data)
			pos += len(data)
		print f_name, "torrent downloaded"
		s.close()

	def download_request_handler(self):
		s = socket.socket()
		self.peer_host = socket.gethostbyname(socket.gethostname())
		s.bind((self.peer_host, 0))
		self.peer_port = int(s.getsockname()[1])
		print "peer start on:", self.peer_host, self.peer_port	
		s.listen(5)
		while True:
			c, addr = s.accept()
			print "Peer get connection from ", addr
			thread = Thread(target = self.download_request_handler_thread, args = (c, ))
			thread.start()

	def download_request_handler_thread(self, client):
		chunk_hash = client.recv(header.SHA1_LEN)
		assert(len(chunk_hash) == header.SHA1_LEN)
		assert(chunk_hash in self.hash_map)

		f_record = self.hash_map[chunk_hash]
		f = open(f_record.f_path)
		f.seek(0, os.SEEK_END)
		f_size = f.tell()
		f.seek(f_record.offset, os.SEEK_SET)
		print "handle request:", f_record.f_path, f_record.offset
		if f_size - f_record.offset >= header.CHUNK_SIZE:
			send_size = header.CHUNK_SIZE
		else:
			send_size = f_size - f_record.offset

		client.send(struct.pack('I', send_size))
		data = f.read(header.CHUNK_SIZE)
		assert(len(data) == send_size)
		client.send(data)
		client.close()

	def download_file(self):
		t_name = raw_input("Input torrent name: ")
		t = open(self.torrents_download_path + '/' + t_name)
		assert(t != None)
		f_name = t.readline().replace('\n', '')
		f_size = int(t.readline())

		# create a new record to indicate the progress
		self.downloading_files[f_name] = downloading_record(f_size)
		chunk_num = int(t.readline())
		chunk_hash_list = []
		for i in range(chunk_num):
			chunk_hash_list.append(t.readline().replace('\n', ''))
		assert(len(chunk_hash_list) == chunk_num)
		tracker_ip_port = t.readline().replace('\n', '')
		t.close()
		tracker_ip, tracker_port = tracker_ip_port.split(":")
		print "tracker is:", tracker_ip, tracker_port
		s = socket.socket()
		s.connect((tracker_ip, int(tracker_port)))

		# request ip for each chunk hash
		s.send(struct.pack('I', header.GET_CHUNK_IP))
		s.send(struct.pack('I', chunk_num))

		# create an empty file
		f = open(self.files_download_path + '/' + f_name, "w+b")
		f.close()
		for i in range(chunk_num):
			s.send(chunk_hash_list[i])
			ip_port = s.recv(header.MAX_IP_LEN + 6).replace('\0', '') # receive ip and port
			print "ip_port:", ip_port, len(ip_port)
			ip, temp = ip_port.split(':')
			port = int(temp)
			print "chunk", i, "assigned", "ip:", ip, "port", port
			Thread(target = self.download_file_thread, args = (chunk_hash_list[i], ip, port, (f_name, f_size, i))).start()
		s.close()

	def download_file_thread(self, chunk_hash, ip, port, f_info):
		assert(len(chunk_hash) == header.SHA1_LEN)
		f_name, f_size, index = f_info[0], f_info[1], f_info[2]
		try:
			f = open(self.files_download_path + '/' + f_name, "r+b")
		except IOError:
			f = open(self.files_download_path + '/' + f_name, "wb")
		f.seek(index * header.CHUNK_SIZE, os.SEEK_SET)
		s = socket.socket()
		s.connect((ip, port))
		s.send(chunk_hash)
		chunk_size = struct.unpack('I', s.recv(header.INT_SIZE))[0]	
		print "in thread", index
		pos = 0

		# check file integrity
		sha1 = hashlib.sha1()
		while pos < chunk_size:
			data = s.recv(header.FILE_BUF_LEN)
			f.write(data)
			sha1.update(data)
			pos += len(data)
		
		print sha1.hexdigest(), chunk_hash, index
		assert(sha1.hexdigest() == chunk_hash)

		self.tell_tracker([chunk_hash])
		print f_name, "chunk", index, "download finish"
		s.close()
		f.close()

	def upload_file(self):
		f_path = raw_input("Input file path: ")
		f_name = f_path.split('/')[-1]
		print "file name is:", f_name
		f = open(f_path)
		hash_list = []
		f_size = 0
		offset = 0
		while True:
			data = f.read(header.CHUNK_SIZE)
			if not data:
				break
			print len(data)
			f_size += len(data)
			sha1 = hashlib.sha1()
			sha1.update(data)
			sha1_hash = sha1.hexdigest()
			hash_list.append(sha1_hash)
			record = chunk_record(f_path, offset)
			self.hash_map[sha1_hash] = record
			offset += header.CHUNK_SIZE

		Thread(target = self.tell_server, args = (f_name, f_size, hash_list)).start()
		Thread(target = self.tell_tracker, args = (hash_list, )).start()

	def tell_server(self, f_name, f_size, hash_list):
		print "start tell server"
		s = socket.socket()
		s.connect((self.server_ip, self.server_port))
		s.send(struct.pack('I', header.SERVER_UPLOAD_FILE))
		print f_name
		s.send(f_name + '\0' * (header.MAX_FILENAME_LEN - len(f_name)))
		s.send(struct.pack('I', f_size))
		count = len(hash_list)
		print "send server hash count:", count
		s.send(struct.pack('I', count))
		for i in range(count):
			s.send(hash_list[i])
		s.send(self.tracker_ip + '\0' * (header.MAX_IP_LEN - len(self.tracker_ip)))
		s.send(struct.pack('I', self.tracker_port))
		s.close()

	def tell_tracker(self, hash_list):
		print "start tell tracker"
		print "tracker", hash_list
		s = socket.socket()
		s.connect((self.tracker_ip, self.tracker_port))
		s.send(struct.pack('I', header.PUT_CHUNK_IP))
		print "send ip port:", self.peer_host, self.peer_port
		s.send(self.peer_host + '\0' * (header.MAX_IP_LEN - len(self.peer_host)))
		s.send(struct.pack('I', self.peer_port))
		count = len(hash_list)
		print "send tracker hash count:", count
		s.send(struct.pack('I', count))
		for i in range(count):
			s.send(hash_list[i])
		s.close()

def test():
	s = socket.socket()
	host = socket.gethostbyname(socket.gethostname())
	port = s.getsockname()[1]
	print host, port

if __name__ == '__main__':
	peer = Peer()
	peer.start()