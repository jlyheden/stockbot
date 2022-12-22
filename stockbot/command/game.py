from . import root_command, Command, BlockingExecuteCommand, ProxyCommand
from epicstore_api import EpicGamesStoreAPI
from datetime import datetime
import logging

LOGGER = logging.getLogger(__name__)


def _get_free_games():
    api = EpicGamesStoreAPI()
    free_games = api.get_free_games()['data']['Catalog']['searchStore']['elements']

    # Few odd items do not seems game and don't have the promotion attribute, so let's check it !
    free_games = list(sorted(
        filter(
            lambda g: g.get('promotions'),
            free_games
        ),
        key=lambda g: g['title']
    ))
    return free_games


def get_latest_free_game(*args, **kwargs):
    response = []
    try:
        for free_game in _get_free_games():
            LOGGER.debug(free_game)
            game_promotions = free_game['promotions']['promotionalOffers']
            game_url = f"https://store.epicgames.com/en-US/p/{free_game['productSlug']}"
            if game_promotions and free_game['price']['totalPrice']['discountPrice'] == 0:
                promotion_data = game_promotions[0]['promotionalOffers'][0]
                start_date_iso, end_date_iso = (
                    promotion_data['startDate'], promotion_data['endDate']
                )
                end_date_datetime = datetime.strptime(end_date_iso, "%Y-%m-%dT%H:%M:%S.%f%z")
                response.append(f"Game: {free_game['title']}, URL: {game_url}, Ends at: {end_date_datetime.astimezone()}")
    except Exception as e:
        LOGGER.exception("failed to get free games", e)
        return "Something broke"
    else:
        if len(response) == 0:
            return "Nothing free today"
        elif len(response) == 1:
            return response[0]
        else:
            return response


game_command = Command(name="game", short_name="g")
epic_command = Command(name="epic", short_name="e")
epic_command.register(BlockingExecuteCommand(name="now", short_name="n", execute_command=get_latest_free_game,
                                             expected_num_args=0))
game_command.register(epic_command)
root_command.register(game_command)
root_command.register(ProxyCommand(name="epic", proxy_command=("game", "epic", "now"), help="",
                                   expected_num_args=0))

