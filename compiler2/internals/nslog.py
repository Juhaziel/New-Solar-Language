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
            
        def setLevel(self, loglevel: LogLevel):
            if not isinstance(loglevel, LogLevel):
                self.warn("tried changing logger level to invalid value.")
            self._level = loglevel
        
        def log(self, message: str, loglevel: LogLevel=LogLevel.WARN):
            if loglevel.value < self._level.value: return
            print(f"[{loglevel.name}] {message}")
            
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
    
    