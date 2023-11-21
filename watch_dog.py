"""Script to check if user has terminated Activity monitor."""
import sys
import traceback
import subprocess
import logging
import smtplib
import ssl
import configparser
import threading
import socket
import pickle
import time
from datetime import datetime
from typing import Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psutil
import pandas as pd
import win32evtlog
import win32evtlogutil

config = configparser.ConfigParser()
config.read("wdconf.ini")

logger = logging.getLogger("watch_dog")
logger.setLevel(logging.INFO)
# Create file handler to keep logs.
file_logger = logging.FileHandler("wd.log")
file_formater = logging.Formatter(
    "%(asctime)s - %(name)s %(levelname)s - %(message)s", 
)
file_logger.setFormatter(file_formater)
logger.addHandler(file_logger)

# Dictionary to keep track of logged in users
login = {}
# List to track clients who are running watch_screen and have connected.
connections = []

# Get Hostname
hostname = socket.gethostname()


def find_activity_monitor_proc(proc_name: str, username: str):
    """
    Find if the user is running a process.

    Parameters
    ----------
    proc_name: str
        Name of the process to be searched for.
    username: str
        Username of the user whose processes are being checked.
    """
    global login
    uname = hostname.lower() + '\\' + username
    proc_list = []
    for proc in psutil.process_iter(["name", "username"]):
        if proc.info["username"].lower() == uname:
            proc_list.append(proc.info["name"])
        
    if proc_name not in proc_list:
        # Terminate user session.
        session_id = get_session_id(username)
        terminate_session(session_id)

        # Remove client from login dictionary.
        try:
            pc_name = get_pc_name(username)
            del login[pc_name]
        except KeyError:
            pass
        except Exception as ex:
            logger.exception(ex)
        
        # Send email.
        alert(username)

def template(user: str, scenario: int = 1) -> Tuple[str, str]:
    """
    Constructs an html and plain message, either of which will be sent
    to the receiver depending on the receiver's email client
    compatibility.
    
    Parameters
    ----------
    user: str
        The IP Address of the client.
    scenario: int
        The value to determine which email message to use.

    Returns
    -------
    Tuple[str, str]
        HTML message format and string/plain message format.
    """
    email_var = {
        1: [
                f"""
                    <p>
                        The session of {user} has been terminated upon
                        detecting that the Activity Monitor client had been
                        terminated.
                    </p>
                """,
                f"""
                    \t The session of {user} has been terminated upon 
                    detecting that the Activity Monitor client had been 
                    terminated. \n
                """
        ],
        2: [
                f"""
                    <p>
                        The session of {user} has been terminated upon
                        detecting that the screenshot/screenrecording blocker
                        is not running or had been terminated.
                    </p>
                """,
                f"""
                    \t The session of {user} has been terminated upon 
                    detecting that the screenshot/screenrecording blocker 
                    is not running or had been terminated. \n
                """
        ],
        3: [
                f"""
                    <p>
                        The session of {user} has been terminated upon
                        detecting that the client PC is not running
                        watch_screen.
                    </p>
                """,
                f"""
                    \t The session of {user} has been terminated upon 
                    detecting that the client PC is not running 
                    watch_screen. \n
                """
        ],
    }
    html = f"""\
                <html>
                <body>
                    <p>
                        {email_var[scenario][0]}
                    </p>
                    <p>
                        Date: {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")}
                    </p>
                </body>
                <footer>
                    <p><i>Watch Dog ({datetime.now().year})</i></p>
                </footer>
                </html>
            """

    plain = f"""\
            {email_var[scenario][1]}
            \t Date: {datetime.now()} \n \n
            """

    return html, plain

def send_email(
        sender: str, password: str,
        receiver: str, username: str,
        scenario: int = 1
    ):
    """
    Sends an email when a user session has been terminated for killing
    the activity monitor client to the email address specified.

    Parameters
    ----------
    sender: str
        Email address from which you want to send emails (host email).
    password: str
        Password associated with your host email account.
    receiver: str
        Receiver's email address where you want to send the alert.
    username: str
        Username of the logged on user whose session was killed.
    scenario: int
        The scenario raising the cause for alert with will be used to
        determine the message to send.
    """
    ctx = ssl.create_default_context()
    message = MIMEMultipart("alternative")
    message["Subject"] = "User Session Terminated"
    message["From"] = sender
    message["To"] = receiver

    html, plain = template(username, scenario=scenario)

    message.attach(MIMEText(plain, "plain"))
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=ctx) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, message.as_string())

