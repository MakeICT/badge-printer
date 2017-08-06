import base64

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5 import QtWebEngineWidgets

class WebViewer(QtWebEngineWidgets.QWebEngineView):
	documentReady = QtCore.pyqtSignal(object)

	def __init__(self, parent):
		super().__init__(parent)
		self.loadFinished.connect(self._contentLoaded)
		self.page().setBackgroundColor(self.palette().color(self.backgroundRole()))
		self.installEventFilter(self)

	def _contentLoaded(self):
		def emitIfReady(content):
			if content != '<html><head></head><body></body></html>':
				self.autoScale()
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
		self.runJS('document.documentElement.outerHTML', processFunction)

	def autoScale(self):
		def haveDocumentSize(size):
			if 0 in size:
				return
			contentSize = QtCore.QSize(size[0], size[1])

			widthRatio = self.width() / contentSize.width()
			heightRatio = self.height() / contentSize.height()
			scale = min(widthRatio, heightRatio)
			self.setZoomFactor(scale)
			# give a little padding
			self.setZoomFactor(.9*scale)

#			# try to vertically center...
#			self._adjustPreviewPosition(int((preview.height() - scale*contentSize.height())))

		js = '[document.documentElement.scrollWidth, document.documentElement.scrollHeight]'
		self.runJS(js, haveDocumentSize)

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

	def eventFilter(self, obj, event):
		if isinstance(event, QtGui.QResizeEvent):
			self.autoScale()

		return super().eventFilter(obj, event)

#	def _adjustPreviewPosition(self, marginInPixels=0, printPrep=False):
#		preview = self.mainWindow.preview
#		preview.page().runJavaScript('''
#			document.documentElement.style.margin = "auto";
#			document.documentElement.style.marginTop = "%dpx";
#		''' % marginInPixels)
#
#		if printPrep:
#			preview.page().setBackgroundColor(QtCore.Qt.white)
#		else:
#			preview.page().setBackgroundColor(
#				preview.palette().color(preview.backgroundRole())
#			)
#####
