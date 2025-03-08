import configparser

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
config['forge.example']['ForwardX11']