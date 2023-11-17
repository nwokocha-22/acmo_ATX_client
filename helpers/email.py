import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

class EmailClient:
    """Sends email from the sender to the receiver.

    Parameters
    ----------
    password: str
        The authentication key for a google email address.
    sender: str
        The email address associated with the specified authentication key
        (password).
    receiver: str
        The email address to which the email is sent.
    
    Attributes
    ----------
    message_template: 
        Generates the html template used in the email message.

    >>> message_template(user, file_size, content)

    send_email: 
        sends the email

    >>> send_email(user, file_size, content, attachment)

    """
    def __init__(self, password, sender, receiver) -> None:
        self.password = password
        self.sender = sender
        self.receiver = receiver
        self.ctx = ssl.create_default_context()

        super().__init__()
       
    def message_template(self, user, file_size, content, etemp):
        """
        Constructs an html and plain message, either of which will be
        sent to the receiver depending on the receiver's email client
        compatibility.
        
        Parameters
        ----------
        user: str
            The IP Address of the client.
        file_size: float
            Size of the copied file.
        content: str

        Returns
        -------
        html: HTML message format
        plain: string/plain message format
        """
        email_var = {
            1: [
                f"""
                    <p>
                        Server: {user}
                    </p>
                    <p>
                        Date: {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")}
                    </p>
                    <h3>
                        File Size:
                        <b><u>{file_size} KB</u></b>
                    </h3>
                    <h4>Copied Content:</h4>
                    <p>
                        {content}
                    </p>
                """,
                f"""
                    \t Server: {user} \n
                    \t Date: {datetime.now()} \n \n
                    \t File Size: {file_size} KB\n
                    Content: \n
                    {content}
                """
            ],
            2: [
                f"""
                    <p>
                        Server: {user}
                    </p>
                    <p>
                        {content}
                    </p>
                    <p>
                        Date: {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")}
                    </p>
                """,
                f"""
                    \t Server: {user}\n
                    \t {content}\n
                    \t Date: {datetime.now()} \n
                """
            ]
        }

        html = f"""\
                    <html>
                    <body>
                        {email_var[etemp][0]}
                    </body>
                    <footer>
                        <p><i>Activity Monitor ({datetime.now().year})</i></p>
                    </footer>
                    </html>
                """

        plain = f"""\
                {email_var[etemp][1]}
                """

        return html, plain

    def send_email(self, user: str, file_size: float, content: str,
            attachment=None, etype=1) -> None:
        """Sends the user's ip, copied file size, content, and 
        attachment to the email address specified.
    
        Parameters
        ----------
        user: str
            IP address of the user's machine
        file_size: float
            Size of the file copied
        content: str
            The actual content of the file (str). Only applicable to text.
        attachment: bytes
            The file (byte) or image copied 
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = "Suspicious Activity Detected"
        message["From"] = self.sender
        message["To"] = self.receiver

        html, plain = self.message_template(user, file_size, content, etype)

        message.attach(MIMEText(plain, "plain"))
        message.attach(MIMEText(html, "html"))

        # If there is an attachment (Image or File)
        if attachment:
            file = MIMEApplication(attachment)
            description = f"Size: {file_size}, Agent: {user}"
            file.add_header("File:", description)
            message.attach(file)

        with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=self.ctx) as server:
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receiver, message.as_string())

     