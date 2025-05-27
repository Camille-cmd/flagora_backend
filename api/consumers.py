from channels.generic.websocket import JsonWebsocketConsumer

from api.flag_store import flag_store


class GameConsumer(JsonWebsocketConsumer):

    def connect(self):
        self.accept()

        flags_data = flag_store.get_path("FR")
        print(flags_data, "test")

        self.send_json({"flags": flags_data})

    def receive_json(self, content, **kwargs):
        print(content)
