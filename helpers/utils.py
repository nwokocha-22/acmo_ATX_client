import os
import zipfile
from helpers.loggers.errorlog import error_logger

def zip(files: list) -> tuple:
        """Gets the size of the copied file(s) and zips it.
    
        Parameters
        ----------
        files: list
            Iterable containing the files to be zipped.
        
        Returns
        -------
        tuple
            file_size: int
                The total size of the zipped files.

            zipped: zipfile.Zipped
                The zipped files.
        """
        file_size = 0
        zip = zipfile.ZipFile("copiedFiles.zip", "w")
        try:
            for file in files:
                if not os.path.islink(file):
                    size = os.path.getsize(file)
                    file_size += round(size / 1000) # converting byte to kilobyte
                    zip.write(file, compress_type=zipfile.ZIP_DEFLATED)
        except Exception as err:
            error_logger.exception(err)
        finally:
            zip.close()

        return file_size, zip



    