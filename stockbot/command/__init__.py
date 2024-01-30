import threading
import logging

LOGGER = logging.getLogger(__name__)


class Command(object):

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.short_name = kwargs.get('short_name', None)
        self.execute_command = kwargs.get('execute_command')
        self.expected_num_args = kwargs.get('expected_num_args', 0)
        self.help = kwargs.get('help', None)
        self.parent_command = None
        self.subcommands = []
        self.fallback_command = None

    def register(self, command):
        command.parent_command = self
        self.subcommands.append(command)

    def register_fallback(self, fallback_command):
        fallback_command.parent_command = self
        self.fallback_command = fallback_command

    def execute(self, *args, **kwargs):
        """
        Recurse the command tree, this method should be overridden when it actually should be doing something

        :param args:
        :return:
        """
        e = args[0]
        LOGGER.debug("Item: {}".format(e))
        c = [x for x in self.subcommands if x.name == e or x.short_name == e]
        if len(c) == 0:
            if self.fallback_command:
                return self.fallback_command.execute(*args[1:], **kwargs)
            return None
        return c[0].execute(*args[1:], **kwargs)

    def __repr__(self):
        help_output = [self.name]
        if self.short_name is not None:
            help_output.append("({})".format(self.short_name))
        if self.help is not None:
            help_output.append(self.help)
        return " ".join(help_output)

    def show_help(self, *args, **kwargs):
        def paths(tree):
            """took and modified https://stackoverflow.com/a/5671568"""
            root = tree
            rooted_paths = [[root]]
            for subtree in tree.subcommands:
                useable = paths(subtree)
                for path in useable:
                    if len(path[-1].subcommands) == 0:
                        rooted_paths.append([root] + path)
            return rooted_paths
        rv = []
        for c in paths(self)[1:]:
            rv.append(" ".join([str(x) for x in c[1:]]))
        return sorted(rv)

    def printable_self_help(self):
        return "Usage: {}".format(self.help)


class ProxyCommand(Command):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy_command = kwargs.get('proxy_command')

    def execute(self, *args, **kwargs):
        new_args = self.proxy_command + args
        return self.parent_command.execute(*new_args, **kwargs)


class BlockingExecuteCommand(Command):

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        cb_args = kwargs.get('callback_args', {})
        if self.expected_num_args > len(args):
            if callable(cb):
                return cb(self.printable_self_help(), **cb_args)
            else:
                return self.printable_self_help()
        if callable(self.execute_command):
            result = self.execute_command(*args, **kwargs.get('command_args'))
        else:
            raise RuntimeError("execute_command not callable")
        if callable(cb):
            return cb(result, **cb_args)
        else:
            return result


class NonBlockingExecuteCommand(Command):

    def __init__(self, *args, **kwargs):
        super(NonBlockingExecuteCommand, self).__init__(*args, **kwargs)
        self.exclusive = kwargs.get('exclusive', True)

    def execute(self, *args, **kwargs):
        cb = kwargs.get('callback', None)
        cb_args = kwargs.get('callback_args', {})
        thread_name = "thread-{}".format("_".join(args))
        if self.exclusive and self.is_already_running(thread_name):
            if callable(cb):
                return cb("Task is currently running, hold your horses")
            return "Task is currently running, hold your horses"
        if callable(self.execute_command):
            thread = CommandThread(name=thread_name, target=self.execute_command, args=args,
                                   kwargs=kwargs.get('command_args'), daemon=False)
            thread.set_callback(cb, cb_args)
            thread.start()
        else:
            raise RuntimeError("execute_command not callable")
        if callable(cb):
            return cb("Task started")
        return "Task started"

    @staticmethod
    def is_already_running(thread_name):
        return len([t for t in threading.enumerate() if t.name == thread_name]) > 0


#
# Thread wrapper
#
class CommandThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(CommandThread, self).__init__(*args, **kwargs)
        self._callback = None
        self._callback_args = {}

    def set_callback(self, cb, cb_args):
        self._callback = cb
        self._callback_args = cb_args

    def run(self):
        # block until task has finished
        result = self._target(*self._args, **self._kwargs)

        if callable(self._callback):
            self._callback(result, **self._callback_args)


root_command = Command(name="root")
root_command.register(BlockingExecuteCommand(name="help", execute_command=root_command.show_help,
                                             help="show help section"))

import stockbot.command.fundamental
import stockbot.command.quote
import stockbot.command.scrape
import stockbot.command.insider
import stockbot.command.ibindex
import stockbot.command.news
import stockbot.command.scheduler
import stockbot.command.game
import stockbot.command.chat
