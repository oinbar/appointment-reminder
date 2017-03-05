#Google Calendar Appiontment Reminder

A python utility that looks for events in a user's google calendar, and sends SMS or email notifications to specified users.
This is different from google's built in reminders feature, which only allows you to send an SMS reminder to yourself, or to  send email reminders only to individuals who have accepted an invite.

This is particularly useful for professional services pratctitioners (dentists, therapists, massuers, etc) who might organize their appointments in google calendar and want to send reminders to individuals about their upcomming appointments in a more rhobust manner, to avoid no-shows, cancellations, etc. Currently sms, and email are supported as the notificaiton methods, and voice calling will added in the future.


##Prerequisites:

1. A twilio account, and a twilio number. This will be used to send out sms messages.
2. A Google account which contains your calendar, and for which you have downloaded a service account authorization key.
   Steps for creating the service account can be found here: 
   https://developers.google.com/identity/protocols/OAuth2ServiceAccount.
3. A google account to act as a email broker. This can be the same account as above, but you will have to grant it unsecure 
   permissions to send emails, so you may want to use a separate account.
4. Another (optional) google account to act as an admin, which will recieve error messages. If left blank the account from #3
   will be used.


##Installation:

1. setup a linux server (using amazon linux here):
	Clone repository  
	`$ git clone https://github.com/oinbar/appointment-reminder.git`  
	Update apt-get
	`$ sudo apt-get -y update`
	Install pip
	`$ sudo apt-get -y install python-pip`
	Install python dependecies
	`$ sudo pip install httplib2 pytz python-dateutil google-api-python-client twilio`


2. Make sure you have python 2.7

3. Install the following python libraries:
	`$ pip install`  

2. Copy your google client_secret.json file into th e application dir

3. Fill in your params.json file with all the necessary information

4. Initialize the google credentials
	`$ python initialize_credentials.py --noauth_local_webserver`  
	Visit the link, and paste the code.

5. Authorize your gmail broker account to enable less secure apps:  
	The application will use this account to send out email notifications.  
	a. log in to the google account  
	b. go to https://www.google.com/settings/security/lesssecureapps  

6. Run the application as a cronjob. By default the application will look for the next 10 events.\n
	crontab -e  
	add the following line (to run hourly): 
		`$ 0 * * * * python /path/to/application.py`
	save and close the file (check cronjob is registered with cronjob -l)  

##Usage:

Google calendar has no formal UI to house the parameters necessary for this application. So, the event description field must be used instead, where "pseudo json" will be the accepted format. A single reminders to be placed in the description field should look something like this (curly braces included, no quotes):

`{  
	hours: 24,  
	sms: (XXX)XXX-XXXX,  
	email: johnsmith@myemail.com,  
}`

The application will then parse the description for such "json" objects, where each object serves as a single reminder to be triggered once at the number of hours specified before the event's start time. If an email address is present, an email will be sent, and if an sms number is present an sms will be sent. To send multiple notifications (such as at different times) simply add additional json objects with the desired parameters.

TODO add calling
TODO dont overwrite entire description...

