#! usr/bin/python 

__version__="0.0.1"
__Author__="Maru Koch"


"""
====================================
||||||||||| = SERVICE = ||||||||||||
====================================

- The service module enables the control of the client scripts through
  Windows Service Interface via Task Manager.
- The service is converted to an executable file using pyinstaller and 
  installed in the client's server.
- Service is started on logon event (When user is session starts)
- And is stopped on logoff event (When user session is terminated)

- WHY DID YOU DECORATE THIS DOCSTRING? BECAUSE I WANT TO! I'M ZOSS!!!
=====================================
=====================================
"""

import sys
sys.path.append('.')
import helpers
from helpers.video import SendVideo as Video
from helpers.email import EmailClient as Email
from helpers.loggers.activitylog import sockLogger
from core import ActivityMonitor
import multiprocessing
import win32serviceutil
import win32serviceutil
import win32event
import servicemanager
import socket
import servicemanager
import configparser

def main_app():
    config = configparser.ConfigParser()
    config.read('amclient.ini')

    IP = socket.gethostbyname(socket.gethostname())
    PORT = int(config["DEFAULT"]['port'])
    SERVER_IP  = int(config["DEFAULT"]['server_ip'])
    SENDER = config["EMAIL"]["email_host_user"]
    PASSWORD= config["EMAIL"]["email_host_password"]
    RECEIVER = config["EMAIL"]["admin_email"]

    video = Video(IP, PORT, config)
    email = Email(PASSWORD, SENDER, RECEIVER)

    ActivityMonitor(video, email, config)
    sockLogger.info(f"Client >>> {IP} started ...")


class ActivityMonitorClientService(win32serviceutil.ServiceFramework):
    """
    This script is the window service that starts and stops the
    core_app.exe client file.
    """

    _svc_name_ = "AMClientService"
    _svc_display_name_ = "AM Client Service"
    _svc_description_ = "Starts, stops, udpate, and removes the activity \
        monitor client service."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.stop()
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        self.start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

    def start(self):
        self.process = multiprocessing.Process(target=main_app)
        self.process.start()
        self.process.join()

    def stop(self):
        self.process.terminate()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ActivityMonitorClientService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ActivityMonitorClientService)

# COMMAND TO CONVERT TO EXECUTABLE
"""
pyinstaller.exe 
--runtime-tmpdir=. 
--hidden-import win32timezone 
--collect-submodules helpers 
--hidden-import logging.handlers 
--hidden-import cv2 
--name main_client 
--onefile service.py
"""

