from flask import Blueprint, request, make_response, url_for, redirect
from flask import current_app as app
from Response import Response
from Services.AuthenticationService import AuthenticationService
from Models.User import User
from Models.Dataset import Dataset
from Models.Session import Session
from Services.MailService import MailService
from mongoengine import DoesNotExist
from uuid import uuid4
import google.oauth2.credentials
import requests



MailService = MailService()
AuthenticationService = AuthenticationService()

auth = Blueprint("AuthenticationController", __name__, url_prefix="/api/auth")

@auth.route("/authorize", methods=["POST"])
def authorize():
    flow = app.flow
    flow.redirect_uri = request.form["redirect_uri"]
    authCode = request.form["code"]
    flow.fetch_token(code=authCode)

    credentials = flow.credentials
    req_url = "https://www.googleapis.com/oauth2/v1/userinfo?access_token=" + credentials.token
    user_info = requests.get(req_url).json()

    user = AuthenticationService.getUser(email=user_info['email'])

    
    if user:
        if not user.password:
            sessionId = uuid4()
            session = Session(user=user, sessionId=sessionId)
            session.save()
            ret = make_response(user_info)
            ret.set_cookie("SID", str(session.sessionId), expires=session.dateExpires)
            return ret
        return Response("Email already registered with our service", status=403)
    else:
        ret = {}
        ret['message'] = "Redirect to complete sign up"
        ret['user'] = user_info
        return Response(ret, status=200)


@auth.route("/login", methods=["POST"])
def login():
    session = AuthenticationService.authenticate(request.form["email"], request.form["password"])
    if not session:
        return Response("Incorrect username or password. Please check your credentials and try again.", status=401)
    
    user = User.objects.get(email=request.form["email"])
    if not AuthenticationService.isUserConfirmed(user):
        return Response("You must confirm your account to log in.", status=403)
    
    ret = make_response("Success")
    ret.set_cookie("SID", str(session.sessionId), expires=session.dateExpires)
    return ret

@auth.route("/logout", methods=["POST"])
def logout():
    try:
        sessionId = request.form["sessionId"]
        AuthenticationService.logout(sessionId)
        return Response("Successfully logged out.", status=200)
    except:
        return Response("Unable to process request. Please reload and try again later.", status=400)


"""
Request params: first name, last name, email (will be used as username), password
Return: Success or failure codes    
"""
@auth.route("/signup", methods=["POST"])
def signup():
    user = {"firstName": request.form["firstName"],
            "lastName": request.form["lastName"],
            "email": request.form["email"],
            "password": request.form["password"],
            "organization": request.form["organization"],
            "location": request.form["location"],
            "userType": request.form["userType"]
            }
    try:
        User.objects.get(email=user["email"])
        return Response("There's already an account with the provided email.", status=400)
    except:
        try:
            AuthenticationService.signup(user)
            userConfirmationId = uuid4()
            user = User.objects.get(email=user["email"])
            if AuthenticationService.isUserConfirmed(user):
                sessionId = uuid4()
                session = Session(user=user, sessionId=sessionId)
                session.save()
                data = {"message": "Google authorized successful!", "user": user.email}
                ret = make_response(data)
                ret.set_cookie("SID", str(session.sessionId),expires=session.dateExpires)
                return ret
            AuthenticationService.setUserConfirmationId(user, userConfirmationId)
            sub = "Confirm Account"
            msg = f"<p>Congratulations, you've registered for Agriworks. Please click the link below to confirm your account.</p><p><a href=\"{app.rootUrl}/confirm-user/{userConfirmationId}\"> Confirm account </a></p>"
            MailService.sendMessage(user, sub, msg)
            return Response("Signup successful", status=200)
        except:
            return Response("Signup unsuccessful. Please try again.", status=403)

