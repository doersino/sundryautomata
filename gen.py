# setup: install cairo (your package manager should have it), then pip3 install cairocffi
# (note to self: on uberspace, cairo is already provided, and the --user flag is needed as the last parameter to pip3)
# usage: python3 gen.py
# based on: https://github.com/doersino/cellular-automata-posters

import sys
import math
import random
import datetime
import cairocffi as cairo

seed = random.randrange(sys.maxsize)
random.seed(seed)

#TODO while True:

# select at random: either one of the well-known, "small" rules below 256, or (with probabilitly 2/3) a large one
smallRules = 0 == random.randint(0,2)
if (smallRules):
    rule = random.randint(0,255)
else:
    rule = random.randint(256,4294967296)

initialCondition = 'random'

cellShape = 'square'  # 'square'  → □
                      # 'circle'  → ◯ (Note that this hides the grid, see
                      #                gridMode option below.)

width  = random.randint(120,240)  # Width (in cells) of the grid, may be
                                  # increased if a non-zero rotation angle is
                                  # set. Height (number of generations) will be
                                  # computed based on this and the image size.

offset = 0  # From which generation on should the states be shown? Handy for
            # rules that take a few generations to converge to a nice repeating
            # pattern. Can also be a decimal number (e.g. 10.5) or negative to
            # adjust the vertical display offset.

angle = random.randint(-20,20)  # Rotation angle in degrees (tested between -45°
                                # and 45°). To fill the resulting blank spots in
                                # the corners, the dimensions of the grid are
                                # increased to keep the displayed cell size
                                # constant (as opposed to scaling up the grid).

colorScheme = random.randint(0,23)  # An index into the colorSchemes list
                                    # defined further down or a tuple of the
                                    # form "('#ffe183', '#ffa24b')", with the
                                    # first element being the living cell color
                                    # and the second element being the dead cell
                                    # color.

gridMode = ['dead', 'dead', 'living'][random.randint(0,2)]  # 'living' or
                                                            # 'dead' to make the
                                                            # grid take on the
                                                            # color of the
                                                            # corresponding
                                                            # cells.

imageWidth  = 900  # ⎤ Image dimensions in pixels. 900×900 is the maximum such
imageHeight = 900  # ⎦ that Twitter doesn't convert to JPEG.

filename = 'out.png'  # Output PDF filename.


###########
# LOGGING #
###########

def log(s):
    with open("gen.log", "a") as logfile:
        logfile.write(str(datetime.datetime.now()) + " " + s + "\n")

log("seed " + str(seed))
log("rule " + str(rule))
log("initialCondition " + str(initialCondition))
log("cellShape " + str(cellShape))
log("width " + str(width))
log("offset " + str(offset))
log("angle " + str(angle))
log("colorScheme " + str(colorScheme))
log("gridMode " + str(gridMode))
log("imageWidth " + str(imageWidth))
log("imageHeight " + str(imageHeight))
log("filename " + str(filename))

######################
# OPTIONS PROCESSING #
######################


