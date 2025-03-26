#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    """Simple endpoint for keeping the app alive"""
    return jsonify({"status": "Bot is running"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)