@auth.route("/resend-confirmation-email/<email>", methods=["POST"])
def resendConfirmationEmail(email):
    try:
        user = User.objects.get(email=email)
        if user.isConfirmed:
            return Response("User already confirmed.",status=403)
        newUserConfirmationId = uuid4()
        AuthenticationService.setUserConfirmationId(user, newUserConfirmationId)
        sub = "Confirm Account"
        msg = f"<p>Congratulations, you've registered for Agriworks. Please click the link below to confirm your account.</p><p><a href=\"{app.rootUrl}/confirm-user/{newUserConfirmationId}\"> Confirm account </a></p>"
        MailService.sendMessage(user, sub, msg)
        return Response("New confirmation email sent.", status=200)
    except:
        return Response("Resend confirmation email unsuccessful.", status=403)

@auth.route("/confirm-user/<userConfirmationId>", methods=["POST"])
def confirmUser(userConfirmationId):
    try:
        user = User.objects.get(confirmationId=userConfirmationId)
        AuthenticationService.setUserAsConfirmed(user)
        return Response("Account confirmed successfully. You may now login.")
    except:
        return Response("No account was found using the provided confirmation code.", status=404)

@auth.route("/forgot-password", methods=["POST"])
def forgotPassword():
    try:
        user = AuthenticationService.getUser(email=request.form["email"])
        passwordResetId = uuid4()
        AuthenticationService.setUserResetID(user, passwordResetId)
        try:
            subject = "Reset Password"
            html = f"<p>We heard you lost your password. No worries, just click the link below to reset your password.</p><p>You can safely ignore this email if you did not request a password reset</p><br/><a href=\"{app.rootUrl}/reset-password/{passwordResetId}\"> Reset password </a><br/>"
            MailService.sendMessage(user, subject, html)
            return Response("An email with instructions to reset your password has been sent to the provided email.", status=200)
        except:
            return Response("Unable to send password reset email. Please try again later.", status=400)
    except:
        return Response("No account with given email found. Please try creating a new account.", status=403)


@auth.route("/reset-password/<passwordResetId>", methods=["POST"])
def resetPassword(passwordResetId):
    try:
       user = AuthenticationService.checkUserResetID(passwordResetId)
       if ("password" not in request.form):
           return Response("Please provide a new password.", status=400)
       
       newPassword = request.form["password"]
       confirmPassword = request.form["confirmPassword"]

       if (newPassword != confirmPassword): 
           return Response("Password and Confirm Password fields must be the same", status=403)
       
       if (AuthenticationService.resetPasswordSame(user, newPassword)): 
           return Response("Please choose a password that you haven't used before", status=403)
       
       AuthenticationService.setUserResetID(user, "")
       AuthenticationService.changePassword(user.email, newPassword)
       return Response("Password sucessfully updated", status=200)
    except:
        return Response("Your password reset link is either invalid or expired. Please request a new one.", status=403)

@auth.route("/verifySession", methods=["POST"])
def verifySession():
    try:
        sessionId = request.form["sessionId"]
        if not AuthenticationService.verifySessionAndReturnUser(sessionId):
            return Response("Your session has expired. Please login again.",status=401)
        else:
            return Response(status=200)
    except DoesNotExist as e:
        return Response("Your session was not found. Please login again.",status=401)
    except ValueError as e:
        return Response("Invalid session. Please login again.", status=400)
    
@auth.route("/delete-account", methods=["POST"])
def deleteAccount():
    try:
        form = request.form #the form submitted
        SID = form["sessionId"] #gets SID from cookie
        session = AuthenticationService.getSession(SID) #uses SID to get session from db
        user = session["user"] #gets user from session

        # found user, remove their datasets
        try:
            Dataset.objects(author=user).delete()
        except:
            return Response("Error deleting datasets.",status=403)
        # once datasets have been removed, remove user from users
        try:
            # log out before deletion
            sessionId = request.form["sessionId"]
            AuthenticationService.logout(sessionId)
            # remove user with query by email
            user.delete()
        except:
            return Response("Error deleting user.", status=403)
        return Response("Account deleted.", status=200)
    except:
        return Response("Error getting user from session.", status=403)
