# This file is part of txgithub.  txgithub is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import re
import json
from twisted.python import log
from twisted.internet import defer, ssl
from twisted.web import client

class _GithubPageGetter(client.HTTPPageGetter):

    def handleStatus_204(self):
        # github returns 204 for e.g., DELETE operations
        self.handleStatus_200()

class _GithubHTTPClientFactory(client.HTTPClientFactory):

    protocol = _GithubPageGetter

    # dont' log about starting and stopping
    noisy = False

class GithubApi(object):
    # Interface to the github API, using
    # - API v3
    # - optional user/pass auth (token is not available with v3)
    # - async API

    def __init__(self, oauth2_token, baseURL=None, reactor=None):
        self._baseURL = baseURL or 'https://api.github.com/'
        self.oauth2_token = oauth2_token
        self.rateLimitWarningIssued = False
        self.contextFactory = ssl.ClientContextFactory()
        if reactor is None:
            from twisted.internet import reactor
        self.reactor = reactor

    def _makeHeaders(self):
        assert self.oauth2_token, "no token specified"
        return { 'Authorization' : 'token ' + self.oauth2_token }

    def makeRequest(self, url_args, post=None, method='GET', page=0):
        headers = self._makeHeaders()

        url = self._baseURL
        url += '/'.join(url_args)
        if page:
            url += "?page=%d" % page

        postdata = None
        if post:
            postdata = json.dumps(post)

        log.msg("fetching '%s'" % (url,), system='github')
        factory = _GithubHTTPClientFactory(url, headers=headers,
                    postdata=postdata, method=method,
                    agent='txgithub', followRedirect=0,
                    timeout=30)

        self.reactor.connectSSL(factory.host, factory.port, factory,
                                self.contextFactory)
        d = factory.deferred
        @d.addCallback
        def check_ratelimit(data):
            self.last_response_headers = factory.response_headers
            remaining = int(factory.response_headers.get(
                                    'x-ratelimit-remaining', [0])[0])
            if remaining < 100 and not self.rateLimitWarningIssued:
                log.msg("warning: only %d Github API requests remaining "
                        "before rate-limiting" % remaining)
                self.rateLimitWarningIssued = True
            return data
        @d.addCallback
        def un_json(data):
            if data:
                return json.loads(data)
        return d

    link_re = re.compile('<([^>]*)>; rel="([^"]*)"')
    @defer.inlineCallbacks
    def makeRequestAllPages(self, url_args):
        page = 0
        data = []
        while True:
            data.extend((yield self.makeRequest(url_args, page=page)))
            if 'link' not in self.last_response_headers:
                break
            link_hdr = self.last_response_headers['link'][0]
            for link in self.link_re.findall(link_hdr):
                if link[1] == 'next':
                    # note that we don't *use* the page -- why bother?
                    break
            else:
                break # no 'next' link, so we're done
            page += 1
        defer.returnValue(data)

    _repos = None
    @property
    def repos(self):
        if not self._repos:
            self._repos = ReposEndpoint(self)
        return self._repos

    _gists = None
    @property
    def gists(self):
        if not self._gists:
            self._gists = GistsEndpoint(self)
        return self._gists

    _pulls = None
    @property
    def pulls(self):
        if not self._pulls:
            self._pulls = PullsEndpoint(self)
        return self._pulls

    _comments = None
    @property
    def comments(self):
        if not self._comments:
            self._comments = IssueCommentsEndpoint(self)
        return self._comments

    _reviews = None
    @property
    def reviews(self):
        if not self._reviews:
            self._reviews = ReviewCommentsEndpoint(self)
        return self._reviews


class BaseEndpoint(object):

    def __init__(self, api):
        self.api = api


class ReposEndpoint(BaseEndpoint):

    @defer.inlineCallbacks
    def getEvents(self, repo_user, repo_name, until_id=None):
        """Get all repository events, following paging, until the end
        or until UNTIL_ID is seen.  Returns a Deferred."""
        done = False
        page = 0
        events = []
        while not done:
            new_events = yield self.api.makeRequest(
                    ['repos', repo_user, repo_name, 'events'],
                    page)

            # terminate if we find a matching ID
            if new_events:
                for event in new_events:
                    if event['id'] == until_id:
                        done = True
                        break
                    events.append(event)
            else:
                done = True

            page += 1
        defer.returnValue(events)

    def getHooks(self, repo_user, repo_name):
        """Get all repository hooks.  Returns a Deferred."""
        return self.api.makeRequestAllPages(
            ['repos', repo_user, repo_name, 'hooks'])

    def getHook(self, repo_user, repo_name, hook_id):
        """
        GET /repos/:owner/:repo/hooks/:id

        Returns the Hook.
        """
        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'hooks', str(hook_id)],
            method='GET',
            )

    def createHook(self, repo_user, repo_name, name, config, events, active):
        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'hooks'],
            method='POST',
            post=dict(name=name, config=config, events=events, active=active))

    def editHook(self, repo_user, repo_name, hook_id, name, config,
            events=None, add_events=None, remove_events=None, active=None):
        """
        PATCH /repos/:owner/:repo/hooks/:id

        :param hook_id: Id of the hook.
        :param name:  The name of the service that is being called.
        :param config: A Hash containing key/value pairs to provide settings
                       for this hook.
        """
        post = dict(
                name=name,
                config=config,
                )
        if events is not None:
            post['events'] = events

        if add_events is not None:
            post['add_events'] = add_events

        if remove_events is not None:
            post['remove_events'] = remove_events

        if active is not None:
            post['active'] = active

        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'hooks', str(hook_id)],
            method='PATCH',
            post=post,
            )

    def testHook(self, repo_user, repo_name, hook_id):
        """
        POST /repos/:owner/:repo/hooks/:id/tests

        Response headers:
            Status: 204 No Content
            X-RateLimit-Limit: 5000
            X-RateLimit-Remaining: 4999
        Response content:
            None
        """
        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'hooks', str(hook_id), 'tests'],
            method='POST',
            )

    def deleteHook(self, repo_user, repo_name, id):
        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'hooks', str(id)],
            method='DELETE')

    def getStatuses(self, repo_user, repo_name, sha):
        """
        :param sha: Full sha to list the statuses from.
        :return: A defered with the result from GitHub.
        """
        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'statuses', sha],
            method='GET')

    def createStatus(self,
            repo_user, repo_name, sha, state, target_url=None,
            description=None, context=None):
        """
        :param sha: Full sha to create the status for.
        :param state: one of the following 'pending', 'success', 'error'
                      or 'failure'.
        :param target_url: Target url to associate with this status.
        :param description: Short description of the status.
        :return: A defered with the result from GitHub.
        """
        payload = {'state': state}

        if description is not None:
            payload['description'] = description

        if target_url is not None:
            payload['target_url'] = target_url

        if context is not None:
            payload['context'] = context

        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'statuses', sha],
            method='POST',
            post=payload)


