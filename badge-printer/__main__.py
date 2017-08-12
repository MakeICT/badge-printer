#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, traceback, io
import shutil
from functools import partial
import subprocess

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5 import QtWebEngineWidgets, QtPrintSupport, QtMultimediaWidgets
from PyQt5 import QtMultimedia

import pyqrcode
import webbrowser

from log import WebFormLogger

CHOOSE_CUSTOM = object()
RELOAD = object()

class BadgePrinterApp(QtWidgets.QApplication):
	def __init__(self, args):
		super().__init__(args)

		self.basePath = os.path.dirname(os.path.realpath(__file__))
		self.templateFilename = None
		self.cameraInfo = None
		self.camera = None
		self.templateElements = []
		self.nameInputs = []
		self.lastImage = None

		# Switch cameras causes a crash when the old camera object is garbage collected
		# This list keeps all cameras in memory
		self.cameraCollection = []

		self.qrTimer = QtCore.QTimer()
		self.qrTimer.setSingleShot(True)
		self.qrTimer.setInterval(1000)
		self.qrTimer.timeout.connect(self.updateQRDisplay)

		self.mainWindow = uic.loadUi(self._path('MainWindow.ui'))
		self.mainWindow.previewTabs.tabBar().hide()
		
		self.mainWindow.cameraViewFinder.setAspectRatioMode(QtCore.Qt.KeepAspectRatio)

		self.mainWindow.actionLoadTemplate.triggered.connect(self.browseForTemplate)
		self.mainWindow.actionSaveACopy.triggered.connect(self.saveACopy)

		self.mainWindow.actionCapture.triggered.connect(self.captureToggle)
		self.mainWindow.actionPrint.triggered.connect(self.attemptPrint)
		self.mainWindow.actionLogOnly.triggered.connect(self.addLogEntry)
		self.mainWindow.actionImportImage.triggered.connect(self.browseForImage)
		self.mainWindow.actionAbout.triggered.connect(self.showAppInfo)

		self.mainWindow.actionExit.triggered.connect(self.exit)
		self.mainWindow.testQR.clicked.connect(self.testQR)
		self.mainWindow.cancelCapture.clicked.connect(self.cancelCapture)

		self.mainWindow.templateSelector.currentIndexChanged.connect(self._templateSelected)

		self.mainWindow.preview.documentReady.connect(self._templateLoadComplete)

		def updatePreviewWithoutQR(qrInputText):
			self._updatePreview(False)

		self.mainWindow.qrInput.textChanged.connect(updatePreviewWithoutQR)

		if '--disable-log' in args:
			self.entryLogger = None
			self.mainWindow.controlsLayout.removeWidget(self.mainWindow.logButton)
			self.mainWindow.logButton.deleteLater()
			self.mainWindow.logButton = None

			self.mainWindow.printButton.setText('Print')
			self.mainWindow.actionPrint.setText('Print...')
			self.mainWindow.menuFile.removeAction(self.mainWindow.actionLogOnly)
			self.mainWindow.actionLogOnly.deleteLater()
			self.mainWindow.actionLogOnly = None

		else:
			self.entryLogger = WebFormLogger(
				'https://script.google.com/macros/s/AKfycbz0IA4vDWAfQJLtBSnrtKhU1TjV5wr3lbziSRDfiNmGLgVoh0s/exec',
				os.path.join('archive', 'log.txt')
			)
			self.entryLogger.logComplete.connect(self._entryLoggingComplete)
			self.entryLogger.fallbackError.connect(self._entryLogFallbackError)


	def doItNowDoItGood(self):
		self.reloadTemplates()
		self.refreshCameras()

		self.mainWindow.showNormal()
		self.exec_()

	def showAppInfo(self):
		QtWidgets.QMessageBox.about(
			self.mainWindow,
			'MakeICT Badge Printer',
			'<p>This app was made with &hearts; by <a href="http://greenlightgo.org">Dominic Canare</a> for MakeICT.</p>' + 
			'<p>Use, modification, and redistribution of this application is allowed under the terms of the <a href="https://www.gnu.org/licenses/gpl-3.0.en.html">GNU General Public License</a>.</p>' +
			'<p>For more information, visit <a href="http://github.com/makeict/badge-printer">this project\'s GitHub page</a>.</p>' +
			'<p>For more immediate help, send an email to <a href="it@makeict.org">it@makeict.org</a>.</p>'
		)

	def _path(self, *paths):
		return os.path.join(self.basePath, *paths)

	def _templateSelected(self, index):
		combobox = self.mainWindow.templateSelector
		data = combobox.itemData(combobox.currentIndex())

		if data == CHOOSE_CUSTOM:
			self.browseForTemplate()
		elif data == RELOAD:
			self.reloadTemplates()
		else:
			self.loadTemplate(combobox.currentText())

	def browseForTemplate(self):
		result = QtWidgets.QFileDialog.getOpenFileName(self.mainWindow, 'Open file', '.', 'SVG Files (*.svg);;All files (*)')
		if result[0] != '':
			self.loadTemplate(result[0])

	def testQR(self):
		webbrowser.open(self.mainWindow.qrInput.text())
	
	def saveACopy(self, filename=False):
		if not isinstance(filename, str):
			result = QtWidgets.QFileDialog.getSaveFileName(
				self.mainWindow,
				'Save a copy',
				'%s.svg' % self.makeFileFriendlyName(),
				'SVG Files (*.svg);;All files (*)'
			)
			if result[0] == '':
				return

			filename = result[0]
			if filename[-4:].lower() != '.svg':
				filename += '.svg'

		def doSave(filename, content):
			with open(filename, 'w') as saveFile:
				saveFile.write(content)

		self.mainWindow.preview.processContent(partial(doSave, filename))

	def captureToggle(self):
		tabs = self.mainWindow.previewTabs
		if tabs.currentWidget() != self.mainWindow.cameraTab:
			tabs.setCurrentWidget(self.mainWindow.waitTab)

			try:
				if self.camera is None:
					if self.cameraInfo is None:
						self._showError('No camera selected!')
						tabs.setCurrentWidget(self.mainWindow.badgePreviewTab)
						return

					self.camera = QtMultimedia.QCamera(self.cameraInfo)
					self.camera.viewfinderSettings().setResolution(640,480)
					self.camera.setViewfinder(self.mainWindow.cameraViewFinder)

					def statusChanged(status):
						if status == QtMultimedia.QCamera.ActiveStatus:
							tabs.setCurrentWidget(self.mainWindow.cameraTab)

					self.camera.statusChanged.connect(statusChanged)
				self.camera.start()
			except Exception as exc:
				print(exc)
				self._showError('Failed to initialize camera. :(')
				tabs.setCurrentWidget(self.mainWindow.badgePreviewTab)
				return

		elif tabs.currentWidget() == self.mainWindow.cameraTab:
			def imageSaved(id, filename):
				self.useImage(filename)

			self.imageCapture = QtMultimedia.QCameraImageCapture(self.camera)
			self.imageCapture.imageSaved.connect(imageSaved)
			tmpFile = os.path.abspath(os.path.join('archive', '_capture.jpg'))
			self.imageCapture.capture(tmpFile)
			self.camera.stop()

	def browseForImage(self):
		result = QtWidgets.QFileDialog.getOpenFileName(self.mainWindow, 'Open file', '.', 'JPEG images (*.jpg);;All files (*)')
		if result[0] != '':
			self.useImage(result[0])

	def useImage(self, filename):
		self.lastImage = filename
		with open(filename, 'rb') as captureFile:
			self.mainWindow.preview.setImage('photo', captureFile.read(), 'jpeg')

		self.mainWindow.previewTabs.setCurrentWidget(self.mainWindow.badgePreviewTab)

	def attemptPrint(self):
		self.mainWindow.statusBar().showMessage('Archiving images...')
		name = self.makeFileFriendlyName()
		filename = os.path.join('archive', 'badges', '%s.svg' % name)
		self.saveACopy(filename)
		if os.path.isfile(os.path.join('archive', '_capture.jpg')):
			shutil.move(
				os.path.join('archive', '_capture.jpg'),
				os.path.join('archive', 'captures', '%s.jpg' % name)
			)

		if self.mainWindow.actionUseInkscape.isChecked():
			printProcess = subprocess.Popen(['inkscape','--verb','FilePrint',filename])
		else:
			self.printer = QtPrintSupport.QPrinter()
			dialog = QtPrintSupport.QPrintDialog(self.printer, self.mainWindow)
			if dialog.exec_() != QtWidgets.QDialog.Accepted:
				return

			def printingDone(ok):
				if ok:
					self.mainWindow.statusBar().showMessage('Printing done!', 5000)
				else:
					self.mainWindow.statusBar().showMessage('Printing failed :(')
				self.mainWindow.statusBar().showMessage('Printing...')
				self.mainWindow.preview.page().print(self.printer, printingDone)
		
		self.addLogEntry()

	def _entryLoggingComplete(self, ok, error):
		if ok:
			self.mainWindow.statusBar().showMessage('Logging done!', 5000)
		else:
			self.mainWindow.statusBar().showMessage('Web logging failed. %s' % error)

	def _entryLogFallbackError(self, error):
		raise error

	def addLogEntry(self):
		if self.entryLogger is None:
			print('Logging disabled')
			return

		self.mainWindow.statusBar().showMessage('Logging entry...')
		data = {}
		for w in self.templateElements:
			fieldID = self.mainWindow.formLayout.labelForField(w).text()
			fieldValue = w.text()
			data[fieldID] = fieldValue

		self.entryLogger.logEntry(data)

	def makeFileFriendlyName(self, replaceBlankWithAnonymous=True):
		names = []
		for w in self.nameInputs:
			if w.text() != '':
				names.append(w.text().replace(' ', '_'))

		name = '_'.join(names)
		if replaceBlankWithAnonymous and name == '':
			name = 'Anonymous_McNameface'

		return name

	def exit(self):
		# @TODO: maybe check if changes made since last print or save
		self.quit()

	def reloadTemplates(self):
		combobox = self.mainWindow.templateSelector
		combobox.clear()
		templates = []
		try:
			for filename in os.listdir('templates'):
				if filename[-4:].lower() == '.svg':
					templates.append(filename)
			templates.sort()
			combobox.addItems(templates)

			combobox.setCurrentIndex(combobox.count()-1)
			self.loadTemplate(combobox.currentText())
		except:
			self._showError('Failed to load templates from %s' % os.path.abspath('templates'))

		combobox.insertSeparator(len(templates))
		combobox.addItem('✎ Choose custom...', CHOOSE_CUSTOM)
		combobox.addItem('⟳ Reload templates', RELOAD)

	def loadTemplate(self, filename):
		self.mainWindow.preview.hide()

		filename = os.path.join('templates', filename)
		self.templateFilename = filename

		self.mainWindow.preview.setUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(filename)))

	# this runs whenever the SVG preview is loaded (including blank loads)
	def _templateLoadComplete(self, content):
		def addElements(elements):
			# Remove boring, old, template-specific widgets from the form
			rememberedValues = {}
			for rowID in range(self.mainWindow.formLayout.rowCount()-1, 3, -1):
				layoutItem = self.mainWindow.formLayout.itemAt(
					rowID,
					QtWidgets.QFormLayout.FieldRole
				)
				if layoutItem is not None:
					widget = layoutItem.widget()
					if widget in self.templateElements:
						label = self.mainWindow.formLayout.labelForField(widget)
						rememberedValues[label.text().replace('&', '')] = widget.text()
						label.deleteLater()
						widget.deleteLater()
		
			self.nameInputs = []

			# add new and exciting template-specific widgets to the form
			self.templateElements = []

			# keep track of this to update tab order
			lastElement = self.mainWindow.testQR
			for element in elements:
				isFirstName = element['id'].lower() == 'first name'
				isLastName = element['id'].lower() == 'last name'

				widget = QtWidgets.QLineEdit(self.mainWindow)
				if element['id'] in rememberedValues:
					widget.setText(rememberedValues[element['id']])
				else:
					widget.setText(element['textContent'])

				widget.textChanged.connect(partial(self.textFieldUpdated, isFirstName or isLastName))

				self.templateElements.append(widget)
				self.mainWindow.formLayout.addRow(element['id'], widget)

				if isFirstName:
					self.nameInputs.insert(0, widget)
				elif isLastName:
					self.nameInputs.append(widget)

				QtWidgets.QWidget.setTabOrder(lastElement, widget)
				lastElement = widget

			QtWidgets.QWidget.setTabOrder(lastElement, self.mainWindow.captureButton)

		self.mainWindow.preview.extractTags('text', ['textContent'], addElements)

		self._updatePreview(False)
		if self.lastImage is not None and os.path.isfile(self.lastImage):
			self.useImage(self.lastImage)
		self.mainWindow.preview.show()

	def textFieldUpdated(self, value):
		self._updatePreview(True)

	def _updatePreview(self, updateQRInput):
		self.qrTimer.stop()
		for widget in self.templateElements:
			id = self.mainWindow.formLayout.labelForField(widget).text().replace('&', '')
			self.mainWindow.preview.setText(id, widget.text())

		if updateQRInput != False:
			name = QtCore.QUrl.toPercentEncoding(self.makeFileFriendlyName(False)).data().decode('utf-8')
			if name == '':
				self.mainWindow.qrInput.setText('http://makeict.org/')
			else:
				self.mainWindow.qrInput.setText('http://makeict.org/wiki/User:%s' % name)

		self.qrTimer.start()

	def updateQRDisplay(self):
		buffer = io.BytesIO()
		qr = pyqrcode.create(self.mainWindow.qrInput.text())
		qr.png(buffer, scale=10, quiet_zone=0)
		self.mainWindow.preview.setImage('qr', buffer.getvalue(), 'png')
	
	def refreshCameras(self):
		self.mainWindow.menuCameras.clear()

		oldCameraInfo = self.cameraInfo
		self.cameraInfo = None
		availableCameras = QtMultimedia.QCameraInfo.availableCameras()
		if len(availableCameras) == 0:
			self._showError('No cameras available. Are you sure it\'s plugged in?')
		else:
			cameraActionGroup = QtWidgets.QActionGroup(self)

			for cameraInfo in availableCameras:
				action = QtWidgets.QAction(
					'%s (%s)' % (cameraInfo.description(), cameraInfo.deviceName()),
					self.mainWindow.menuCameras
				)
				action.setCheckable(True)
				action.triggered.connect(partial(self.setCamera, cameraInfo))

				if self.cameraInfo is None:
					if oldCameraInfo is None or oldCameraInfo.deviceName() == cameraInfo.deviceName():
						action.setChecked(True)
						self.cameraInfo = cameraInfo

				self.mainWindow.menuCameras.addAction(action)
				cameraActionGroup.addAction(action)

		self.mainWindow.menuCameras.addSeparator()
		actionRefreshCameras = QtWidgets.QAction('⟳ &Refresh', self.mainWindow.menuCameras)
		self.mainWindow.menuCameras.addAction(actionRefreshCameras)
		actionRefreshCameras.triggered.connect(self.refreshCameras)

	def cancelCapture(self):
		self.camera.stop()
		self.mainWindow.previewTabs.setCurrentWidget(self.mainWindow.badgePreviewTab)
	
	def setCamera(self, cameraInfo):
		takingPic = self.mainWindow.previewTabs.currentWidget() != self.mainWindow.badgePreviewTab

		if takingPic:
			self.cancelCapture()

		if self.camera is not None:
			self.cameraCollection.append(self.camera)
			self.camera.setViewfinder(None)
			self.camera = None
			self.mainWindow.cameraViewFinder.setMediaObject(None)

		self.cameraInfo = cameraInfo

		if takingPic:
			self.captureToggle()


	def _showError(self, msg):
		QtWidgets.QMessageBox.warning(self.mainWindow, 'MakeICT Badge Printer', msg)

