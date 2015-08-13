import socket, os, header, struct
from threading import Thread

torrents_folder_path = "./torrents"

def main():
	# socket init
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host = socket.gethostbyname(socket.gethostname())
	s.bind((host, 0))
	port = s.getsockname()[1]
	print "server start on:", host, port
	s.listen(5)
	while True:
		c, addr = s.accept()
		print "Get connection from ", addr
		thread = Thread(target = handler, args = (c, ))
		thread.start()

def handler(client):
	print "Handler assigned"
	h = client.recv(header.INT_SIZE) # receive a header to decide what to do
	if struct.unpack('I', h)[0] == header.GET_TORRENT_LIST:
		get_torrent_list_handler(client)
	elif struct.unpack('I', h)[0] == header.DOWNLOAD_TORRENT:
		download_torrent_handler(client)
	elif struct.unpack('I', h)[0] == header.SERVER_UPLOAD_FILE:
		upload_torrent_handler(client)
	client.close()

def get_torrent_list_handler(client):
	print "handle get torrent list request"

	if not os.path.exists(torrents_folder_path):
		os.makedirs(torrents_folder_path)

	torr_lst = os.listdir(torrents_folder_path)

	# first send how many files will be sent
	client.send(struct.pack('I', len(torr_lst)))

	# send torrent name, file name, file size
	for torr_name in torr_lst:
		client.send(torr_name + '\0' * (header.MAX_FILENAME_LEN - len(torr_name)))
		f = open(torrents_folder_path + '/' + torr_name)
		f_name = f.readline().replace('\n', '')
		client.send(f_name + '\0' * (header.MAX_FILENAME_LEN - len(f_name)))
		f_size = int(f.readline())
		client.send(struct.pack('I', f_size))

	print "finish get torrent list request"

def download_torrent_handler(client):
	print "handle download torrent request"

	f_name = client.recv(header.MAX_FILENAME_LEN).split('\0')[0]

	print "Get file name:", f_name
	f = open(torrents_folder_path + '/' + f_name)

	# send file size first
	f_start = f.tell()
	f.seek(0, os.SEEK_END)
	f_size = f.tell()
	f.seek(f_start, os.SEEK_SET)

	print "Send file size:", f_size
	client.send(struct.pack('I', f_size))

	# send file content
	data = ""
	while True:
		data = f.read(header.FILE_BUF_LEN)
		if not data:
			break
		client.send(data)

	print "finish download torrent request"

def upload_torrent_handler(client):
	print "handle upload torrent request"
	f_name_len = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	print "get file name len:", f_name_len
	f_name = client.recv(f_name_len)
	print "before:", f_name, len(f_name)
	f_name = f_name.replace('.', '_')
	print "get file name:", f_name, len(f_name)

	f = open(torrents_folder_path + '/' + f_name + ".torrent", "w+b")
	f_size = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	print "get file size:", f_size

	count = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	print "get hash count:", count
	f.write(f_name + "\n")
	f.write(str(f_size) + "\n")
	f.write(str(count) + "\n")
	for i in range(count):
		f.write(client.recv(header.SHA1_LEN) + "\n")
	tracker_ip_len = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	tracker_ip = client.recv(tracker_ip_len)
	print "get tracker ip:", tracker_ip
	tracker_port = struct.unpack('I', client.recv(header.INT_SIZE))[0]
	f.write(tracker_ip + ":" + str(tracker_port))
	print "finish upload torrent request"

if __name__ == '__main__':
	main()