
import os
import time
import threading
import pickle
from dataclasses import dataclass
from datetime import datetime
import itertools as it

@dataclass
class Timex():

    @property
    def params(cls):
        """Retrieves the login time. """
        if os.path.exists('timeConf'):
            with open('timeConf', 'rb') as time_:
                time_dict = pickle.load(time_)
                return time_dict
        else:
            return None

    @params.getter
    def get_params(cls):
        return cls.params

    def update_params(cls, **kwargs):
        """Updates the configuration file with the keyword args.

        Opens the time configuration file, if it exists, for reading
        and writing.
        """
        time_dict = None
        try:
            if os.path.exists("timeConf"):
                with open('timeConf', 'rb+') as time_:
                    time_dict = pickle.load(time_)
                    time_.seek(0)
            else:
                # Create the config if it doesn't exist
                with open('timeConf', 'wb') as time_:
                    if not time_dict:
                        time_dict = {
                            'date': datetime.now().date(), 
                            'time_in': time.time(), 
                            'last_checked': None, 
                            'content_size_1hr': 0, 
                            'content_size_24hr': 0}
        except FileExistsError as err:
            print(err)
        finally:
            new_dict = {k:v for k, v in kwargs.items() if k in time_dict.keys()}
            time_dict.update(new_dict)
            pickle.dump(time_dict, time_)

    @staticmethod
    def save_time_in(time_dict: dict = {}):
        """Saves the date and time user logs in.
        
        Parameters
        ----------
        time_dict: `dict`
            date:
                the current date
            time_in: 
                the time user logged in/started working in the current day
            last_checked: 
                the last time the user copied content
            content_size_1hr: 
                the size of content copied in the current time frame less than 1 hour
            content_size_24hr: 
                the size of content copied in less than 24 hrs
        """
        try:
            with open('timeConf', 'wb') as time_:
                if not time_dict:
                    time_dict = {
                        'date': datetime.now().date(), 
                        'time_in': time.time(), 
                        'last_checked': None, 
                        'content_size_1hr': 0, 
                        'content_size_24hr': 0}
                pickle.dump(time_dict, time_)
        except FileExistsError as err:
            print(err)
        finally:
            return time_dict

    def get_config_params(cls):
        """The time user began working for the day."""
        try:
            _params = cls.get_params
            if _params is not None and _params['date'] == datetime.now().date():
                return _params
            else:
                time_ = Timex.save_time_in()
                return time_
        except Exception as err:
            print(err)
    
    @classmethod
    def interval(cls, t2:datetime, t1:datetime):
        """Evaluates the time difference from time-in until present in
        hour.
        """
        try:
            d2 = datetime.fromtimestamp(t2)
            d1 = datetime.fromtimestamp(t1)
            diff = (d2 - d1).total_seconds()
            diff_in_hr = diff // 3600
            return diff_in_hr
        except TypeError as type_error:
            print(type_error)


class _Timer(threading.Thread):
    """This thread blocks for the interval specified and set the threading
    event when the time elapses.

    Parameters
    ----------
    interval: int
        The number of seconds/minutes/hours to block before timing out.
    
    mode: str
        Time unit of measurement. Either seconds, minutes,or hours
    """
  
    def __init__(self, interval, mode="sec"):
        super(_Timer, self).__init__()

        self._mode = mode
        self.interval = interval
        self.event = threading.Event()
        self.should_run = threading.Event()
        self._init()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def set_mode(self, value):
        """Sets a new value to mode; either, seconds, minutes, 
        or hours. 
        """
        self._mode = value

    def _init(self):
        self.event.clear()
        self.should_run.set()

    def stop(self):
        """Clears the event and Stops the thread. Ensures to call 
        immediately afterwards
        """
        self.should_run.clear()

    def consume(self):
        was_set = self.event.is_set()
        if was_set:
            self.event.clear()
        return was_set

    def run(self):
        """
        The internal main method of this thread. Block for :attr:`interval`
        seconds before setting :attr:`Ticker.evt`

        :warning::
        Do not call this directly!  Instead call :meth:`start`.
        """
        
        interval = self.interval

        if self.mode == "min":
            interval = self.interval * 60
        elif self.mode == "hour":
            interval = self.interval * 60 * 60

        while self.should_run.is_set():
            time.sleep(interval)
            self.event.set()
    
def timer(func):
    def _timer(callback, interval, mode):
        """A decorator function that calls the function after 
        the interval elapses
        
        Parameters
        ----------
        callback:
            The function to be called.
        interval
            The specified interval.
        mode
            The time frame -> sec, min or hour.
        """
       
        _time = _Timer(interval)
        _time.set_mode = mode
        _time.start() 
       
        try:
        
            while _time.event.wait(): # waits until the sets method of the thread event is called
                _time.event.clear() 
                callback()
        except:

            _time.stop() 
            _time.join() 

        return func(callback, interval, mode)
    return _timer

"""
USE CASE
if __name__=="__main__":
    def callback1():
        print("alarm call 1")

    def callback2():
        print("alarm call 2 !!")

    @timer
    def func(callback, interval, mode):
        print("alarm triggered")

    @timer
    def func1(callback, interval, mode):
        print("alarm triggered")

    t1 = threading.Thread(target=func, args=(callback1, 2, 'sec'))
    t1.start()
    t2 = threading.Thread(target=func1, args=(callback2, 4, 'sec'))
    t2.start()
    t1.join()
    t2.join()

"""
# if __name__== "__main__":
#     time_ = Time()
#     time_in = time_.time_in()
#     time_.update_params(content_size_24hr=38, content_size_1hr=3, mode=0.9, juju=True)
#     content_ = time_.get_params

