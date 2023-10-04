# ACTIVITY MONITOR
# V 1.0.0

# GETTING STARTED

- # About the Script

    This script continously monitors user's activity by capturing video 
    of the user's screen, mouse and keyboard activities, and the content copied to clipboard.
    
    If the copy policy is violated, an email, which includes the IP address of the User's machine, 
    size of the file copied, the actual copied content, date and time, is sent to the chief administrator.
    
    As a result of this violation, the user's clipboard will be disabled for 24hours even after reboot.

    --------------------
    TRANSMITION OF CAPTURED VIDEO
    The captured video is transmitted to a remote server using a UDP socket.

    --------------------
    TRANSMITION OF LOG
    Logged user activity (Keyboard and mouse) is instantly transmitted to a remote server
    via the Logger socket formatter.

    --------------------
    DEPENDED MODULES:
        :videoClient: A module with a threaded class that captures the screen video frame in mpeg format.
        :keyMouseActivity: A module that logs the users activity every 10 minutes.
        :emailClient: A module that handles sending emails to a recipient email when the user defaults on the content copy policy.
        :ClipboardActivity: A module with a threaded class that monitors the clipboard. It fetches the content copied to clipboard so that its size can be estimated. 

- # Running the Script
    `python ./core.py` 

## SETUP FOR DEVELOPMENT

### 1. Enviromental Varialbles (.env)
- without the enviromental variable, starting the core.py module will fail.
- ensure you have .env file in your root directory and the values for the IP (address of the server), PORT, PASSWORD, SENDER, RECEIVER are provided.
- For the PASSWORD (Google App Authentication Key), you need to setup app authentication using google gmail settings. The PASSWORD Associated with the SENDER Email is required for the email functionality to work.

### 2. Google Email 2Auth Setup
    https://support.google.com/accounts/answer/185839?hl=en&co=GENIE.Platform%3DDesktop


## SCRIPT FEATURES AND FUNCTIONALITIES

### 1. Keyboard and Mouse Monitoring
- The KeyMouseActivity module monitors the user's keyboard and mouse activities. It captures the number of key strokes and mouse moves every 10 munites to indicate when a user is idle or active.

### 2. Clipboard Monitoring
- The clipboardActivity Module monitors the content copied to clipboard. It also detects the type of content (text, image or file), and calls appropriate functions (on_text, on_image, and on_file) in the main application (core.py) for coresponding handling of the copied content.

- The clipboard event handlers invokes a policy check to see if the copied content violates the copy policy or not. If not, it takes count of the size of the copied content else, it invokes a disciplinary action which disables the clipboard and updates the `policyConfig` file by setting the `hasDefaulted` key to True and appends the time the defaulting occurs. An email is sent to the admin to inform him/her of the policy violation.

### 4. Video Monitoring
- The VideoClient Module captures the user's screens and transmit the video to a remote server via an UDP socket where it can be live streamed and also saved in a video file in a designated folder for future references. A new folder where the video is saved is created using the client's ip address if it does not already exist.

### 5. Email Functionality
- If the copy policy is violated by the user, an email is sent to the admin with details of the size of the copied content, the actual content, date and time, and the user's IP address.

# LIBRARIES AND DEPENDENCIES
- Refer to the requirement.txt for freezed dependencies
- Ensure that the right versions of libraries are installed as captured in the requirements.txt file.
- If the right version of pyautogui and pillow is NOT used, you will run into errors when screenshot function of pyautogui is called. error => `pyscreeze.PyScreezeException: The Pillow package is required to use this function`

# PREPARING SCRIPT FOR DEPLOYMENT
- House keeping: Ensure to remove all generated binary files that are not needed in running the script e.g error.log, .env, policyConfig, timeConf, copiedFiles.zip, requirement.txt, and others, including the test folder.

- WARNING: The values for the parameters provided in the `.env` should be passed directly to the variable before conversion. Failure to do this will cause the script conversion to fail.

# CONVERTING TO AN EXECUTABLE

- Run the command below in the terminal

- `pyinstaller.exe --runtime-tmpdir=. --hidden-import win32timezone --collect-submodules helpers --hidden-import logging.handlers --hidden-import cv2 --name main_client --onefile service.py`

### WINDOW SERVICE

# TO INSTALL
- dist/main_client.exe install

# TO START
- dist/main_client.exe start

# TO STOP
- dist/main_client.exe stop

# To REMOVE
- dist/main_client.exe remove

### WARNING: The Client scripts, if installed as a window service, will only work if the user is logged in, not as an admin, and 'allow service interact with desktop' is enabled. Pyautogui will fail to grab screen, and no video will be transmitted, if the two conditions stated above are not met.

### ENABLE SERVICE TO INTERACT WITH DESKTOP

- PROCEDURES:

1. Open the Services control panel. For example: Start > Control Panel > Administrative Tools > Services.
2. Right-click the service name ('AMClientService'), and select Properties. The Service Properties window is displayed.
3. Select the Log On tab.
4. Select Local System account and then select Allow service to interact with desktop.
5. Click OK.
6. Click Restart.

## ALTERNATIVE CONFIGURATION ( RECOMMENDED )

- STEP 1: 

Compile the script without the service. Ensure the `--noconsole` flag is used to avoid the popup of window shell when running the executable.

-   `pyinstaller.exe --runtime-tmpdir=. --hidden-import win32timezone --collect-submodules helpers --hidden-import logging.handlers --hidden-import cv2 --name main_client --onefile --noconsole core.py`

- START 2:

- To RUN this script unanimously on the Client computer, it is important to setup Logon and Logoff events. To do this, follow the steps outlined below.

- STEP 2 - i : SET UP TASK IN TASK SCHEDULER

-   `General`: Name the scheduled task. ensure to select `Run only when user is logged on`

-   `Triggers`: 
        `log`:    Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational, 
        `Source`: TerminalServices-RemoteConnectionManager
        `Event ID`: 1149

-   `Actions`: C:\atmo_client\dist\monitor.bat

# NOTE: You may specify a different path to where the executable file is saved

- monitor.bat is the batch script that is triggered when there is a logon event. The batch script starts the executable file which runs in the background

 ## TERMINATE ON LOGOFF

-TRIGGER (ON EVENT)
-   -   Log: Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational
-   -   SOURCE: TerminalServices-RemoteConnectionManager
-   -   EVENTID: 216

- ACTIONS
-   -   Action: Start a program
-   -   Details: C:/stop_AM_service.bat

## CONTENT OF stop_AM_service.bat
`:: Kill The main_client.exe process`
`@Echo off`
`Echo main_client.exe`
`TASKKILL /F /IM main_client.exe /T`

## NEED MORE INFO?
- Reachout to Maruche

