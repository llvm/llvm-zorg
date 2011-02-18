import os
import unittest

import llvmlab
from llvmlab.ui import app

class TestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.App.create_test_instance().test_client()

    def tearDown(self):
        pass

    def login(self, username, password):
        return self.app.post('/login', data=dict(
                username=username,
                password=password), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

class TestBasic(TestCase):
    def test_index(self):
        rv = self.app.get('/')
        assert rv.data.startswith('<!DOCTYPE')

    def test_login_sequence(self):
        # Check that we aren't initially logged in.
        rv = self.app.get('/')
        assert "Logged in" not in rv.data

        # Check that the users page doesn't show up.
        rv = self.app.get('/users')
        assert """You must <a href="/login">login</a>.""" in rv.data

        # Check that the login page shows what we expect.
        rv = self.app.get('/login')
        assert """<input type=text name=username>""" in rv.data

        # Log in as the test admin user.
        rv = self.login("admin", "admin")
        assert "Logged In: <i>admin</i>""" in rv.data

        # Check that the login page shows something sensible.
        rv = self.app.get('/login')
        assert """You are already logged in.""" in rv.data
        
        # Check that we can access the users page now.
        rv = self.app.get('/users')
        assert """You must <a href="/login">login</a>.""" not in rv.data
        assert """<td>Administrator</td>""" in rv.data

        # Log out.
        rv = self.logout()
        assert "Logged in" not in rv.data

if __name__ == '__main__':
    unittest.main()
