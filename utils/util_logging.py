import logging

class Logger:

	def __init__(self, name, level=logging.INFO):
		logging.basicConfig(level=logging.INFO)
		self.logger = logging.getLogger(name)

	def info(self, text):
		self.logger.info(text)
