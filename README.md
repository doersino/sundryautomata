# sundryautomata

*A simple-ish Twitter bot that posts pretty pictures of cellular automata.*

The 1D cellular automaton generation is based on a [previous project of mine](https://github.com/doersino/cellular-automata-posters/), while the tweeting and logging part is adapted from [another project of mine](https://github.com/doersino/aerialbot/). Everything is a remix.

#### Check it out at [@sundryautomata](https://twitter.com/sundryautomata)!

![](screenshot.png)


## Setup

The most vital dependency, apart from [Python 3](https://www.python.org) which the bot is written in, is [Cairo](https://www.cairographics.org). You'll need to figure out how to install it on your system yourself, but chances are that it's available through your package manager. In fact, it might already be installed and you don't have to do anything!

Assuming things have gone smoothly so far, let's proceed – I suggest using the `venv` module (which is conveniently included in your Python installation) to avoid dependency hell. Run the following commands to get the bot installed on your system:

```bash
$ git clone https://github.com/doersino/sundryautomata
$ python3 -m venv sundryautomata
$ cd sundryautomata
$ source bin/activate
$ pip3 install -r requirements.txt
```

(To deactivate the virtual environment, run `deactivate`.)


### Configuration

Copy `config.sample.ini` to `config.ini`, open it and modify it based on the instructions in the comments. Most notably, fill in your Twitter API keys and secrets (but the bot will still generate images without those).


### Running

Once you've set everything up and configured it to your liking, run:

```bash
$ python3 sundryautomata.py
```

That's basically it!

If you want your bot to tweet at predefined intervals, use `cron`, [`runwhen`](http://code.dogmap.org/runwhen/) or a similar tool. To make `cron` work with `venv`, you'll need to use bash and execute the `activate` script before running the bot (in this example, it runs every six hours at 42 minutes past the hour):

```
42 */6 * * * /usr/bin/env bash -c 'cd /PATH/TO/sundryautomata && source bin/activate && python3 sundryautomata.py'
```
