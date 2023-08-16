import json
import time
import core
import pytest
from pathlib import Path
from helpers.timer import Timex
from datetime import datetime
from core import ActivityMonitor
from helpers.policies import CopyPolicy
from helpers.clipboard import ClipboardMonitor
from helpers.video import SendVideo
from helpers.email import EmailClient
from helpers.keymouse import KeyMouseMonitor, KeyboardActivity, MouseActivity
from pynput.keyboard import Controller

@pytest.fixture
def config():
    path = Path.joinpath(Path.cwd(), "tests", "data", "config.json")
    file = open(path)
    config = json.load(file)
    return config

@pytest.fixture
def videoClient(config):
    video = SendVideo(config["ip"], config["port"])
    return video

@pytest.fixture
def emailClient(config):
    email = EmailClient(config["password"], config["sender"], config["receiver"])
    return email

@pytest.fixture
def clipBoard():
    clip_mon = ClipboardMonitor()
    return clip_mon
    
@pytest.fixture
def copyPolicy():
    copy_policy = CopyPolicy()
    return copy_policy

@pytest.fixture
def policyConfigPath():
    path = Path.joinpath(Path.cwd(), "policyConfig")
    return path

@pytest.fixture
def coreApp(videoClient, emailClient, keyMouse):
    app = ActivityMonitor(videoClient, emailClient, keyMouse)
    return app

@pytest.fixture
def video():
    ip = ''
    port = 5055
    video_client = SendVideo(ip, port)
    return video_client

@pytest.fixture
def email_client():
    email_ = EmailClient(config('PASSWORD'), config('SENDER'), config('RECEIVER'))
    return email_

@pytest.fixture
def clipboard():
    clipb = ClipboardMonitor()
    return clipb

@pytest.fixture
def coreApp(video, email_client):
    app = core(video, email_client)
    return app

@pytest.fixture
def time_():
    timex = Timex()
    return timex

@pytest.fixture
def time_config():
    time_dict = {
                'date':datetime.now().date(), 
                'time_in':time.time(), 
                'last_checked':None, 
                'content_size_1hr':0, 
                'content_size_24hr':0}
    return time_dict

@pytest.fixture
def policy():
    copy_policy = CopyPolicy()
    return copy_policy

@pytest.fixture
def keymouse():
    keymouse = KeyMouseMonitor()
    return keymouse

@pytest.fixture
def keyboard():
    keyboard = KeyboardActivity()
    return keyboard

@pytest.fixture
def mouse():
    mouse = MouseActivity()
    return mouse

@pytest.fixture
def controller():
    controller = Controller()
    return controller
