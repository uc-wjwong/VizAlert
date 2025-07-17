#! python
# -*- coding: utf-8 -*-
# This is a utility module for integrating email functionality into VizAlerts.

import smtplib
import re
import os.path
import uuid
# import aspose.email as ae
from email.encoders import encode_base64

# added for MIME handling
from itertools import chain
from errno import ECONNREFUSED
from mimetypes import guess_type
from subprocess import Popen, PIPE

from io import StringIO
from email.header import Header
from email.generator import Generator
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from socket import error as SocketError

# import local modules
from . import config
from . import log
from . import vizalert

# regular expression used to split recipient address strings into separate email addresses
EMAIL_RECIP_SPLIT_REGEX = '[\t\n\s;,]'
_logged_addresses = set()
_logged_field_values = set()
_logged_field_names = set()

class Email(object):
    """Represents an email to be sent"""

    def __init__(self, fromaddr, toaddrs, subject, content, ccaddrs=None, bccaddrs=None, inlineattachments=None,
               appendattachments=None):
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.content = content
        self.ccaddrs = ccaddrs
        self.bccaddrs = bccaddrs
        self.inlineattachments = inlineattachments
        self.appendattachments = appendattachments

        # REVISIT: Should add other methods in this module to this class? Validation, at least.

# def save_eml_file(msg, directory="./sent_emails"):
#     """Save the email message as a .eml file."""
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#     filename = os.path.join(directory, f"email_{uuid.uuid4().hex}.eml")
#     with open(filename, 'w', encoding='utf-8') as f:
#         f.write(msg.as_string())
#     log.logger.info(f"Email saved to .eml file: {filename}")



