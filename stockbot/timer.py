from datetime import datetime


class OneshotTimer(object):

    seconds_slack = 300

    def __init__(self, command, fire_after):
        self.command = command
        self.fire_after = fire_after

    def should_fire(self):
        return datetime.now().timestamp() > (self.fire_after.astimezone().timestamp() + self.seconds_slack)
