import zlib
import asyncio

from channels.consumer import AsyncConsumer
from honahlee.protocols.base import AsgiAdapterProtocol, AsyncGameConsumerMixin

# Much of this code has been adapted from the Evennia project https://github.com/evennia/evennia
# twisted.conch.telnet was also used for inspiration.
# Credit where credit is due.

TCODES_BYTES = {}
TCODES_NAMES = {}

TCODES = {
    "NUL": 0,
    "BEL": 7,
    "CR": 13,
    "LF": 10,
    "SGA": 3,
    "NAWS": 31,
    "SE": 240,
    "NOP": 241,
    "DM": 242,
    "BRK": 243,
    "IP": 244,
    "AO": 245,
    "AYT": 246,
    "EC": 247,
    "EL": 248,
    "GA": 249,
    "SB": 250,
    "WILL": 251,
    "WONT": 252,
    "DO": 253,
    "DONT": 254,
    "IAC": 255,

    "TTYPE": 24,
    "MXP": 91,
    "MSSP": 70,
    "MCCP2": 86,
    "MCCP3": 87,
    "GMCP": 201,
    "MSDP": 69
}

TCODES_INTS = {}

for (name, b) in TCODES.items():
    TCODES_BYTES[name] = bytes([b])
    TCODES_NAMES[bytes([b])] = name
    TCODES_INTS[b] = name


def debug_telnet(data):
    output = b''
    for b in data:
        if b in TCODES_INTS:
            if len(output) > 0 and bytes([output[-1]]) != b' ':
                output += b' '
            output += TCODES_INTS[b].encode("ascii")
            output += b' '
        else:
            output += bytes([b])
    output = output.strip()
    formatted = output.decode("utf-8", errors="ignore")
    return formatted


# Yeah this is basically an enum.
class TSTATE:
    DATA = 0
    ESCAPED = 1
    SUBNEGOTIATION = 2
    IN_SUBNEGOTIATION = 3
    SUB_ESCAPED = 4
    COMMAND = 5
    ENDLINE = 6


class TelnetOptionState:

    def __init__(self, handler):
        self.handler = handler
        self.enabled = False
        self.negotiating = False


class TelnetOptionHandler:
    # op_code must be the byte that represents this option.
    op_code = None
    op_name = 'N\A'

    start_order = 0
    write_transform_order = 0
    read_transform_order = 0

    # If true, this OptionHandler will send a WILL <op_code> during protocol setup.
    will = False
    # if True, this optionhandler will send a DO <op>ccode> during protocol setup.
    do = False

    def __init__(self, protocol):
        self.protocol = protocol
        self.us = TelnetOptionState(self)
        self.them = TelnetOptionState(self)

    async def start(self):
        if self.do:
            self.us.negotiating = True
            await self.protocol.from_app.put({
                'type': 'negotiate',
                'command': TCODES_BYTES["DO"],
                'op_name': self.op_name,
                'op_code': self.op_code
            })
        if self.will:
            self.us.negotiating = True
            await self.protocol.from_app.put({
                'type': 'negotiate',
                'command': TCODES_BYTES["WILL"],
                'op_name': self.op_name,
                'op_code': self.op_code
            })

    async def recv_WILL(self):

        if self.us.negotiating:
            # The client is enabling a feature on their end after we sent a DO.
            self.us.negotiating = False
            self.us.sent = None
            self.them.enabled = True
            await self.enableRemote()
        else:
            # If the above isn't true, then we are receiving a WILL from out of nowhere. That means the Remote Side
            # wants to enable. We will answer an affirmative and enable it.
            if not self.them.enabled:
                self.them.enabled = True
                await self.protocol.send_data(TCODES_BYTES["DO"])
                await self.enableRemote()

    async def recv_WONT(self):
        # We will not be answering this but let's see what needs doing...

        if self.us.negotiating:
            # We asked the remote party to enable this and they refused.
            self.us.negotiating = False
            await self.refusedRemote()
        else:
            # If we randomly received a WONT for a feature that we can use... we should disable this if it's enabled.
            # Else, we're going to ignore this.
            if self.them.enabled:
                self.them.enabled = False
                await self.disableRemote()

    async def recv_DO(self):
        if self.us.negotiating:
            # We asked the client if we can use this, and they said yes.
            self.us.negotiating = False
            self.us.enabled = True
            await self.enableLocal()
        else:
            # If the above isn't true, the client wants us to use this.
            if not self.us.enabled:
                self.us.enabled = True
                await self.enableLocal()

    async def recv_DONT(self):
        if self.us.negotiating:
            # Well. We wanted to use this, but they say nope...
            self.us.negotiating = False
            await self.refusedLocal()

    async def refusedLocal(self):
        pass

    async def refusedRemote(self):
        pass

    async def disableLocal(self):
        pass

    async def disableRemote(self):
        pass

    async def enableLocal(self):
        pass

    async def enableRemote(self):
        pass

    async def receive_sb(self, data):
        pass

    async def send_sb(self, data, callback=None):
        await self.protocol.from_app.put({
            'type': 'subnegotiate',
            'op_name': self.op_name,
            'op_code': self.op_code,
            'data': data,
            'callback': callback
        })

    def read_transform(self, data):
        return data

    def write_transform(self, data):
        return data


