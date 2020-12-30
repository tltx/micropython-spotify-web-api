import sys


if sys.implementation.name == 'micropython':
    import urequests as requests

    # noinspection PyUnresolvedReferences
    import ujson as json

    # noinspection PyShadowingBuiltins
    class FileNotFoundError(Exception):
        pass


else:
    import requests
    import json


class SpotifyWebApiClient:
    def __init__(self, session):
        self.session = session

    def play(self, context_uri=None, uris=None, offset=None, position_ms=None):
        request_body = {}
        if context_uri is not None:
            request_body['context_uri'] = context_uri
        if uris is not None:
            request_body['uris'] = list(uris)
        if offset is not None:
            request_body['offset'] = offset
        if position_ms is not None:
            request_body['position_ms'] = position_ms

        self.session.put(
            url='https://api.spotify.com/v1/me/player/play',
            json=request_body,
        )

    def pause(self):
        self.session.put(
            url='https://api.spotify.com/v1/me/player/pause',
        )

    def devices(self):
        response = self.session.get(
            url='https://api.spotify.com/v1/me/player/devices',
        )
        for device in response['devices']:
            yield Device(**device)


class Device:
    def __init__(
        self,
        id,
        is_active,
        is_private_session,
        is_restricted,
        name,
        type,
        volume_percent,
    ):
        self.id = id
        self.is_active = is_active
        self.is_private_session = is_private_session
        self.is_restricted = is_restricted
        self.name = name
        self.type = type
        self.volume_percent = volume_percent

    def __repr__(self):
        return 'Device(name={}, type={}, id={})'.format(self.name, self.type, self.id)


class Session:
    def __init__(self, credentials):
        self.credentials = credentials
        self.device_id = credentials['device_id']

    def get(self, url, **kwargs):
        def get_request():
            return requests.get(
                url,
                headers=self._headers(),
                **kwargs,
            )

        return self._execute_request(get_request)

    def put(self, url, json=None, **kwargs):
        # Workaround for urequests not sending "Content-Length" on empty data
        if json is None:
            json = {}

        def put_request():
            return requests.put(
                url=self._add_device_id(url),
                headers=self._headers(),
                json=json,
                **kwargs,
            )

        return self._execute_request(put_request)

    def _headers(self):
        return {'Authorization': 'Bearer {access_token}'.format(**self.credentials)}

    def _execute_request(self, request):
        response = request()

        if response.status_code == 401:
            error = Session._error_from_response(response)

            if error['message'] == 'The access token expired':
                self._refresh_access_token()
                response = request()  # Retry

        self._check_status_code(response)

        if response.content:
            return response.json()

    @staticmethod
    def _check_status_code(response):
        if response.status_code >= 400:
            error = Session._error_from_response(response)
            raise SpotifyWebApiError(**error)

    @staticmethod
    def _error_from_response(response):
        try:
            error = response.json()['error']
            message = error['message']
            reason = error.get('reason')
        except (ValueError, KeyError):
            message = response.text
            reason = None
        return {'message': message, 'status': response.status_code, 'reason': reason}

    def _add_device_id(self, url):
        return '{path}?device_id={device_id}'.format(path=url, device_id=self.device_id) if self.device_id else url

    def _refresh_access_token(self):
        token_endpoint = "https://accounts.spotify.com/api/token"
        params = dict(
            grant_type="refresh_token",
            refresh_token=self.credentials['refresh_token'],
            client_id=self.credentials['client_id'],
            client_secret=self.credentials['client_secret'],
        )
        response = requests.post(
            token_endpoint,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=urlencode(params),
        )
        self._check_status_code(response)

        tokens = response.json()
        self.credentials['access_token'] = tokens['access_token']
        if 'refresh_token' in tokens:
            self.credentials['refresh_token'] = tokens['refresh_token']
            save_credentials(self.credentials)


class SpotifyWebApiError(Exception):
    def __init__(self, message, status=None, reason=None):
        super().__init__(message)
        self.status = status
        self.reason = reason


def save_credentials(credentials):
    with open('credentials.json', 'w') as credentials_file:
        credentials_file.write(json.dumps(credentials))


def load_credentials():
    try:
        with open('credentials.json') as credentials_file:
            credentials = json.loads(credentials_file.read())
        assert credentials['refresh_token']
        assert credentials['client_id']
        assert credentials['client_secret']
        assert credentials['device_id']
    except (OSError, ValueError, FileNotFoundError, KeyError, AssertionError):
        return None

    return credentials


def spotify_client():
    credentials = load_credentials()
    if not credentials:
        from . import authorization_code_flow

        return authorization_code_flow.setup_wizard()
    session = Session(credentials)
    return SpotifyWebApiClient(session)


# urllib replacement


def parse_qs(qs):
    parsed_result = {}
    pairs = parse_qsl(qs)
    for name, value in pairs:
        if name in parsed_result:
            parsed_result[name].append(value)
        else:
            parsed_result[name] = [value]
    return parsed_result


def parse_qsl(qs):
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r = []
    for name_value in pairs:
        if not name_value:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            continue
        if len(nv[1]):
            name = nv[0].replace('+', ' ')
            name = unquote(name)
            value = nv[1].replace('+', ' ')
            value = unquote(value)
            r.append((name, value))
    return r


def quote(s):
    always_safe = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' 'abcdefghijklmnopqrstuvwxyz' '0123456789' '_.-'
    res = []
    for c in s:
        if c in always_safe:
            res.append(c)
            continue
        res.append('%%%x' % ord(c))
    return ''.join(res)


def quote_plus(s):
    s = quote(s)
    if ' ' in s:
        s = s.replace(' ', '+')
    return s


def unquote(s):
    res = s.split('%')
    for i in range(1, len(res)):
        item = res[i]
        try:
            res[i] = chr(int(item[:2], 16)) + item[2:]
        except ValueError:
            res[i] = '%' + item
    return "".join(res)


def unquote_plus(s):
    s = s.replace('+', ' ')
    return unquote(s)


def urlencode(query):
    if isinstance(query, dict):
        query = query.items()
    li = []
    for k, v in query:
        if not isinstance(v, list):
            v = [v]
        for value in v:
            k = quote_plus(str(k))
            v = quote_plus(str(value))
            li.append(k + '=' + v)
    return '&'.join(li)
