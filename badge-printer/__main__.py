#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, traceback, io
import base64
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5 import QtWebEngineWidgets, QtPrintSupport, QtMultimediaWidgets
from PyQt5 import QtMultimedia

import pyqrcode

#d V4L2

CHOOSE_CUSTOM = object()
RELOAD = object()

class BadgePrinterApp(QtWidgets.QApplication):
	def __init__(self, args):
		super().__init__(args)
		self.basePath = os.path.dirname(os.path.realpath(__file__))
		self.templateFilename = None
		self.camera = None

		self.mainWindow = uic.loadUi(self._path('MainWindow.ui'))
		self.mainWindow.previewTabs.tabBar().hide()
		
		self.cameraViewFinder = QtMultimediaWidgets.QCameraViewfinder(self.mainWindow.cameraTab)
		self.mainWindow.cameraTab.layout().addWidget(self.cameraViewFinder)

		preview = self.mainWindow.preview
		preview.page().setBackgroundColor(
			preview.palette().color(preview.backgroundRole())
		)

		self.mainWindow.actionImport.triggered.connect(self.attemptImport)
		self.mainWindow.actionLoadTemplate.triggered.connect(self.browseForTemplate)
		self.mainWindow.actionSaveACopy.triggered.connect(self.saveACopy)

		self.mainWindow.actionCapture.triggered.connect(self.captureToggle)
		self.mainWindow.actionPrint.triggered.connect(self.attemptPrint)

		self.mainWindow.actionExit.triggered.connect(self.exit)

		self.reloadTemplates()

		self.mainWindow.templateSelector.currentIndexChanged.connect(self._templateSelected)
		
		self.mainWindow.preview.installEventFilter(self)

		self.mainWindow.preview.loadFinished.connect(self._contentLoaded)
		
		self.mainWindow.firstName.textChanged.connect(partial(self._updatePreview, True))
		self.mainWindow.lastName.textChanged.connect(partial(self._updatePreview, True))
		self.mainWindow.title.textChanged.connect(self._updatePreview)
		self.mainWindow.qrInput.textChanged.connect(self._updatePreview)

	def _path(self, *paths):
		return os.path.join(self.basePath, *paths)

	def _templateSelected(self, index):
		try:
			combobox = self.mainWindow.templateSelector
			data = combobox.itemData(combobox.currentIndex())

			if data == CHOOSE_CUSTOM:
				self.browseForTemplate()
			elif data == RELOAD:
				self.reloadTemplates()
			else:
				self.loadTemplate(self._path('templates', combobox.currentText()))
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def browseForTemplate(self):
		result = QtWidgets.QFileDialog.getOpenFileName(self.mainWindow, 'Open file', '.', 'SVG Files (*.svg);;All files (*)')
		if result[0] != '':
			self.loadTemplate(result[0])

	def doItNowDoItGood(self):
		self.mainWindow.showNormal()
		self.exec_()

	def attemptImport(self):
		try:
			raise NotImplementedError()
		except Exception as exc:
			unhandledError(exc, self.mainWindow)


	def saveACopy(self):
		try:
			raise NotImplementedError()
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def captureToggle(self):
		try:
			tabs = self.mainWindow.previewTabs
			if tabs.currentWidget() == self.mainWindow.badgePreviewTab:
				tabs.setCurrentWidget(self.mainWindow.waitTab)

				if self.camera is None:
					cameraInfo = QtMultimedia.QCameraInfo.availableCameras()[0]
					self.camera = QtMultimedia.QCamera(cameraInfo)
					self.camera.viewfinderSettings().setResolution(640,480)
					self.camera.setViewfinder(self.cameraViewFinder)
					self.cameraViewFinder.setAspectRatioMode(QtCore.Qt.KeepAspectRatio)

					def statusChanged(status):
						if status == QtMultimedia.QCamera.ActiveStatus:
							tabs.setCurrentWidget(self.mainWindow.cameraTab)

					self.camera.statusChanged.connect(statusChanged)
				self.camera.start()

			elif tabs.currentWidget() == self.mainWindow.cameraTab:
				def imageSaved(id, filename):
					self.useImage(filename)

				self.imageCapture = QtMultimedia.QCameraImageCapture(self.camera)
				self.imageCapture.imageSaved.connect(imageSaved)
				tmpFile = os.path.abspath(os.path.join('archive', '_capture.jpg'))
				self.imageCapture.capture(tmpFile)
				self.camera.stop()

		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def useImage(self, filename):
		try:
			with open(filename, 'rb') as captureFile:
				self.updateImage('photo', captureFile.read(), 'jpeg')
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def attemptPrint(self):
		try:
			raise NotImplementedError()

			printer = QtPrintSupport.QPrinter()
			dialog = QtPrintSupport.QPrintDialog(printer, self.mainWindow)
			if dialog.exec_() != QtWidgets.QDialog.Accepted:
				return
			
			painter = QtGui.QPainter(printer)
			painter.begin(printer)
			painter.end()

		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def exit(self):
		try:
			# @TODO: check if changes made since last print or save
			self.quit()
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def reloadTemplates(self):
		try:
			combobox = self.mainWindow.templateSelector
			combobox.clear()
			templates = []
			for filename in os.listdir(self._path('templates')):
				if filename[-4:].lower() == '.svg':
					templates.append(filename)
			templates.sort()
			combobox.addItems(templates)

			combobox.setCurrentIndex(combobox.count()-1)
			self.loadTemplate(combobox.currentText())

			combobox.insertSeparator(len(templates))
			combobox.addItem('✎ Choose custom...', CHOOSE_CUSTOM)
			combobox.addItem('⟳ Reload templates', RELOAD)

		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def loadTemplate(self, filename):
		try:
			filename = self._path('templates', filename)
			self.templateFilename = filename

			self.mainWindow.preview.setUrl(QtCore.QUrl.fromLocalFile(filename))
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def _contentLoaded(self):
		self._updatePreview()
		self.autoScale()

	def autoScale(self):
		preview = self.mainWindow.preview
		def haveDocumentSize(size):
			if 0 in size:
				return
			contentSize = QtCore.QSize(size[0], size[1])

			widthRatio = preview.width() / contentSize.width()
			heightRatio = preview.height() / contentSize.height()
			scale = min(widthRatio, heightRatio)
			preview.setZoomFactor(scale)
			# give a little padding
			preview.setZoomFactor(.9*scale)

			# try to vertically center...
			preview.page().runJavaScript('''
				document.documentElement.style.margin = "auto";
				document.documentElement.style.marginTop = "%dpx";
			''' % int((preview.height() - scale*contentSize.height())))

		js = '[document.documentElement.scrollWidth, document.documentElement.scrollHeight]'
		preview.page().runJavaScript(js, haveDocumentSize)


	def eventFilter(self, obj, event):
		if obj == self.mainWindow.preview:
			if isinstance(event, QtGui.QResizeEvent):
				#self.mainWindow.preview.setZoomFactor(1)
				#self.ignoreNextScaleChange = False
				self.autoScale()

		return super().eventFilter(obj, event)

	def _updatePreview(self, updateQRInput=False):
		self.autoScale()
		# Hack-job alert :(
		# QtWebEngine cannot access page elements...
		# But it can run arbirtary javascript!
		js = '''
			var el = document.getElementById("%s");
			if(el) el.firstChild.textContent = "%s";
		'''

		def update(id, value):
			self.mainWindow.preview.page().runJavaScript(js % (id, value))
		
		update('firstName', self.mainWindow.firstName.text())
		update('lastName', self.mainWindow.lastName.text())
		update('title', self.mainWindow.title.text())

		if updateQRInput:
			nameInputs = [
				self.mainWindow.firstName.text().strip(),
				self.mainWindow.lastName.text().strip(),
			]
			while '' in nameInputs:
				nameInputs.remove('')

			for id, name in enumerate(nameInputs):
				name = name.replace(' ', '_')
				name = QtCore.QUrl.toPercentEncoding(name).data()
				name = name.decode('utf-8')
				nameInputs[id] = name

			name = '_'.join(nameInputs)

			if name == '':
				self.mainWindow.qrInput.setText('http://makeict.org/')
			else:
				self.mainWindow.qrInput.setText('http://makeict.org/wiki/User:%s' % name)

		buffer = io.BytesIO()
		qr = pyqrcode.create(self.mainWindow.qrInput.text())
		qr.png(buffer, scale=10, quiet_zone=0)
		self.updateImage('qr', buffer.getvalue(), 'png')
	
	#	type should be "png" or "jpeg"
	def updateImage(self, id, rawData, imageType):
		def goToPreview(dummy=None):
			self.mainWindow.previewTabs.setCurrentWidget(self.mainWindow.badgePreviewTab)

		data = 'data:image/%s;base64,%s' % (imageType, base64.b64encode(rawData).decode('ascii'))
		js = '''
			var el = document.getElementById("%s");
			if(el) el.setAttribute("xlink:href", "%s");
		'''
		self.mainWindow.preview.page().runJavaScript(js % (id, data), goToPreview)

def unhandledError(exc, parent=None):
	dialog = QtWidgets.QMessageBox(parent)
	dialog.setWindowTitle('Error :(')
	if isinstance(exc, NotImplementedError):
		dialog.setText('Sorry! This feature isn\'t implemented yet :(\n\nWanna help? Visit http://github.com/makeict/badge-printer')
	else:
		stack = traceback.format_exc()
		print(stack)
		dialog.setText('Well this is embarrasing... Something went wrong and I didn\'t know how to handle it.\n\nPlease help us fix this bug!')
		dialog.setDetailedText(
			'The details below can help troubleshoot the issue. Please copy-and-paste this in any report.\n\n' +
			'Developer info at http://github.com/makeict/badge-printer\n\n' + 
			'%s' % stack
		)

	dialog.setModal(True)
	dialog.exec_()

if __name__ == '__main__':
	try:
		os.makedirs('archive', exist_ok=True)

		app = BadgePrinterApp(sys.argv)
		app.doItNowDoItGood()
	except Exception as exc:
		unhandledError(exc)