#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, traceback
#import cups

from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport, QtSvg, uic

#from V4L2

CHOOSE_CUSTOM = object()
RELOAD = object()

class BadgePrinterApp(QtWidgets.QApplication):
	def __init__(self, args):
		super().__init__(args)
		self.basePath = os.path.dirname(os.path.realpath(__file__))
		self.templateFilename = None

		self.mainWindow = uic.loadUi(self._path('MainWindow.ui'))

		self.mainWindow.actionImport.triggered.connect(self.attemptImport)
		self.mainWindow.actionLoadTemplate.triggered.connect(self.browseForTemplate)
		self.mainWindow.actionSaveACopy.triggered.connect(self.saveACopy)

		self.mainWindow.actionCapture.triggered.connect(self.capture)
		self.mainWindow.actionPrint.triggered.connect(self.attemptPrint)

		self.mainWindow.actionExit.triggered.connect(self.exit)

		self.reloadTemplates()

		self.mainWindow.templateSelector.currentIndexChanged.connect(self._templateSelected)

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

	def capture(self):
		try:
			raise NotImplementedError()
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def attemptPrint(self):
		try:
			printer = QtPrintSupport.QPrinter()
			dialog = QtPrintSupport.QPrintDialog(printer, self.mainWindow)
			if dialog.exec_() != QtWidgets.QDialog.Accepted:
				return
			
			painter = QtGui.QPainter(printer)
			#painter.begin(printer)
			with open(self.templateFilename) as svgFile:
				svgRenderer = QtSvg.QSvgRenderer(svgFile.read())
			
			svgRenderer.render(painter)
			painter.end()

			self.mainWindow.setStyleSheet(styleSheet)
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
			self.mainWindow.previewBadge.setPixmap(QtGui.QPixmap(filename))
			self._updatePreview()
		except Exception as exc:
			unhandledError(exc, self.mainWindow)

	def _updatePreview(self):
		pass

def unhandledError(exc, parent=None):
	stack = traceback.format_exc()

	dialog = QtWidgets.QMessageBox(parent)
	dialog.setWindowTitle('Error :(')
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
		app = BadgePrinterApp(sys.argv)
		app.doItNowDoItGood()
	except Exception as exc:
		unhandledError(exc)
