from . import root_command, Command, BlockingExecuteCommand, ProxyCommand
from ..timer import OneshotTimer
from epicstore_api import EpicGamesStoreAPI
from datetime import datetime
import logging

LOGGER = logging.getLogger(__name__)


def _get_free_games():
    rv = []
    api = EpicGamesStoreAPI(country="SE")
    free_games = api.get_free_games()['data']['Catalog']['searchStore']['elements']

    # Few odd items do not seems game and don't have the promotion attribute, so let's check it !
    free_games = list(sorted(
        filter(
            lambda g: g.get('promotions') and g.get('price'),  # Sometimes price is null and then shit falls apart
            free_games
        ),
        key=lambda g: g['title']
    ))

    for free_game in free_games:
        LOGGER.debug(free_game)
        game_promotions = free_game['promotions']['promotionalOffers']
        game_url = f"https://store.epicgames.com/en-US/p/{free_game['productSlug']}"
        if game_promotions and free_game['price']['totalPrice']['discountPrice'] == 0:
            promotion_data = game_promotions[0]['promotionalOffers'][0]
            end_date_datetime = datetime.strptime(promotion_data['endDate'], "%Y-%m-%dT%H:%M:%S.%f%z")
            rv.append({
                "name": free_game['title'],
                "url": game_url,
                "end_date": end_date_datetime
            })
    return rv


def get_latest_free_games(*args, **kwargs):
    response = []
    bot = kwargs.get('instance')
    try:
        free_games = _get_free_games()
        for free_game in free_games:
            response.append(f"Game: {free_game['name']}, URL: {free_game['url']}, Ends at: {free_game['end_date'].astimezone()}")
    except Exception as e:
        LOGGER.exception("failed to get free games", e)
        return "Something broke"
    else:
        try:
            latest_time = max([x["end_date"] for x in free_games])
            bot.ephemeral_oneshot_timers.add(OneshotTimer(("game", "epic", "now"), latest_time))
        except Exception as e:
            LOGGER.exception("failed to create the ephemeral oneshot timer", e)
        if len(response) == 0:
            return "Nothing free today"
        else:
            return response


game_command = Command(name="game", short_name="g")
epic_command = Command(name="epic", short_name="e")
epic_command.register(BlockingExecuteCommand(name="now", short_name="n", execute_command=get_latest_free_games,
                                             expected_num_args=0))
game_command.register(epic_command)
root_command.register(game_command)
root_command.register(ProxyCommand(name="epic", proxy_command=("game", "epic", "now"), help="",
                                   expected_num_args=0))