def send_email(email_instance):
    """Generic function to send an email. The presumption is that all arguments have been validated prior to the call
        to this function.

    Input arguments are:
        fromaddr    single email address
        toaddr      string of recipient email addresses separated by the list of separators in EMAIL_RECIP_SPLIT_REGEX
        subject     string that is subject of email
        content     body of email, may contain HTML
        ccaddrs     cc recipients, see toaddr
        bccaddrs    bcc recipients, see toaddr
        inlineattachments   List of vizref dicts where each dict has one attachment. The minimum dict has an
                            imagepath key that points to the file to be attached.
        appendattachments   Appended (non-inline attachments). See inlineattachments for details on structure.

    Nothing is returned by this function unless there is an exception.

    """
    
    # Save .eml file
    def save_eml_file(msg, directory="/unified/roaming/extapps/vizalert/sent_emails"):
        """Save the email message as a .eml file."""
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, f"email_{uuid.uuid4().hex}.eml")
        with open(filename, 'w', encoding='utf-8') as f:
            gen = Generator(f, False)
            gen.flatten(msg)
        log.logger.info(f"Email saved to .eml file: {filename}")


    # # Change .eml to .msg file
    # def save_msg_file(eml_path, directory="/unified/roaming/extapps/vizalert/sent_emails"):
    #     """Convert an .eml file to .msg format using Aspose.Email (if available)."""
    #     if ae is None:
    #         log.logger.warning("Aspose.Email for Python via .NET not installed; skipping .msg export.")
    #         return

    #     try:
    #         if not os.path.exists(directory):
    #             os.makedirs(directory)

    #         # Load .eml using Aspose
    #         load_options = ae.EmlLoadOptions()
    #         message = ae.MailMessage.load(eml_path, load_options)

    #         # Save as .msg
    #         msg_filename = os.path.join(directory, os.path.basename(eml_path).replace(".eml", ".msg"))
    #         message.save(msg_filename, ae.SaveOptions.default_msg_unicode)

    #         log.logger.info(f"Converted .eml to .msg: {msg_filename}")
    #     except Exception as e:
    #         log.logger.error(f"Failed to convert EML to MSG: {e}")
    

    # def save_eml_file(msg, directory="/unified/roaming/extapps/vizalert/sent_emails"):
    #     """Save the email message as a .eml file compatible with Outlook and trigger .msg export."""
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)

    #     filename = os.path.join(directory, f"email_{uuid.uuid4().hex}.eml")

    #     # Save as EML using binary write
    #     with open(filename, 'wb') as f:
    #         f.write(msg.as_bytes())
    #     log.logger.info(f"Email saved to .eml file: {filename}")

    #     # Optional: convert to .msg if Aspose is available
    #     save_msg_file(filename)


    # def save_eml_file(msg, directory="./sent_emails"):
    #     """Save the email message as a .eml file compatible with Outlook."""
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)
    #     filename = os.path.join(directory, f"email_{uuid.uuid4().hex}.eml")
    #     with open(filename, 'wb') as f:
    #         f.write(msg.as_bytes())
    #     log.logger.info(f"Email saved to .eml file: {filename}")


    # # Save .mht file
    # def save_as_mht(subject, html_body, directory="./sent_emails"):
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)
    #     filename = os.path.join(directory, f"email_{uuid.uuid4().hex}.mht")
        
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         f.write("From: someone@example.com\n")
    #         f.write(f"Subject: {subject}\n")
    #         f.write("MIME-Version: 1.0\n")
    #         f.write("Content-Type: multipart/related; type=\"text/html\"; boundary=\"----=_NextPart_000_0000\"\n\n")

    #         f.write("------=_NextPart_000_0000\n")
    #         f.write("Content-Type: text/html; charset=\"utf-8\"\n")
    #         f.write("Content-Transfer-Encoding: quoted-printable\n\n")
    #         f.write(html_body)
    #         f.write("\n------=_NextPart_000_0000--")
        
    #     log.logger.info(f"Email saved to .mht file: {filename}")

    try:
        log.logger.info(
            'sending email: {},{},{},{},{},{},{}'.format(config.configs['smtp.serv'], email_instance.fromaddr,
                                                          email_instance.toaddrs, email_instance.ccaddrs,
                                                          email_instance.bccaddrs,
                                                          email_instance.subject, email_instance.inlineattachments,
                                                          email_instance.appendattachments))
        log.logger.debug('email body: {}'.format(email_instance.content))

        # using mixed type because there can be inline and non-inline attachments
        msg = MIMEMultipart('mixed')
        msg.set_charset('UTF-8')
        msg['From'] = Header(email_instance.fromaddr)
        msg['Subject'] = Header(email_instance.subject, 'utf-8')

        log.logger.debug('TO ADDRESS: {}'.format(email_instance.toaddrs))

        # Process direct recipients
        toaddrs = [address for address in filter(None, re.split(EMAIL_RECIP_SPLIT_REGEX, email_instance.toaddrs)) if len(address) > 0]
        msg['To'] = Header(', '.join(toaddrs))
        allrecips = toaddrs

        log.logger.debug('CC ADDRESS: {}'.format(email_instance.ccaddrs))

        # Process indirect recipients
        if email_instance.ccaddrs:
            ccaddrs = [address for address in filter(None, re.split(EMAIL_RECIP_SPLIT_REGEX, email_instance.ccaddrs)) if len(address) > 0]
            msg['CC'] = Header(', '.join(ccaddrs))
            allrecips.extend(ccaddrs)

        log.logger.debug('BCC ADDRESS: {}'.format(email_instance.bccaddrs))

        if email_instance.bccaddrs:
            bccaddrs = [address for address in filter(None, re.split(EMAIL_RECIP_SPLIT_REGEX, email_instance.bccaddrs)) if len(address) > 0]
            # don't add to header, they are blind carbon-copied
            allrecips.extend(bccaddrs)

        # Create a section for the body and inline attachments
        msgalternative = MIMEMultipart('related')
        msg.attach(msgalternative)
        # msg['MIME-Version'] = '1.0'
        msgalternative.attach(MIMEText(email_instance.content, 'html', 'utf-8'))

        # # Create a section for the body and inline attachments
        # msgalternative = MIMEMultipart('alternative')
        # msg.attach(msgalternative)

        # # Add plain text fallback for older clients
        # plain_text = re.sub(r'<[^>]+>', '', email_instance.content)  # crude HTML stripper
        # msgalternative.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        # msgalternative.attach(MIMEText(email_instance.content, 'html', 'utf-8'))

        # Add inline attachments
        if email_instance.inlineattachments != None:
            for vizref in email_instance.inlineattachments:
                msgalternative.attach(mimify_file(vizref['imagepath'], inline=True))

        # Add appended attachments from Email Attachments field and prevent dup custom filenames
        #  MC: Feels like this code should be in VizAlert class? Or module? Not sure, leaving it here for now
        appendedfilenames = []
        if email_instance.appendattachments != None:
            appendattachments = vizalert.merge_pdf_attachments(email_instance.appendattachments)
            for vizref in appendattachments:
                # if there is no |filename= option set then use the exported imagepath
                if 'filename' not in vizref:
                    msg.attach(mimify_file(vizref['imagepath'], inline=False))
                else:
                    # we need to make sure the custom filename is unique, if so then
                    # use the custom filename
                    if vizref['filename'] not in appendedfilenames:
                        appendedfilenames.append(vizref['filename'])
                        msg.attach(mimify_file(vizref['imagepath'], inline=False, overridename=vizref['filename']))
                    # use the exported imagepath
                    else:
                        msg.attach(mimify_file(vizref['imagepath'], inline=False))
                        log.logger.info('Warning: attempted to attach duplicate filename ' + vizref[
                            'filename'] + ', using unique auto-generated name instead.')

        # Save the email content as a .eml file
        save_eml_file(msg)

        # # Save the email content as a .mht file
        # save_as_mht(email_instance.subject, email_instance.content)

        server = smtplib.SMTP(config.configs['smtp.serv'], config.configs['smtp.port'])
        if config.configs['smtp.ssl']:
            server.ehlo()
            server.starttls()
        if config.configs['smtp.user']:
            server.login(str(config.configs['smtp.user']), str(config.configs['smtp.password']))

        # from http://wordeology.com/computer/how-to-send-good-unicode-email-with-python.html
        io = StringIO()
        g = Generator(io, False)  # second argument means "should I mangle From?"
        g.flatten(msg)
        
        server.sendmail(email_instance.fromaddr, [addr for addr in allrecips],
                        io.getvalue())
        server.quit()
    except smtplib.SMTPConnectError as e:
        log.logger.error('Email failed to send; there was an issue connecting to the SMTP server: {}'.format(e))
        raise e
    except smtplib.SMTPHeloError as e:
        log.logger.error('Email failed to send; the SMTP server refused our HELO message: {}'.format(e))
        raise e
    except smtplib.SMTPAuthenticationError as e:
        log.logger.error('Email failed to send; there was an issue authenticating to SMTP server: {}'.format(e))
        raise e
    except smtplib.SMTPException as e:
        log.logger.error('Email failed to send; there was an issue sending mail via SMTP server: {}'.format(e))
        raise e
    except Exception as e:
        log.logger.error('Email failed to send: {}'.format(e))
        raise e

