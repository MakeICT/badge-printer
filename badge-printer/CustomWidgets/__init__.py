import base64

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5 import QtWebEngineWidgets
from PyQt5 import QtMultimediaWidgets

class ClickableCameraViewfinder(QtMultimediaWidgets.QCameraViewfinder):
	clicked = QtCore.pyqtSignal()

	def __init__(self, parent=None):
		super().__init__(parent)
		self.installEventFilter(self)

	def eventFilter(self, obj, event):
		if event.type() == QtCore.QEvent.MouseButtonRelease:
			self.clicked.emit()

		return False


class LineEditSubmitter(QtWidgets.QLineEdit):
	enterKeyPressed = QtCore.pyqtSignal()

	def __init__(self, parent=None):
		super().__init__(parent)
		self.installEventFilter(self)

	def eventFilter(self, obj, event):
		if event.type() == QtCore.QEvent.KeyPress:
			if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
				self.enterKeyPressed.emit()

		return False

class WebViewer(QtWebEngineWidgets.QWebEngineView):
	documentReady = QtCore.pyqtSignal(object)

	def __init__(self, parent):
		super().__init__(parent)
		self.loadFinished.connect(self._contentLoaded)
		self._css = '''
			<style>
				@media screen {
					svg {
						background: ''' + self.palette().color(self.backgroundRole()).name() + ''';
						margin: auto;
						margin-top: 2%;
						height: 96%;
						width: auto;
						max-width: 96%;
					}
				}
			</style>
		'''
		self._css = self._css.replace('\n', '').replace('\t', '')

	def _contentLoaded(self):
		def emitIfReady(content):
			if content != '<html><head></head><body></body></html>':

				self.runJS('document.documentElement.innerHTML += "' + self._css + '";')
				self.documentReady.emit(content)

		self.processContent(emitIfReady)

	def runJS(self, js, callback=None):
		if callback is not None:
			self.page().runJavaScript(js, callback)
		else:
			self.page().runJavaScript(js)

	def setText(self, id, text, callback=None):
		# QtWebEngine cannot access page elements...
		# But it can run arbirtary javascript!
		js = '''
			var el = document.getElementById("%s");
			if(el) el.firstChild.textContent = "%s";
		'''
		self.runJS(js % (id, text), callback)

	#	type should be "png" or "jpeg"
	def setImage(self, id, data, imageType, callback=None):
		data = 'data:image/%s;base64,%s' % (imageType, base64.b64encode(data).decode('ascii'))
		js = '''
			var el = document.getElementById("%s");
			if(el) el.setAttribute("xlink:href", "%s");
		'''
		self.runJS(js % (id, data), callback)

	def processContent(self, processFunction):
		def stripCSS(content):
			processFunction(content.replace(self._css, ''))

		self.runJS('document.documentElement.outerHTML', stripCSS)

	def extractTags(self, tagName, attributes, processFunction):
		attributes.insert(0, 'id')
		js = '''
			var collection = document.getElementsByTagName("%s");
			var attributes = %s;
			var result = [];
			for(var i=0; i<collection.length; i++){
				if(collection[i].id){
					var obj = {};
					for(var j=0; j<attributes.length; j++){
						var key = attributes[j];
						obj[key] = collection[i][key];
					}
					result.push(obj);
				}
			}
			result;'''
		self.runJS(js % (tagName, attributes), processFunction)


