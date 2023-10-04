import socket
from threading import Thread
import cv2
import numpy as np
import pyautogui
import queue
import time
from configparser import ConfigParser
from helpers.loggers.errorlog import error_logger

_BUFFER: int = 65536
config = ConfigParser()
config.read('amclient.ini')

class SendVideo:
    """Captures and transmits the video frame via UDP socket.

    Parameters
    ----------
    ip: `str`
        IP address of the receiver device (server)
    port: `int`
        Port number on which to send data from sender side
    config: `configParser.ConfigParser`
        Video configurations

    Attributes
    ----------
    address: `tuple`
        2-element tuple containing server's IPv4 address, port number for sending datagrams,
    queue: `queue.Queue`
        Queue object used by thread to store frames received from screen capturing
    size: `stuple`
        Video frame resolution
    IMAGE_QUALITY:
        Quality of transmitted image
    """

    queue = queue.Queue()
    frame_height = int(config['VIDEO']['frame.height'])
    frame_width = int(config['VIDEO']['frame.width'])
    IMAGE_QUALITY = int(config['VIDEO']['quality'])

    def __init__(self, ip, port):
        self.address = (ip, port)
        self.trial =0
    
    def captureScreen(self):
        """Captures screen image and adds it to queue. """
        try:
            img = pyautogui.screenshot()
            self.queue.put(img)
            time.sleep(0.3)
        except OSError as err:
            time.sleep(1)
            error_logger.exception(err)  
            img = pyautogui.screenshot()
            self.queue.put(img)  

    def send_data(self): 
        """Create a window with the width title of the client ip.
        Capture the user's screen and send the frame to a server
        through tcp socket.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock_udp:
            sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, _BUFFER)
            while True:
                try:
                    self.captureScreen()
                    video_frame = self.queue.get()
                    frame = np.array(video_frame)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    frame = cv2.resize(frame, (self.frame_height, self.frame_width))
                    img_bytes = cv2.imencode(
                        '.jpg',
                        frame,
                        [cv2.IMWRITE_JPEG_QUALITY, self.IMAGE_QUALITY])[1].tobytes()
                    sock_udp.sendto(img_bytes, self.address)
                    
                except OSError as os_err:
                    if self.trial >= 12:
                        error_logger.info(f"{self.address[0]}: \
                            Terminating screen capturing...")
                        time.sleep(5)
                        self.trial += 1

    def connect_to_server(self):
        """Establishes a three-way handshake with the clients, and
        spawns a thread to send data to the connected client.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_tcp:
                connected = False
                try:
                    while not connected:
                        try:
                            sock_tcp.connect(self.address)
                            connected = True
                        except Exception as error:
                            error_logger.exception("Server not responding. "
                                "Trying to connect...")
                        time.sleep(10)

                        if connected:
                            # If connected to server, send data.
                            while True: 
                                try:
                                    sock_tcp.send(b"ready")
                                    data = sock_tcp.recv(1024).decode()
                                    if data == "shoot":
                                        send_thread = Thread(target=self.send_data)
                                        send_thread.start()
                                        send_thread.join()
                                except (ConnectionResetError, ConnectionAbortedError) as err:
                                    # If server is shut down or connection to server is terminated,
                                    # try to reconnect again.
                                    error_logger.exception(err)
                                    connected = False
                                    break
                                
                except ConnectionAbortedError as err:
                    error_logger.exception("Server not communicating. Trying to connect...")
        except ConnectionRefusedError as err:
            error_logger.exception(err)
                   
