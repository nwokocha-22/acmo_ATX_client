#! /usr/bin/python

__version__="0.0.1"
__author__="Nwokocha Maruche"

import sys
import io
import time
import socket
from typing import Callable
from threading import Thread
from datetime import datetime
from helpers.video import SendVideo as Video
from helpers.email import EmailClient as Email
from helpers.keymouse import KeyMouseMonitor as KeyMouse
from helpers.clipboard import ClipboardMonitor as Clipboard
from helpers.loggers.activitylog import sockLogger
from helpers.timer import timer, Timex
import winreg


class ActivityMonitor():
    """Monitors user's activities.

    Parameters
    ----------
    video: `Video`
        Instance of the video class that captures and send the screen video frame
    email: 'EmailClient`
        Instance of the email client to send emails
    config: `configParser.ConfigParser()`
        Config parser object with all configurations
    """
    def __init__(self, video, email, config):

        self.video = video
        self.email = email
        self.config = config
        self.tx = Timex()
        
        #MOUSE & KEYSTROKE
        self.key_stroke_count:int = 0
        self.mouse_move_count:int = 0
        self.status = str()

        #TIME
        self._time_in:datetime = None
        self._time_last_checked:datetime = None
        self._time_out:datetime = None
        #CONTENT
        self._copied_content_size:int = None
        self._copied_content:str = str()
        self._copied_content_size_24hr:int = None
        self._copied_content_24hr:str = str()
        
        self.start()

    def start(self):
        """Loads the configuration parameters on script start. """

        params = self.tx.get_config_params()
        self._time_in=params['time_in']
        self._copied_content_size=params['content_size_1hr']
        self._copied_content_size_24hr=params['content_size_24hr']
        self._time_last_checked=params['last_checked']
        self._LOG_INTERVAL=int(self.config['POLICY']['log_interval'])
        self._CHECK_STATUS_INTERVAL=int(self.config['POLICY']['check_status_interval'])
        self._copied_content_limit=self.config['POLICY']['copied_content_limit']
        self._copied_content_limit_24hrs=self.config['POLICY']['copied_content_limit_24hrs']
    
        self.start_lone_threads()

    def start_lone_threads(self):
        """Starts the standalone threads. """
        self.clipboard = Clipboard(self._on_text, self._on_image, self._on_file)
        # self.clipboard.reset() #Resets clipboard in development
        clipboard_thread = Thread(target=self.clipboard.run_clipboard_listener)
        clipboard_thread.start()
        video_thread = Thread(target=self.video.connect_to_server)
        video_thread.start()

        #: Log user mouse and keyboard activities every 10 minutes
        timer_thread = Thread(target=self._activityTimer, 
                              args=(self.logUserActivities, self._LOG_INTERVAL, 'min',))

        timer_thread.start()

        #: check the policy status every 1 hour
        timer_hr_thread = Thread(
            target=self._policyTimer, 
            args=(self._checkPolicyStatus, 1, 'hour'))

        timer_hr_thread.start()
        clipboard_thread.join()
        video_thread.join() 
        timer_thread.join()
        timer_hr_thread.join()

    def _on_text(self, text:str):
        """Triggered when text is copied to clipboard. 
        
        Invokes copy policy to check if policy has been violated.
        """
        text_size = sys.getsizeof(text)
        self.check_policy_violation(text_size, text, "text")

    def _on_file(self, files:io.FileIO):
        """Triggered when files are copied to clipboard. """
        file_size, zipped_files = zip(files)
        self.check_policy_violation(file_size, zipped_files, "file")
    
    def _on_image(self, image):
        """Triggered when image(s) are copied to clipboar. """
        image_size = sys.getsizeof(image)
        self.check_policy_violation(image_size, image, "image")

    def check_policy_violation(self, file_size, file, file_type):
        """Validates Policy.

        Checks if the size of the copied file is more than five hundred Kilobytes. 
        if yes, invokes a disciplinary action, fires an email to the admin
        Else, increment the _copied_content_size.
    
        parameter
        ---------
            file_size: `int`
                size of the copied file
            file:  Any[`str`, `bytes`]
                content of the copied file (can be either string or bytes)
            file_type: `str`
                type of the copied data - can be one of ["text", "file", "image"]
        """
        message = f"clipboard >>> copied file size: {file_size} KB, file type: {file_type}"
        sockLogger.info(message)

        if file_type == "text":

            # add the copied file to previous copied content
            file_size += self._copied_content_size
            file += self._copied_content

            # check if the copied file size is greater than content limit (500KB)
            limit_exceeded_1hr = file_size >= self._copied_content_limit
            limit_exceeded_24hr = file_size + self._copied_content_size_24hr \
                                  >= self._copied_content_limit_24hr
           
            # if this is the first time user is coping content 
            # and the content size exceeds the limit of 500KB
            # invoke the disciplinary action

            if not self._time_last_checked:
                if limit_exceeded_1hr:
                    self.invokeDisciplinaryAction(file_size, file, file_type)
                else:
                    self._time_last_checked = time.time()
                    self.update_copied_content(file, file_size)
            else:

                # check time passed (interval) after the previous copy was made
                interval = self.tx.interval(
                            time.time(), 
                            self.tx.get_params['last_checked'])

                # if the time passed is less than 1 hr
                # and the copied file size exceeds the 1hour limit,
                # invoke the disciplinary action

                if interval <= 1 and limit_exceeded_1hr:
                    self.invokeDisciplinaryAction(file_size, file, file_type)
                
                #: Else if the time passed since the previous copy is less than 24hrs
                #: and the copied file size exceeds the 24hrs limit (1500kb)
                #: invoke disciplinary action

                elif (interval > 1 and interval < 24) and limit_exceeded_24hr:
                    self.invokeDisciplinaryAction(file_size, file, file_type)
                else:
                    self.update_copied_content(content=file, size=file_size, level=0)

    def clear_copied_content(self, level:int=0):
        """Clears the copied content.

        Parameters
        ----------
        level : int
            Level at which the data needs to be cleared. One of [1, 0, -1]
                :0: clears 1 hr copied content -> at the end of every 1 hour
                :1: clear 24hr copied content
                :-1: clear all-> when there is a policy violation
        """
        if level == 0:
            self._copied_content_size += 'No longer valid'
            self._copied_content += "\n" + 'No longer valid'
        elif level == 1:
            self._copied_content_size_24hr += self._copied_content_size
            self._copied_content_24hr += "\n"+self._copied_content
            self._copied_content_size = 0
            self._copied_content = ''
        else:
            self._copied_content_size_24hr = 0
            self._copied_content_24hr = ''
            self._copied_content_size = 0
            self._copied_content = ''
    
    def update_copied_content(self, content='', size=0, level=0):
        """Updates Copied content.

        increment the copied content [self._copied_content]
        and content size [self._copied_content_size] each time 
        text file is copied
        """
        if level == 0:
            # everytime content is copied
            self._copied_content_size += size
            self._copied_content += "\n" + content

            self.tx.update_params(
            content_size_1hr=self._copied_content_size,
            content_size_24hr=self._copied_content_size_24hr,
            last_checked=time.time()
            )

        elif level == 1:
            #: after one hour
            self._copied_content_size_24hr += self._copied_content_size
            self._copied_content_24hr += "\n"+self._copied_content
            self._copied_content_size = 0
            self._copied_content = ''

            self.tx.update_params(
            content_size_1hr=self._copied_content_size,
            content_size_24hr=self._copied_content_size_24hr,
            last_checked=time.time()
            )

        else:
            # when policy is violated or at the end of 24hours
            self._copied_content_size_24hr = 0
            self._copied_content_24hr = ''
            self._copied_content_size = 0
            self._copied_content = ''

            self.tx.update_params(
            content_size_1hr=0,
            content_size_24hr=0,
            last_checked=None)

    def checkCopiedContent(self):
        """Checks the size of the copied content every hour.

        if greater than 500, calls the send method of the email client and sends
        all content copied up until that time.
        """
        if self._copied_content_size >= 500:
            self.invokeDisciplinaryAction(
                self._copied_content_size, 
                self._copied_content, "text")
        else:
            self.update_copied_content(clear=True)
        
    def logUserActivities(self):
        """Determines if user is active or idle.

        gets the keystroke and mouse move from the 
        getCount method in the KeyMouse module.
        logs the keystroke and mouseMove activities every 10 minutes
        """

        key_mouse = KeyMouse()
        keyStroke, mouseMove = key_mouse.getCount()
        k = keyStroke - self.key_stroke_count
        m = mouseMove - self.mouse_move_count

        if not k and not m:
            self.status = "idle"
        else:
            self.status = "active"

        self.key_stroke_count = keyStroke   
        self.mouse_move_count = mouseMove
    
        message = f"Keyboard >>> keystroke:{k}, mouseMoves:{m}, status:{self.status}"
        sockLogger.info(message)

        
    def invokeDisciplinaryAction(self, file_size, file, file_type):
        """Invokes displinary Action.

        This is called when the copy policy is violiated. 
        It sets the users hasDefaulted status to True, set the time of violation, 
        and triggers the function to disable clipboard for 24hours
        """
        client_ip = socket.gethostbyname(socket.gethostname())
        if file_type == "text":
            self.email.send_email(client_ip, file_size, file)
        else:
            #: send files as attachment if not text (i.e for bytes and images)
            self.email.send_email(client_ip, file_size, "see attached zipped file(s)", file)
        if not self.clipboard.has_defaulted():
            self.clipboard.updatePolicy(True, time.time())
        #: clear the copied file content and copied file size. 
        # level -1 means every thing will be cleared
        self.update_copied_content(level=-1)

    def _checkPolicyStatus(self):
        """Checks the policy status every one hour to see if the 
        penalty time has elapsed.

        At the end of the one hour interval, clears the copied_content variable and
        increment the _copied_content_24hr variable
        """
        has_defaulted = self.clipboard.has_defaulted()
        # if user has not defaulted, clear copied content within 1 hr
        # increment the copied content withing 24hr
        if not has_defaulted:
            self.update_copied_content(level=1)
            
    @staticmethod
    @timer
    def _setTimer(callback:Callable, interval:int, mode:str):
        # WARNING: removing the static method will cause _Time class to fail
        """Sets the alarm interval.
        
        Note
        -----
        the callback function is triggered on the expiration of the interval 
        
        parameter
        ----------
        callback: `Callable`
            a function that is called when the interval alapses
        interval: `int`
            The duration for the callback is triggered
        mode: `str`
            The time frame i.e sec, min, or hour
        """
        pass

    @staticmethod
    @timer
    def _activityTimer(callback:Callable, interval:int, mode:str):
        """ Activity timer. triggered every 10 mins """
        pass

    @staticmethod
    @timer
    def _policyTimer(callback:Callable, interval:int, mode:str):
        """ Policy timer. 
        
        Triggered every one hour to check the policy status 
        """
        pass

    def disable_screenshot(self):
        """Disables the window print screen keys. """
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Control Panel\\Keyboard')
        winreg.SetValueEx(winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            'Control Panel\\Keyboard', 
            0, winreg.KEY_ALL_ACCESS), 
            'Scancode Map', 0, 
            winreg.REG_BINARY, '\x00\x00\x00\x00\x00\x00\x00\x00\x03\
            \x00\x00\x00\x00\x00\x5b\xe0\x00\x00\x5c\xe0\x00\x00\x00\x00')
        
if __name__=="__main__":
    
    def main():
        from helpers.loggers.activitylog import sockLogger
        import configparser
        
        config = configparser.ConfigParser()
        config.read('amclient.ini')

        IP = socket.gethostbyname(socket.gethostname())
        PORT = int(config["DEFAULT"]['port'])
        SENDER = config["EMAIL"]["email_host_user"]
        PASSWORD= config["EMAIL"]["email_host_password"]
        RECEIVER = config["EMAIL"]["admin_email"]

        video = Video(IP, PORT, config)
        email = Email(PASSWORD, SENDER, RECEIVER)
        ActivityMonitor(video, email, config)

        sockLogger.info(f"{IP} started ")
 
    process = Thread(target=main)
    process.start()
    process.join()

#: CONVERT SCRIPT TO EXECUTABLE  
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
    
