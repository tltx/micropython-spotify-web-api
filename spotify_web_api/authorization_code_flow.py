import sys

from . import (
    parse_qs,
    save_credentials,
    Session,
    SpotifyWebApiClient,
    urlencode,
)

if sys.implementation.name == 'micropython':
    # noinspection PyUnresolvedReferences
    import usocket as socket

    # noinspection PyUnresolvedReferences
    import urequests as requests


else:
    import socket
    import requests


INITIAL_RESPONSE_TEMPLATE = """\
HTTP/1.0 200 OK
Content-Type: text/html

<h1>Authenticate with Spotify</h1>
1) Go to <a target="_blank" href="https://developer.spotify.com/dashboard/applications">Spotify for Developers</a> and "Create an app"<br>
2) Edit Settings on the app, add "{redirect_uri}" as a Redirect URI and Save<br>
3) Enter Client ID below, submit and then allow the scopes for the app.<br><br>

<form action="/auth-request" method="post">
    client_id: <input type="text" name="client_id" size="34" value="{default_client_id}"><br><br>
    client_secret: <input type="text" name="client_secret" size="34" value="{default_client_secret}"><br><br>
    <input type="submit" value="Submit">
</form>
"""


SELECT_DEVICE_TEMPLATE = """\
HTTP/1.0 200 OK
Content-Type: text/html

<h1>Select device</h1>

<form action="/select-device" method="post">
    {device_list}
    <input type="submit" value="Submit">
</form>
"""


AUTH_REDIRECT_TEMPLATE = """\
HTTP/1.0 302 Found
Location: {url}
"""

NOT_FOUND = """\
HTTP/1.0 404 NOT FOUND

"""

DONE_RESPONSE = """\
HTTP/1.0 200 OK
Content-Type: text/html

Setup completed successfully!
"""


def setup_wizard(default_client_id='', default_client_secret='', default_device_id=''):
    micropython_optimize = sys.implementation.name == 'micropython'
    s = socket.socket()

    # Binding to all interfaces - server will be accessible to other hosts!
    ai = socket.getaddrinfo("0.0.0.0", 8080)
    addr = ai[0][-1]

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    print("Listening, connect your browser to http://{myip}:8080/".format(myip=myip()))

    redirect_uri = None
    client_id = None
    client_secret = None
    credentials = None
    device_selected = False
    spotify_client = None

    while not device_selected:
        client_sock, _ = s.accept()

        if micropython_optimize:
            client_stream = client_sock
        else:
            client_stream = client_sock.makefile("rwb")

        req = client_stream.readline().decode()
        content_length = None

        while True:
            h = client_stream.readline().decode()
            if h.startswith("Host: "):
                host = h[6:-2]
                redirect_uri = 'http://{host}/auth-response/'.format(host=host)
            if h.startswith("Content-Length: "):
                content_length = int(h[16:-2])
            if h == "" or h == "\r\n":
                break

        def write_response(resp):
            client_stream.write(resp.encode())
            client_stream.close()
            if not micropython_optimize:
                client_sock.close()

        if req.startswith("GET / "):
            write_response(
                INITIAL_RESPONSE_TEMPLATE.format(
                    redirect_uri=redirect_uri,
                    default_client_id=default_client_id,
                    default_client_secret=default_client_secret,
                )
            )

        elif req.startswith("POST /auth-request"):
            authorization_endpoint = 'https://accounts.spotify.com/authorize'
            form_values = parse_qs(client_stream.read(content_length).decode())
            client_id = form_values['client_id'][0]
            client_secret = form_values['client_secret'][0]
            params = dict(
                client_id=client_id,
                response_type='code',
                redirect_uri=redirect_uri,
                scope='user-read-playback-state user-modify-playback-state',
            )
            url = "{path}?{query}".format(path=authorization_endpoint, query=urlencode(params))
            write_response(AUTH_REDIRECT_TEMPLATE.format(url=url))

        elif req.startswith("GET /auth-response"):
            authorization_code = parse_qs(req[4:-11].split('?')[1])['code'][0]
            credentials = refresh_token(authorization_code, redirect_uri, client_id, client_secret)
            spotify_client = SpotifyWebApiClient(Session(credentials))
            template = """<input type="radio" name="device_id" value="{id}" {checked}> {name}<br>"""
            device_list_html = [
                template.format(id='', checked='checked' if not default_device_id else '', name='All devices')
            ]
            for device in spotify_client.devices():
                checked = 'checked' if device.id == default_device_id else ''
                device_list_html.append(template.format(id=device.id, checked=checked, name=device.name))
            write_response(SELECT_DEVICE_TEMPLATE.format(device_list=''.join(device_list_html)))

        elif req.startswith("POST /select-device"):
            response = client_stream.read(content_length).decode()
            device_id = parse_qs(response).get('device_id')
            if device_id:
                device_id = device_id[0]
            credentials['device_id'] = device_id
            spotify_client.session.device_id = device_id
            write_response(DONE_RESPONSE)
            device_selected = True
        else:
            write_response(NOT_FOUND)

    save_credentials(credentials)
    return spotify_client


def refresh_token(authorization_code, redirect_uri, client_id, client_secret):
    params = dict(
        grant_type="authorization_code",
        code=authorization_code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret,
    )

    access_token_endpoint = "https://accounts.spotify.com/api/token"
    response = requests.post(
        access_token_endpoint,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=urlencode(params),
    )
    tokens = response.json()
    return dict(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        client_id=client_id,
        client_secret=client_secret,
        device_id=None,
    )


def myip():
    if sys.implementation.name == 'micropython':
        try:
            import network

            return network.WLAN(network.STA_IF).ifconfig()[0]
        except ImportError:
            return "<my host>"
    else:
        return (
            (
                [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
                or [
                    [
                        (s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close())
                        for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
                    ][0][1]
                ]
            )
            + ["no IP found"]
        )[0]
