#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains a Flask server to keep the Replit environment alive
using UptimeRobot or a similar service.
"""

from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    """Render the home page showing the bot is alive"""
    return "Bot is running!"

def run():
    """Run the Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Start the Flask server in a separate thread to keep the Replit alive"""
    t = Thread(target=run)
    t.daemon = True  # Allow the thread to be terminated when the main program ends
    t.start()