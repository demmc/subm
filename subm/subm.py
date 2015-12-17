import argparse
import sys
from datetime import timedelta
import logging
import json

import arrow
import praw
from praw.helpers import flatten_tree
from praw.errors import HTTPException, Forbidden, NotFound, InvalidSubreddit
from praw.objects import Submission, Comment
from retry.api import retry_call
from requests.exceptions import Timeout


VERSION = '0.1.1'
reddit = praw.Reddit(user_agent='subm/{}'.format(VERSION),
                     store_json_result='true')
logger = logging.getLogger(__name__)


class SplitTime:

    def __init__(self, begin, end):
        self._at = begin + timedelta(days=1)  # avoid overlap
        self._end = end
        self._is_end = False

    def next_time(self, delta):
        begin = self._at
        end = begin + delta
        if self._end <= end:
            end = self._end
            self._is_end = True

        self._at = begin + delta

        return begin, end

    def is_end(self):
        return self._is_end


def get_submissions(subreddit, begin, end):
    assert begin < end

    unit_days, subms = estimate_period_unit(subreddit, begin, end)
    if subms is not None:
        yield from subms
        return

    # There is timestamp offset in cloudsearch syntax.
    # In order to make up for it , extend the period .
    # see https://www.reddit.com/r/redditdev/comments/1r5wqx/is_the_timestamp_off_by_8_hours_in_cloudsearch
    a_begin, a_end = begin.replace(days=-1), end.replace(days=+1)

    # TODO: When it was 1,000 or more per unit time , leak acquired .
    times = SplitTime(a_begin, a_end)
    delta = timedelta(days=unit_days)
    while not times.is_end():
        a, b = times.next_time(delta)

        query = 'timestamp:{}..{}'.format(a.timestamp, b.timestamp)

        def search():  # for lazy loading
            # For more than 900 , there are data not returned.
            subms = reddit.search(query, subreddit, sort='new', limit=1000, syntax='cloudsearch')
            return list(subms)
        subms = request_with_retry(search)

        subms = sorted(subms, key=lambda s: s.created_utc)
        for s in subms:
            if begin.timestamp <= s.created_utc <= end.timestamp:
                # `s.created` is shifted slightly in the compared with local
                yield s

        # estimate the just the period
        per_day = len(subms) // (delta.days or 1)  # avoid zero division
        if not subms or per_day == 0:
            # the number of subm per day is unknown
            delta = timedelta(days=unit_days)
        elif per_day > 100:  # 100 is the maximum value in a time of request
            delta = timedelta(days=1)
        else:
            delta = timedelta(days=min(unit_days, 100 // per_day))


def estimate_period_unit(subreddit, begin, end):
    subr = reddit.get_subreddit(subreddit)

    def created(s): return s.created_utc

    def get_new():
        return sorted(subr.get_new(limit=100), key=created)
    subms = request_with_retry(get_new)

    if len(subms) < 100:
        # tiny subreddit
        ret = [s for s in subms if begin < arrow.get(s.created_utc) < end]
        return None, ret

    latest = max(subms, key=created)
    oldest = min(subms, key=created)
    term = timedelta(seconds=latest.created_utc - oldest.created_utc)
    if term.days == 0:
        # per day, the number of submissions is greater than 100
        return 1, None

    return term.days, None


class ServerError(Exception):
    pass


def request_with_retry(func, *args, **kwds):
    def request_wrapper():
        try:
            return func(*args, **kwds)
        except HTTPException as e:
            if isinstance(e, (Forbidden, NotFound)):
                raise
            status = e._raw.status_code  # XXX: access private field
            raise ServerError('http error occurs in status={}'.format(status))

    return retry_call(request_wrapper,
                      exceptions=(ServerError, Timeout),
                      delay=60, jitter=60, max_delay=60 * 5, logger=logger)


def get_comments(subm):
    request_with_retry(subm.replace_more_comments, limit=None)

    comms = subm.comments
    flatten_comms = flatten_tree(comms)
    return flatten_comms


class JSONEncoder(json.JSONEncoder):
    # if compact_replies is True, Comment's replies have Comment objects.
    # otherwise Comment's replies have Comment names.
    compact_replies = False

    def default(self, o):
        if isinstance(o, Submission):
            d = o.json_dict
            return d

        if isinstance(o, Comment):
            d = o.json_dict

            # remove api meta data
            replies = d.get('replies')
            if isinstance(replies, dict) and replies:
                d = dict(d)  # dont touch original dict
                children = replies['data']['children']
                if self.compact_replies:
                    d['replies'] = [c.name for c in children]
                else:
                    d['replies'] = children

            return d

        return super().default(o)


def to_json(obj):
    return json.dumps(obj, sort_keys=True, cls=JSONEncoder)


def download(subreddit, begin, end, output, is_comment):
    subms = get_submissions(subreddit, begin, end)
    for subm in subms:
        subm_d = to_json(subm)
        print(subm_d, file=output)

        if not is_comment:
            continue

        comms = get_comments(subm)
        for comm in comms:
            comm_d = to_json(comm)
            print(comm_d, file=output)


def parse_args():
    p = argparse.ArgumentParser(
        description='A tool downloads reddit\'s submissions and comments')
    p.add_argument('subreddit', help='target subreddit (example: "news", "gif+funny")')
    p.add_argument('time',
                   help='submission period (example: "20150908" "2015-9-8", "2015-09-02,2015-09-12", "0908", "9-12")')
    p.add_argument('-c', '--comment', action='store_true', help='get comments also')
    p.add_argument('--compact-replies', action='store_true', help='Comment\'s replies have only the object name (example: t1_dk58b9)')
    p.add_argument('--timezone', default='local', help='`time`\'s timezone. The default is %(default)s. (example: "+09:00", "utc")')
    p.add_argument('--version', action='version', version='subm ' + VERSION)

    a = p.parse_args()
    return a


def parse_time(time_str, tzinfo):
    fmts = [
        'YYYY-M-D',
        'YYYYMMDD',
        'M-D',
        'MMDD',
    ]
    day = arrow.get(time_str, fmts)

    if day.year == 1:
        year = arrow.get().replace(tzinfo=tzinfo).year
        day = day.replace(year=year)

    return day.replace(tzinfo=tzinfo)


def justify_period(subreddit, begin, end):
    if end - begin > timedelta(days=3):
        subr = reddit.get_subreddit(subreddit)
        begin_s = subr.created_utc

        if begin.timestamp < begin_s:
            begin = arrow.get(begin_s)
            if end <= begin:
                return None, None  # no period

    return begin, end


def main():
    args = parse_args()

    time = args.time
    tz = args.timezone
    if ',' in time:
        times = [t.strip() for t in time.split(',')]
        begin = parse_time(times[0], tz).floor('day')
        end = parse_time(times[1], tz).ceil('day')
    else:
        begin, end = parse_time(time, tz).span('day')

    subreddit = args.subreddit
    is_comment = args.comment
    output = sys.stdout
    JSONEncoder.compact_replies = args.compact_replies

    # we can safety ignore these warnings.
    # see https://github.com/praw-dev/praw/issues/329
    import warnings
    warnings.filterwarnings('ignore', message=r'unclosed <ssl\.SSLSocket',
                            category=ResourceWarning)
    warnings.filterwarnings('ignore', message=r'sys\.meta_path is empty',
                            category=ImportWarning)

    try:
        begin, end = justify_period(subreddit, begin, end)
        if begin is None:
            return  # no period

        with output:
            download(subreddit, begin, end, output, is_comment)
    except (NotFound, InvalidSubreddit):
        print('not found:', subreddit, file=sys.stderr)
    except Forbidden:
        print('forbidden:', subreddit, file=sys.stderr)
    else:
        return

    sys.exit(1)

if __name__ == '__main__':
    main()