def alert(username: str, etype: int = 1):
    """
    Prepare and send email about user whose session has been
    terminated.

    Parameters
    ----------
    username: str
        Username of user whose session has been terminated.
    etype: int
        Key to eventually denote which email will be sent.
    """
    # Get sender, password, and receiver details from config file.
    try:
        sender = config["EMAIL"]["email_host_user"]
        password = config["EMAIL"]["email_host_password"]
        receiver = config["EMAIL"]["receiver_email"]

        send_email(sender, password, receiver, username, scenario=etype)
        logger.info(f"Email sent to {receiver} (scenario - {etype})")
    except Exception as ex:
        logger.exception(ex)

def terminate_session(id: int):
    """
    Function to terminate user session with session ID.

    Parameters
    ----------
    id: int
        The session ID for the session to be terminated.
    """
    try:
        obj = subprocess.run(f"tsdiscon {id}", text=True)
        logger.info(f"Session {id} terminated")
        if obj.stderr:
            logger.debug("terminate_session:", obj.stderr)
    except Exception as ex:
        logger.exception(ex)

def get_session_id(username: str) -> int:
    """
    Get the session ID for the given username. Username should be all
    lower case.

    Parameters
    ----------
    username: str
        The username for which the session ID will be retrieved.
    
    Returns
    -------
    int
        The session ID of the specified user.
    """
    id = None
    # Get all sessions.
    obj = subprocess.run("query session", stdout=subprocess.PIPE, text=True)
    obj.stdout = obj.stdout.replace(">", "", 1)
    if obj.stderr:
        logger.debug("get_session_id:", obj.stderr)
    data = obj.stdout.split("\n")[1:-1]
    data = [line.split() for line in data]
    for items in data:
        if items[1].lower() == username.lower() and len(items) == 4:
            id = int(items[2])
    return id

# Get non admin users.
def user_list() -> pd.DataFrame:
    """
    Get the list of non admin users.

    Returns
    -------
    pd.Dataframe
        Data frame containing data about all users who aren't admin.
    """
    obj = subprocess.run("query user", stdout=subprocess.PIPE, text=True)
    obj.stdout = obj.stdout.replace(">", "", 1)
    if obj.stderr:
        logger.debug("user_list:", obj.stderr)
    data = obj.stdout.split("\n")[1:-1]
    data = [line.split() for line in data]
    # Create a pandas data frame with the response.
    df = pd.DataFrame(data=data, columns=obj.stdout.split("\n")[0].split())
    users = df[df.USERNAME != "administrator"]
    return users

def get_login_events() -> dict:
    """
    Read Windows events and get only logon events from a few seconds
    ago. The number of seconds should be equal to the period (15s)
    between messages sent from the client side in case client logs in
    early in the period in-between sending messages.

    Returns
    -------
    dict:
        Dictionary containing PC names of clients who logged in as well
        as the username of the account they logged into and the time of
        login.
    """
    server = "localhost" # name of the target computer to get event logs
    logtype = "Security" # 'Application' # 'System'
    hand = win32evtlog.OpenEventLog(server, logtype)
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ|\
        win32evtlog.EVENTLOG_SEQUENTIAL_READ
    total = win32evtlog.GetNumberOfEventLogRecords(hand)

    evt_dict = {}
    begin_sec = time.time()
    try:
        events = 1
        while events:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            for ev_obj in events:
                the_time = ev_obj.TimeGenerated
                sec = time.mktime(
                    datetime.strptime(str(the_time), "%Y-%m-%d %H:%M:%S")\
                        .timetuple()
                )
                # Check events in the last few seconds.
                if sec < begin_sec-15: break
                # Check only logon events
                # (logon events have 4624 as event ID).
                if ev_obj.EventID == 4624:
                    msg = str(
                        win32evtlogutil.SafeFormatMessage(ev_obj, logtype)
                    ).split("\n")
                    username = msg[14].split()[-1].strip()
                    workstation = msg[24].split()[-1].strip()
                    evt_dict[workstation] = [str(the_time), username]
            if sec < begin_sec-15: break # Get out of while loop as well.
        win32evtlog.CloseEventLog(hand)
        if len(evt_dict) > 0:
            logger.info("Logon Event logs: %s", evt_dict)
        return evt_dict
    except Exception:
        logger.error(traceback.print_exc(sys.exc_info()))

