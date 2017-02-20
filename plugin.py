###
# Copyright (c) 2007, Benjamin Rubin
# Copyright (c) 2017, Dan39
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

#import supybot.utils as utils
from supybot.commands import *
#import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
#import supybot.conf as conf
#import supybot.log as log
from apiclient.discovery import build
from apiclient.errors import HttpError

class Supytube(callbacks.Plugin):
    """Add the help for "@plugin help Supytube" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Supytube, self)
        self.__parent.__init__(irc)
        api_key = self.registryValue('api_key')
        self.service = build('youtube', 'v3', developerKey=api_key)
        self.results = {}

    def getVideoid(self, msg):
        for word in msg.args[1].split():
            if 'youtube' in word and 'v=' in word:
                pos = word.find('v=')
                return word[pos+2:pos+13]
            elif 'youtu.be' in word:
                videoid = word.split('/')[-1]
                self.log.info(videoid)
                return videoid

    def convertRating(self, video):
        likes = float(video['statistics']['likeCount'])
        dislikes = float(video['statistics']['dislikeCount'])

        rating = likes / (likes + dislikes) 

        return '{:.2%}'.format(rating)

    def doPrivmsg(self, irc, msg):
        if (self.registryValue('enable', msg.args[0]) and
                ('youtube' in msg.args[1] or 'youtu.be' in msg.args[1])):
            vid = self.getVideoid(msg)
            if vid:
                self.log.debug('videoid = {0}'.format(id))
                try:
                    results = self.service.videos().list(part='id,snippet,statistics',
                            id=vid,
                            fields='items(snippet(title),statistics)').execute()
                    video = results['items'][0]
                except HttpError as e:
                    self.log.error('Supytube.py: Error: {0}'.format(e))
                    return
                try:
                    rating = ircutils.bold(self.convertRating(video))
                except (AttributeError, ZeroDivisionError) as e:
                    rating = ircutils.bold('n/a')

                title = ircutils.bold(video['snippet']['title']).encode('utf-8', 'replace')
                views = ircutils.bold('{:,}'.format(int(video['statistics']['viewCount'])))
                reply = u'Title: {0}, Views {1}, Rating: {2}'.format(title, views, rating)
                irc.queueMsg(ircmsgs.privmsg(msg.args[0], reply))
            else:
                irc.noReply()

    def getVidInfo(self, irc, vid):
        video = self.service.videos().list(part='id,snippet,statistics',
                id=vid,
                fields='items(snippet(description,tags,title),statistics)').execute()
        video = video['items'][0]

        try:
            rating = ircutils.bold(self.convertRating(video))
        except (AttributeError, ZeroDivisionError) as e:
            rating = ircutils.bold('n/a')

        title = ircutils.bold(video['snippet']['title']).encode('utf-8', 'replace')
        views = ircutils.bold('{:,}'.format(int(video['statistics']['viewCount'])))


        irc.reply(u'https://youtu.be/{} - {}, Views {}, Rating {}'.format(vid, title, views, rating), prefixNick=False)
        irc.reply(u'\x1FDescription:\x1F {}'.format(video['snippet']['description'].replace('\n', ' ')), prefixNick=False)
        irc.reply(u'\x1FTags:\x1F {}'.format(', '.join(video['snippet']['tags'][:10])), prefixNick=False)

    def youtube(self, irc, msg, args, opts, text):
        """[-v | --views] <search string>
        Search for a youtube video. Add -v or --views to sort by view count instead of relevance"""

        orderby = 'relevance'

        for opt,val in opts:
            if opt == 'v' or opt == 'views':
                orderby = 'viewCount'

        resp = self.service.search().list(
                q=text,
                part="id,snippet",
                type="video",
                order=orderby,
                safeSearch='none',
                maxResults=20).execute()

        if len(resp['items']) == 0:
            irc.reply('No results')
            return

        self.results[msg.nick] = resp

        vid = resp['items'].pop(0)['id']['videoId']

        self.getVidInfo(irc, vid)

    youtube = wrap(youtube, [getopts({'v': '', 'views': ''}), 'text'])

    def ytn(self, irc, msg, args):
        """Grabs next youtube result"""

        if msg.nick not in self.results:
            irc.error('You havnt made a search yet')
            return

        items = self.results[msg.nick]['items']

        if len(items) == 0:
            irc.error('No more results')
            return

        vid = items.pop(0)['id']['videoId']

        self.getVidInfo(irc, vid)

    ytn = wrap(ytn)



Class = Supytube
