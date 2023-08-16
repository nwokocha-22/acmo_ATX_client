import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

class EmailClient:
    """Sends email from the sender to the receiver.

    Parameter
    ---------
    password: `str `
        the authentication key for a google email address
    sender: `str`
        the email address associated with the specified authentication key (password)
    receiver: `str`
        The email address to which the email is sent
    
    Attributes
    ----------
    message_template: 
        generates the html template used in the email message

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
       
    def message_template(self, user, file_size, content):
        """Constructs a html and plain messages either of which will sent to the receiver
        depending on the receiver's email client compatibility.
        
        Parameters
        ---------------
        user : `str`
            The IP Address of the client 
        file_size: `int`
            Size of the copied file
        content: `str`

        Returns
        --------
        html: HTML message format
        plain: string/plain message format
        """
        html = f"""\
                    <html>
                    <body>
                        <p>
                            Server: {user}
                        </p>
                         <p>
                            Date: {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")}
                        </p>
                        <h2>
                            File Size:
                            <b><u><i>{file_size} KB</i></u></b>
                        </h2>
                        <h4>Copied Content</h4>
                        <p>
                            {content}
                        </p>
                    </body>
                    <footer>
                        <p><i>{datetime.now().year}</i></P>
                    </footer>
                    </html>
                """

        plain = f"""\
                \t Server: {user} \n
                \t Date: {datetime.now()} \n \n
                \t File Size: {file_size} KB\n
                Content: \n
                {content}
                """

        return html, plain

    def send_email(self, user:str, file_size:int, content:str, attachment=None) -> None:
        """Sends the user's ip, copied file size, content, and 
        attachment to the email address specified.
    
        Parameters
        -----------
        user: `str`
            IP address of the user's machine
        file_size: `int`
            Size of the file copied
        content: `str`
            The actual content of the file (str). only applicable to text
        attachment: `bytes`
            The file (byte) or image copied 
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = "Suspicious Activity Detected"
        message["From"] = self.sender
        message["To"] = self.receiver

        html, plain = self.message_template(user, file_size, content)

        message.attach(MIMEText(plain, "plain"))
        message.attach(MIMEText(html, "html"))

        #: If there is an attachment (Image or File)
        if attachment:
            file = MIMEApplication(attachment)
            description = f"Size: {file_size}, Agent: {user}"
            file.add_header("File:", description)
            message.attach(file)

        with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=self.ctx) as server:
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receiver, message.as_string())

     