def receive_messages(conn: socket.socket):
    global login
    # conn.settimeout(15)
    try:
        message = conn.recv(1024)
        clientname, greetings = pickle.loads(message)
        print("I am:", clientname)
        if clientname and greetings == "hi":
            conn.send(str.encode("go on"))
        while True:
            message = conn.recv(1024).decode()
            if clientname not in connections: connections.append(clientname)
            # print("Connections:", connections)
            # print("Logins:", login)
            # print("Watch_screen:", message)
            if clientname not in login.keys():
                # print("You got me!")
                continue
                # Get event logs to find if clientname has logged in.
                # logons = get_login_events()
                # print("logons:", logons)
                # if clientname not in logons.keys():
                    # Client has not logged in
                    # continue
                # Multiple logs are made for the logged in user. After
                # logging the name of the client PC which is remotely
                # connected to the server this watchdog is running on
                # and the username it logged in as, there is also
                # another log for the same username but this time with
                # the server name. So if both logs contain the same
                # username, then the logged in user is confirmed. There
                # might be conflicts, I believe, if multiple client
                # machines log in at the same time with different
                # usernames. The way the logs are being gathered will
                # cause one of the usernames to be confirmed and the
                # other's session would be terminated. The situation
                # has been handled and a special email will be sent so
                # that the user whose session was terminated can log in
                # again and the previous login won't be counted as a
                # violation.
                # if logons[hostname][1] == logons[clientname][1]:
                    # Add user to login dictionary
                    # login[clientname] = logons[clientname][1]
                # else:
                #     # Different usernames in event log.
                #     logger.error(
                #         "Username logged by host machine does not match "
                #         "username of recent login by remote client. "
                #         "Terminating session."
                #     )
                #     # Terminate session"
                #     session_id = get_session_id(logons[clientname][1])
                #     if session_id:
                #         # User is logged in.
                #         terminate_session(session_id)
                #         # Email
                #         alert(username=logons[clientname][1], etype=3)
                #     continue
            if message != "pass":
                # When the client has stopped running anti-screenshot
                # program.
                username = login[clientname]
                session_id = get_session_id(username)
                if session_id: # Client is currently logged in.
                    terminate_session(session_id)
                    # Email
                    alert(username=username, etype=2)
                # Remove client from login dictionary.
                del login[clientname]
    except (ConnectionResetError, socket.timeout):
        try:
            username = login[clientname]
            connections.remove(clientname)
            session_id = get_session_id(login[clientname])
            if session_id:
                terminate_session(session_id)
                alert(username=username, etype=3)
            del login[clientname]
        except (ValueError, KeyError, Exception):
            pass
        return
    except Exception as ex:
        logger.exception(ex)
        conn.close()
        try:
            username = login[clientname]
            connections.remove(clientname)
            session_id = get_session_id(login[clientname])
            if session_id:
                terminate_session(session_id)
                alert(username=username, etype=2)
            del login[clientname]
        except (ValueError, KeyError, Exception):
            pass
        return

def screen_job() -> None:
    """
    This function will run as a thread and listen to messages
    that suggest that the client sending the messages is running
    anti-screenshot program.
    """
    port = int(config["DEFAULT"]["port"])
    ip_address = socket.gethostbyname(hostname)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip_address, port))
        sock.listen()

        while True:
            print("Watchdog is ready to accept connections...")
            conn, addr = sock.accept()
            client_ip, _ = addr
            msg = f"{client_ip} connected"
            print(msg)
            logger.info(msg)

            # create thread to receive client messages
            t = threading.Thread(target=receive_messages, args=(conn,))
            t.start()

def get_pc_name(username: str) -> str:
    """
    Get the corresponding PC name for the client logged in as
    `username`.

    Parameters
    ----------
    username: str
        The username of the active account.
    
    Returns
    -------
    str:
        PC name of client who logged in as `username`.
    """
    try:
        global login
        if len(login) == 0:
            logons = get_login_events()
            evt_users = [user[1].lower() for user in logons.values()]
            if username in evt_users and len(evt_users) == 3:
                tname = list(logons.keys())[2]
                login[tname] = list(logons.values())[2][1]
                return tname
            elif username in evt_users and len(evt_users) == 1:
                tname = list(logons.keys())[0]
                login[tname] = list(logons.values())[0][1]
                return tname
        for pc_name, name in login.items():
            if name.lower() == username:
                return pc_name
        return None
    except Exception:
        logger.error(traceback.format_exc())

def main():
    global login
    logger.info("Watchdog started")
    s = threading.Thread(target=screen_job)
    s.start()
    # TO DO: maybe make the activity monitor name configurable
    try:
        while True:
            # Get all non admin users.
            users = user_list()
            for i in range(len(users)):
                user_name = users.iloc[i, 0]
                if users.iloc[i, 3] == "Active":
                    find_activity_monitor_proc("main_client.exe", user_name)
                    # Get PC name for client that logged on as
                    # user_name.
                    pc_name = get_pc_name(user_name)
                    if pc_name not in connections:
                        # Terminate session
                        session_id = get_session_id(user_name)
                        terminate_session(session_id)
                        alert(user_name, 3)
            time.sleep(2)
    except Exception as ex:
        logger.exception(ex)


if __name__ == "__main__":
    main()