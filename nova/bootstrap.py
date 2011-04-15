"""
Bootstrap premailer by installing it
into the Python virtual environment.
"""
import os
import subprocess

def install():
    # Install gems into the virtual env
    os.environ['GEM_HOME'] = os.getenv('VIRTUAL_ENV')

    # Gem install premailer and nokogiri dependency
    args = ['gem', 'install', 'premailer', 'nokogiri']
    subprocess.call(args)
