#Summary
This utility determines other Lego sets you can build based on the Lego sets you own. In order to do so, you need to:
- Create an account at Brickset.com (it's a really nice website anyway if you like Lego)
- Add Lego sets to your collection in Brickset.com
- Get a Brickset.com API key. You can get one at https://brickset.com/tools/webservices/requestkey. They will send you
a key to your email address in a matter of seconds/minutes

#Installation

Clone this repo:
```
git clone https://github.com/amcarvalho/lego-finder
```

Install requirements (it's a good idea to do this within a python virtual environment):
```
pip install -r requirements.txt
```

# Usage
    python set_finder.py <brickset_username> <brickset_password> <brickset_api_key> [-p PERCENTAGE] [-m MIN_PARTS] [-c] [-r]

    Arguments:
        brickset_username       Your account/username on Brickset.com
        brickset_password       Your account password on Brickset.com
        brickset_api_key        Your Brickset.com API key. Get a key at: https://brickset.com/tools/webservices/requestkey

    Options:
        -h --help                                       Show this screen.
        -r --reload_inventory                           Rebuilds inventory DB. Do this once in a while when Lego releases
                                                        new sets [default=False].
        -c --color_match_disabled                       If set, it will return sets where you have all the parts but some
                                                        of them will not match colors [default=False].
        -p PERCENTAGE --percentage_min_match=PERCENTAGE Yields sets where you have at least a percentage of all parts
                                                        [default=95].
        -m MIN_PARTS --min_parts=MIN_PARTS              Filters results by sets with at least MIN_PARTS. [default=10]
