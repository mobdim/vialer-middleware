import datetime
import os
from time import time
from urllib.parse import urljoin

from django.conf import settings

from apns_clerk import Session, APNs, Message
from gcm.gcm import GCM, GCMAuthenticationException
from pyfcm import FCMNotification
from pyfcm.errors import AuthenticationError, InternalPackageError, FCMServerError

from app.utils import log_middleware_information, WARNING, INFO, EXCEPTION, ERROR
from .models import APNS_PLATFORM, GCM_PLATFORM, ANDROID_PLATFORM


TYPE_CALL = 'call'
TYPE_MESSAGE = 'message'


def send_call_message(device, unique_key, phonenumber, caller_id, attempt):
    """
    Function to send the call push notification.

    Args:
        device (Device): A Device object.
        unique_key (string): String with the unique_key.
        phonenumber (string): Phonenumber that is calling.
        caller_id (string): ID of the caller.
    """
    data = {
        'unique_key': unique_key,
        'phonenumber': phonenumber,
        'caller_id': caller_id,
        'attempt': attempt,
    }
    if device.app.platform == APNS_PLATFORM:
        send_apns_message(device, device.app, TYPE_CALL, data)
    elif device.app.platform == GCM_PLATFORM:
        send_gcm_message(device, device.app, TYPE_CALL, data)
    elif device.app.platform == ANDROID_PLATFORM:
        send_fcm_message(device, device.app, TYPE_CALL, data)
    else:
        log_middleware_information(
            '{0} | Trying to sent \'call\' notification to unknown platform:{1} device:{2}'.format(
                unique_key,
                device.app.platform,
                device.token,
            ),
            WARNING,
            device=device,
        )


def send_text_message(device, app, message):
    """
    Function to send a push notification with a message.

    Args:
        device (Device): A Device object.
        message (string): The message that needs to be send to the device.
    """
    if app.platform == APNS_PLATFORM:
        send_apns_message(device, app, TYPE_MESSAGE, {'message': message})
    elif app.platform == GCM_PLATFORM:
        send_gcm_message(device, app, TYPE_MESSAGE, {'message': message})
    elif app.platform == ANDROID_PLATFORM:
        send_fcm_message(device, app, TYPE_MESSAGE, {'message': message})
    else:
        log_middleware_information(
            'Trying to sent \'message\' notification to unknown platform:{0} device:{1}'.format(
                app.platform,
                device.token,
            ),
            WARNING,
            device=device,
        )


def get_call_push_payload(unique_key, phonenumber, caller_id):
    """
    Function to create a dict used in the call push notification.

    Args:
        unique_key (string): The unique_key for the call.
        phonenumber (string): The phonenumber that is calling.
        caller_id (string): ID of the caller.

    Returns:
        dict: A dictionary with the following keys:
                type
                unique_key
                phonenumber
                caller_id
                response_api
                message_start_time
    """
    response_url = urljoin(settings.APP_API_URL, 'api/call-response/')

    payload = {
        'type': TYPE_CALL,
        'unique_key': unique_key,
        'phonenumber': phonenumber,
        'caller_id': caller_id,
        'response_api': response_url,
        'message_start_time': time(),
    }
    return payload


def get_message_push_payload(message):
    """
    Function to create a dict used in the message push notification.

    Args:
        message (string): The message send in the notification.

    Returns:
        dict: A dictionary with the following keys:
                type
                message
    """
    payload = {
        'type': TYPE_MESSAGE,
        'message': message,
    }
    return payload


def send_apns_message(device, app, message_type, data=None):
    """
    Send an Apple Push Notification message.
    """
    token_list = [device.token]
    unique_key = device.token

    if message_type == TYPE_CALL:
        unique_key = data['unique_key']
        message = Message(token_list, payload=get_call_push_payload(unique_key, data['phonenumber'],
                                                                    data['caller_id']))
    elif message_type == TYPE_MESSAGE:
        message = Message(token_list, payload=get_message_push_payload(data['message']))
    else:
        log_middleware_information(
            '{0} | TRYING TO SENT MESSAGE OF UNKNOWN TYPE: {1}'.format(
                unique_key,
                message_type,
            ),
            WARNING,
            device=device,
        )

    session = Session()

    push_mode = settings.APNS_PRODUCTION
    if device.sandbox:
        # Sandbox push mode.
        push_mode = settings.APNS_SANDBOX

    full_cert_path = os.path.join(settings.CERT_DIR, app.push_key)

    con = session.get_connection(push_mode, cert_file=full_cert_path)
    srv = APNs(con)

    try:
        log_middleware_information(
            '{0} | Sending APNS \'{1}\' message at time:{2} to {3} Data:{4}'.format(
                unique_key,
                message_type,
                datetime.datetime.fromtimestamp(time()).strftime('%H:%M:%S.%f'),
                device.token,
                data,
            ),
            INFO,
            device=device,
        )
        res = srv.send(message)

    except Exception:
        log_middleware_information(
            '{0} | Error sending APNS message'.format(unique_key),
            EXCEPTION,
            device=device,
        )

    else:
        # Check failures. Check codes in APNs reference docs.
        for token, reason in res.failed.items():
            code, errmsg = reason
            # According to APNs protocol the token reported here
            # is garbage (invalid or empty), stop using and remove it.
            log_middleware_information(
                '{0} | Sending APNS message failed for device: {1}, reason: {2}'.format(
                    unique_key,
                    token,
                    errmsg,
                ),
                WARNING,
                device=device,
            )

        # Check failures not related to devices.
        for code, errmsg in res.errors:
            log_middleware_information(
                '{0} | Error sending APNS message. \'{1}\''.format(
                    unique_key,
                    errmsg,
                ),
                WARNING,
                device=device,
            )

        # Check if there are tokens that can be retried.
        if res.needs_retry():
            log_middleware_information(
                '{0} | Could not sent APNS message, retrying...',
                INFO,
                device=device,
            )
            # Repeat with retry_message or reschedule your task.
            res.retry()


