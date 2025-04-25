from . import root_command, Command, BlockingExecuteCommand
from ..service.reddit import RedditFreeGamesService
from ..db import Session
from ..configuration import configuration
import logging

LOGGER = logging.getLogger(__name__)


def get_latest_free_games_reddit(*args, **kwargs):
    response = []
    try:
        with Session() as session:
            reddit_service = RedditFreeGamesService(ignore_words=configuration.game_ignore_list)
            reddit_service.refresh(session)
            free_games = reddit_service.gimme(session)
            for free_game in free_games:
                title = free_game.title.replace(": ", " ")
                if len(title) > 200:
                    title = f"{title[:200]}..."
                response.append(f"Game: {title}, URL: {free_game.link}, Published: {free_game.published}")
        return response
    except Exception as e:
        LOGGER.exception("failed to get free reddit games", e)
        return "Something broke"


game_command = Command(name="game", short_name="g")
game_command.register(BlockingExecuteCommand(name="reddit", execute_command=get_latest_free_games_reddit,
                                             expected_num_args=0))
root_command.register(game_command)
