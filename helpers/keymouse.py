
from dataclasses import field
from pynput import keyboard, mouse
from threading import Thread


class MouseActivity:

    _total_mouse_move_count: int = field(default=0)
    _mouse_move_count: int = 0
    
    def __init__(self) -> None:
        m = Thread(target=self.mouseMonitor)
        m.start()
        
    @staticmethod
    def on_click(x, y, button, pressed):
        MouseActivity._mouse_move_count += 1

    @staticmethod
    def on_move(x, y):
        MouseActivity._mouse_move_count += 1

    def mouseMonitor(self):
        """Listens for mouse input. """
        with mouse.Listener(on_click=self.on_click, on_move=self.on_move) \
            as mouseMonitor:
            mouseMonitor.join()

    def get_mouseMoveCount(cls):
        return cls._mouse_move_count

    def reset(cls):
        cls._mouse_move_count = 0
    

class KeyboardActivity: 

    _total_key_stroke_count: int = field(default = 0) 
    _key_stroke_count:int = 0
    
    def __init__(self):
        k = Thread(target = self.keyMonitor)
        k.start()

    @staticmethod
    def on_press(key):
        KeyboardActivity._key_stroke_count += 1

    @staticmethod
    def on_release(key):
        if key == keyboard.Key.esc: 
            return False
    
    def keyMonitor(self):
        """Listens for keyboard inputs. """
        with keyboard.Listener(on_press= self.on_press, on_release=self.on_release)\
            as keyMonitor:
            keyMonitor.join()

    def get_keyStrokeCount(cls):
        return cls._key_stroke_count

    def reset(cls):
        cls._key_stroke_count = 0


class KeyMouseMonitor(Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start()

    def getCount(self):
        """Gets the average key stroke and mouse move per minute or hour.

        Returns
        -------
            key_count: `int`
                Average key stroke per minute

            mouse_count: `int`
                Average mouse move per minute
        """
        _mouse = MouseActivity()
        _keyboard = KeyboardActivity()

        key_count = _keyboard.get_keyStrokeCount()
        mouse_count = _mouse.get_mouseMoveCount()

        _mouse.reset()
        _keyboard.reset()   

        return key_count, mouse_count

        