import logging
import logging.handlers


error_logger = logging.getLogger(__name__)

error_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('error.log')

file_formater = logging.Formatter('%(asctime)s - %(name)s %(levelname)s - %(message)s', )

file_handler.setFormatter(file_formater)

# prevent multiple printing of error messages in the log file
if not error_logger.hasHandlers():
    error_logger.addHandler(file_handler)






