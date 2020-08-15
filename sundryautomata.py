import sys
import math
import random
import time
from datetime import datetime

import logging
import logging.config
import traceback

import cairocffi as cairo

from configobj import ConfigObj

import tweepy

seed = time.time_ns()
random.seed()

LOGGER = None
VERBOSITY = None

class Log:
    """
    A simplifying wrapper around the parts of the logging module that are
    relevant here, plus some minor extensions. Goal: Logging of warnings
    (depending on verbosity level), errors and exceptions on stderr, other
    messages (modulo verbosity) on stdout, and everything (independent of
    verbosity) in a logfile.
    """

    def __init__(self, logfile):

        # name and initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # via https://stackoverflow.com/a/36338212
        class LevelFilter(logging.Filter):
            def __init__(self, low, high):
                self.low = low
                self.high = high
                logging.Filter.__init__(self)
            def filter(self, record):
                return self.low <= record.levelno <= self.high

        # log errors (and warnings if a higher verbosity level is dialed in) on
        # stderr
        eh = logging.StreamHandler()
        if VERBOSITY == "quiet":
            eh.setLevel(logging.ERROR)
        else:
            eh.setLevel(logging.WARNING)
        eh.addFilter(LevelFilter(logging.WARNING, logging.CRITICAL))
        stream_formatter = logging.Formatter('%(message)s')
        eh.setFormatter(stream_formatter)
        self.logger.addHandler(eh)

        # log other messages on stdout if verbosity not set to quiet
        if VERBOSITY != "quiet":
            oh = logging.StreamHandler(stream=sys.stdout)
            if VERBOSITY == "deafening":
                oh.setLevel(logging.DEBUG)
            elif VERBOSITY == "verbose":
                oh.setLevel(logging.INFO)
            oh.addFilter(LevelFilter(logging.DEBUG, logging.INFO))
            stream_formatter = logging.Formatter('%(message)s')
            oh.setFormatter(stream_formatter)
            self.logger.addHandler(oh)

        # log everything to file independent of verbosity
        if logfile is not None:
            fh = logging.FileHandler(logfile)
            fh.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
            fh.setFormatter(file_formatter)
            self.logger.addHandler(fh)

    def debug(self, s): self.logger.debug(s)
    def info(self, s): self.logger.info(s)
    def warning(self, s): self.logger.warning(s)
    def error(self, s): self.logger.error(s)
    def critical(self, s): self.logger.critical(s)

    def exception(self, e):
        """
        Logging of game-breaking exceptions, based on:
        https://stackoverflow.com/a/40428650
        """

        e_traceback = traceback.format_exception(e.__class__, e, e.__traceback__)
        traceback_lines = []
        for line in [line.rstrip('\n') for line in e_traceback]:
            traceback_lines.extend(line.splitlines())
        for line in traceback_lines:
            self.critical(line)
        sys.exit(1)

class Tweeter:
    """Basic class for tweeting images, a simple wrapper around tweepy."""

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):

        # for references, see:
        # http://docs.tweepy.org/en/latest/api.html#status-methods
        # https://developer.twitter.com/en/docs/tweets/post-and-engage/guides/post-tweet-geo-guide
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

    def upload(self, path):
        """Uploads an image to Twitter."""

        return self.api.media_upload(path)

    def tweet(self, text, media):
        self.api.update_status(text, media_ids=[media.media_id])