def handle_exception(parentWindow, excType, exc, tb):
	if issubclass(excType, KeyboardInterrupt):
		sys.__excepthook__(excType, exc, tb)
		return

	stack = traceback.format_tb(tb)
	print('Exception: %s' % exc)
	print(''.join(stack))

	if isinstance(exc, NotImplementedError):
		if str(exc).strip() == '':
			name = 'This feature'
		else:
			name = 'The "%s" feature' % exc

		QtWidgets.QMessageBox.warning(
			parentWindow,
			'Feature not ready',
			name + ' isn\'t ready yet.\n\nWanna help? Visit http://github.com/makeict/badge-printer' 
		)
	else:		
		dialog = QtWidgets.QMessageBox(parentWindow)
		dialog.setWindowTitle('Error :(')
		dialog.setText('Well this is embarrasing... Something went wrong and I didn\'t know how to handle it.\n\nPlease help us fix this bug!')
		dialog.setDetailedText(
			'The details below can help troubleshoot the issue. Please copy-and-paste this in any report.\n\n' +
			'Developer info at http://github.com/makeict/badge-printer\n\n' + 
			'Exception: ' + str(exc) + '\n'
			'%s' % ''.join(stack)
		)
		dialog.setModal(True)
		dialog.exec_()

if __name__ == '__main__':
	os.makedirs(os.path.join('archive', 'captures'), exist_ok=True)
	os.makedirs(os.path.join('archive', 'badges'), exist_ok=True)

	app = BadgePrinterApp(sys.argv)
	sys.excepthook = partial(handle_exception, app.mainWindow)
	app.doItNowDoItGood()

	try:
		# clean up
		if os.path.isfile(os.path.join('archive', '_capture.jpg')):
			os.remove(os.path.join('archive', '_capture.jpg'))
	except:
		pass
