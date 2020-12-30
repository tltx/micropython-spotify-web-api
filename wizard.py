#!/usr/bin/env python3
import time

import click
import serial

from ampy import pyboard
from ampy.files import Files
from serial.tools import list_ports


@click.command()
def main():
    click.echo(
        """
Setup for a ESP8266 based, Micropython powered, Spotify web API utilizing, IoT device. 
There is a lot of setup ;) so let's get started!
For a new device you should go through all the steps.
"""
    )
    ports = list(list_ports.comports())
    for port in ports:
        click.echo(port)
    click.echo('')

    port = click.prompt(
        'serial port',
        type=click.Choice([p for p, _, _ in ports]),
    )
    click.echo(
        """
Erase the flash memory and write the Micropython with Spotify web API firmware.
(WiFi and Spotify credentials will be lost)
"""
    )
    if click.confirm('Erase and flash firmware?'):
        import esptool

        esptool.main(['--port', port, 'erase_flash'])
        esptool.main(
            [
                '--port',
                port,
                '--baud',
                '460800',
                'write_flash',
                '--flash_size',
                'detect',
                '0',
                'spotify_web_api_micropython.bin',
            ]
        )
        serial.Serial(port).close()
        click.echo('\n')

    if click.confirm('Transfer application code (main.py)?'):
        pyb = pyboard.Pyboard(port)
        files = Files(pyb)
        with open('main.py') as main_file:
            main_code = main_file.read()
            files.put('main.py', main_code.encode())
        pyb.close()

    if click.confirm('Updated WiFi settings (transfer boot.py)?'):
        ssid = click.prompt('SSID')
        password = click.prompt('password')
        pyb = pyboard.Pyboard(port)
        files = Files(pyb)
        with open('boot.py') as boot_file:
            boot_code = boot_file.read()
            boot_code = boot_code.replace('<SSID>', ssid)
            boot_code = boot_code.replace('<password>', password)
            files.put('boot.py', boot_code.encode())
        pyb.close()

    if click.confirm('Setup Spotify web API credentials?'):
        pyb = pyboard.Pyboard(port)
        files = Files(pyb)
        credentials_file_name = '/credentials.json'
        for file_name in files.ls():
            if file_name.startswith(credentials_file_name):
                files.rm(credentials_file_name)
                break
        pyb.close()

        ser = serial.Serial(port, 115200, timeout=10)
        ser.write(b'\r\x03\x03\x04')  # soft reboot
        url = None
        while True:
            line = ser.readline()
            if not line:
                break
            _, match, url = line.partition(b'Listening, connect your browser to')
            if match:
                url = url.decode().strip()
                time.sleep(5)
                click.echo('\nContinue setup in the browser {}'.format(url))
                click.launch(url)
                break
        if not url:
            click.echo('\nFailed to fetch url for the next part of the setup')


if __name__ == '__main__':
    main()
