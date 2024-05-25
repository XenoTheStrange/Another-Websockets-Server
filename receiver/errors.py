#!/usr/bin/python3

class WebsocketError(Exception):
    def __init__(self, message, socket, data=""):
        super().__init__(message)
        self.socket = socket
        self.message = message
        if data == "":
            self.data = ""
        else:
            self.data = f": data:{data}"
