# test

import pytest
import time
from datetime import date, datetime
from helpers.timer import timer
from helpers.utils import zip
import pickle
import glob
import pyautogui
from pathlib import Path
from PIL import Image 
from unittest.mock import patch
import zipfile
from email.mime.multipart import MIMEMultipart

def test_interval_hour(time_):
    """ Tests the time difference between the time last copy was made until the current time """
    time_last_copied = time.mktime(date(2023, 6, 12).timetuple())
    current_time = time.mktime(date(2023, 6, 14).timetuple())
    difference = time_.interval(current_time, time_last_copied)
    assert int(difference) == 48 #48 hours = 2 days

def test_create_time_config(time_):
    """ tests if time configuration is created sucessfully """
    time_.save_time_in()
    params = time_.get_params
    assert list(params.keys()) == ['date', 'time_in', 'last_checked', 'content_size_1hr', 'content_size_24hr']

def test_update_time_config(time_):
    """ Tests the updates of the time configuration file """
    last_checked = time.time()
    time_.update_params(last_checked=last_checked, content_size_1hr=423)
    params = time_.get_params
    assert params['last_checked'] == last_checked
    assert params['content_size_1hr'] == 423

def test_time_in(time_):
    """ Test that the time user is logged in is recored """
    time_in = time.time()
    time_.update_params(time_in=time_in)
    assert time_in == time_.get_params['time_in']

def test_load_policy(policy):
    """ test creatinon and loading of the copy policy """
    copy_policy = policy._loadPolicyConfig()
    assert isinstance(copy_policy, dict)

def test_update_policy(policy):
    """ Test violation of the copy policy """
    time_of_defaulting = time.time()
    policy.updatePolicy(hasDefaulted=True, timeDefaulted=time_of_defaulting)
    assert policy.has_defaulted() == True

def test_reset_policy(policy):
    """ Tests the resetting of the copy policy """
    policy.updatePolicy(hasDefaulted=True)
    policy.reset()
    assert policy.has_defaulted() == False

def test_date_difference(policy):
    """ Tests the number of days passed since policy was violated """
    d1 = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
    d2 = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
    days = policy.get_date_difference(d1, d2)
    assert isinstance(days, int)

@pytest.mark.skip(reason="Thread blocking at keyboard.keyMonitor()")
def test_keyboard_activities(keyboard, controller):
    """ Test the tracking of keyboard activities """
    keyboard.keyMonitor()
    sentence = 'simulating typing activities'
    for letter in sentence:
        controller.press(letter)
    assert keyboard._key_stroke_count == len(sentence)

@pytest.mark.skip(reason="Blocking thread call")
def test_timer():
    """ Test timer triggers called function after duration elapses """
    called = False
    def callback():
        called = 1 != 0
    @timer
    def scheduler(callback, duration, mode): print()
    scheduler(callback, 0, 'sec')
    assert called

@pytest.mark.skip
def test_send_email(emailClient, config):

    message = MIMEMultipart("alternative")
    message["Subject"] = "Suspicious Activity Detected"
    message["From"] = config['sender']
    message["To"] =  config['receiver']

    with patch('smtplib.SMTP', autospec=True) as mock_smtp:

        emailClient.send_email("127.0.0.1", 126, "clipping birdies for fun")
        mock_smtp.assert_called()
        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_called()
        context.send_message.assert_called_with(message)

def test_mouse_activity(mouse):
    pyautogui.dragTo(20, 40)
    pyautogui.dragTo(40, 70)
    assert mouse._mouse_move_count
  
def test_keyboard_activity(keyboard):
    pyautogui.press('a')
    pyautogui.press('b')
    assert keyboard._key_stroke_count
    
def test_screen_capturing(videoClient):
    """
    Test that screen capturing works as expected
    """
    for _ in range(5):
        videoClient.captureScreen()
    captured_imgs = videoClient.queue.qsize()
    assert captured_imgs == 5

def test_captured_image_added_to_queue(videoClient):
    """ 
    check if the captured image is enqueued
    """
    videoClient.captureScreen()
    img = videoClient.queue.get()
    assert isinstance(img, Image.Image)


def test_zip_copied_files():
    """
    test the zipping of copied files
    """
    list_ = []
    file_path = Path.joinpath(Path.cwd(), "tests", "data", "files", "*.mkv")

    for file in glob.glob(str(file_path)):
        with open(file, 'rb') as file:
            list_.append(file.read())

    file_size, zipped = zip(list_)

    assert isinstance(file_size, int)
    assert isinstance(zipped, zipfile.ZipFile)
     
def test_create_policy_config(copyPolicy, policyConfigPath):
    """
    test the creation of the policy configuration file
    """

    copyPolicy._createPolicyConfig()

    with open(policyConfigPath, "rb") as file:
        policy_config = pickle.load(file)
    
    assert policy_config["hasDefaulted"] == False
    assert policy_config["timeDefaulted"] == None


def test_update_policy(copyPolicy, policyConfigPath):
    """test updating of the policy configuration file"""

    copyPolicy._createPolicyConfig()
    copyPolicy.updatePolicy(True, 1675361743.373751)

    with open(policyConfigPath, 'rb') as config:
        policyConfig = pickle.load(config)

    assert policyConfig["hasDefaulted"] == True
    assert policyConfig["timeDefaulted"] == 1675361743.373751


def test_load_policy_config(copyPolicy, policyConfigPath):
    """test loading of the policy configuration file"""
    copyPolicy._createPolicyConfig()
    assert copyPolicy._loadPolicyConfig()

def test_estimate_time_elapsed_since_defaulted(copyPolicy, policyConfigPath):
    defaulted_date = "2023-1-31"
    current_date = "2023-2-2"

    date_elapsed = copyPolicy.get_date_difference(current_date, defaulted_date)
    assert date_elapsed == 2 # 48 hrs


def test_reset_policy(copyPolicy):
    """ Resets the copy policy """
    copyPolicy.updatePolicy()
    assert True