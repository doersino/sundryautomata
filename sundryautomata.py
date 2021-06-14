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

seed = "%.20f" % time.time()
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

class ColorHSL():
    """
    HSL colors, convertable from RGB. Via https://stackoverflow.com/a/17433060.
    """

    def __init__(self, h, s, l):
        self.h = h
        self.s = s
        self.l = l

    def __repr__(self):
        return f"ColorHSL({self.h}, {self.s}, {self.l})"

    @classmethod
    def from_rgb(cls, rgb):
        r = rgb.r / 255
        g = rgb.g / 255
        b = rgb.b / 255
        c_max = max(r, g, b)
        c_min = min(r, g, b)
        delta = c_max - c_min
        l = (c_max + c_min) / 2
        h = 0
        s = 0

        if delta == 0:
            h = 0
        elif c_max == r:
            h = 60 * (((g - b) / delta) % 6)
        elif c_max == g:
            h = 60 * (((b - r) / delta) + 2)
        else:
            h = 60 * (((r - g) / delta) + 4)

        if delta == 0:
            s = 0
        else:
            s = (delta / (1 - abs(2 * l - 1)))

        return cls(h, s, l)

class ColorRGB():
    """
    RGB colors, convertable from HSL and adjustable. Via
    https://stackoverflow.com/a/17433060.
    """

    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __repr__(self):
        return f"ColorRGB({self.r}, {self.g}, {self.b})"

    def filename_style(self):
        return f"r{self.r}g{self.g}b{self.b}"

    @classmethod
    def random(cls):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)

        return cls(r, g, b)

    @classmethod
    def from_hsl(cls, hsl):
        h = hsl.h
        s = hsl.s
        l = hsl.l
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60 ) % 2 - 1))
        m = l - c / 2
        r = None
        g = None
        b = None

        if h < 60:
            r = c
            g = x
            b = 0
        elif h < 120:
            r = x
            g = c
            b = 0
        elif h < 180:
            r = 0
            g = c
            b = x
        elif h < 240:
            r = 0
            g = x
            b = c
        elif h < 300:
            r = x
            g = 0
            b = c
        else:
            r = c
            g = 0
            b = x

        r = max(0, math.floor((r + m) * 255))
        g = max(0, math.floor((g + m) * 255))
        b = max(0, math.floor((b + m) * 255))

        return cls(r, g, b)

    def hue_shifted(self, degrees):
        """Shifts the hue of a copy by a number of degrees."""

        hsl = ColorHSL.from_rgb(self)
        hsl.h += degrees
        if hsl.h > 360:
            hsl.h -= 360
        elif hsl.h < 0:
            hsl.h += 360
        return ColorRGB.from_hsl(hsl)

    def saturation_shifted(self, offset):
        """Shifts the saturation of a copy by an offset in [-1, 1]."""

        hsl = ColorHSL.from_rgb(self)
        hsl.s += offset
        if hsl.s > 1.0:
            hsl.s = 1.0
        elif hsl.s < 0.0:
            hsl.s = 0.0
        return ColorRGB.from_hsl(hsl)

    def lightness_shifted(self, offset):
        """Shifts the lightness of a copy by an offset in [-1, 1]."""

        hsl = ColorHSL.from_rgb(self)
        hsl.l += offset
        if hsl.l > 1.0:
            hsl.l -= 1.1
        elif hsl.l < 0.0:
            hsl.l = 0.0
        return ColorRGB.from_hsl(hsl)

    def distance_to(self, other):
        """
        Unscientific, ad-hoc perceptual distance score between two colors,
        ranges between 0 and 1. This is used to make sure foreground and
        background colors aren't too similar.
        """

        self_hsl = ColorHSL.from_rgb(self)
        other_hsl = ColorHSL.from_rgb(other)

        score = 0
        score += 0.15 * abs(self_hsl.h - other_hsl.h) / 360
        score += 0.25 * abs(self_hsl.s - other_hsl.s)
        score += 0.45 * abs(self_hsl.l - other_hsl.l)
        score += 0.05 * abs(self.r - other.r) / 255
        score += 0.05 * abs(self.g - other.g) / 255
        score += 0.05 * abs(self.b - other.b) / 255

        return score

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
    width = random.randint(50, 350)

    # From which generation on should the states be shown? Handy for rules
    # that take a few generations to converge to a nice repeating pattern.
    # Can also be a decimal number (e.g. 10.5) or negative to adjust the
    # vertical display offset.
    offset = 0

    # Rotation angle in degrees (tested between -45° and 45°). To fill the
    # resulting blank spots in the corners, the dimensions of the grid are
    # increased to keep the displayed cell size constant (as opposed to scaling
    # up the grid). Here, the angle is kept zero with a probability of 1/10, and
    # around ±4-35 degrees otherwise.
    angle = 0
    if 0 != random.randint(0, 9):
        angle = random.randint(4, 35)
        if bool(random.getrandbits(1)):
            angle = -angle

    # 'living' or 'dead' to make the grid take on the color of the
    # corresponding cells.
    grid_mode = 'dead'


    ######################
    # OPTIONS PROCESSING #
    ######################

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

    # color scheme generation, while making sure the color of dead cells differs
    # sufficiently from the living cell color (which doesn't work super well for
    # dark colors, but it's better than nothing)
    living_color = ColorRGB.random()
    dead_color = living_color
    print(living_color)
    while dead_color.distance_to(living_color) < 0.2:
        dead_color = living_color.saturation_shifted(random.random() - 0.5)

        # rarely shift hue a lot, mostly a little
        dead_hue_shift = 0
        if random.random() > 0.9:
            dead_hue_shift = random.randint(0, 360)
        else:
            dead_hue_shift = random.randint(0, 40) - 20
        dead_color.hue_shifted(dead_hue_shift)

        # push dead color for dark and bright living colors towards the middle
        living_lightness = ColorHSL.from_rgb(living_color).l
        if living_lightness < 0.1:
            dead_color = dead_color.lightness_shifted(0.2 + random.random() / 2)
        elif living_lightness > 0.9:
            dead_color = dead_color.lightness_shifted(-(0.2 + random.random() / 2))
        else:
            dead_color = dead_color.lightness_shifted(random.random() - 0.5)

        print(dead_color)
        print(dead_color.distance_to(living_color))

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
    LOGGER.debug("living_color=" + str(living_color))
    LOGGER.debug("dead_color=" + str(dead_color))
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

        # select rule: either one of the well-known, "small" rules below 256,
        # or with higher probability a "large" one.
        small_rules = 0 == random.randint(0, 9)
        if small_rules:
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
        context.set_source_rgb(dead_color.r / 255, dead_color.g / 255, dead_color.b / 255)
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
                context.set_source_rgb(living_color.r / 255, living_color.g / 255, living_color.b / 255)
                context.rectangle(xp, yp, cell_size, cell_size)
                context.fill()
            context.set_source_rgb(grid_color.r / 255, grid_color.g / 255, grid_color.b / 255)
            context.rectangle(xp, yp, cell_size, cell_size)
            context.stroke()
    context.translate(image_width / 2, image_height / 2)
    context.rotate(-angle)
    context.translate(-image_width / 2, -image_height / 2)

    LOGGER.info("Writing image to disk...")
    image_path = image_path_template.format(
        datetime=datetime.today().strftime("%Y-%m-%dT%H.%M.%S"),
        rule=rule,
        seed=seed,
        living_color=living_color.filename_style(),
        dead_color=dead_color.filename_style()
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
