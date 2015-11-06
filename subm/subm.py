import csv
import argparse
import sys
from datetime import timedelta
import os

import arrow
import praw
from praw.helpers import flatten_tree
from praw.errors import HTTPException, Forbidden, NotFound
from retry.api import retry_call
from requests.exceptions import ReadTimeout


VERSION = '0.0.1'
reddit = praw.Reddit(user_agent='subm/{}'.format(VERSION))


def split_time(begin, end, delta):
    a = begin + timedelta(seconds=1)  # avoid overlap
    b = begin + delta
    while True:
        if end < b:
            b = end
        yield a, b

        if end <= b:
            return

        a += delta
        b += delta


def get_submissions(subreddits, begin, end):
    assert begin < end
    # 期間をしても過不足のある結果が帰ってくるため範囲を大きめに指定する
    a_begin, a_end = begin.replace(days=-1), end.replace(days=+1)
    subrs = '+'.join(subreddits)

    # TODO: When it was 1,000 or more per unit time , leak acquired .
    for a, b in split_time(a_begin, a_end, timedelta(days=1)):
        query = 'timestamp:{}..{}'.format(a.timestamp, b.timestamp)

        # For more than 900 , there are data not returned.
        subms = request_with_retry(reddit.search, query, subrs,
                                   sort='new', limit=1000, syntax='cloudsearch')

        subms = sorted(subms, key=lambda s: s.created_utc)
        for s in subms:
            if begin.timestamp <= s.created_utc <= end.timestamp:
                # `s.created` is shifted slightly in the compared with local
                yield s


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
                      exceptions=(ServerError, ReadTimeout),
                      delay=60, jitter=60, max_delay=60 * 5)


def get_comments(subm):
    request_with_retry(subm.replace_more_comments, limit=None)

    comms = subm.comments
    flatten_comms = flatten_tree(comms)
    return flatten_comms


def submission_to_dict(subm):
    attrs = [
        'author_flair_css_class',
        'author_flair_text',
        'created',
        'created_utc',
        'domain',
        'id',
        'is_self',
        'link_flair_css_class',
        'link_flair_text',
        'locked',
        'media',
        'media_embed',
        'name',
        'num_comments',
        'over_18',
        'permalink',
        'score',
        'selftext',
        'selftext_html',
        'thumbnail',
        'title',
        'url',
        'edited',
        'distinguished',
        'stickied',
    ]
    ret = {}
    for a in attrs:
        ret[a] = getattr(subm, a)

    if not ret['media_embed']:
        ret['media_embed'] = None  # delete empty dict

    ret['subreddit'] = subm.subreddit.display_name
    ret['author'] = subm.author.name

    return ret

submission_keys = sorted([
    'author',
    'author_flair_css_class',
    'author_flair_text',
    'created',
    'created_utc',
    'domain',
    'distinguished',
    'edited',
    'id',
    'is_self',
    'link_flair_css_class',
    'link_flair_text',
    'locked',
    'media',
    'media_embed',
    'name',
    'num_comments',
    'over_18',
    'permalink',
    'score',
    'selftext',
    'selftext_html',
    'stickied',
    'subreddit',
    'thumbnail',
    'title',
    'url',
])
# keys that are not menthoned(clicked, hidden, likes, saved)
# are for logged in users.


def comment_to_dict(comm):
    attrs = [
        'author_flair_css_class',
        'author_flair_text',
        'body',
        'body_html',
        'created',
        'created_utc',
        'edited',
        'gilded',
        'id',
        'name',
        'num_reports',
        'parent_id',
        'score',
        'score_hidden',
        'distinguished',
    ]
    ret = {}
    for a in attrs:
        ret[a] = getattr(comm, a)

    subm = comm.submission
    ret['link_author'] = subm.author.name
    ret['link_id'] = subm.id
    ret['link_title'] = subm.title
    ret['link_url'] = subm.url
    ret['subreddit'] = subm.subreddit.display_name

    ret['author'] = comm.author.name if comm.author else None

    ret['replies'] = ' '.join(r.name for r in comm.replies)
    return ret

