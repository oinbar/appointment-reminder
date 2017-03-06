from __future__ import print_function
import httplib2
import os
import re
import traceback
import json
import argparse

# date stuff
import datetime
from datetime import timedelta
import pytz
import dateutil.parser # $ pip install python-dateutil

# for google cal
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.service_account import ServiceAccountCredentials

# for twilio SMS
from twilio.rest import TwilioRestClient

# for email
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRET_FILE = "client_secret.json"
APPLICATION_NAME = 'Dr-Sivan-Reminder'

PARAMS = json.load(open(os.path.dirname(os.path.realpath(__file__)) + "/params.json"))
if not PARAMS["admin_email"]:
    PARAMS["admin_email"] = PARAMS["gmail_account"]

now = datetime.datetime.now(pytz.timezone(PARAMS["time_zone"]))

    
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(
        credential_dir, 'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        print("need to initialize credentials")
    return credentials

def build_service():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)    
    return service
    
def get_events(n_events, calendar_id): 
    print('Getting %s upcomming events' % str(n_events))
    service = build_service()    
    eventsResult = service.events().list(
        calendarId=calendar_id, 
        timeMin=now.isoformat(), 
        maxResults=n_events,
        singleEvents=True,
        orderBy='startTime').execute()    
    return eventsResult

def get_event_dtime(event_item):
    s = event_item["start"]["dateTime"]
    dt = dateutil.parser.parse(s)
    return dt

def build_event_repr(event):
    s = event["summary"] + " @ " + str(get_event_dtime(event))[:19]
    return s
    
def get_hours(notification):
    print("parse hours from notification")
    keyword = "hours:"
    if "hours:" not in notification:
        print("hours not found, defaulting to 24")
        return 24
    # get the string following the keyword + ':'
    s = notification[notification.find(keyword)+len(keyword):]
    # find the first number after keyword    
    hours = re.findall(r'(\d+(\.\d+)?)', notification)[0][0]
    print("hours = %s" % hours)
    return hours
        
def get_email(notification):
    print("parse email from notification")
    keyword = "email:"
    # get the string following the keyword + ':'
    s = notification[notification.find(keyword)+len(keyword):]
    # find the first email after keyword    
    email = re.findall(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b', 
         notification)
    if email:
        email = email[0]
        print("email = %s" % email)
        return email
    else:
        print("email not found")
        return None

def get_sms_num(notification):
    print("parse email from notification")
    keyword = "sms:"
    # get the string following the keyword + ':'
    s = notification[notification.find(keyword)+len(keyword):]
    s = re.sub(r'\(|\)|\+|\.|-', '', s).strip()
    # find the first number after keyword    
    num = re.findall(r'([0-9]{8,15})', s)
    if num:
        num = num[0]
        # normalize number
        if num[:1]=='1': num = num[1:]
        print("sms num = %s" % num)
        return num
    else:
        print("sms num not found")
        return None

def get_sent_status(notification):
    print("parse sent status from notification")
    keyword = "sent:"
    # get the string following the keyword + ':'
    s = notification[notification.find(keyword)+len(keyword):]
    yes_no = re.findall(r'(yes|no)', s.lower())
    if yes_no:
        print("sent = %s" % yes_no[0])
        return yes_no[0]
    else:
        print("sent status not found, defaulting to 'no'")
        return unicode("no")

def parse_vars_from_notification(notification, keywords=["hours","email","sms","sent"]):
    print("parse vars from notification")
    d = {}
    hours = get_hours(notification)
    if hours: d["hours"] = hours
    email = get_email(notification)
    if email: d["email"] = email            
    sms = get_sms_num(notification)
    if sms: d["sms"] = sms
    sent = get_sent_status(notification)
    if sent: d["sent"] = sent
    return d

def parse_desc_from_event(event):
    try:
        print("parse description from event")
        desc = event["description"]
        assert("email:" in desc or "sms:" in desc)
        objs_raw = re.findall(r'\{((\s*?.*?)*)\}', desc)        
        objs_raw = [o[0] for o in objs_raw]
        parsed_desc = [parse_vars_from_notification(o) for o in objs_raw]
        print("parsed: " + str(parsed_desc))
        return parsed_desc
    except:
        print("No reminders found")
        return None
    
def rebuild_desc_from_parsed(parsed_desc):
    s = ""
    for parsed_reminder in parsed_desc:
        s += "{\n"
        for k,v in parsed_reminder.iteritems():
            s += str(k) + ": " + str(v) + ",\n"
        s += "}\n"
    return s

