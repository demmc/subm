# subm

This is a tool that downloads Reddit's submissions or comments.
You can get the data for the specified period without number restrictions.

## Installation

This project supports Python 3.

```sh
$ git clone https://github.com/demmc/subm
$ cd subm
$ python setup.py install
```

or

```
$ pip install https://github.com/demmc/subm/archive/master.tar.gz
```

## Usage

This downloads submissions of r/news of April 1.

```sh
$ subm news 2015-04-01
{"approved_by": null, "archived": true, "author": "WheelsOnPavement", "author_flair_css_class": null, "author_flair_text": null, "banned_by": null, "clicked": false, "created": 1427843486.0, "created_utc": 1427814686.0, "distinguished": null, "domain": "time.com", "downs": 0, "edited": false, "from": null, "from_id": null, "from_kind": null, "gilded": 0, "hidden": false, "hide_score": false, "id": "30xlna", "is_self": false, "likes": null, "link_flair_css_class": null, "link_flair_text": null, "locked": false, "media": null, "media_embed": {}, "mod_reports": [], "name": "t3_30xlna", "num_comments": 5, "num_reports": null, "over_18": false, "permalink": "/r/news/comments/30xlna/facebooks_new_office_building_has_a_park_on_the/?ref=search_posts", "quarantine": false, "removal_reason": null, "report_reasons": null, "saved": false, "score": 39, "secure_media": null, "secure_media_embed": {}, "selftext": "", "selftext_html": null, "stickied": false, "subreddit": "news", "subreddit_id": "t5_2qh3l", "suggested_sort": null, "thumbnail": "", "title": "Facebook's new office building has a park on the roof the size of 7 football fields", "ups": 39, "url": "http://time.com/3763880/facebook-campus-grass-roof/", "user_reports": [], "visited": false}
{"approved_by": null, "archived": true, "author": "hdfga", "author_flair_css_class": null, "author_flair_text": null, "banned_by": null, "clicked": false, "created": 1427843546.0, "created_utc": 1427814746.0, "distinguished": null, "domain": "stamfordadvocate.com", "downs": 0, "edited": false, "from": null, "from_id": null, "from_kind": null, "gilded": 0, "hidden": false, "hide_score": false, "id": "30xlsh", "is_self": false, "likes": null, "link_flair_css_class": null, "link_flair_text": null, "locked": false, "media": null, "media_embed": {}, "mod_reports": [], "name": "t3_30xlsh", "num_comments": 474, "num_reports": null, "over_18": false, "permalink": "/r/news/comments/30xlsh/connecticut_bans_state_trips_to_indiana_in_wake/?ref=search_posts", "quarantine": false, "removal_reason": null, "report_reasons": null, "saved": false, "score": 1486, "secure_media": null, "secure_media_embed": {}, "selftext": "", "selftext_html": null, "stickied": false, "subreddit": "news", "subreddit_id": "t5_2qh3l", "suggested_sort": null, "thumbnail": "", "title": "Connecticut bans state trips to Indiana in wake of gay discrimination law", "ups": 1486, "url": "http://www.stamfordadvocate.com/local/article/Malloy-bans-state-trips-to-Indiana-in-wake-of-gay-6168474.php", "user_reports": [], "visited": false}
...
```

This downloads submissions and comments of r/news from April 1 to April 2.
This is slow.

```sh
$ subm news 2015-04-01,2015-04-02 --comment | grep '"t1_'
{"approved_by": null, "archived": true, "author": "black_flag_4ever", "author_flair_css_class": null, "author_flair_text": null, "banned_by": null, "body": "They take FarmVille too seriously.", "body_html": "<div class=\"md\"><p>They take FarmVille too seriously.</p>\n</div>", "controversiality": 0, "created": 1427846858.0, "created_utc": 1427818058.0, "distinguished": null, "downs": 0, "edited": false, "gilded": 0, "id": "cpwrnps", "likes": null, "link_id": "t3_30xlna", "mod_reports": [], "name": "t1_cpwrnps", "num_reports": null, "parent_id": "t3_30xlna", "removal_reason": null, "replies": "", "report_reasons": null, "saved": false, "score": 8, "score_hidden": false, "stickied": false, "subreddit": "news", "subreddit_id": "t5_2qh3l", "ups": 8, "user_reports": []}
{"approved_by": null, "archived": true, "author": "Slimerbacca", "author_flair_css_class": null, "author_flair_text": null, "banned_by": null, "body": "That is pretty cool, I am jealous of a friend whose business is right on a park. ", "body_html": "<div class=\"md\"><p>That is pretty cool, I am jealous of a friend whose business is right on a park. </p>\n</div>", "controversiality": 0, "created": 1427843613.0, "created_utc": 1427814813.0, "distinguished": null, "downs": 0, "edited": false, "gilded": 0, "id": "cpwpm9g", "likes": null, "link_id": "t3_30xlna", "mod_reports": [], "name": "t1_cpwpm9g", "num_reports": null, "parent_id": "t3_30xlna", "removal_reason": null, "replies": "", "report_reasons": null, "saved": false, "score": 3, "score_hidden": false, "stickied": false, "subreddit": "news", "subreddit_id": "t5_2qh3l", "ups": 3, "user_reports": []}
...
```

## Licence

MIT
