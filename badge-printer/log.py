#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5 import QtCore
from functools import partial
import urllib3

import time
from datetime import datetime

import json

class WebFormLogger(QtCore.QObject):
	logComplete = QtCore.pyqtSignal(object, object)
	fallbackError = QtCore.pyqtSignal(object)

	def __init__(self, url, fallbackFile=None, parent=None):
		super().__init__(parent)
		self.threads = []
		self.url = url
		self.fallbackFile = fallbackFile

	def threadFinished(self, worker):
		self.threads.remove(worker)
		if worker.submissionState == 'ok':
			self.logComplete.emit(True, None)
		else:
			self.logComplete.emit(False, worker.error)
			
			if worker.fallbackError is not None:
				self.fallbackError.emit(worker.fallbackError)

	def logEntry(self, data):
		currentTime = int(time.time())
		if 'timestamp' not in data:
			data['timestamp'] = currentTime
			data['hr-timestamp'] = datetime.fromtimestamp(currentTime).strftime('%Y-%m-%d %H:%M:%S')

		thread = WebWorkerThread(self.url, data, self.fallbackFile)
		self.threads.append(thread)
		thread.finished.connect(partial(self.threadFinished, thread))
		thread.start()

class WebWorkerThread(QtCore.QThread):
	def __init__(self, url, data, fallbackFile=None):
		super().__init__()
		self.url = url
		self.data = data
		self.fallbackFile = fallbackFile
		self.submissionState = None
		self.error = None
		self.fallbackError = None

	def run(self):
		self.submissionState = 'sending'
		try:
			http = urllib3.PoolManager()
			request = http.request('GET', self.url, fields=self.data, timeout=1.0, retries=0)

			response = request.data.decode('utf-8')
			if response == 'ok':
				self.submissionState = 'ok'
			else:
				print(response)
				raise Exception('Unknown submission error')

		except Exception as exc:
			self.submissionState = 'fail'
			self.error = 'Exception: %s' % exc

			try:
				with open(self.fallbackFile, 'a') as logFile:
					logFile.write(json.dumps(self.data, sort_keys=True) + '\n')
			except Exception as exc:
				print('Failed to write to fallback log!')
				self.fallbackError = exc