def send_fcm_message(device, app, message_type, data=None):
    """
    Function for sending a push message using firebase.
    """
    registration_id = device.token
    unique_key = device.token
    if message_type == TYPE_CALL:
        unique_key = data['unique_key']
        message = get_call_push_payload(
            unique_key,
            data['phonenumber'],
            data['caller_id'],
        )
    elif message_type == TYPE_MESSAGE:
        message = get_message_push_payload(data['message'])
    else:
        log_middleware_information(
            '{0} | Trying to sent message of unknown type: {1}'.format(
                unique_key,
                message_type,
            ),
            WARNING,
            device=device,
        )

    push_service = FCMNotification(api_key=app.push_key)

    try:
        start_time = time()
        result = push_service.notify_single_device(registration_id=registration_id, data_message=message)
    except AuthenticationError:
        log_middleware_information(
            '{0} | Our Google API key was rejected!!!'.format(unique_key),
            ERROR,
            device=device,
        )
    except InternalPackageError:
        log_middleware_information(
            '{0} | Bad api request made by package.'.format(unique_key),
            ERROR,
            device=device,
        )
    except FCMServerError:
        log_middleware_information(
            '{0} | FCM Server error.'.format(unique_key),
            ERROR,
            device=device,
        )
    else:
        if result.get('success'):
            log_middleware_information(
                '{0} | FCM \'{1}\' message sent at time:{2} to {3} Data:{4}'.format(
                    unique_key,
                    message_type,
                    datetime.datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f'),
                    registration_id,
                    data,
                ),
                INFO,
                device=device,
            )

        if result.get('failure'):
            log_middleware_information(
                '{0} | Should remove {1} because {2}'.format(
                    unique_key,
                    registration_id,
                    result['results'],
                ),
                WARNING,
                device=device,
            )

        if result.get('canonical_ids'):
            log_middleware_information(
                '{0} | Should replace device token {1}'.format(
                    unique_key,
                    registration_id,
                ),
                WARNING,
                device=device,
            )


def send_gcm_message(device, app, message_type, data=None):
    """
    Send a Google Cloud Messaging message.
    """
    token_list = [device.token, ]
    unique_key = device.token

    key = "%d-cycle.key" % int(time())
    if message_type == TYPE_CALL:
        unique_key = data['unique_key']
        message = get_call_push_payload(
            unique_key,
            data['phonenumber'],
            data['caller_id'],
        )
    elif message_type == TYPE_MESSAGE:
        message = get_message_push_payload(data['message'])
    else:
        log_middleware_information(
            '{0} | Trying to sent message of unknown type: {1}'.format(
                unique_key,
                message_type,
            ),
            WARNING,
            device=device,
        )

    gcm = GCM(app.push_key)

    try:
        start_time = time()
        response = gcm.json_request(
            registration_ids=token_list,
            data=message,
            collapse_key=key,
            priority='high',
        )

        success = response.get('success')
        canonical = response.get('canonical')
        errors = response.get('errors')

        if success:
            for reg_id, msg_id in success.items():
                log_middleware_information(
                    '{0} | GCM \'{1}\' message sent at time:{2} to {3} Data:{4}'.format(
                        unique_key,
                        message_type,
                        datetime.datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f'),
                        reg_id,
                        data,
                    ),
                    INFO,
                    device=device,
                )

        if canonical:
            for reg_id, new_reg_id in canonical.items():
                log_middleware_information(
                    '{0} | Should replace device token {1} with {2} in database'.format(
                        unique_key,
                        reg_id,
                        new_reg_id,
                    ),
                    WARNING,
                    device=device,
                )

        if errors:
            for err_code, reg_id in errors.items():
                log_middleware_information(
                    '{0} | Should remove {1} because {2}'.format(
                        unique_key,
                        reg_id,
                        err_code,
                    ),
                    WARNING,
                    device=device,
                )

    except GCMAuthenticationException:
        # Stop and fix your settings.
        log_middleware_information(
            '{0} | Our Google API key was rejected!!!'.format(unique_key),
            ERROR,
            device=device,
        )
    except ValueError:
        # Probably your extra options, such as time_to_live,
        # are invalid. Read error message for more info.
        log_middleware_information(
            '{0} | Invalid message/option or invalid GCM response'.format(unique_key),
            ERROR,
            device=device,
        )
    except Exception:
        log_middleware_information(
            '{0} | Error sending GCM message'.format(unique_key),
            EXCEPTION,
            device=device,
        )
