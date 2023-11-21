import random
import socket
import pickle
import configparser
from time import sleep

import numpy as np
import cv2
from mss.windows import MSS as mss

config = configparser.ConfigParser()
config.read("wsconf.ini")

def main():
    ip = config["DEFAULT"]["ip"]
    port = int(config["DEFAULT"]["port"])
    # Get computer name.
    cname = socket.gethostname()
    with mss() as sct:
        monitor = sct.monitors[1]
        # Get screen dimensions.
        width = monitor["width"]
        height = monitor["height"]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(5)
            try:
                sock.connect((ip, port))
                to_send = pickle.dumps([cname, "hi"])
                sock.sendall(to_send)
                resp = sock.recv(1024).decode()
                if resp != "go on":
                    return
                print("Good to go!")
                while True:
                    # Get random position on screen.
                    left = random.randint(0, (width-50))
                    top = random.randint(0, (height-50))
                    monitor["left"] = left
                    monitor["top"] = top
                    monitor["width"] = 50
                    monitor["height"] = 50
                    # Take a screenshot
                    img = np.array(sct.grab(monitor))
                    # Convert to grayscale.
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                    # Check if all values in the image are 0; pitch
                    # black image.
                    # if not img.any():
                    if all(v == 0 for values in img for v in values):
                        # Send computer name and status (pass/fail).
                        # print("pass")
                        sock.send(str.encode("pass"))
                    else:
                        # print("fail")
                        sock.send(str.encode("fail"))
                    sleep(15)
                # TO DO: if not
            except (socket.timeout, ConnectionResetError, ConnectionAbortedError):
                print("Connection timed out.")


if __name__ == "__main__":
    main()