class SGAHandler(TelnetOptionHandler):
    op_code = TCODES_BYTES["SGA"]
    op_name = "SGA"
    will = True


class NAWSHandler(TelnetOptionHandler):
    op_code = TCODES_BYTES["NAWS"]
    op_name = 'NAWS'

    do = True
    sb = True

    def __init__(self, protocol):
        super().__init__(protocol)
        self.width = self.protocol.scope["game_client"]["width"]
        self.height = self.protocol.scope["game_client"]["height"]

    async def receive_sb(self, data):
        if len(data) == 4:
            # NAWS is negotiated with 16bit words
            new_width = int.from_bytes(bytes([data[0]]) + bytes([data[1]]), byteorder="big")
            new_height = int.from_bytes(bytes([data[2]]) + bytes([data[3]]), byteorder="big")

            if new_width != self.width:
                self.change_width(new_width)
            if new_height != self.height:
                self.change_height(new_height)

    def change_width(self, new_width):
        self.protocol.scope["game_client"]["width"] = new_width

    def change_height(self, new_height):
        self.protocol.scope["game_client"]["height"] = new_height


class TTYPEHandler(TelnetOptionHandler):
    op_code = TCODES_BYTES["TTYPE"]
    op_name = "TTYPE"
    do = True
    sb = True

    MTTS = [
        (128, "PROXY"),
        (64, "SCREENREADER"),
        (32, "OSC_COLOR_PALETTE"),
        (16, "MOUSE_TRACKING"),
        (8, "XTERM256"),
        (4, "UTF-8"),
        (2, "VT100"),
        (1, "ANSI"),
    ]

    def __init__(self, protocol):
        super().__init__(protocol)
        self.counter = 0
        self.name_bytes = None

    async def enableRemote(self):
        await self.request()

    async def request(self):
        # IAC SB TTYPE SEND IAC SE
        await self.send_sb(bytes([1]))

    def set_client(self, name):
        name = name.upper()

        self.protocol.scope["game_client"]["name"] = name

        # use name to identify support for xterm256. Many of these
        # only support after a certain version, but all support
        # it since at least 4 years. We assume recent client here for now.
        xterm256 = False
        if name.startswith("MUDLET"):
            name, version = name.split()
            name = name.strip()
            version = version.strip()
            self.protocol.scope["game_client"]["version"] = version
            self.protocol.scope["game_client"]["name"] = name

            # supports xterm256 stably since 1.1 (2010?)
            xterm256 = version >= "1.1"

        if name.startswith("TINTIN++"):
            self.protocol.scope["game_client"]["forced_endline"] = True

        if (
                name.startswith("XTERM")
                or name.endswith("-256COLOR")
                or name
                in (
                "ATLANTIS",  # > 0.9.9.0 (aug 2009)
                "CMUD",  # > 3.04 (mar 2009)
                "KILDCLIENT",  # > 2.2.0 (sep 2005)
                "MUDLET",  # > beta 15 (sep 2009)
                "MUSHCLIENT",  # > 4.02 (apr 2007)
                "PUTTY",  # > 0.58 (apr 2005)
                "BEIP",  # > 2.00.206 (late 2009) (BeipMu)
                "POTATO",  # > 2.00 (maybe earlier)
                "TINYFUGUE",  # > 4.x (maybe earlier)
        )
        ):
            xterm256 = True

        # all clients supporting TTYPE at all seem to support ANSI
        self.protocol.scope["game_client"]["capabilities"]["xterm256"] = xterm256
        self.protocol.scope["game_client"]["capabilities"]["ansi"] = True

    def set_capabilities(self, data):
        # this is a term capabilities flag
        term = data.decode("utf-8", errors="ignore")
        tupper = term.upper()
        # identify xterm256 based on flag
        xterm256 = (
                tupper.endswith("-256COLOR")
                or tupper.endswith("XTERM")  # Apple Terminal, old Tintin
                and not tupper.endswith("-COLOR")  # old Tintin, Putty
        )
        if xterm256:
            self.protocol.scope["game_client"]["capabilities"]["ansi"] = True
            self.protocol.scope["game_client"]["capabilities"]["xterm256"] = xterm256
        self.protocol.scope["game_client"]["terminal"] = term

    def set_mtts(self, data):
        # the MTTS bitstring identifying term capabilities
        if data.startswith(b"MTTS"):
            option = data[4:].strip()

            if option.isdigit():
                # a number - determine the actual capabilities
                option = int(option)
                support = dict(
                    (capability, True) for bitval, capability in self.MTTS if option & bitval > 0
                )
                if "SCREENREADER" in support:
                    self.protocol.scope["game_client"]["options"]["screenreader"] = True
                if "XTERM256" in support:
                    self.protocol.scope["game_client"]["capabilities"]["xterm256"] = True
                if "ANSI" in support:
                    self.protocol.scope["game_client"]["capabilities"]["ansi"] = True
                if "UTF-8" in support:
                    self.protocol.scope["game_client"]["capabilities"]["utf8"] = True

    async def receive_sb(self, data):

        if bytes([data[0]]) != bytes([0]):
            # Received a malformed TTYPE answer. Let's ignore it for now.
            return

        # slice off that IS. we don't need it.
        data = data[1:]

        if self.counter == 0:
            # This is the first time we're receiving a TTYPE IS.
            client = data.decode("utf-8", errors='ignore')
            self.set_client(client)
            self.name_bytes = data
            self.counter += 1
            # Request round 2 of our data!
            await self.request()
            return

        if self.counter == 1:
            if data == self.name_bytes:
                # Some clients don't support giving further information. In that case, there's nothing
                # more for TTYPE to do.
                return
            self.set_capabilities(data)
            self.counter += 1
            await self.request()
            return

        if self.counter == 2:
            self.set_mtts(data)
            self.counter += 1
            return


