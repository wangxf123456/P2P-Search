from PyQt4.QtGui import *
from PyQt4.QtCore import *
from peer import Peer
import sys, operator

class MainInterface(QWidget):
	torrentHeader = ["Name", "File Name", "Size"]
	taskHeader = ["File Name", "Size", "Progress"]
	data = [("1", "2")]
	def __init__(self):
		super(MainInterface, self).__init__()
		self.peer = Peer()
		self.peer.start()
		self.initData()
		self.initUI()

	def initData(self):
		self.torrentData = self.peer.request_torrent_list()

		# configure table view of torrents
		torrentTableModel = MyTableModel(self, self.torrentData, self.torrentHeader)
		self.torrentTableView = QTableView()
		self.torrentTableView.setModel(torrentTableModel)

	def initUI(self):
		self.setGeometry(300, 300, 1000, 500)
		self.setWindowTitle("P2P Search")

		# self.torrentTableView.resizeColumnsToContents()

		# configure table view of tasks
		taskTableModel = MyTableModel(self, self.data, self.taskHeader)
		self.taskTableView = QTableView()
		self.taskTableView.setModel(taskTableModel)
		# self.taskTableView.resizeColumnsToContents()

		self.taskInfo = QTextEdit()
		self.taskInfo.setReadOnly(True)
		self.taskInfo.setLineWrapMode(QTextEdit.NoWrap)

		self.torrentLabel = QLabel()
		self.torrentLabel.setText("Torrents On Server")

		rightLayout = QVBoxLayout()
		rightLayout.addWidget(self.taskTableView)
		rightLayout.addWidget(self.taskInfo, 3)
		leftLayout = QVBoxLayout()
		leftLayout.addWidget(self.torrentLabel)
		leftLayout.addWidget(self.torrentTableView)
		mainLayout = QHBoxLayout()
		mainLayout.addLayout(leftLayout)
		mainLayout.addLayout(rightLayout, 3)

		self.setLayout(mainLayout)
		self.show()

class MyTableModel(QAbstractTableModel):
	def __init__(self, parent, list, header, *args):
		QAbstractTableModel.__init__(self, parent, *args)
		self.list = list
		self.header = header

	def rowCount(self, parent):
		return len(self.list)

	def columnCount(self, parent):
		if self.list is None:
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

def main():
	app = QApplication(sys.argv)
	program = MainInterface()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()