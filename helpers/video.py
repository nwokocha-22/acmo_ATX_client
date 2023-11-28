import subprocess
import socket
import struct
import cv2
import queue
import time
import pickle
from threading import Thread
from configparser import ConfigParser

import numpy as np
import pyautogui

from helpers.loggers.errorlog import error_logger
from helpers.email import EmailClient

config = ConfigParser()
config.read('amclient.ini')

class SendVideo:
    """Captures and transmits the video frame via UDP socket.

    Parameters
    ----------
    ip: str
        IP address of the receiver device (server)
    port: int
        Port number on which to send data from sender side

    Attributes
    ----------
    address: tuple
        2-element tuple containing server's IPv4 address and port
        number for sending datagrams.
    queue: queue.Queue
        Queue object used by thread to store frames received from
        screen capturing.
    size: tuple
        Video frame resolution.
    IMAGE_QUALITY:
        Quality of transmitted image.
    """

    queue = queue.Queue()
    IMAGE_QUALITY = int(config['VIDEO']['quality'])

    try:
        width, height = pyautogui.size()
        # Interchanging the width and height to match with server side
        # and configuration. Apologies in advance for the confusion.
        frame_width = height
        frame_height = width
    except Exception:
        frame_height = int(config['VIDEO']['frame.height'])
        frame_width = int(config['VIDEO']['frame.width'])

    def __init__(self, ip, port):
        self.address = (ip, port)
        self.trial = 0
    
    def captureScreen(self):
        """Captures screen image and adds it to queue."""
        try:
            img = pyautogui.screenshot()
            self.queue.put(img)
            time.sleep(0.3)
        except OSError as err:
            time.sleep(1)
            error_logger.exception(err)  
            img = pyautogui.screenshot()
            self.queue.put(img)
    
    def alertTermination(self, username):
        """
        Sends a message to notify that the user has been disconnected.

        Parameters
        ----------
        username: str
            Username of the client who was disconnected.
        """
        sender = config["EMAIL"]["email_host_user"]
        password = config["EMAIL"]["email_host_password"]
        receiver = config["EMAIL"]["admin_email"]
        email = EmailClient(password, sender, receiver)

        content = (f"The session of {username} has been terminated on the "
            "server upon detecting that they are running a "
            "screen-record/screenshot blocking software prohibiting the "
            "function of the activity monitor.")
        server = socket.gethostbyname(socket.gethostname())
        email.send_email(server, 0, content, etype=2)

    def send_data(self, sock_tcp: socket.socket): 
        """Create a window with the width title of the client ip.
        Capture the user's screen and send the frame to a server
        through tcp socket.
        """
        while True:
            try:
                self.captureScreen()
                video_frame = self.queue.get()
                frame = np.array(video_frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                # frame = cv2.resize(
                #     frame, (self.frame_height, self.frame_width)
                # )

                # If all pixels are black; this will denote the
                # activity monitor inability to record the screen,
                # indicating that there is possibly a screen record
                # blocker being run on the server.
                if not frame.any():
                    # Terminate user session.
                    ret = subprocess.run(
                        "query session", stdout=subprocess.PIPE, text=True
                    )
                    data = ret.stdout.split("\n")
                    for line in data:
                        if line.startswith(">"):
                            try:
                                id = line.split()[2]
                                name = line.split()[1]
                                self.alertTermination(name)
                                error_logger.info(
                                    f"{name} session disconnected."
                                )
                                subprocess.run(f"tsdiscon {id}", text=True)
                            except Exception as ex:
                                error_logger.exception(ex)
                img_bytes = cv2.imencode(
                    '.jpg',
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, self.IMAGE_QUALITY]
                )[1].tobytes()
                # a = pickle.dumps(frame)
                message = struct.pack("Q", len(img_bytes)) + img_bytes
                sock_tcp.sendall(message)
            except ConnectionResetError:
                break
                
            except OSError as os_err:
                if self.trial >= 12:
                    error_logger.info(f"{self.address[0]}: "
                        "Terminating screen capturing...")
                    break
                # time.sleep(5)
                self.trial += 1

    def connect_to_server(self):
        """Establishes a three-way handshake with the clients, and
        spawns a thread to send data to the connected client.
        """
        connected = False
        while not connected:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_tcp:
                sock_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock_tcp.connect(self.address)
                    connected = True
                except Exception as error:
                    connected = False
                    error_logger.exception("Server not responding. "
                        "Trying to connect...")
                    time.sleep(10)

                if connected:
                    # If connected to server, send data.
                    while True:
                        try:
                            # Width and height have been interchanged
                            # right from their initialization and
                            # config assignments.
                            data = [
                                "ready", self.frame_height, self.frame_width
                            ]
                            to_send = pickle.dumps(data)
                            sock_tcp.sendall(to_send)
                            data = sock_tcp.recv(1024).decode()
                            if data == "shoot":
                                send_thread = Thread(
                                    target=self.send_data, args=(sock_tcp,)
                                )
                                send_thread.start()
                                send_thread.join()
                        except (ConnectionResetError, ConnectionAbortedError)\
                            as err:
                            # If server is shut down or connection to
                            # server is terminated, try to reconnect
                            # again.
                            error_logger.exception(err)
                            sock_tcp.close()
                            connected = False
                            break
