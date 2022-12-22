from datetime import datetime


class OneshotTimer(object):

    def __init__(self, command, fire_after):
        self.command = command
        self.fire_after = fire_after

    def should_fire(self):
        return datetime.now() > self.fire_after.astimezone()
