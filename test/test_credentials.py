import os

from spotify_web_api import load_credentials


def test_device_id_can_be_none(tmp_path):
    content = """
    {
        "refresh_token": "AQD...", 
        "access_token": "BQE...", 
        "device_id": null, 
        "client_secret": "29f...", 
        "client_id": "17c..."
    }
    """
    credentials_file = tmp_path / 'credentials.json'
    credentials_file.write_text(content)
    os.chdir(tmp_path)
    credentials = load_credentials()
    assert credentials['device_id'] is None

