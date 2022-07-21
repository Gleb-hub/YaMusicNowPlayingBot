import logging
from aiohttp import ClientSession
import yandex_music
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class YaManager:
    def __init__(self):
        self.session = ClientSession()

    async def get_music_token(self, username: str, password: str):
        logger.debug("Get music token")

        link_post = 'https://oauth.yandex.com/token'
        payload = {
            # Thanks to https://github.com/MarshalX/yandex-music-api/
            'client_secret': '53bc75238f0c4d08a118e51fe9203300',
            'client_id': '23cabbbdc6cd418abb4b39c32c41195d',
            'grant_type': 'password',
            'username': username,
            'password': password
        }
        r = await self.session.post(
            link_post, data=payload
        )
        resp = await r.json()
        assert 'access_token' in resp, resp
        logger.debug(resp['access_token'])
        return resp['access_token']

    @staticmethod
    def get_curr_track(token: str) -> yandex_music.Track:
        ym_client: yandex_music.Client = yandex_music.Client(token).init()
        queue_list = ym_client.queues_list()
        queue_item = queue_list[0]
        ym_queue = ym_client.queue(queue_item.id)
        ym_track = ym_queue.tracks[ym_queue.current_index].fetch_track()
        return ym_track
