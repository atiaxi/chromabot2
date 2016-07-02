from pyparsing import ParseException

class Command:

    def __init__(self, tokens):
        self.tokens = tokens
        self.message = None

    def execute(self, message):
        pass


# Hijacking result codes from HTTP for my own use

# The thing you tried to do worked
CODE_OK = 200
# the thing you tried to do didn't work.
CODE_NOK = 400

# And for my own specific use:  The 6xx series codes are intended for the
# Outsider to pick up on during the reporting phase, and act on them
# accordingly using the code and any information in the 'extra' field.

# Purely informational.
CODE_INFO = 600
# A team gained points.  Extra is a dict indicating
# the team in question in the 'team' field and how
# many in the 'amount' field
CODE_SCORE = 601
# The battle indicated in the 'extra' field has begun
CODE_BEGIN_BATTLE = 698
# The battle indicated in the 'extra' field has ended.
CODE_END_BATTLE = 699


class Result:

    @classmethod
    def from_exception(cls, e, message):
        text = e.args[0]
        if isinstance(e, ParseException):
            text = (
                "Parse error for command `{line}`, col {col}.  "
                "Message: {msg}"
            ).format(
                line=e.line,
                col=e.column,
                msg=e.msg
            )
        return cls(text, message, False, code=400, extra=e)

    def __init__(self, text, message=None, success=True, code=200, extra=None):
        self.message = message
        self.text = text
        self.success = success
        self.code = code
        self.extra = extra

    def is_internal(self):
        return self.message is None

    def __repr__(self):
        return "Result(text='%s')" % self.text


# Actual commands follow:
class StatusCommand(Command):

    def execute(self, message):
        status = message.outside.status_for(message.issuer)
        return Result(status, message)
