# Aaargh 0.4
# Taken from https://github.com/wbolster/aaargh
# BSD License per setup.py

"""
Aaargh, an astonishingly awesome application argument helper
"""

from argparse import ArgumentParser

_NO_FUNC = object()


__all__ = ['App', '__version__']

# XXX: Keep version number in sync with setup.py
__version__ = '0.4'


class App(object):
    """
    Simple command line application.

    Constructor arguments are propagated to :py:class:`ArgumentParser`.
    """

    def __init__(self, *args, **kwargs):
        self._parser = ArgumentParser(*args, **kwargs)
        self._global_args = []
        self._subparsers = self._parser.add_subparsers(title="Subcommands")
        self._pending_args = []
        self._defaults = {}

    def arg(self, *args, **kwargs):
        """Add a global application argument.

        All arguments are passed on to :py:meth:`ArgumentParser.add_argument`.
        """
        self._global_args.append((args, kwargs))
        return self._parser.add_argument(*args, **kwargs)

    def defaults(self, **kwargs):
        """Set global defaults.

        All arguments are passed on to :py:meth:`ArgumentParser.set_defaults`.
        """
        return self._parser.set_defaults(**kwargs)

    def cmd(self, _func=_NO_FUNC, name=None, *args, **kwargs):
        """Decorator to create a command line subcommand for a function.

        By default, the name of the decorated function is used as the
        name of the subcommand, but this can be overridden by specifying the
        `name` argument. Additional arguments are passed to the subcommand's
        :py:class:`ArgumentParser`.
        """
        if _func is not _NO_FUNC:
            # Support for using this decorator without calling it, e.g.
            #    @app.cmd        <---- note: no parentheses here!
            #    def foo(): pass
            return self.cmd()(_func)

        parser_args = args
        parser_kwargs = kwargs

        def wrapper(func):
            subcommand = name if name is not None else func.__name__

            parser_kwargs.setdefault('help', "")  # improves --help output
            subparser = self._subparsers.add_parser(
                    subcommand, *parser_args, **parser_kwargs)

            # Add global arguments to subcommand as well so that they
            # can be given after the subcommand on the CLI.
            for global_args, global_kwargs in self._global_args:
                subparser.add_argument(*global_args, **global_kwargs)

            # Add any pending arguments
            for args, kwargs in self._pending_args:
                subparser.add_argument(*args, **kwargs)
            self._pending_args = []

            # Add any pending default values
            try:
                pending_defaults = self._defaults.pop(None)
            except KeyError:
                pass  # no pending defaults
            else:
                self._defaults[func] = pending_defaults

            # Store callback function and return the decorated function
            # unmodified
            subparser.set_defaults(_func=func)
            return func

        return wrapper

    def cmd_arg(self, *args, **kwargs):
        """Decorator to specify a command line argument for a subcommand.

        All arguments are passed on to :py:meth:`ArgumentParser.add_argument`.

        Note: this function must be used in conjunction with .cmd().
        """

        # TODO: perhaps add a 'group' argument to cmd_arg() that
        # translates to add_argument_group

        if len(args) == 1 and callable(args[0]) and not kwargs:
            raise TypeError("cmd_arg() decorator requires arguments, "
                            "but none were supplied")

        # Remember the passed args, since the command is not yet known
        # when this decorator is called.
        self._pending_args.append((args, kwargs))

        # Return a do-nothing decorator
        return lambda func: func

    def cmd_defaults(self, **kwargs):
        """Decorator to specify defaults for a subcommand.

        This can be useful to override global argument defaults for specific
        subcommands.

        All arguments are passed on to :py:meth:`ArgumentParser.set_defaults`.

        Note: this function must be used in conjunction with .cmd().
        """
        if len(kwargs) == 1 and callable(list(kwargs.values())[0]):
            raise TypeError("defaults() decorator requires arguments, "
                            "but none were supplied")

        # Work-around http://bugs.python.org/issue9351 by storing the
        # defaults outside the ArgumentParser. The special key "None" is
        # used for the pending defaults for a yet-to-be defined command.
        self._defaults[None] = kwargs
        return lambda func: func

    def run(self, *args, **kwargs):
        """Run the application.

        This method parses the arguments and takes the appropriate actions. If
        a valid subcommand was found, it will be executed and its return value
        will be returned.

        All arguments are passed on to :py:meth:`ArgumentParser.parse_args`.
        """
        if self._pending_args:
            raise TypeError("cmd_arg() called without matching cmd()")

        if None in self._defaults:
            raise TypeError("cmd_defaults() called without matching cmd()")

        kwargs = vars(self._parser.parse_args(*args, **kwargs))
        func = kwargs.pop('_func')

        if func in self._defaults:
            kwargs.update(self._defaults[func])

        return func(**kwargs)