def update_reminder_as_sent(calendar_id, event, parsed_desc, parsed_reminder):    
    i = parsed_desc.index(parsed_reminder)
    event_id = event["id"]
    parsed_desc[i]["sent"] = "yes"
    
    print("update reminder: \n event: %s\n reminder: %s" % (build_event_repr(event), parsed_desc))
    updated_desc = rebuild_desc_from_parsed(parsed_desc)
    event["description"] = updated_desc
    service = build_service()
    service.events().update(calendarId=calendar_id, 
                            eventId=event_id, 
                            body=event).execute()       
    
def send_sms(to, body):
    print("send sms to %s" % to)
    if str(to)[:1]!="+1": to = "+1"+str(to)
    client = TwilioRestClient(
        PARAMS["twilio_account_sid"], PARAMS["twilio_auth_token"])
    client.messages.create(to=str(to), from_=PARAMS["twilio_number"], body=body)
    
def send_email(to_email, subj, body):
    print("send email %s to %s" % (subj, to_email))
    try:
        msg = MIMEMultipart()
        msg['From'] = APPLICATION_NAME
        msg['To'] = to_email
        msg['Subject'] = subj
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(PARAMS["gmail_account"], PARAMS["gmail_pass"])
        text = msg.as_string()
        server.sendmail(PARAMS["gmail_account"], to_email, text)
        server.quit()
    except Exception as e:
        if "SMTPAuthenticationError" in str(e):
            print("Unable to login to %s. Enable authentication from %s" % 
                  (PARAMS["gmail_account"], 
                   "https://www.google.com/settings/security/lesssecureapps"))
        print(format_exc())

def is_time_to_send(event, parsed_reminder):
    event_start = get_event_dtime(event)
    hours = parsed_reminder["hours"]
    if event_start - timedelta(hours=float(hours)) <= now: 
        return True
    else:
        return False

def should_send_reminder(event, parsed_reminder):
    print("should send reminder?")
    already_sent = True if parsed_reminder["sent"]=="yes" else False
    time_to_send = is_time_to_send(event, parsed_reminder)
    if time_to_send and not already_sent:
        print("yes, conditions are met")
        return True
    else:
        print("no, conditions not met")
        return False
    
def send_reminder(calendar_id, event, parsed_desc, parsed_reminder):    
    msg = PARAMS["base_msg"] +\
        get_event_dtime(event).ctime()\
        .replace("  ", " ").replace(" ", ", ")[:21]
    if "sms" in parsed_reminder.keys():
        send_sms(parsed_reminder["sms"], msg)        
    if "email" in parsed_reminder.keys():
        send_email(to_email=parsed_reminder["email"], subj="Appointment Reminder",body=msg)
    update_reminder_as_sent(calendar_id, event, parsed_desc, parsed_reminder)
    
def email_error_to_admin(err, admin_email, event, reminder):
    subj = "Appointment Reminder ERROR"
    body = "EVENT: %s\n REMINDER_OBJ: %s\n, ERROR: \n%s" %\
        (build_event_repr(event), str(reminder), str(err))
    send_email(admin_email, subj, body)


def main(calendar_id, n_events):
    try:
        events = get_events(n_events, calendar_id)
        for event in events["items"]:
            print("event: " + build_event_repr(event))
            parsed_desc = parse_desc_from_event(event)
            if parsed_desc:
                for parsed_reminder in parsed_desc:
                    try:
                        if should_send_reminder(event, parsed_reminder): 
                            send_reminder(calendar_id, event, parsed_desc, parsed_reminder)
                    except Exception as e:
                        err = traceback.format_exc()
                        print("Failed on event: " + build_event_repr(event))
                        print(err)
                        email_error_to_admin(
                            err, 
                            admin_email=PARAMS["admin_email"], 
                            body="EVENT: %s\n REMINDER_OBJ: %s\n, ERROR: \n%s" %\
                            (build_event_repr(event), str(reminder), str(err)))
    except Exception as e:
        err = traceback.format_exc()
        print(err)
        email_error_to_admin(
            err, 
            admin_email=PARAMS["admin_email"], 
            body="ERROR: %s" % err)

parser = argparse.ArgumentParser(prog="Python reminder app")
# parser.add_argument("-params", required=True, type=argparse.FileType('r'), help="params json")

if __name__ == "__main__":
    args = parser.parse_args()
    main(calendar_id="primary", n_events=10)