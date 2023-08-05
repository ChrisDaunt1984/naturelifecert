import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import click
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dataclasses import dataclass


@dataclass
class DonationCertCreator:
    """
    A class to generate a donation certificate.

    Args:
        first_name (str): The first name of the donor.
        last_name (str): The last name of the donor.
        amount (float): The amount donated.
        email (str): The email address of the donor.

    Attributes:
        first_name (str): The first name of the donor.
        last_name (str): The last name of the donor.
        amount (float): The amount donated.
        email (str): The email address of the donor.
    """
    first_name: str
    last_name: str
    amount: float
    email: str

    def generate_pdf(self) -> str:
        """
        Generate a PDF of the donation certificate.

        Returns:
            str: The path to the PDF file.
        """
        return 'path_to_pdf'


@dataclass
class EmailParser:
    """
    A class to parse an email and extract information from it.

    Args:
        sender (str): The email sender.
        subject (str): The email subject.
        text (str): The email text.

    Attributes:
        sender (str): The email sender.
        subject (str): The email subject.
        text (str): The email text.
    """
    sender: str
    subject: str
    text: str

    def extract_info(self) -> dict:
        """
        Extract information from the email.

        Returns:
            dict: A dictionary containing the extracted information.
        """
        return None


def send_mail(username: str, password: str, email_address: str, path_to_pdf: str) -> None:
    """
    Send a thank you email with a PDF attachment.

    Args:
        username (str): The username of the outlook account.
        password (str): The password to connect with.
        email_address (str): The email address of the recipient.
        path_to_pdf (str): The path to the PDF file to attach.
    """
    # create message object instance
    msg = MIMEMultipart()

    # setup the parameters of the message
    msg['From'] = username
    msg['To'] = email_address
    msg['Subject'] = "Thank you for your donation"

    # attach the pdf file
    with open(path_to_pdf, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=path_to_pdf)
        msg.attach(attach)

    # send the message via the server.
    server = smtplib.SMTP('smtp.office365.com', 587)
    server.starttls()
    # Login Credentials for sending the mail
    server.login(username, password)

    # send the message via the server.
    server.sendmail(username, email_address, msg.as_string())

    # terminating the session
    server.quit()

def extract_text_from_email_payload(payload: str) -> str:
    """
    Extract text from an email payload.

    Args:
        payload (str): The email payload.

    Returns:
        str: The extracted text.
    """
    if isinstance(payload, list):
        # if multiple parts, recursively call the function on each part
        text_content = ''.join(extract_text_from_email_payload(part.get_payload()) for part in payload)
    else:
        # decode the payload as bytes and then parse with BeautifulSoup to extract text
        try:
            # decode the payload if it's a bytes object, then parse with BeautifulSoup to extract text
            if isinstance(payload, bytes):
                payload_text = payload.decode(errors='ignore')
                soup = BeautifulSoup(payload_text, 'html.parser')
                text_content = soup.get_text()
            else:
                # if it's not bytes, it's probably already a string, so we don't need to decode
                text_content = payload
        except Exception as e:
            # handle any exceptions that might occur during parsing
            print(f"Error extracting text from payload: {e}")
            text_content = ''
    return text_content


def extract_info_from_email(imap, mail) -> dict:
    """
    Extract information from an email.

    Args:
        imap (imaplib.IMAP4): The IMAP4 object.
        mail (bytes): The email ID.

    Returns:
        dict: A dictionary containing the extracted information.
    """
    # fetch the email message by ID
    res, msg = imap.fetch(mail, "(RFC822)")

    for response in msg:
        if isinstance(response, tuple):
            # parse a bytes email into a message object
            msg = email.message_from_bytes(response[1])

            # decode the email subject and sender
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                # if it's a bytes type, decode to str
                subject = subject.decode()
            sender = decode_header(msg["From"])[0][0]
            if isinstance(sender, bytes):
                # if it's a bytes type, decode to str
                sender = sender.decode()

            # extract text from the email payload
            payload = msg.get_payload()
            text_content = extract_text_from_email_payload(payload)

            # extract information from the email using the EmailParser class
            info = EmailParser(sender=sender, subject=subject, text=text_content).extract_info()

            return info


@click.command()
@click.option('--username', '-n', default='USERNAME', help='The username of the outlook account.')
@click.option('--password', '-p', default='PASSWORD', help='The password to connect with')
def outlook_check(username: str, password: str) -> None:
    """
    Check for new emails in the Outlook inbox.

    Args:
        username (str): The username of the outlook account.
        password (str): The password to connect with.
    """
    # create an IMAP4 class with SSL
    imap = imaplib.IMAP4_SSL("outlook.office365.com", 993)

    try:
        # authenticate
        imap.login(f'{username}@outlook.com', password)
        status = True
    except imaplib.IMAP4.error as e:
        print(e)
        status = False

    if status:
        imap.select("inbox")

        # filter for emails with the subject line containing 'Welcome'
        filter_search_string = 'Welcome'
        filter_on = f'SUBJECT "{filter_search_string}"'
        unseen_only = True #ONLY SET TO FALSE FOR DEBUGGING, OTHERWISE YOU WILL SPAM!
        status_string = 'UNSEEN' if unseen_only else 'All'

        # perform the search
        status, messages = imap.search(None, status_string, filter_on)
        if len(messages[0]) == 0:
            print('No new messages')
        else:
            # convert messages to a list of email IDs
            messages = messages[0].split(b' ')

            for mail in messages:
                # extract information from the email
                info = extract_info_from_email(imap, mail)

                # create a donation certificate
                donation_creator = DonationCertCreator(first_name=info['first_name'],
                                                       last_name=info['last_name'],
                                                       amount=info['amount'],
                                                       email=info['email'])
                pdf = donation_creator.generate_pdf()

                # send a thank you email with the donation certificate attached
                send_mail(username=username, password=password, email_address=info['email'], path_to_pdf=pdf)

        # close the mailbox and logout
        imap.close()
        imap.logout()


if __name__ == "__main__":
    outlook_check()



