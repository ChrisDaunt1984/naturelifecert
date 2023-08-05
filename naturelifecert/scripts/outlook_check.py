import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import email
import click
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dataclasses import dataclass


@dataclass
class DonationCertCreator:
    first_name: str
    last_name: str
    amount: float
    email:  str

    def generate_pdf(self):
        return 'path_to_pdf'
    
@dataclass
class EmailParser:
    sender: str
    subject: str
    text: str

    def extract_info(self):
        return None
    

    
def send_mail(username, password, email_address, path_to_pdf):

    # create message object instance
    msg = MIMEMultipart()

    # setup the parameters of the message
    msg['From'] = username
    msg['To'] = email_address
    msg['Subject'] = "Thank you for your donation"

    # attach the pdf file
    with open(path_to_pdf, "rb") as f:
        attach = MIMEApplication(f.read(),_subtype="pdf")
        attach.add_header('Content-Disposition','attachment',filename=path_to_pdf)
        msg.attach(attach)

    # send the message via the server.
    server = smtplib.SMTP('smtp.office365.com', 587)
    server.starttls()
    # Login Credentials for sending the mail
    server.login(username, password)

def extract_text_from_email_payload(payload):
    if isinstance(payload, list):
        # if multiple parts
        text_content = ''
        for part in payload:
            # recursively call the function to extract text from subparts
            text_content += extract_text_from_email_payload(part.get_payload())
    else:
        # decode the payload as bytes and then parse with BeautifulSoup to extract text
        try:
            # decode the payload if it's a bytes object, then parse with BeautifulSoup to extract text
            if isinstance(payload, bytes):
                payload_text = payload.decode(errors='ignore')
                soup = BeautifulSoup(payload_text, 'html.parser')
                text_content = soup.get_text()
            else:
                # If it's not bytes, it's probably already a string, so we don't need to decode.
                text_content = payload
        except Exception as e:
            # handle any exceptions that might occur during parsing
            print(f"Error extracting text from payload: {e}")
            text_content = ''
    return text_content

def extract_info_from_email(imap, mail):
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

                # print the subject and sender
                # print("Subject:", subject)
                # print("From:", sender)
        
                payload = msg.get_payload()
                text_content = extract_text_from_email_payload(payload)

                #If you have filtered your mails correctly you should be able to parse the text
                # print(text_content)

                info = EmailParser(sender=sender,
                                   subject=subject,
                                   text=text_content).extract_info()
                
                return info


@click.command()
@click.option('--username', '-n', default = 'USERNAME', help='The username of the outlook account.')
@click.option('--password', '-p', default = 'PASSWORD', help='The password to connect with')
def outlook_check(username, password):

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

        #For an example, we will look through the subject line for the words 'Welcome'
        filter_search_string = 'Welcome'
        filter_on = f'SUBJECT "{filter_search_string}"'
        unseen_only = False
        status_string = 'UNSEEN' if unseen_only else 'All'

        #Perform the search
        status, messages = imap.search(None, status_string, filter_on)
        if len(messages[0]) == 0:
            print('No new messages')
        else:
            # convert messages to a list of email IDs
            messages = messages[0].split(b' ')

            for mail in messages:
                info = extract_info_from_email(mail)
                                
                donation_creator = DonationCertCreator(first_name=info['first_name'],
                                                       last_name=info['last_name'],
                                                       amount=info['amount'],
                                                       email=info['email'])
                pdf = donation_creator.generate_pdf()

                send_mail(username=username,
                          password=password,
                          info=info['email'],
                          path_to_pdf=pdf)


        # close the mailbox and logout
        imap.close()
        imap.logout()

if __name__ == "__main__":
    outlook_check()



