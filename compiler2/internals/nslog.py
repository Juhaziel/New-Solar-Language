from enum import IntEnum
# Helper for logging info, warnings, errors, etc.

class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    FATAL = 4

class LoggerFactory:
    __logger = None
    
    class Logger:
        def __init__(self):
            self._level = LogLevel.WARN
            self._padlevel = 0 # For debug only
            
        def setLevel(self, loglevel: LogLevel):
            if not isinstance(loglevel, LogLevel):
                self.warn("tried changing logger level to invalid value.")
            self._level = loglevel
        
        def log(self, message: str, loglevel: LogLevel=LogLevel.WARN):
            if loglevel.value < self._level.value: return
            pad = ""
            if loglevel == LogLevel.DEBUG:
                pad = "  " * self._padlevel
            print(f"{pad}[{loglevel.name}] {message}")
            
        def increasepad(self):
            self._padlevel += 1
        
        def decreasepad(self):
            if self._padlevel == 0: return
            self._padlevel -= 1
        
        def resetpad(self):
            self._padlevel = 0
            
        def debug(self, message: str): self.log(message, LogLevel.DEBUG)
        def info(self, message: str): self.log(message, LogLevel.INFO)
        def warn(self, message: str): self.log(message, LogLevel.WARN)
        def error(self, message: str): self.log(message, LogLevel.ERROR)
        def fatal(self, message: str): self.log(message, LogLevel.FATAL)
            
    
    @classmethod
    def getLogger(cls):
        if not cls.__logger:
            cls.__logger = LoggerFactory.Logger()
        return cls.__logger
    
    