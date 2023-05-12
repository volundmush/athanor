from twisted.internet import reactor, task


class PromptHandler:

    def __init__(self, owner):
        self.owner = owner
        self.task = None

    def prepare(self, prompt_delay=0.1):
        if self.task:
            self.task.cancel()
        self.task = task.deferLater(reactor, prompt_delay, self.print)
        self.task.addErrback(self.error)

    def print(self):
        self.owner.msg(prompt=f"\n{self.owner.render_prompt()}\n")

    def error(self, err):
        pass
