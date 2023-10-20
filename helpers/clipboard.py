
from typing import Union, List, Optional
import win32clipboard as wc
from pathlib import Path
from dataclasses import dataclass
import win32gui
import  win32api
import ctypes
import sys

sys.path.append(".")

from helpers.policies import CopyPolicy
from helpers.loggers.errorlog import error_logger
from helpers.loggers.activitylog import sockLogger
   
@dataclass
class ClipboardMonitor(CopyPolicy):
    """Handles clipboard activities.
        
    Parameters
    ----------
    on_text: callable
        Function to be called when the content type is text.
    on_image: callable
        Function to be called when the content type is image.
    on_file: callable
        Function to be called when the content type is file.
    """
    @dataclass
    class Content:
        """Copied content blue print.
        
        Parameters
        ----------
        type:
            The type of content content copied ['Text' or 'Image' or
            'File'].
        value:
            The actual content copied.
        """
        def __init__(self, type: str, value: Union[str, List[Path]]):
            self.type = type
            self.value = value
        
    def __init__(self, on_text=None, on_image=None, on_file=None):
        self._on_text = on_text
        self._on_image = on_image
        self._on_files = on_file
        
    def _create_base_window(self) -> int:
        """Creates a window for listening to clipboard.

        Returns
        -------
            window hwnd
        """
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._handle_message_from_clipboard
        wc.lpszClassName = self.__class__.__name__
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        return win32gui.CreateWindow(
            class_atom, 
            self.__class__.__name__, 0, 0, 0, 0, 0, 0, 0, 
            wc.hInstance, None)
    
    def _handler():
        pass

    def run_clipboard_listener(self):
        print("Clipthread started!")
        hwnd = self._create_base_window()
        ctypes.windll.user32.AddClipboardFormatListener(hwnd)
        win32gui.PumpMessages()
           
    def _handle_message_from_clipboard(
        self, 
        hwnd: int, 
        msg: int, 
        wparam: int, 
        lparam: int
    ):
        WM_CLIPBOARDUPDATE = 0x031D
        if msg == WM_CLIPBOARDUPDATE:
            self._handle_clipboard_content()
        return 0

    def _handle_clipboard_content(self):
        """Processes the clipboard content based on the file type."""
        try:
            content = self.getClipboardContent()
        except Exception as e:
            # e = pywintypes.error
            error_logger.exception(e)
        try:
            if content:
                if content.type == "text" and self._on_text:
                    self.copied_content = content.value
                    self._on_text(content.value)

                elif content.type == "image" and self._on_image:
                    self._on_image(content.value)
                    # prevent copying of image(s)
                    self.clearClipboard()

                elif content.type == "files" and self._on_files:
                    self._on_files(content.value)
                    # prevent copying of file(s)
                    self.clearClipboard()
            # wc.CloseClipboard()
        except Exception as err:
            error_logger.exception(err)

    def getClipboardContent(self) -> Optional[Content]:
        """Checks the format of the copied content. Gets and returns
        the recently copied content if the user has not defaulted.

        Returns
        -------
        content: ClipboardMonitor.Content
            The copied content.
        """
        try:
            wc.OpenClipboard()
            def checkFormat(format):
                if wc.IsClipboardFormatAvailable(format):
                    if not self.has_defaulted():
                        return wc.GetClipboardData(format)
                    else:
                        wc.EmptyClipboard()
                return ''

            # Check the format of the copied content
            # (text, image, or **byte)
            if text := checkFormat(wc.CF_UNICODETEXT):
                return ClipboardMonitor.Content('text', text)
                
            elif image := checkFormat(wc.CF_BITMAP):
                return ClipboardMonitor.Content('image', image)
            
            elif files := checkFormat(wc.CF_HDROP):
                return ClipboardMonitor.Content(
                    'files', [Path(file) for file in files]
                )

            return None
            
        finally:
            # if self.has_defaulted():
            wc.CloseClipboard()

    def disableClipboard(self):
        """Empties and disables the clipboard."""
        self.hasDefaulted = True
        self.clearClipboard()

    @staticmethod
    def clearClipboard():
        wc.OpenClipboard(None)
        wc.EmptyClipboard()
        wc.CloseClipboard()

# if __name__=="__main__":
#     clipboard = ClipboardMonitor(on_text=print, on_file=None, on_image=None)
#     clipboard.run_clipboard_listener()
#     clipboard.join()
    
  
        