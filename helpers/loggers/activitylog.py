import logging, logging.handlers
import configparser

sockLogger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('amclient.ini')

if not sockLogger.hasHandlers():
    
    sockLogger.setLevel(logging.INFO)

    #: specify the ip of the server to send the user's activity log
    receiving_server_ip = config['DEFAULT']['server_ip'] # e.g '192.168.170.191'

    socketHandler = logging.handlers.SocketHandler(receiving_server_ip, logging.handlers.DEFAULT_TCP_LOGGING_PORT)

    #: NOTE: Didn't use formatter as that will not be recognized by the socket

    sockLogger.addHandler(socketHandler)

    #keyMouseLogger = logging.getLogger('activityLog')
    #clipboardLogger = logging.getLogger('clipboardLog')
    #activityLogger = logging.getLogger('activityLog')

