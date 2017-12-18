#!/usr/bin/env python3

print('Welcome to ASE Attendance Tracking')

class State:

    def execute(self):
        raise NotImplementedError

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self, data):
        raise NotImplementedError
    
class StateManager:
    states = []

    def push(self, state):
        self.push(self.states)
        self.peek().execute()

    def pop(self):
        return self.states.pop()

    def replace(self, state):
        self.pop()
        self.push(state)

    def peek(self):
        return self.states[-1]

    def reset(self):
        states = [] # TODO: set idle state
