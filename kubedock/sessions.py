
# KuberDock - is a platform that allows users to run applications using Docker
# container images and create SaaS / PaaS based on these applications.
# Copyright (C) 2017 Cloud Linux INC
#
# This file is part of KuberDock.
#
# KuberDock is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# KuberDock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with KuberDock; if not, see <http://www.gnu.org/licenses/>.

from itsdangerous import (JSONWebSignatureSerializer as FallbackSerializer,
                          TimedJSONWebSignatureSerializer as Serializer,
                          SignatureExpired)

from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin
from flask import current_app, _request_ctx_stack
from uuid import uuid4

from .users.models import SessionData
from .users.signals import user_logged_in
from .billing.models import Package
from .kapi.users import UserCollection, User
from .system_settings.models import SystemSettings
from .core import db, ConnectionPool
from .login import create_identifier, get_remote_addr
from .utils import randstr
from .validation.validators import V


def get_secret_key():
    return (SystemSettings.get_by_name('sso_secret_key') or
            current_app.config.get('SECRET_KEY'))


def create_token(session):
    if getattr(session, 'sid', None) is None:
        return
    secret = get_secret_key()
    lifetime = current_app.config.get('SESSION_LIFETIME')
    s = Serializer(secret, lifetime)
    token = s.dumps(dict(dict(session), sid=session.sid))
    return token.decode('ascii')


def add_and_auth_user(data):
    username = data.get('username')
    if username is not None:
        user = User.query.filter(User.username_iequal(username)).first()
        if user is None:
            if 'package' not in data:
                pkgid = data.pop('pkgid', None)
                if pkgid is None:
                    data['package'] = Package.get_default().name
                else:
                    package = Package.query.get(int(pkgid))
                    if package is None:
                        package = Package.get_default()
                    data['package'] = package.name
            if 'rolename' not in data:
                data['rolename'] = 'User'
            if 'password' not in data:
                data['password'] = randstr(20, secure=True)
            if 'email' not in data and V().validate(
                    {'email': username}, {'email': {'type': 'email'}}):
                data['email'] = username
            if 'active' not in data:
                data['active'] = True
            user = UserCollection().create(data, return_object=True)
    sid = str(uuid4())
    session_data = {
        'user_id': user.id,
        '_fresh': True,
        '_id': create_identifier()}
    current_app.login_manager.adder_callback(sid, user.id, user.role_id)
    _request_ctx_stack.top.user = user
    user_logged_in.send((user.id, get_remote_addr()))
    return ManagedSession(sid=sid, initial=session_data)


class FakeSessionInterface(SessionInterface):
    def open_session(self, app, req):
        pass

    def save_session(self, app, sess, res):
        pass


class ManagedSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=True):
        def on_update(self):
            self.modified = True

        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class SessionManager(object):
    def new_session(self):
        """Creates a new session"""
        raise NotImplemented

    def exists(self, sid):
        """Does the given session exists"""
        raise NotImplemented

    def remove(self, sid):
        """Remove the session"""
        raise NotImplemented

    def get(self, sid, digest):
        """Retrieve a managed session by session-id,
        checking the HMAC digest"""
        raise NotImplemented

    def put(self, session):
        """Store a managed session"""
        raise NotImplemented


class ManagedSessionInterface(SessionInterface):
    def __init__(self, manager, time_delta):
        self.manager = manager
        self.time_delta = time_delta

    def open_session(self, app, request):
        token = request.headers.get('X-Auth-Token', request.args.get('token2'))
        if not token:   # new unauthorized request
            return self.manager.new_session()
        secret = get_secret_key()
        lifetime = current_app.config.get('SESSION_LIFETIME')
        try:
            s = Serializer(secret, lifetime)
            data = s.loads(token)
            return self.manager.get(data, token)
        except SignatureExpired:
            try:
                s = FallbackSerializer(secret)
                data = s.loads(token)
                self.manager.remove(data.get('sid'))
            except Exception:
                return self.manager.new_session()
        except Exception:
            return self.manager.new_session()

    def save_session(self, app, session, response):
        if session.sid is None:
            return
        if not session:
            self.manager.remove(sid=session.sid)
            return
        user_id = session.get('user_id')
        if user_id is None:
            return
        if 'X-Auth-Token' not in response.headers:
            response.headers['X-Auth-Token'] = create_token(session)


class DataBaseSessionManager(SessionManager):

    def remove(self, sid=None):
        if not sid:
            return
        saved = db.session.query(SessionData).get(sid)
        print 'Removing sid:{0}'.format(sid)
        if saved is not None:
            db.session.delete(saved)
            db.session.commit()

    def new_session(self):
        return ManagedSession()

    def get(self, data, token=None, key="USED_TOKENS"):
        sid = data.pop('sid', None)
        if sid is None:
            if data.pop('auth', None):
                conn = ConnectionPool.get_connection()
                if conn.hexists(key, token):
                    return self.new_session()
                conn.hset(key, token, 1)
                return add_and_auth_user(data)
            return self.new_session()
        saved = SessionData.query.get(sid)
        if saved is None:
            return self.new_session()
        return ManagedSession(sid=sid, initial=data)
