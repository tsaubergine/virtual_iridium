import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email import encoders

def sendMail(subject, text, user, recipient, password, smtp_server, attachmentFilePath):
    gmailUser = user
    gmailPassword = password

    msg = MIMEMultipart()
    msg['From'] = 'sbdservice@sbd.iridium.com'
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(text, 'plain'))

    attachment = getAttachment(attachmentFilePath)
    if attachment:
        msg.attach(attachment)

    mailServer = smtplib.SMTP(smtp_server, 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(gmailUser, gmailPassword)
    mailServer.sendmail(gmailUser, recipient, msg.as_string())
    mailServer.close()

    print('Sent email to %s' % recipient)

def getAttachment(attachmentFilePath):
    contentType, encoding = mimetypes.guess_type(attachmentFilePath)

    if contentType is None or encoding is not None:
        contentType = 'application/octet-stream'

    mainType, subType = contentType.split('/', 1)
    with open(attachmentFilePath, 'rb') as file:
        if mainType == 'text':
            attachment = MIMEText(file.read().decode(), _subtype=subType)
        elif mainType == 'image':
            attachment = MIMEImage(file.read(), _subtype=subType)
        elif mainType == 'audio':
            attachment = MIMEAudio(file.read(), _subtype=subType)
        else:
            attachment = MIMEBase(mainType, subType)
            attachment.set_payload(file.read())
            encoders.encode_base64(attachment)

        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachmentFilePath))
        return attachment