def addresses_are_invalid(emailaddresses, emptystringok, regex_eval=None):
    """Validates all email addresses found in a given string, optionally that conform to the regex_eval"""
    if emailaddresses not in _logged_field_values:
        log.logger.debug('Validating email field value: {}'.format(emailaddresses))
        _logged_field_values.add(emailaddresses)
    address_list = [address for address in filter(None, re.split(EMAIL_RECIP_SPLIT_REGEX, emailaddresses)) if len(address) > 0]
    for address in address_list:
        if emailaddresses not in _logged_field_values:
            log.logger.debug('Validating presumed email address: {}'.format(address))
            _logged_field_values.add(emailaddresses)
        if emptystringok and (address == '' or address is None):
            return None
        else:
            errormessage = address_is_invalid(address, regex_eval)
            if errormessage:
                log.logger.debug('Address is invalid: {}, Error: {}'.format(address, errormessage))
                if len(address) > 64:
                    address = address[:64] + '...'  # truncate a too-long address for error formattting purposes
                return {'address': address, 'errormessage': errormessage}
    return None


def address_is_invalid(address, regex_eval=None):
    """Checks for a syntactically invalid email address."""
    # (most code derived from from http://zeth.net/archive/2008/05/03/email-syntax-check)

    # Email address must not be empty
    if address is None or len(address) == 0 or address == '':
        errormessage = 'Address is empty'
        log.logger.error(errormessage)
        return errormessage
    
    # Only log address-specific debug info once per run
    if address not in _logged_addresses:
        log.logger.debug(f'Validating address: {address}')
        _logged_addresses.add(address)
    
    # Validate address according to admin regex
    if regex_eval:
        if address not in _logged_addresses:  # avoid repeating this log
            log.logger.debug("testing address {} against regex {}".format(address, regex_eval))
        if not re.match(regex_eval, address, re.IGNORECASE):
            errormessage = 'Address must match regex pattern set by the administrator: {}'.format(regex_eval)
            log.logger.error(errormessage)
            return errormessage

    # Email address must be 6 characters in total.
    # This is not an RFC defined rule but is easy
    if len(address) < 6:
        errormessage = 'Address is too short: {}'.format(address)
        log.logger.error(errormessage)
        return errormessage

    # Unicode in addresses not yet supported
    try:
        address.encode(encoding='ascii', errors='strict')
    except Exception as e:
        errormessage = 'Address must contain only ASCII characers: {}'.format(address)
        log.logger.error(errormessage)
        return errormessage

    # Split up email address into parts.
    try:
        localpart, domainname = address.rsplit('@', 1)
        host, toplevel = domainname.rsplit('.', 1)
        if address not in _logged_addresses:
            log.logger.debug('Splitting Address: localpart, domainname, host, toplevel: {},{},{},{}'.format(localpart,
                                                                                                     domainname,
                                                                                                     host,
                                                                                                     toplevel))
    except ValueError:
        errormessage = 'Address has too few parts'
        log.logger.error(errormessage)
        return errormessage

    for i in '-_.%+.':
        localpart = localpart.replace(i, "")
    for i in '-_.':
        host = host.replace(i, "")
    
    if address not in _logged_addresses:
        log.logger.debug('Removing other characters from address: localpart, host: {},{}'.format(localpart, host))

    # check for length
    if len(localpart) > 64:
        errormessage = 'Localpart of address exceeds max length (65 characters)'
        log.logger.error(errormessage)
        return errormessage

    if len(address) > 254:
        errormessage = 'Address exceeds max length (254 characters)'
        log.logger.error(errormessage)
        return errormessage

    if localpart.isalnum() and host.isalnum():
        return None  # Email address is fine.
    else:
        errormessage = 'Address has funny characters'
        log.logger.error(errormessage)
        return errormessage


