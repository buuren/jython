from org.apache.log4j import Logger

class log4j():
	def __init__(self, className):
		self.log = Logger.getLogger(className)
		
	def infoMessage(self, methodName, message, noSkip = True):
		if noSkip:
			formattedMessage = '[%s]: %s' % (methodName, message)
			self.log.info(formattedMessage)
		
	def debugMessage(self, methodName, message, noSkip = True):
		if noSkip:
			formattedMessage = '[%s]: %s' % (methodName, message)
			self.log.debug(formattedMessage)
	
	def warnMessage(self, methodName, message, noSkip = True):
		if noSkip:
			formattedMessage = '[%s]: %s' % (methodName, message)
			self.log.warn(formattedMessage)
