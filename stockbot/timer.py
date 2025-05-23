from datetime import datetime


class OneshotTimer(object):

    seconds_slack = 300

    def __init__(self, command, fire_after):
        self.command = command
        self.fire_after = fire_after
        self.fire_after_epoch = self.fire_after.astimezone().timestamp() + self.seconds_slack
        self.identity = f"{'_'.join(self.command)}_{self.fire_after_epoch}"

    def should_fire(self):
        return datetime.now().timestamp() > self.fire_after_epoch

    def __eq__(self, other):
        if hasattr(other, "identity"):
            return self.identity == other.identity
        return False

    def __hash__(self):
        return hash(self.identity)


class OncePerDayTimer(object):

    def __init__(self, command, fire_at_hour, fire_at_minute):
        self.command = command
        self.fire_at_hour = fire_at_hour
        self.fire_at_minute = fire_at_minute
        self.identity = f"{'_'.join(self.command)}_{self.fire_at_hour}_{self.fire_at_minute}"

    def should_fire(self):
        now = datetime.now()
        return now.hour == self.fire_at_hour and now.minute == self.fire_at_minute

    def __eq__(self, other):
        if hasattr(other, "identity"):
            return self.identity == other.identity
        return False

    def __hash__(self):
        return hash(self.identity)


class OncePerHourTimer(object):

    def __init__(self, command, fire_at_minute):
        self.command = command
        self.fire_at_minute = fire_at_minute
        self.identity = f"{'_'.join(self.command)}_{self.fire_at_minute}"

    def should_fire(self):
        now = datetime.now()
        return now.minute == self.fire_at_minute

    def __eq__(self, other):
        if hasattr(other, "identity"):
            return self.identity == other.identity
        return False

    def __hash__(self):
        return hash(self.identity)