class MCCP2Handler(TelnetOptionHandler):
    """
    When MCCP2 is enabled, all of our outgoing bytes will be mccp2 compressed.
    """
    op_code = TCODES_BYTES["MCCP2"]
    op_name = 'MCCP2'
    will = True

    def __init__(self, protocol):
        super().__init__(protocol)
        self.compress = zlib.compressobj(9)

    async def enableLocal(self):
        await self.send_sb(bytes([]), callback=self.add_transform)

    def add_transform(self):
        self.protocol.add_write_transform(self)

    async def disableLocal(self):
        self.protocol.remove_write_transform(self)

    def write_transform(self, data):
        return self.compress.compress(data) + self.compress.flush(zlib.Z_SYNC_FLUSH)


class MCCP3Handler(TelnetOptionHandler):
    """
    Not yet functional.
    """
    op_code = TCODES_BYTES["MCCP3"]
    op_name = 'MCCP3'
    will = True

    def __init__(self, protocol):
        super().__init__(protocol)
        self.decompress = zlib.decompressobj(9)
        self.active = False

    def receive_sb(self, data):
        # MCCP3 can only be sending us one thing (IAC SB MCCP3 IAC SE), so we're gonna ignore the details.
        if not data and not self.active:
            self.protocol.add_read_transform(self)
            self.active = True

    def disable(self):
        self.protocol.remove_read_transform(self)
        self.active = False

    def read_transform(self, data):
        try:
            print(f"READ TRANSFORM CALLED FOR: {data}")
            decompressed = self.decompress.decompress(data)
            print(f"DECOMPRESSED TO: {decompressed}")
            return decompressed
        except Exception as e:
            print(e)