def main():
    global VERBOSITY
    global LOGGER

    # load configuration either from config.ini or from a user-supplied file
    # (the latter option is handy if you want to run multiple instances of
    # sundryautomata with different configurations, for whatever reason)
    configpath = "config.ini"
    if (len(sys.argv) == 2):
        configpath = sys.argv[1]
    config = ConfigObj(configpath, unrepr=True)

    # first of all, set up logging at the correct verbosity (and make the
    # verbosity available globally since it's needed for the progress indicator)
    VERBOSITY = config['GENERAL']['verbosity']
    logfile = config['GENERAL']['logfile']
    LOGGER = Log(logfile)

    ############################################################################

    # copy the configuration into variables for brevity
    LOGGER.info("Processing configuration...")

    image_path_template = config['GENERAL']['image_path_template']

    image_width = config['GENERAL']['image_width']
    image_height = config['GENERAL']['image_height']

    consumer_key = config['TWITTER']['consumer_key']
    consumer_secret = config['TWITTER']['consumer_secret']
    access_token = config['TWITTER']['access_token']
    access_token_secret = config['TWITTER']['access_token_secret']

    tweet_text = config['TWITTER']['tweet_text']

    # whether to enable or disable tweeting
    tweeting = all(x is not None for x in [consumer_key, consumer_secret, access_token, access_token_secret])

    ############################################################################

    # the code below, until the tweeting bit, is taken from the original version
    # of the bot. it's not great by any means, but i don't feel like pulling it
    # apart, cleaning and oiling the parts, and putting it back together, so i
    # just made some minor changes to make it work with the new config and
    # logging setup

    ###########
    # OPTIONS #
    ###########

    LOGGER.info("Setting, randomizing and processing parameters...")

    # Width (in cells) of the grid, may be increased if a non-zero rotation
    # angle is set. Height (number of generations) will be computed based on
    # this and the image size.
    width = random.randint(60, 300)

    # From which generation on should the states be shown? Handy for rules
    # that take a few generations to converge to a nice repeating pattern.
    # Can also be a decimal number (e.g. 10.5) or negative to adjust the
    # vertical display offset.
    offset = 0

    # Rotation angle in degrees (tested between -45° and 45°). To fill the
    # resulting blank spots in the corners, the dimensions of the grid are
    # increased to keep the displayed cell size constant (as opposed to scaling
    # up the grid). Here, the angle is kept zero with a probability of 1/10, and
    # around ±4-20 degrees otherwise.
    angle = 0
    if 0 != random.randint(0, 9):
        angle = random.randint(4, 20)
        if bool(random.getrandbits(1)):
            angle = -angle

    # An index into the color_schemes list defined further up or a tuple of
    # the form "('#ffe183', '#ffa24b')", with the first element being the
    # living cell color and the second element being the dead cell color.
    color_scheme = random.randint(0, 23)

    # 'living' or 'dead' to make the grid take on the color of the
    # corresponding cells.
    grid_mode = ['dead', 'dead', 'living'][random.randint(0, 2)]


    ######################
    # OPTIONS PROCESSING #
    ######################

    color_schemes = [
        ('#ffe183', '#ffa24b'),
        ('#bddba6', '#83b35e'),
        ('#000000', '#b84c8c'),
        ('#000000', '#8cb84c'),
        ('#ffb1b0', '#c24848'),
        ('#fc5e5d', '#8e0033'),
        ('#4b669b', '#c0d6ff'),
        ('#cbe638', '#98ad20'),
        ('#ffe5db', '#f2936d'),
        ('#fff9db', '#f2dc6e'),
        ('#1baaef', '#0d6ca5'),
        ('#e9c3fe', '#6f5b7e'),
        ('#dddddd', '#333333'),
        ('#FC766A', '#5B84B1'),
        ('#00203F', '#ADEFD1'),
        ('#97BC62', '#2C5F2D'),
        ('#FEE715', '#101820'),
        ('#89ABE3', '#FCF6F5'),
        ('#D4B996', '#A07855'),
        ('#990011', '#FCF6F5'),
        ('#EDC2D8', '#8ABAD3'),
        ('#ccf381', '#4831d4'),
        ('#2f3c7e', '#fbeaeb'),
        ('#ec4d37', '#1d1b1b')
    ]

    # offset: split into decimal and integer part
    generation_offset = max(0, int(offset))
    display_offset = offset - generation_offset

    # dimensions
    height = math.ceil((image_height / image_width) * width)
    if display_offset > 0:
        height += 1

    # rotation
    angle = math.radians(angle)
    required_image_width = math.sin(abs(angle)) * image_height + math.cos(abs(angle)) * image_width
    required_image_height = math.sin(abs(angle)) * image_width  + math.cos(abs(angle)) * image_height

    translation = ((required_image_width - image_width) / 2,
                   (required_image_height - image_height) / 2)

    original_width = width
    width = math.ceil(width * required_image_width / image_width)
    height = math.ceil(height * required_image_height / image_height)

    # color scheme selection
    if isinstance(color_scheme, int):
        colors = color_schemes[color_scheme]
    else:
        colors = color_scheme

    torgb = lambda hex: tuple(int((hex.lstrip('#'))[i:i+2], 16)/255 for i in (0, 2, 4))
    living_color, dead_color = map(torgb, colors)

    # grid
    if grid_mode == 'living':
        grid_color = living_color
    elif grid_mode == 'dead':
        grid_color = dead_color

    # write config to log
    LOGGER.debug("seed=" + str(seed))
    LOGGER.debug("width=" + str(width))
    LOGGER.debug("offset=" + str(offset))
    LOGGER.debug("angle=" + str(angle))
    LOGGER.debug("color_scheme=" + str(color_scheme))
    LOGGER.debug("grid_mode=" + str(grid_mode))


    ######################
    # CELLULAR AUTOMATON #
    ######################

    grid = None

    # repeat the following until a rule which does not result in a stable state is
    # found or until the number of tries is exhausted
    LOGGER.info("Generating a rule...")
    rule = None

    retry = True
    remaining_tries = 3
    while retry and remaining_tries > 0:
        retry = False

        # select rule: either one of the well-known, "small" rules below 256, or with ⅔
        # probability a "large" one.
        small_rules = 0 == random.randint(0, 5)
        if (small_rules):
            rule = random.randint(0, 255)
        else:
            rule = random.randint(256, 4294967296)
        LOGGER.debug("rule=" + str(rule))

        # compute width (i.e. number of cells) of current state to consider
        current_state_width = max(3, math.ceil(math.log2(math.log2(rule+1))))

        # convert rule to binary and pad to required length
        rule_binary = format(rule, 'b').zfill(int(math.pow(2,current_state_width)))

        # compute transistions, i.e. set up mapping from each possible current
        # configuration to the rule-defined next state
        transistions = {bin(current_state)[2:].zfill(current_state_width): resulting_state for current_state, resulting_state in enumerate(reversed(rule_binary))}

        # generate initial state
        initial_state = [str(random.randint(0,1)) for b in range(0,width)]

        LOGGER.debug("initial_state=" + ''.join(initial_state))
        grid = [''.join(initial_state)]  # list of sucessive states

        # run ca to generate grid
        LOGGER.info("Simulating rule {} cellular automaton...".format(rule))
        for y in range(0, height + generation_offset):
            current_state = grid[y]
            current_state_padded = current_state[-math.floor(current_state_width/2):width] + current_state + current_state[0:current_state_width-math.floor(current_state_width/2)-1]

            next_state = ''
            for x in range(0, width):
                pattern = current_state_padded[x:x+current_state_width]
                next_state += transistions[pattern]
            grid.append(next_state)

            # retry for boring rules
            boring = next_state == current_state or next_state[1:] == current_state[:-1] or next_state[:-1] == current_state[1:]
            if boring and remaining_tries > 1:
                LOGGER.info("Rule " + str(rule) + " was boring, retrying...")
                retry = True
                remaining_tries = remaining_tries - 1
                break


    ###########
    # DRAWING #
    ###########

    grid = grid[generation_offset:]  # discard any unwanted generations

    cell_size = image_width / original_width
    x_positions = [x * cell_size - translation[0] for x in range(0, width)]
    y_positions = [(y - display_offset) * cell_size - translation[1] for y in range(0, height + 1)]

    LOGGER.info('Drawing image...')

    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, image_width, image_height)
    context = cairo.Context(surface)

    # fill with background color
    with context:
        context.set_source_rgb(dead_color[0], dead_color[1], dead_color[2])
        context.paint()

    # draw cells and grid
    context.set_line_width(cell_size / 16)
    context.translate(image_width / 2, image_height / 2)
    context.rotate(angle)
    context.translate(-image_width / 2, -image_height / 2)
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            xp = x_positions[x]
            yp = y_positions[y]
            if cell == '1':
                context.set_source_rgb(living_color[0], living_color[1], living_color[2])
                context.rectangle(xp, yp, cell_size, cell_size)
                context.fill()
            context.set_source_rgb(grid_color[0], grid_color[1], grid_color[2])
            context.rectangle(xp, yp, cell_size, cell_size)
            context.stroke()
    context.translate(image_width / 2, image_height / 2)
    context.rotate(-angle)
    context.translate(-image_width / 2, -image_height / 2)

    LOGGER.info("Writing image to disk...")
    image_path = image_path_template.format(
        datetime=datetime.today().strftime("%Y-%m-%dT%H.%M.%S"),
        rule=rule,
        seed=seed
    )
    LOGGER.debug(image_path)
    surface.write_to_png(image_path)

    ############################################################################

    if tweeting:
        LOGGER.info("Connecting to Twitter...")
        tweeter = Tweeter(consumer_key, consumer_secret, access_token, access_token_secret)

        LOGGER.info("Uploading image to Twitter...")
        media = tweeter.upload(image_path)

        LOGGER.info("Sending tweet...")
        tweet_text = tweet_text.format(rule=rule)
        LOGGER.debug("tweet_text=" + tweet_text)
        tweeter.tweet(tweet_text, media)
    else:
        LOGGER.info("Tweeting is disabled – not all of the keys and secrets have been set.")

    LOGGER.info("All done!")


if __name__ == "__main__":

    # log all exceptions
    try:
        main()
    except Exception as e:
        LOGGER.exception(e)
