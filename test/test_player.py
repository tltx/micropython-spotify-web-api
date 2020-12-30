import pytest

from spotify_web_api import (
    Session,
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


@pytest.fixture
def spotify_web_api_client():
    return SpotifyWebApiClient(
        Session(
            credentials=dict(
                refresh_token='refresh_token',
                access_token='access_token',
                client_id='client_id',
                client_secret='client_secret',
                device_id=None,
            )
        )
    )


@pytest.fixture
def spotify_web_api_client_device_id():
    return SpotifyWebApiClient(
        Session(
            credentials=dict(
                refresh_token='refresh_token',
                access_token='access_token',
                client_id='client_id',
                client_secret='client_secret',
                device_id='device_id',
            )
        )
    )


def test_non_json_error(requests_mock, spotify_web_api_client):
    text = """<!DOCTYPE html>
    <html lang=en>
      <meta charset=utf-8>
      <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
      <title>Error 411 (Length Required)!!1</title>
      <a href=//www.google.com/><span id=logo aria-label=Google></span></a>
      <p><b>411.</b> <ins>That’s an error.</ins>
      <p>POST requests require a <code>Content-length</code> header.  <ins>That’s all we know.</ins>
    """
    requests_mock.put(
        'https://api.spotify.com/v1/me/player/play',
        text=text,
        status_code=411,
    )

    with pytest.raises(SpotifyWebApiError) as excinfo:
        spotify_web_api_client.play(uris=['broken_uri'])
    assert excinfo.value.status == 411
    assert str(excinfo.value) == text


def test_access_token_expired(requests_mock, spotify_web_api_client):
    current_access_token = spotify_web_api_client.session.credentials['access_token']
    new_access_token = "NgA6ZcYI...ixn8bUQ"
    assert current_access_token != new_access_token
    requests_mock.put(
        'https://api.spotify.com/v1/me/player/pause',
        status_code=401,
        json={
            "error": {
                "status": 401,
                "message": "The access token expired",
            }
        },
        request_headers={'Authorization': 'Bearer {}'.format(current_access_token)},
    )

    requests_mock.post(
        "https://accounts.spotify.com/api/token",
        status_code=200,
        json={
            "access_token": new_access_token,
            "token_type": "Bearer",
            "scope": "user-read-private user-read-email",
            "expires_in": 3600,
        },
    )
    requests_mock.put(
        'https://api.spotify.com/v1/me/player/pause',
        status_code=204,
        request_headers={'Authorization': 'Bearer {}'.format(new_access_token)},
    )
    spotify_web_api_client.pause()

    assert requests_mock.call_count == 3
    assert requests_mock.request_history[1].url == "https://accounts.spotify.com/api/token"
    assert spotify_web_api_client.session.credentials['access_token'] == new_access_token


def test_play(requests_mock, spotify_web_api_client):
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    response = spotify_web_api_client.play()
    assert response is None
    assert requests_mock.last_request.qs == {}
    assert requests_mock.last_request.text == '{}'


def test_play_device_id(requests_mock, spotify_web_api_client_device_id):
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    spotify_web_api_client_device_id.play()
    assert requests_mock.last_request.qs['device_id'] == [spotify_web_api_client_device_id.session.device_id]


def test_play_uris(requests_mock, spotify_web_api_client):
    seagulls = 'spotify:track:471sXvN5C5vfMSBdKrGpo7'
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    spotify_web_api_client.play(uris=[seagulls])
    assert requests_mock.last_request.json() == {'uris': [seagulls]}


def test_play_context_uri(requests_mock, spotify_web_api_client):
    daft_punk = 'spotify:artist:4tZwfgrHOc3mvqYlEYSvVi'
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    spotify_web_api_client.play(context_uri=daft_punk)
    assert requests_mock.last_request.json() == {'context_uri': daft_punk}


def test_play_offset(requests_mock, spotify_web_api_client):
    seagulls = 'spotify:track:471sXvN5C5vfMSBdKrGpo7'
    offset = {'position': 5}
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    spotify_web_api_client.play(uris=[seagulls], offset=offset)
    assert requests_mock.last_request.json() == {'uris': [seagulls], 'offset': offset}


def test_play_position_ms(requests_mock, spotify_web_api_client):
    seagulls = 'spotify:track:471sXvN5C5vfMSBdKrGpo7'
    position_ms = 23
    requests_mock.put('https://api.spotify.com/v1/me/player/play', status_code=204)
    spotify_web_api_client.play(uris=[seagulls], position_ms=position_ms)
    assert requests_mock.last_request.json() == {'uris': [seagulls], 'position_ms': position_ms}


def test_play_error(requests_mock, spotify_web_api_client):
    requests_mock.put(
        'https://api.spotify.com/v1/me/player/play',
        status_code=400,
        json={
            "error": {
                "status": 400,
                "message": "Invalid track uri: broken_uri",
            },
        },
    )

    with pytest.raises(SpotifyWebApiError) as excinfo:
        spotify_web_api_client.play(uris=['broken_uri'])
    assert excinfo.value.status == 400
    assert str(excinfo.value) == 'Invalid track uri: broken_uri'


def test_pause(requests_mock, spotify_web_api_client):
    requests_mock.put('https://api.spotify.com/v1/me/player/pause', status_code=204)
    response = spotify_web_api_client.pause()
    assert response is None
    assert requests_mock.last_request.qs == {}
    assert requests_mock.last_request.text == '{}'


def test_pause_device_id(requests_mock, spotify_web_api_client_device_id):
    requests_mock.put('https://api.spotify.com/v1/me/player/pause', status_code=204)
    spotify_web_api_client_device_id.pause()
    assert requests_mock.last_request.qs['device_id'] == [spotify_web_api_client_device_id.session.device_id]


def test_pause_error(requests_mock, spotify_web_api_client):
    requests_mock.put(
        'https://api.spotify.com/v1/me/player/pause',
        status_code=403,
        json={
            "error": {
                "status": 403,
                "message": "Player command failed: Restriction violated",
                "reason": "UNKNOWN",
            },
        },
    )

    with pytest.raises(SpotifyWebApiError) as excinfo:
        spotify_web_api_client.pause()
    assert excinfo.value.status == 403
    assert str(excinfo.value) == 'Player command failed: Restriction violated'
    assert excinfo.value.reason == "UNKNOWN"


def test_devices(requests_mock, spotify_web_api_client):
    device_dict = {
        "id": "5fbb3ba6aa454b5534c4ba43a8c7e8e45a63ad0e",
        "is_active": False,
        "is_private_session": True,
        "is_restricted": False,
        "name": "My fridge",
        "type": "Computer",
        "volume_percent": 100,
    }

    requests_mock.get(
        'https://api.spotify.com/v1/me/player/devices',
        status_code=200,
        json={"devices": [device_dict]},
    )

    for device in spotify_web_api_client.devices():
        assert device.id == device_dict["id"]
        assert device.is_active == device_dict["is_active"]
        assert device.is_private_session == device_dict["is_private_session"]
        assert device.is_restricted == device_dict["is_restricted"]
        assert device.name == device_dict["name"]
        assert device.type == device_dict["type"]
        assert device.volume_percent == device_dict["volume_percent"]

    assert requests_mock.last_request.qs == {}
    assert requests_mock.last_request.text is None


#
