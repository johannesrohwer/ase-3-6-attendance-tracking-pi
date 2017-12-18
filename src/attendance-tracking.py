#!/usr/bin/env python3

import requests


class Constants:
    BASE_URL = 'https://ase-3-6-attendance-tracking.appspot.com'
    AUTH_TOKEN = ""


class State:
    state_manager = None

    def __init__(self, state_manager):
        self.state_manager = state_manager

    def execute(self):
        print("- - -")

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self):
        raise NotImplementedError


class Idle_State(State):
    def execute(self):
        print("Idle state")


class Authentification_State(State):
    id = None
    password = None
    authorization_token = None

    def execute(self):
        super().execute()

        # Get credentials from user
        print('Please authenticate yourself.')
        self.id = input('ID:\t')
        self.password = input('password:\t')

        # Send credentials to API and obtain Authorization token
        url = Constants.BASE_URL + '/api/login'
        payload = {'id': self.id,
                   'password': self.password}
        response = requests.post(url, json=payload)
        responseObj = response.json()

        if response.status_code == 200:
            self.authorization_token = responseObj["token"]

        else:
            print("An error occured: {}".format(responseObj["error"]))

        self.transition()

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self):
        if self.authorization_token:
            # Pass token to state manager
            self.state_manager.authorization_token = self.authorization_token

            # Perform the transition to the next state
            self.state_manager.replace(Idle_State(self.state_manager))

        else:
            # An error occured, start again
            self.state_manager.replace(Authentification_State(self.state_manager))


class StateManager:
    states = []

    def push(self, state):
        self.states.append(state)
        self.peek().execute()

    def pop(self):
        return self.states.pop()

    def replace(self, state):
        self.pop()
        self.push(state)

    def peek(self):
        return self.states[-1]

    def reset(self):
        self.states = []  # TODO: set idle state


if __name__ == "__main__":
    print('Welcome to ASE Attendance Tracking')
    sm = StateManager()
    sm.push(Authentification_State(sm))