def mimify_file(filename, inline=True, overridename=None):
    """Returns an appropriate MIME object for the given file.

    :param filename: A valid path to a file
    :type filename: str

    :returns: A MIME object for the given file
    :rtype: instance of MIMEBase
    """

    filename = os.path.abspath(os.path.expanduser(filename))
    if overridename:
        basefilename = overridename
    else:
        basefilename = os.path.basename(filename)

    if inline:
        msg = MIMEBase(*get_mimetype(filename))
        msg.set_payload(open(filename, "rb").read())
        msg.add_header('Content-ID', '<{}>'.format(basefilename))
        msg.add_header('Content-Disposition', 'inline; filename="%s"' % basefilename)
    else:
        msg = MIMEBase(*get_mimetype(filename))
        msg.set_payload(open(filename, "rb").read())
        if overridename:
            basefilename = overridename

        msg.add_header('Content-Disposition', 'attachment; filename="%s"' % basefilename)

    encode_base64(msg)
    return msg


def get_mimetype(filename):
    """Returns the MIME type of the given file.

    :param filename: A valid path to a file
    :type filename: str

    :returns: The file's MIME type
    :rtype: tuple
    """
    content_type, encoding = guess_type(filename)
    if content_type is None or encoding is not None:
        content_type = "application/octet-stream"
    return content_type.split("/", 1)


def validate_addresses(vizdata,
                       allowed_from_address,
                       allowed_recipient_addresses,
                       email_action_actionfield,
                       email_to_actionfield,
                       email_from_actionfield,
                       email_cc_actionfield,
                       email_bcc_actionfield):
    """Loops through the viz data for an Advanced Alert and returns a list of dicts
        containing any errors found in recipients"""

    errorlist = []
    rownum = 2  # account for field header in CSV

    for row in vizdata:
        if len(row) > 0:
            if email_action_actionfield.get_value_from_dict(row) == '1':\

                email_to = email_to_actionfield.get_value_from_dict(row)
                # if email_from not in _logged_field_values:
                    # log.logger.debug('Validating "To" addresses: {}'.format(email_to))
                    # _logged_field_values.add(email_to)
                result = addresses_are_invalid(email_to, False, allowed_recipient_addresses)  # empty string not acceptable as a To address
                if result:
                    errorlist.append(
                        {'Row': rownum, 'Field': (email_to_actionfield.field_name if email_to_actionfield.field_name else email_to_actionfield.name),
                        'Value': result['address'], 'Error': result['errormessage']})
                
                email_from = email_from_actionfield.get_value_from_dict(row)
                # if email_from not in _logged_field_values:
                    # og.logger.debug('Validating "From" addresses: {}'.format(email_from))
                    # _logged_field_values.add(email_from)
                result = addresses_are_invalid(email_from, False, allowed_from_address)  # empty string not acceptable as a From address
                if result:
                    errorlist.append({'Row': rownum, 'Field': (email_from_actionfield.field_name if email_from_actionfield.field_name else email_from_actionfield.name),
                        'Value': result['address'], 'Error': result['errormessage']})

                # REVISIT THIS!
                if email_cc_actionfield.field_name:
                    # if email_cc_actionfield.field_name not in _logged_field_names:
                        # log.logger.debug('Validating "CC" addresses')
                        # _logged_field_names.add(email_cc_actionfield.field_name)
                    result = addresses_are_invalid(row[email_cc_actionfield.field_name], True, allowed_recipient_addresses)
                    if result:
                        errorlist.append({'Row': rownum, 'Field': email_cc_actionfield.field_name, 'Value': result['address'],
                                          'Error': result['errormessage']})
                if email_bcc_actionfield.field_name:
                    # if email_bcc_actionfield.field_name not in _logged_field_names:
                        # log.logger.debug('Validating "BCC" addresses')
                        # _logged_field_names.add(email_bcc_actionfield.field_name)
                    result = addresses_are_invalid(row[email_bcc_actionfield.field_name], True, allowed_recipient_addresses)
                    if result:
                        errorlist.append({'Row': rownum, 'Field': email_bcc_actionfield.field_name, 'Value': result['address'],
                                          'Error': result['errormessage']})
        rownum += 1

    return errorlist
