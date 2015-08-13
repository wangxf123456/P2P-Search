from PyQt4.QtGui import *
from PyQt4.QtCore import *
from peer import Peer
from threading import Thread
from functools import partial
import sys, operator, os

local_torrents_folder_path = "./download_torrents"

class MyTableModel(QAbstractTableModel):
	def __init__(self, parent, list, header, *args):
		QAbstractTableModel.__init__(self, parent, *args)
		self.list = list
		self.header = header

	def rowCount(self, parent):
		return len(self.list)

	def columnCount(self, parent):
		if self.list is None or len(self.list) == 0:
			return 0
		else:
			return len(self.list[0])

	def data(self, index, role):
		if not index.isValid():
			return None
		elif role != Qt.DisplayRole:
			return None
		return self.list[index.row()][index.column()]

	def headerData(self, col, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return self.header[col]
		return None

	def sort(self, col, order):
		self.emit(SIGNAL("layoutAboutToBeChanged()"))
		self.list = sorted(self.list, key=operator.itemgetter(col))
		if order == Qt.DescendingOrder:
			self.list.reverse()

		self.emit(SIGNAL("layoutChanged()"))

class MainInterface(QMainWindow):
	torrentHeader = ["Name", "File Name", "Size"]
	taskHeader = ["Torrent Name", "File Name", "Size", "Progress"]

	def __init__(self):
		super(MainInterface, self).__init__()
		self.peer = Peer()
		self.peer.set_parent(self)
		self.peer.start()
		self.initUI()
		self.initSignals()
		self.initData()

	def initMenu(self):
		openFile = QAction('Make torrent', self)
		openFile.setStatusTip('Upload file')
		openFile.triggered.connect(self.makeTorrent)

		self.statusBar()
		menuBar = self.menuBar()

		fileMenu = menuBar.addMenu("&File")
		fileMenu.addAction(openFile)

	def makeTorrent(self):
		fPath = QFileDialog.getOpenFileName(self, 'Open File', "~/Desktop")
		self.peer.upload_file(unicode(fPath.toUtf8(), encoding="UTF-8"))

	def initSignals(self):
		QObject.connect(self, SIGNAL("GET_TORRENT_ON_SERVER"), self.retrieveTorrentOnServer)
		QObject.connect(self, SIGNAL("FINISH_DOWNLOAD_TORRENT(PyQt_PyObject)"), self.showDownloadFinishMsg)
		QObject.connect(self.torrentTableView, SIGNAL("doubleClicked(QModelIndex)"), self.downloadTorrentAtIndex)
		QObject.connect(self.taskTableView, SIGNAL("doubleClicked(QModelIndex)"), self.downloadFileAtIndex)
	
	def initData(self):
		self.emit(SIGNAL("GET_TORRENT_ON_SERVER"))

	def retrieveTorrentOnServer(self):
		self.torrentOnServer = self.peer.request_torrent_list()

		# configure table view of torrents
		self.torrentTableModel = MyTableModel(self, self.torrentOnServer, self.torrentHeader)
		self.torrentTableView.setModel(self.torrentTableModel)

	def retrieveLocalTorrent(self):
		self.localTorrentData = []
		torr_list = os.listdir(local_torrents_folder_path)
		for name in torr_list:
			f = open(local_torrents_folder_path + '/' + name)
			f_name = f.readline().replace('\n', '')
			f_size = int(f.readline())
			self.localTorrentData.append((name, f_name, f_size, 0))

	def downloadTorrentAtIndex(self, index):
		item = self.torrentOnServer[index.row()]
		Thread(target=self.peer.download_torrent, args=(item[0],)).start()

	def downloadFileAtIndex(self, index):
		item = self.localTorrentData[index.row()]
		Thread(target=self.peer.download_file, args=(item[0],)).start()

	def finishDownloadTorrentHandler(self, tName):
		self.emit(SIGNAL("FINISH_DOWNLOAD_TORRENT(PyQt_PyObject)"), tName)

	def showDownloadFinishMsg(self, tName):
		f = open(local_torrents_folder_path + '/' + tName)
		f_name = f.readline().replace('\n', '')
		f_size = int(f.readline())
		self.taskTableModel.layoutAboutToBeChanged.emit()
		self.localTorrentData.append((tName, f_name, f_size, 0))
		self.taskTableModel.layoutChanged.emit()
		msgBox = QMessageBox()
		msgBox.setText(tName + " download finish")
		msgBox.exec_()

	def initUI(self):
		self.initMenu()
		self.retrieveLocalTorrent()

		self.setGeometry(300, 300, 1000, 500)
		self.setWindowTitle("P2P Search")

		self.torrentTableView = QTableView()
		# self.torrentTableView.resizeColumnsToContents()
		# self.taskTableView.resizeColumnsToContents()

		# configure table view of tasks
		print "1"
		self.taskTableView = QTableView()
		print self.localTorrentData[1:4]
		self.taskTableModel = MyTableModel(self, self.localTorrentData, self.taskHeader)
		self.taskTableView.setModel(self.taskTableModel)	

		self.taskInfo = QTextEdit()
		self.taskInfo.setReadOnly(True)
		self.taskInfo.setLineWrapMode(QTextEdit.NoWrap)

		self.torrentLabel = QLabel()
		self.torrentLabel.setText("TORRENTS")

		rightLayout = QVBoxLayout()
		rightLayout.addWidget(self.taskTableView)
		rightLayout.addWidget(self.taskInfo, 2)
		leftLayout = QVBoxLayout()
		leftLayout.addWidget(self.torrentLabel)
		leftLayout.addWidget(self.torrentTableView)
		mainLayout = QHBoxLayout()
		mainLayout.addLayout(leftLayout)
		mainLayout.addLayout(rightLayout, 3)

		widget = QWidget()
		widget.setLayout(mainLayout)
		self.setCentralWidget(widget);
		self.show()

def main():
	app = QApplication(sys.argv)
	program = MainInterface()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()