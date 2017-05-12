# This file is part of eventmq.
#
# eventmq is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# eventmq is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with eventmq.  If not, see <http://www.gnu.org/licenses/>.
import time
import unittest

import mock

from .. import constants, jobmanager

ADDR = 'inproc://pour_the_rice_in_the_thing'


class TestCase(unittest.TestCase):
    @mock.patch('uuid.uuid4')
    def test__setup(self, name_mock):
        name_mock.return_value = 'some_uuid'
        override_settings = {
            'NAME': 'RuckusBringer'
        }
        jm = jobmanager.JobManager(override_settings=override_settings)
        self.assertEqual(jm.name.decode('ascii'), 'RuckusBringer:some_uuid')

        self.assertFalse(jm.awaiting_startup_ack)
        self.assertEqual(jm.status, constants.STATUS.ready)

# EMQP Tests
    @mock.patch('uuid.uuid4')
    def test_reset(self, name_mock):
        name_mock.return_value = 'some_uuid'
        jm = jobmanager.JobManager()

        self.assertEqual(jm.name.decode('ascii'), 'some_uuid')

        self.assertFalse(jm.awaiting_startup_ack)
        self.assertEqual(jm.status, constants.STATUS.ready)

    @mock.patch('eventmq.jobmanager.sendmsg')
    def test_send_ready(self, sndmsg_mock):
        jm = jobmanager.JobManager()
        jm.send_ready()

        sndmsg_mock.assert_called_with(jm.frontend, 'READY')

    @mock.patch('multiprocessing.pool.Pool.close')
    @mock.patch('eventmq.jobmanager.JobManager.process_message')
    @mock.patch('eventmq.jobmanager.Sender.recv_multipart')
    @mock.patch('eventmq.jobmanager.Poller.poll')
    @mock.patch('eventmq.jobmanager.JobManager.maybe_send_heartbeat')
    def test__start_event_loop(self, maybe_send_hb_mock,
                               poll_mock, sender_mock, process_msg_mock,
                               pool_close_mock):

        # Create a jobmanager with no child processes for testing
        jm = jobmanager.JobManager(override_settings={
            'CONNECT_ADDR': ADDR,
            'CONCURRENT_JOBS': 0,
        })
        maybe_send_hb_mock.return_value = False
        poll_mock.return_value = {jm.frontend: jobmanager.POLLIN}
        sender_mock.return_value = [1, 2, 3]

        jm._start_event_loop()

        process_msg_mock.assert_called_with(
            sender_mock.return_value)

        jm.received_disconnect = True
        jm.should_reset = True
        jm._start_event_loop()

    def test_on_request(self):
        _msgid = 'aaa0j8-ac40jf0-04tjv'
        _msg = ['a', 'b', '["run", {"a": 1}]']

        jm = jobmanager.JobManager()

        jm.on_request(_msgid, _msg)

    def test_on_request_with_timeout(self):
        timeout = 3
        _msgid = 'aaa0j8-ac40jf0-04tjv'
        _msg = ['a', 'timeout:{}'.format(timeout), '["run", {"a": 1}]']

        jm = jobmanager.JobManager()

        jm.on_request(_msgid, _msg)

    def test_on_request_with_timeout_and_reply(self):
        timeout = 3
        _msgid = 'aaa0j8-ac40jf0-04tjv'
        _msg = ['a',
                'timeout:{},reply-requested'.format(timeout),
                '["run", {"a": 1}]']

        jm = jobmanager.JobManager()

        jm.on_request(_msgid, _msg)

    @mock.patch('eventmq.jobmanager.sendmsg')
    @mock.patch('zmq.Socket.unbind')
    def test_on_disconnect(self, socket_mock, sendmsg_mock):
        msgid = 'goog8l-uitty40-007b'
        msg = ['a', 'b', 'whatever']

        socket_mock.return_value = True

        jm = jobmanager.JobManager()
        jm.frontend.status = constants.STATUS.listening
        jm.on_disconnect(msgid, msg)
        self.assertTrue(jm.received_disconnect, "Did not receive disconnect.")

    # Other Tests
    @mock.patch('eventmq.jobmanager.reload_settings')
    def test_sighup_handler(self, load_settings_mock):
        jm = jobmanager.JobManager()

        jm.sighup_handler(982374, "FRAMEY the frame")

        # called once on init, and once for the sighup handler
        self.assertEqual(2, load_settings_mock.call_count)
        # check to see if the last call was called with the jobmanager section
        load_settings_mock.assert_called_with('jobmanager', None)

    @mock.patch('eventmq.jobmanager.sendmsg')
    def test_sigterm_handler(self, sendmsg_mock):
        jm = jobmanager.JobManager()

        jm.sigterm_handler(13231, "FRAMEY the evil frame")

        sendmsg_mock.assert_called_with(jm.frontend, constants.KBYE)
        self.assertFalse(jm.awaiting_startup_ack)
        self.assertTrue(jm.received_disconnect)

    def cleanup(self):
        self.jm.on_disconnect(None, None)
        self.jm = None


def call_done(jm):
    jm.active_jobs += 1
    return True


def start_jm(jm, addr):
    jm.start(addr)


def pretend_job(t):
    time.sleep(t)
    return "I slept for {} seconds".format(t)


def work_job(t):
    import time

    begin_time = time.time()

    while time.time() < begin_time + t:
        a = 1+1

    return a


def test_setup():
    import time
    assert time
