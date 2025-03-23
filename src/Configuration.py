
import configparser

'''
##  write
config = configparser.ConfigParser()
config['DEFAULT'] = {'ServerAliveInterval': '45',
                     'Compression': 'yes',
                     'CompressionLevel': '9'}
config['forge.example'] = {}
config['forge.example']['User'] = 'hg'
config['topsecret.server.example'] = {}
topsecret = config['topsecret.server.example']
topsecret['Port'] = '50022'     # mutates the parser
topsecret['ForwardX11'] = 'no'  # same here
config['DEFAULT']['ForwardX11'] = 'yes'
with open('test.ini', 'w') as configfile:
  config.write(configfile)

## read
config = configparser.ConfigParser()
config.sections()
config.read('test.ini')
print(config.sections())
'forge.example' in config
'python.org' in config
config['forge.example']['User']
config['DEFAULT']['Compression']
topsecret = config['topsecret.server.example']
topsecret['ForwardX11']
topsecret['Port']
for key in config['forge.example']:
    print(key)
config['forge.example']['ForwardX11']'
'''

defaultfile = "./MyUniverse.ini"

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigBase:
    config = None
    def __init__(self):
        self.read()
        # self.printData()
    def read(self, filename=defaultfile):
        self.config = configparser.ConfigParser()
        self.config.sections()
        self.config.read(filename)
        # print(self.config.sections())
    def printData(self):
        for key in self.config['Data']:
            print(key)
    def getValue(self, set, name):
        return self.config[set][name]
    def write(self, filename=defaultfile):
        config = configparser.ConfigParser()
        config['DEFAULT'] = {'ServerAliveInterval': '45',
                            'Compression': 'yes',
                            'CompressionLevel': '9'}
        config['forge.example'] = {}
        config['forge.example']['User'] = 'hg'
        config['topsecret.server.example'] = {}
        topsecret = config['topsecret.server.example']
        topsecret['Port'] = '50022'     # mutates the parser
        topsecret['ForwardX11'] = 'no'  # same here
        config['DEFAULT']['ForwardX11'] = 'yes'
        with open('test.ini', 'w') as configfile:
            config.write(configfile)

class Configuration(ConfigBase, metaclass=Singleton):
    pass