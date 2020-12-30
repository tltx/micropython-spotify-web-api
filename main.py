import time

import machine

from spotify_web_api import (
    spotify_client,
    SpotifyWebApiError,
)


def run(button):
    print("Running")
    spotify = spotify_client()
    while True:
        try:
            if not button.value():
                time.sleep(0.3)
                if button.value():
                    print("Play: Seagulls! Stop it now!")
                    spotify.play(uris=["spotify:track:471sXvN5C5vfMSBdKrGpo7"])
                else:
                    print("Pause")
                    spotify.pause()
                while not button.value():
                    time.sleep(0.1)
            time.sleep(0.05)
        except SpotifyWebApiError as e:
            print('Error: {}, Reason: {}'.format(e, e.reason))


def main():
    print("\033c")
    button = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
    run(button)


if __name__ == '__main__':
    main()