class GistsEndpoint(BaseEndpoint):
    def create(self, files, description=None, public=True):
        data = { 'files': files, 'public': bool(public) }
        if description is not None:
            data['description'] = description
        return self.api.makeRequest(
                ['gists'],
                method='POST',
                post=data)


class PullsEndpoint(BaseEndpoint):
    def edit(self, repo_user, repo_name, pull_number,
             title=None, body=None, state=None):
        """
        PATCH /repos/:owner/:repo/pulls/:number

        :param pull_number: The pull request's number
        :param title: The new title for the pull request
        :param body: The new top-level body for the pull request
        :param state: The new top-level body for the pull request
        """
        if not any((title, body, state)):
            raise ValueError("must provide at least one of:"
                             " title, body, state")

        post = {}
        if title is not None:
            post['title'] = title
        if body is not None:
            post['body'] = body
        if state is not None:
            if state not in ('open', 'closed'):
                raise ValueError("state must be either 'open' or 'closed'")
            post['state'] = state

        return self.api.makeRequest(
            ['repos', repo_user, repo_name, 'pulls', pull_number],
            method='PATCH',
            post=post)


class IssueCommentsEndpoint(BaseEndpoint):
    def create(self, repo_user, repo_name, issue_number, body):
        """
        PATCH /repos/:owner/:repo/issues/:number/comments

        :param issue_number: The issue's (or pull request's) number
        :param body: The body of this comment
        """
        return self.api.makeRequest(
            ['repos', repo_user, repo_name,
             'issues', issue_number, 'comments'],
            method='POST',
            post=dict(body=body))


class ReviewCommentsEndpoint(BaseEndpoint):
    def getRepoComments(self, repo_user, repo_name):
        """
        GET /repos/:owner/:repo/pulls/comments
        """
        return self.api.makeRequestAllPages(
            ['repos', repo_user, repo_name, 'pulls', 'comments'])

    def getPullRequestComments(self, repo_user, repo_name, pull_number):
        """
        GET /repos/:owner/:repo/pulls/:number/comments

        :param pull_number: The pull request's number.
        """
        return self.api.makeRequestAllPages(
            ['repos', repo_user, repo_name,
             'pulls', str(pull_number), 'comments'])

    def getComment(self, repo_user, repo_name, comment_id):
        """
        GET /repos/:owner/:repo/pull/comments/:number

        :param comment_id: The review comment's ID.
        """
        return self.api.makeRequest(
            ['repos', repo_user, repo_name,
             'pulls', 'comments', str(comment_id)])

    def createComment(self, repo_user, repo_name, pull_number,
                      body, commit_id, path, position):
        """
        POST /repos/:owner/:repo/pulls/:number/comments

        :param pull_number: The pull request's ID.
        :param body: The text of the comment.
        :param commit_id: The SHA of the commit to comment on.
        :param path: The relative path of the file to comment on.
        :param position: The line index in the diff to comment on.
        """
        return self.api.makeRequest(
            ["repos", repo_user, repo_name,
             "pulls", str(pull_number), "comments"],
            method="POST",
            data=dict(body=body,
                      commit_id=commit_id,
                      path=path,
                      position=position))

    def replyToComment(self, repo_user, repo_name, pull_number,
                       body, in_reply_to):
        """
        POST /repos/:owner/:repo/pulls/:number/comments

        Like create, but reply to an existing comment.

        :param body: The text of the comment.
        :param in_reply_to: The comment ID to reply to.
        """
        return self.api.makeRequest(
            ["repos", repo_user, repo_name,
             "pulls", str(pull_number), "comments"],
            method="POST",
            data=dict(body=body,
                      in_reply_to=in_reply_to))

    def editComment(self, repo_user, repo_name, comment_id, body):
        """
        PATCH /repos/:owner/:repo/pulls/comments/:id

        :param comment_id: The ID of the comment to edit
        :param body: The new body of the comment.
        """
        return self.api.makeRequest(
            ["repos", repo_user, repo_name,
             "pulls", "comments", str(comment_id)],
            method="POST",
            data=dict(body=body))

    def deleteComment(self, repo_user, repo_name, comment_id):
        """
        DELETE /repos/:owner/:repo/pulls/comments/:id

        :param comment_id: The ID of the comment to edit
        :param body: The new body of the comment.
        """
        return self.api.makeRequest(
            ["repos", repo_user, repo_name,
             "pulls", "comments", str(comment_id)],
            method="DELETE")

