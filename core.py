#! /usr/bin/python

__version__="0.0.1"
__author__="Nwokocha Maruche"

import sys
import io
import time
import socket
import tkinter
import win32api
import win32con
import pywintypes
import pyautogui
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

        self.video: Video = video
        self.email: Email = email
        self.config = config
        self.tx = Timex()
        
        #MOUSE & KEYSTROKE
        self.key_stroke_count: int = 0
        self.mouse_move_count: int = 0
        self.status = str()

        #TIME
        self._time_in: datetime = None
        self._time_last_checked: datetime = None
        self._time_out: datetime = None

        #CONTENT
        self._copied_content_size: int = 0
        self._copied_content: str = str()
        self._copied_content_size_24hr: int = 0
        self._copied_content_24hr: str = str()
        
        self.start()

    def start(self):
        """Loads the configuration parameters on script start."""

        params = self.tx.get_config_params()
        self._time_in = params['time_in']
        self._copied_content_size = params['content_size_1hr']
        self._copied_content_size_24hr = params['content_size_24hr']
        self._time_last_checked = params['last_checked']
        self._LOG_INTERVAL = int(self.config['POLICY']['log_interval'])
        self._CHECK_STATUS_INTERVAL = \
            int(self.config['POLICY']['check_status_interval'])
        self._copied_content_limit = \
            int(self.config['POLICY']['copied_content_limit'])
        self._copied_content_limit_24hrs = \
            int(self.config['POLICY']['copied_content_limit_24hrs'])
    
        self.start_lone_threads()

    def start_lone_threads(self):
        """Starts the standalone threads."""
        self.clipboard = Clipboard(
            self._on_text, self._on_image, self._on_file)
        # Resets clipboard in development
        # self.clipboard.reset()
        clipboard_thread = Thread(
            target=self.clipboard.run_clipboard_listener)
        clipboard_thread.start()
        video_thread = Thread(target=self.video.connect_to_server)
        video_thread.start()

        #: Logs user mouse and keyboard activities every 10 minutes
        timer_thread = Thread(target=self._activityTimer, 
            args=(self.logUserActivities, self._LOG_INTERVAL, 'min',))

        timer_thread.start()

        # checks the policy status every 1 hour
        timer_hr_thread = Thread(
            target=self._policyTimer, 
            args=(self._checkPolicyStatus, 1, 'hour'))

        timer_hr_thread.start()
        sockLogger.info(
            f"{socket.gethostbyname(socket.gethostname())} started"
        )
        clipboard_thread.join()
        video_thread.join() 
        timer_thread.join()
        timer_hr_thread.join()

    def _on_text(self, text: str):
        """Triggered when text is copied to clipboard.
        
        Invokes copy policy to check if policy has been violated.
        """
        text_size = sys.getsizeof(text)
        self.check_policy_violation(text_size, text, "text")

    def _on_file(self, files: io.FileIO):
        """Triggered when files are copied to clipboard."""
        file_size, zipped_files = zip(files)
        self.check_policy_violation(file_size, zipped_files, "file")
    
    def _on_image(self, image):
        """Triggered when image(s) are copied to clipboard."""
        image_size = sys.getsizeof(image)
        self.check_policy_violation(image_size, image, "image")

    def check_policy_violation(self, file_size, file, file_type):
        """Checks for policy violation.

        Checks if the size of the copied file is more than five hundred
        bytes. If so, invokes a disciplinary action, fires an email to
        the admin. Else, increment the _copied_content_size.
    
        Parameters
        ----------
        file_size: int
            The size of the copied file/content in bytes.
        file:  Optional[str, bytes]
            Content of the copied file (can be either string or bytes).
        file_type: str
            The type of the copied data - can be "text", "file", or
            "image".
        """
        message = (f"clipboard >>> copied file size: {file_size} Bytes, "
            f"file type: {file_type}")
        sockLogger.info(message)

        if file_type == "text":
            # add the copied file to previous copied content
            tfile_size = file_size + self._copied_content_size
            tfile = self._copied_content + "\n" + file

            # check if the copied file size is greater than content
            # limit (default=500 B)
            limit_exceeded_1hr = tfile_size >= self._copied_content_limit
            limit_exceeded_24hr = tfile_size + self._copied_content_size_24hr\
                                  >= self._copied_content_limit_24hrs
           
            # If this is the first time user is copying content
            # and the content size exceeds the limit of 500 B,
            # invoke the disciplinary action.
            if not self._time_last_checked:
                if limit_exceeded_1hr:
                    self.invokeDisciplinaryAction(tfile_size, tfile, file_type)
                else:
                    self._time_last_checked = time.time()
                    self.update_copied_content(file, file_size)
            else:
                # Check time passed (interval) after the previous copy
                # was made.
                interval = self.tx.interval(
                            time.time(), 
                            self.tx.get_params['last_checked'])

                # If the time passed is less than 1 hr
                # and the copied file size exceeds the 1hour limit,
                # invoke the disciplinary action.
                if interval <= 1 and limit_exceeded_1hr:
                    self.invokeDisciplinaryAction(tfile_size, tfile, file_type)
                
                # Else if the time passed since the previous copy is
                # less than 24hrs and the copied file size exceeds the
                # 24hrs limit (1500 B), invoke disciplinary action
                elif (interval > 1 and interval < 24) and limit_exceeded_24hr:
                    self.invokeDisciplinaryAction(tfile_size, tfile, file_type)
                else:
                    self.update_copied_content(
                        content=file, size=file_size, level=0
                    )

    # function is never used
    def clear_copied_content(self, level: int = 0):
        """Clears the copied content.

        Parameters
        ----------
        level: int
            Level at which the data needs to be cleared. One of
            [1, 0, -1]:
            - 0: clears 1 hr copied content -> at the end of every 1
            hour
            - 1: clears 24hr copied content
            - -1: clears all-> when there is a policy violation
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
        """Updates copied content.

        Increase/Update the copied content (`self._copied_content`) and
        content size (`self._copied_content_size`) each time text file
        is copied.
        """
        if level == 0:
            # everytime content is copied
            self._copied_content_size += size
            self._copied_content += "\n"+content

            self.tx.update_params(
                content_size_1hr=self._copied_content_size,
                content_size_24hr=self._copied_content_size_24hr,
                last_checked=time.time()
            )

        elif level == 1:
            # after one hour
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
                last_checked=None
            )

    # function is never used
    def checkCopiedContent(self):
        """Checks the size of the copied content every hour.

        If greater than 500, calls the send method of the email client
        and sends all content copied up until that time.
        """
        if self._copied_content_size >= 500:
            self.invokeDisciplinaryAction(
                self._copied_content_size, 
                self._copied_content, "text")
        else:
            # wrong use of this function
            self.update_copied_content(clear=True)
        
    def logUserActivities(self):
        """Determines if user is active or idle.

        Gets the keystroke and mouse move from the getCount method in
        the KeyMouse module. Logs the keystroke and mouseMove
        activities every 10 minutes (default).
        """
        key_mouse = KeyMouse()
        keyStroke, mouseMove = key_mouse.getCount()
        k = keyStroke - self.key_stroke_count
        m = mouseMove - self.mouse_move_count

        if k <= 0 and m <= 0:
            self.status = "idle"
        else:
            self.status = "active"

        self.key_stroke_count = keyStroke
        self.mouse_move_count = mouseMove
    
        message = (f"Keyboard >>> keystroke: {k}, mouseMoves: {m}, "
            f"status: {self.status}")
        sockLogger.info(message)

        
    def invokeDisciplinaryAction(self, file_size, file, file_type):
        """Invokes displinary Action.

        This is called when the copy policy is violated. It sets the
        user's `hasDefaulted` status to True, sets the time of
        violation, and triggers the function to disable clipboard for
        24hours.
        """
        sockLogger.info("Unauthorized action. Copy Policy violated")
        client_ip = socket.gethostbyname(socket.gethostname())
        if file_type == "text":
            self.email.send_email(client_ip, (file_size/1000), file)
        else:
            # send files as attachment if not text (i.e for bytes and
            # images)
            self.email.send_email(client_ip, (file_size/1000),
                "See attached zipped file(s)", file
            )
        if not self.clipboard.has_defaulted():
            self.clipboard.updatePolicy(True, time.time())
        # clear the copied file content and copied file size.
        # level -1 means every thing will be cleared.
        self.update_copied_content(level=-1)

    def _checkPolicyStatus(self):
        """Checks the policy status every one hour to see if the
        penalty time has elapsed.

        At the end of the one hour interval, clears the copied_content
        variable and increment the _copied_content_24hr variable.
        """
        has_defaulted = self.clipboard.has_defaulted()
        # If user has not defaulted, clear copied content within 1 hr
        # increase the copied content within 24hr
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
        """Activity timer; triggered every 10 mins.
        """
        pass

    @staticmethod
    @timer
    def _policyTimer(callback:Callable, interval:int, mode:str):
        """Policy timer. 
        
        Triggered every one hour to check the policy status.
        """
        pass

    # function is never used
    def disable_screenshot(self):
        """Disables the window print screen keys."""
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Control Panel\\Keyboard')
        winreg.SetValueEx(winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            'Control Panel\\Keyboard', 
            0, winreg.KEY_ALL_ACCESS), 
            'Scancode Map', 0, 
            winreg.REG_BINARY, '\x00\x00\x00\x00\x00\x00\x00\x00\x03\
            \x00\x00\x00\x00\x00\x5b\xe0\x00\x00\x5c\xe0\x00\x00\x00\x00')
        
if __name__=="__main__":
    def display_message(message: str):
        """
        Create "uninteractable" text label overlay.

        Parameters
        ----------
        message: str
            String to display as message over desktop.
        """
        message = message.replace("\n", " ")
        label = tkinter.Label(
            text=message, font=("Times New Roman", 10),
            fg="orange", bg="white"
        )
        label.master.overrideredirect(True)
        # Get width and height of screen.
        width, height = pyautogui.size()
        label.master.geometry(f"+{width-width//3}+{height-height//16}")
        label.master.lift()
        label.master.wm_attributes("-topmost", True)
        label.master.wm_attributes("-disabled", True)
        label.master.wm_attributes("-transparentcolor", "white")

        hWindow = pywintypes.HANDLE(int(label.master.frame(), 16))
        exStyle = win32con.WS_EX_COMPOSITED | win32con.WS_EX_LAYERED | \
            win32con.WS_EX_NOACTIVATE | win32con.WS_EX_TOPMOST | \
                win32con.WS_EX_TRANSPARENT
        win32api.SetWindowLong(hWindow, win32con.GWL_EXSTYLE, exStyle)

        label.pack()
        # label.update_idletasks()
        # label.update()
        label.mainloop()

    def main():
        from helpers.loggers.activitylog import sockLogger
        import configparser
        
        config = configparser.ConfigParser()
        config.read('amclient.ini')

        # IP = socket.gethostbyname(socket.gethostname())
        IP = config["DEFAULT"]["server_ip"]
        PORT = int(config["DEFAULT"]["port"])
        SENDER = config["EMAIL"]["email_host_user"]
        PASSWORD = config["EMAIL"]["email_host_password"]
        RECEIVER = config["EMAIL"]["admin_email"]
        MESSAGE = config["POLICY"]["message"] \
            + f" - ({datetime.now().strftime('%d-%m-%Y %H:%M:%S')})"

        tlabel = Thread(target=display_message, args=(MESSAGE,))
        tlabel.start()

        video = Video(IP, PORT)
        email = Email(PASSWORD, SENDER, RECEIVER)
        ActivityMonitor(video, email, config)

        sockLogger.info(f"{IP} started")
 
    process = Thread(target=main)
    process.start()
    process.join()

# CONVERT SCRIPT TO EXECUTABLE  
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
    