colorSchemes = [
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
generationOffset = max(0, int(offset))
displayOffset    = offset - generationOffset

# dimensions
height = math.ceil((imageHeight / imageWidth) * width)
if displayOffset > 0:
    height += 1

# rotation
angle = math.radians(angle)
requiredimageWidth  = math.sin(abs(angle)) * imageHeight + math.cos(abs(angle)) * imageWidth
requiredimageHeight = math.sin(abs(angle)) * imageWidth  + math.cos(abs(angle)) * imageHeight

translation = ((requiredimageWidth - imageWidth) / 2,
               (requiredimageHeight - imageHeight) / 2)

originalWidth = width
width  = math.ceil(width * requiredimageWidth / imageWidth)
height = math.ceil(height * requiredimageHeight / imageHeight)

# color scheme selection
if isinstance(colorScheme, int):
    colors = colorSchemes[colorScheme]
else:
    colors = colorScheme

torgb = lambda hex: tuple(int((hex.lstrip('#'))[i:i+2], 16)/255 for i in (0, 2, 4))
livingColor, deadColor = map(torgb, colors)

# grid
if gridMode == 'living':
    gridColor = livingColor
elif gridMode == 'dead':
    gridColor = deadColor


######################
# CELLULAR AUTOMATON #
######################

# compute width (i.e. number of cells) of current state to consider
currentStateWidth = max(3, math.ceil(math.log2(math.log2(rule+1))))

# convert rule to binary and pad to required length
ruleBinary = format(rule, 'b').zfill(int(math.pow(2,currentStateWidth)))

# compute transistions, i.e. set up mapping from each possible current
# configuration to the rule-defined next state
transistions = {bin(currentState)[2:].zfill(currentStateWidth): resultingState for currentState, resultingState in enumerate(reversed(ruleBinary))}

# generate initial state
if initialCondition == 'middle':
    initialState = list('0' * width)
    initialState[int(width/2)] = '1'
elif initialCondition == 'left':
    initialState = '1' + '0' * (width-1)
elif initialCondition == 'right':
    initialState = '0' * (width-1) + '1'
elif initialCondition == 'random':
    initialState = [str(random.randint(0,1)) for b in range(0,width)]
else:
    initialState = (initialCondition[0:width])[::-1].zfill(width)[::-1]

log('Initial state: ' + ''.join(initialState))
grid = [''.join(initialState)]  # list of sucessive states

# run ca to generate grid
log('Running rule {} cellular automaton...'.format(rule))
for y in range(0, height + generationOffset):
    currentState = grid[y]
    #log(currentState)
    currentStatePadded = currentState[-math.floor(currentStateWidth/2):width] + currentState + currentState[0:currentStateWidth-math.floor(currentStateWidth/2)-1]

    nextState = ''
    for x in range(0, width):
        pattern = currentStatePadded[x:x+currentStateWidth]
        nextState += transistions[pattern]
    grid.append(nextState)


###########
# DRAWING #
###########

grid = grid[generationOffset:]  # discard any unwanted generations

cellSize = imageWidth / originalWidth
xPositions = [x * cellSize - translation[0] for x in range(0,width)]
yPositions = [(y - displayOffset) * cellSize - translation[1] for y in range(0,height+1)]

log('Drawing...')

surface = cairo.ImageSurface(cairo.FORMAT_RGB24, imageWidth, imageHeight)
context = cairo.Context(surface)

# fill with background color
with context:
    context.set_source_rgb(deadColor[0], deadColor[1], deadColor[2])
    context.paint()

# draw cells and grid
context.set_line_width(cellSize / 16)
context.translate(imageWidth / 2, imageHeight / 2)
context.rotate(angle)
context.translate(-imageWidth / 2, -imageHeight / 2)
for y, row in enumerate(grid):
    #log('Drawing row {}/{}...'.format(y, height))
    for x, cell in enumerate(row):
        xP = xPositions[x]
        yP = yPositions[y]
        if cell == '1':
            context.set_source_rgb(livingColor[0], livingColor[1], livingColor[2])
            if cellShape == 'square':
                context.rectangle(xP, yP, cellSize, cellSize)
            else:
                context.arc(xP + cellSize / 2, yP + cellSize / 2, cellSize / 2, 0, 2*math.pi)
            context.fill()
        if gridColor is not None and cellShape == 'square':
            context.set_source_rgb(gridColor[0], gridColor[1], gridColor[2])
            context.rectangle(xP, yP, cellSize, cellSize)
            context.stroke()
context.translate(imageWidth / 2, imageHeight / 2)
context.rotate(-angle)
context.translate(-imageWidth / 2, -imageHeight / 2)

log('Writing to "{}"...'.format(filename))
surface.write_to_png(filename)

log('-' * 42)
