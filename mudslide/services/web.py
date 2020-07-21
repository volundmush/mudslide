import ujson

from django.conf.urls import url

from channels.routing import URLRouter
from channels.routing import ProtocolTypeRouter
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer
from channels.consumer import AsyncConsumer
from channels.auth import AuthMiddlewareStack

from honahlee.core import BaseService


class LifespanAsyncConsumer(AsyncConsumer):
    app = None
    service = None

    async def lifespan_startup(self, event):
        await self.send({
            'type': 'lifespan.startup.complete'
        })

    async def lifespan_startup_complete(self, event):
        pass

    async def lifespan_startup_failed(self, event):
        pass

    async def lifespan_shutdown(self, event):
        await self.send({
            'type': 'lifespan.shutdown.complete'
        })

    async def lifespan_shutdown_complete(self, event):
        pass

    async def lifespan_shutdown_failed(self, event):
        pass


class GameConsumer(AsyncWebsocketConsumer):
    app = None
    service = None

    async def connect(self):
        await self.accept()
        print(f"RECEIVED A GAME CONNECTION: {self.scope}")

    async def disconnect(self, code):
        print(f"CLOSED {self} with {code}")


class LinkConsumer(AsyncJsonWebsocketConsumer):
    app = None
    service = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link = None

    async def decode_json(cls, text_data):
        return ujson.loads(text_data)

    async def connect(self):
        await self.accept()

    async def disconnect(self, code):
        print(f"CLOSED {self} with {code}")

    async def receive_json(self, content, **kwargs):
        if not (msg_type := content.get('type', None)):
            raise ValueError("Malformed message. Messages require a type!")
        if not (method := getattr(self, f'msg_{msg_type}', None)):
            raise ValueError(f"Unsupported Message Type: {msg_type}")
        await method(content)

    async def msg_link(self, message):
        """
        Link this game to this consumer.
        A game can only have one link at a time
        """
        if not (api_key := message.get('api_key', None)):
            raise ValueError("Link message requires an api_key")
        self.link = await self.service.app.services['link'].link_consumer(self, api_key)

    async def msg_unlink(self, message):
        """
        Terminates this game link and unbinds all clients connected to it. Will close the websocket connection too.
        """
        self.link.unlink(self)


class WebService(BaseService):

    def __init__(self):
        super().__init__()
        self.task = None
        self.config = None
        self.asgi_app = None
        self.consumer_classes = dict()

    async def setup(self):
        self.consumer_classes = self.app.config.classes['consumers']
        self.asgi_app = ProtocolTypeRouter(self.get_protocol_router_config())

    def get_protocol_router_config(self):
        return {
            "websocket": self.get_protocol_websocket_config(),
            "lifespan": self.consumer_classes["lifespan"],
            "telnet": AuthMiddlewareStack(self.consumer_classes["telnet"])
        }

    def get_protocol_websocket_config(self):

        return AuthMiddlewareStack(URLRouter([
            url(r"^game/$", self.consumer_classes["game"]),
            url(r"^link/$", self.consumer_classes["link"])
        ]))

    def get_protocol_router_http_config(self):
        pass

    async def start(self):
        from hypercorn.asyncio import serve
        self.task = self.app.loop.create_task(serve(self.asgi_app, self.config))