comment_keys = sorted([
    'author',
    'author_flair_css_class',
    'author_flair_text',
    'body',
    'body_html',
    'created',
    'created_utc',
    'distinguished',
    'edited',
    'gilded',
    'id',
    'name',
    'link_author',
    'link_id',
    'link_title',
    'link_url',
    'num_reports',
    'parent_id',
    'replies',
    'score',
    'score_hidden',
    'subreddit',
])
# keys that are not mentioned(approved_by, banned_by, likes, saved)
# are for logged in or mod users.


class CSVWriter:

    def __init__(self, fields, file):
        self.writer = csv.DictWriter(file, fields)
        self.writer.writeheader()

    def write(self, d):
        self.writer.writerow(d)


class Progress:

    def __init__(self, max_value, width):
        self.max_value = max_value
        self.width = width
        self.num = 0

    def update(self, now):
        self.num += 1
        done = int(round(now / self.max_value * self.width))
        blank = self.width - done

        bar = '[{}{}] {}'.format('=' * done, ' ' * blank, self.num)
        sys.stderr.write('\r' + bar)
        sys.stderr.flush()


def download(subreddits, begin, end, subm_writer, comm_writer, is_comment):
    max_value = end.timestamp - begin.timestamp
    progress = Progress(max_value, 50)

    subms = get_submissions(subreddits, begin, end)
    for subm in subms:
        subm_d = submission_to_dict(subm)
        subm_writer.write(subm_d)

        progress.update(subm.created_utc - begin.timestamp)

        if not is_comment:
            continue

        comms = get_comments(subm)
        for c in comms:
            comm_d = comment_to_dict(c)
            comm_writer.write(comm_d)


def parse_args():
    p = argparse.ArgumentParser(
        description='A tool downloads reddit\'s submissions and comments')
    p.add_argument('subreddit', nargs='+', help='target subreddits')
    p.add_argument('time',
                   help='submission period (example: "2015-09-08", "2015-09-02,2015-09-12")')
    p.add_argument('-c', '--comment', nargs='?', const='comments.csv', default='', metavar='FILE',
                   help='file stores comments data. If not provided, it is not requested. If FILE not provided, default file is "%(const)s".')
    p.add_argument('-s', '--submission', default='submissions.csv', metavar='FILE',
                   help='file stores submissions data. (default: "%(default)s").')
    p.add_argument('--timezone', default='local', help='`time`\'s timezone. The default is %(default)s. (example: "+09:00", "utc")')
    p.add_argument('-e', '--encoding', default='utf-8', help='output encoding (default: "%(default)s")')

    a = p.parse_args()
    return a


def parse_time(time_str, tzinfo):
    return arrow.get(time_str, 'YYYY-MM-DD').replace(tzinfo=tzinfo)


def main():
    args = parse_args()

    time = args.time
    tz = args.timezone
    if ',' in time:
        times = time.split(',')
        begin = parse_time(times[0], tz).floor('day')
        end = parse_time(times[1], tz).ceil('day')
    else:
        begin, end = parse_time(time, tz).span('day')

    subreddits = args.subreddit
    c_out_file = args.comment
    s_out_file = args.submission
    is_comment = bool(c_out_file)
    encoding = args.encoding

    s_file = open(s_out_file, 'w', encoding=encoding, newline='')
    subm_writer = CSVWriter(submission_keys, s_file)
    if c_out_file:
        c_file = open(c_out_file, 'w', encoding=encoding, newline='')
        comm_writer = CSVWriter(comment_keys, c_file)
    else:
        c_file = open(os.devnull, 'w')
        comm_writer = None

    # we can safety ignore these warnings.
    # see https://github.com/praw-dev/praw/issues/329
    import warnings
    warnings.filterwarnings('ignore', message=r'unclosed <ssl\.SSLSocket',
                            category=ResourceWarning)
    warnings.filterwarnings('ignore', message=r'sys\.meta_path is empty',
                            category=ImportWarning)

    with s_file, c_file:
        download(subreddits, begin, end, subm_writer, comm_writer, is_comment)


if __name__ == '__main__':
    main()
