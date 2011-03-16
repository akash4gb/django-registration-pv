from django import forms
from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template import RequestContext

from jquery.ajax import validation_error_message
from emailverification.utils import send_email_verification

from settings import APP_NICE_SHORT_NAME

try:
	import recaptcha.client.captcha
	from settings import RECAPTCHA_PUBLIC_KEY, RECAPTCHA_PRIVATE_KEY
	has_recaptcha = True
except:
	has_recaptcha = False

def captcha_html(error = None):
	if not has_recaptcha: return ""
	return recaptcha.client.captcha.displayhtml(RECAPTCHA_PUBLIC_KEY, error = error, use_ssl=True)

def validate_captcha(request):
	if not has_recaptcha: return
	# This may have to be the last check in a form because if the captcha succeeds, the user
	# cannot resubmit without a new captcha.
	try:
		cx = recaptcha.client.captcha.submit(request.POST["recaptcha_challenge_field"], request.POST["recaptcha_response_field"], RECAPTCHA_PRIVATE_KEY, request.META["REMOTE_ADDR"])
	except Exception, e:
		raise forms.ValidationError("There was an error processing the CAPTCHA.")
	if not cx.is_valid:
		e = forms.ValidationError("Please try the two reCAPTCHA words again. If you have trouble recognizing the words, try clicking the new challenge button to get a new pair of words to type.")
		e.recaptcha_error = cx.error_code
		raise e

def validate_username(value, skip_if_this_user=None, for_login=False, fielderrors=None):
	try:
		value = forms.CharField(min_length=4 if not for_login else None, error_messages = {'min_length': "The username is too short. Usernames must be at least four characters."}).clean(value) # raises ValidationException
		if " " in value:
			raise forms.ValidationError("Usernames cannot contain spaces.")
		if "@" in value:
			raise forms.ValidationError("Usernames cannot contain the @-sign.")
			
		if not for_login:
			users = User.objects.filter(username = value)
			if len(users) > 0 and users[0] != skip_if_this_user:
				raise forms.ValidationError("The username is already taken.")
			
		return value
	except forms.ValidationError, e:
		if fielderrors == None:
			e.source_field = "username"
			raise e
		else:
			fielderrors["username"] = validation_error_message(e)
			return value
	
def validate_password(value, fielderrors=None):
	try:
		value = forms.CharField(min_length=5, error_messages = {'min_length': "The password is too short. It must be at least five characters."}).clean(value)
		if " " in value:
			raise forms.ValidationError("Passwords cannot contain spaces.")	
		return value
	except forms.ValidationError, e:
		if fielderrors == None:
			e.source_field = "password"
			raise e
		else:
			fielderrors["password"] = validation_error_message(e)
			return value
		
def validate_email(value, skip_if_this_user=None, for_login=False, fielderrors=None):
	try:
		value = forms.EmailField(max_length = 75, error_messages = {'max_length': "Email addresses on this site can have at most 75 characters."}).clean(value) # Django's auth_user table has email as varchar(75)
		if not for_login:
			users = User.objects.filter(email = value)
			if len(users) > 0 and users[0] != skip_if_this_user:
				raise forms.ValidationError("If that's your email address, it looks like you're already registered. You can try logging in instead.")
		return value
	except forms.ValidationError, e:
		if fielderrors == None:
			e.source_field = "email"
			raise e
		else:
			fielderrors["email"] = validation_error_message(e)
			return value

class ChangeEmailAddressAction:
	user = None
	newemail = None
	
	def email_subject(self):
		return APP_NICE_SHORT_NAME + ": Verify Your New Address"
	def email_body(self):
		return """To change your """ + APP_NICE_SHORT_NAME + """ account's email address to this address,
please complete the verification by following this link:

<URL>

All the best,

""" + APP_NICE_SHORT_NAME + """
"""

	def get_response(self, request, vrec):
		self.user.email = self.newemail
		self.user.save()
		return render_to_response('registration/email_change_complete.html', context_instance=RequestContext(request))

def change_email_address(user, newaddress):
	axn = ChangeEmailAddressAction()
	axn.user = user
	axn.newemail = newaddress
	send_email_verification(newaddress, None, axn)