class MSSPHandler(TelnetOptionHandler):
    """
    It is the responsibility of the factory to report Mud Server Status Protocol data.
    """
    op_code = bytes([70])
    op_name = "MSSP"

    will = True

    def enable(self):
        response = None
        try:
            # On the off-chance that specific MSSP crawlers should be blocked, pass the protocol so the method
            # has a way to know who's asking.
            response = self.protocol.server.generate_mssp_data(self.protocol)
        except Exception as e:
            pass
        if response:
            # this is not finished - still need to format response properly
            # self.send_sb(response)
            pass


class TelnetAsgiProtocol(AsgiAdapterProtocol):
    asgi_type = 'telnet'

    handler_classes = [
        MCCP2Handler,
        #MCCP3Handler,
        SGAHandler,
        NAWSHandler,
        TTYPEHandler,
        #MSSPHandler,
    ]

    def __init__(self, reader, writer, server, application):
        super().__init__(reader, writer, server, application)

        self.data_buffer = []
        self.command_list = []

        self.telnet_state = TSTATE.DATA

        # If handlers want to do read/write-transforms on outgoing data, they'll be stored here and sorted
        # by their property.
        self.reader_transforms = []
        self.writer_transforms = []

        # These two handle when we're dealing with IAC WILL/WONT/DO/DONT and IAC SB <code>, storing data until it's
        # needed.
        self.iac_command = bytes([0])
        self.negotiate_buffer = []

        self.handler_codes = dict()
        self.handler_names = dict()

        self.forced_endline = False

        for h_class in self.handler_classes:
            handler = h_class(self)
            self.handler_codes[h_class.op_code] = handler
            self.handler_names[h_class.op_name] = handler

    def add_read_transform(self, handler):
        if handler not in self.reader_transforms:
            self.reader_transforms.append(handler)
            self.sort_read_transform()

    def remove_read_transform(self, handler):
        if handler in self.reader_transforms:
            self.reader_transforms.remove(handler)
            self.sort_read_transform()

    def add_write_transform(self, handler):
        if handler not in self.writer_transforms:
            self.writer_transforms.append(handler)
            self.sort_write_transform()

    def remove_write_transform(self, handler):
        if handler in self.writer_transforms:
            self.writer_transforms.remove(handler)
            self.sort_write_transform()

    def sort_read_transform(self):
        self.reader_transforms.sort(key=lambda h: h.read_transform_order)

    def sort_write_transform(self):
        self.writer_transforms.sort(key=lambda h: h.write_transform_order)

    async def start_negotiation(self):
        for handler in sorted(self.handler_codes.values(), key=lambda x: x.start_order):
            await handler.start()
        await asyncio.sleep(0.3)
        await self.asgi()

    async def handle_reader(self, data):
        """
        Iterate over all bytes.

        This is largely shamelessly ripped from twisted.conch.telnet
        """
        app_data_buffer = []

        async def flush_app_buffer():
            event = {
                'type': 'application',
                'data': b''.join(app_data_buffer)
            }
            app_data_buffer.clear()
            await self.handle_protocol_event(event)

        # This is mostly for MCCP3.
        for handler in self.reader_transforms:
            data = handler.read_transform(data)

        for c in data:
            b = bytes([c])

            if self.telnet_state == TSTATE.DATA:
                if b == TCODES_BYTES["IAC"]:
                    self.telnet_state = TSTATE.ESCAPED
                elif b == b'\r':
                    self.telnet_state = TSTATE.ENDLINE
                else:
                    app_data_buffer.append(b)
            elif self.telnet_state == TSTATE.ESCAPED:
                if b == TCODES_BYTES["IAC"]:
                    app_data_buffer.append(b)
                    self.telnet_state = TSTATE.DATA
                elif b == TCODES_BYTES["SB"]:
                    self.telnet_state = TSTATE.SUBNEGOTIATION
                    self.negotiate_buffer = []
                elif b in (TCODES_BYTES["WILL"], TCODES_BYTES["WONT"], TCODES_BYTES["DO"], TCODES_BYTES["DONT"]):
                    self.telnet_state = TSTATE.COMMAND
                    self.iac_command = b
                else:
                    self.telnet_state = TSTATE.DATA
                    if app_data_buffer:
                        await flush_app_buffer()
                    await self.handle_protocol_event({
                        'type': 'command',
                        'command': b
                    })
            elif self.telnet_state == TSTATE.COMMAND:
                self.telnet_state = TSTATE.DATA
                if app_data_buffer:
                    await flush_app_buffer()
                await self.handle_protocol_event({
                    'type': 'negotiate',
                    'command': self.iac_command,
                    'option': b
                })
                self.iac_command = bytes([0])
            elif self.telnet_state == TSTATE.ENDLINE:
                self.telnet_state = TSTATE.DATA
                if b == b'\n':
                    app_data_buffer.append(b'\n')
                elif b == b'\0':
                    app_data_buffer.append(b'\r')
                elif b == TCODES_BYTES["IAC"]:
                    # IAC isn't really allowed after \r, according to the
                    # RFC, but handling it this way is less surprising than
                    # delivering the IAC to the app as application data.
                    # The purpose of the restriction is to allow terminals
                    # to unambiguously interpret the behavior of the CR
                    # after reading only one more byte.  CR LF is supposed
                    # to mean one thing (cursor to next line, first column),
                    # CR NUL another (cursor to first column).  Absent the
                    # NUL, it still makes sense to interpret this as CR and
                    # then apply all the usual interpretation to the IAC.
                    app_data_buffer.append(b'\r')
                    self.telnet_state = TSTATE.ESCAPED
                else:
                    app_data_buffer.append(b'\r' + b)
            elif self.telnet_state == TSTATE.SUBNEGOTIATION:
                if b == TCODES_BYTES["IAC"]:
                    self.telnet_state = TSTATE.SUB_ESCAPED
                else:
                    self.telnet_state = TSTATE.IN_SUBNEGOTIATION
                    self.negotiate_code = b
            elif self.telnet_state == TSTATE.IN_SUBNEGOTIATION:
                if b == TCODES_BYTES["IAC"]:
                    self.telnet_state = TSTATE.SUB_ESCAPED
                else:
                    self.negotiate_buffer.append(b)
            elif self.telnet_state == TSTATE.SUB_ESCAPED:
                if b == TCODES_BYTES["SE"]:
                    self.telnet_state = TSTATE.DATA
                    if app_data_buffer:
                        await flush_app_buffer()
                    await self.handle_protocol_event({
                        'type': 'subnegotiate',
                        'option': self.negotiate_code,
                        'data': b''.join(self.negotiate_buffer)
                    })
                    self.negotiate_code = bytes([0])
                    self.negotiate_buffer.clear()
                else:
                    self.telnet_state = TSTATE.SUBNEGOTIATION
                    self.negotiate_buffer.append(b)
            else:
                raise ValueError("How'd you do this?")

        if app_data_buffer:
            await flush_app_buffer()

    async def handle_protocol_event(self, event):
        """
        This serves as a general switchboard for the kinds of events
        that can be triggered by incoming data. Kinda inspired by ASGI,
        but is more here for debug purposes.
        """
        if event["type"] == 'application':
            await self.parse_application_data(event["data"])
        elif event["type"] == "negotiate":
            await self.execute_iac_negotiation(event["command"], event["option"])
        elif event["type"] == "command":
            await self.execute_iac_command(event["command"])
        elif event["type"] == "subnegotiate":
            await self.sub_negotiate(event["option"], event["data"])
        else:
            print(f"how the heck did we get here? Unknown Event Type: {event['data']}")

    async def sub_negotiate(self, op_code, data):
        if (handler := self.handler_codes.get(op_code, None)):
            await handler.receive_sb(data)

    async def execute_iac_command(self, command):
        pass

    async def execute_iac_negotiation(self, command, op_code):
        if (handler := self.handler_codes.get(op_code, None)):
            if command == TCODES_BYTES["WILL"]:
                await handler.recv_WILL()
            if command == TCODES_BYTES["WONT"]:
                await handler.recv_WONT()
            if command == TCODES_BYTES["DO"]:
                await handler.recv_DO()
            if command == TCODES_BYTES["DONT"]:
                await handler.recv_DONT()
        else:
            pass

    async def parse_application_data(self, data):
        """
        This is called by super().dataReceived() and it receives a pile of bytes.
        This will never contain IAC-escaped sequences, but may contain other special
        characters/symbols/bytes.
        """
        # First, append all the new data to our app buffer.

        for b in [bytes([i]) for i in data]:

            if b in (TCODES_BYTES["NUL"], TCODES_BYTES["NOP"]):
                # Ignoring this ancient keepalive
                # convert it to the IDLE COMMAND here...
                await self.user_command(b"IDLE")
                continue
            if b == TCODES_BYTES["LF"]:
                await self.user_command(b''.join(self.data_buffer))
                self.data_buffer.clear()
                continue

            # Nothing else stands out? Append the data to data buffer...
            self.data_buffer.append(b)

    async def user_command(self, command):
        """
        Decodes user-entered command into preferred style, such as UTF-8.

        Args:
            command (byte string): The user-entered command, minus terminating CRLF
        """

        decoded = command.decode("utf-8", errors='ignore')
        event = {
            "type": "telnet.line",
            "line": decoded
        }
        print(f"GOT USER COMMAND: {command}")
        await self.to_app.put(event)

    async def send_data(self, data):
        """
        Run transforms on all outgoing data before sending to transport.

        Args:
            data (bytearray): The data being sent.

        """
        for handler in self.writer_transforms:
            data = handler.write_transform(data)
        await self.write_data(data)

    async def handle_event(self, event):
        """
        This isn't NECESSARILY events just from the ASGI app. It might also be outgoing
        messages from the this protocol instance.
        """
        if event["type"] == "text":
            await self.send_text(event["data"])
        elif event["type"] == "subnegotiate":
            await self.send_data(TCODES_BYTES["IAC"] + TCODES_BYTES["SB"] + event["op_code"] + event['data'] + TCODES_BYTES["IAC"] + TCODES_BYTES["SE"])
        elif event["type"] == "negotiate":
            await self.send_data(TCODES_BYTES["IAC"] + event["command"] + event["op_code"])
        else:
            print("GOD ONLY KNOWS WHAT HAPPENED HERE")
        if (callback := event.get('callback', None)):
            callback()

    async def send_text(self, text):
        """

        Args:
            text (str): The utf-8 text to send.

        Returns:

        """
        await self.send_data(text.encode("ascii"))

    async def generate_connect(self):
        await self.to_app.put({
            'type': f"{self.asgi_type}.connect",
            "data": self.scope["game_client"]
        })


class AsyncTelnetConsumer(AsyncConsumer, AsyncGameConsumerMixin):
    app = None
    service = None

    def __init__(self, scope):
        super().__init__(scope)
        self.game_setup()

    async def telnet_line(self, event):
        await self.game_input("text", event['line'])

    async def telnet_disconnect(self, event):
        await self.game_close(event['reason'])

    async def telnet_connect(self, event):
        # Gotta set this to the same dictionary that's contained in the base
        self.scope["game_client"] = event["data"]
        await self.game_connect()
