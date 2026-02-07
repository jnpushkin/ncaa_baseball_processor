"""
Partner League team data: logos, stadiums, and coordinates.

Covers 4 MLB Partner Leagues:
- Pioneer League (12 teams)
- Atlantic League (10 teams)
- American Association (12 teams)
- Frontier League (18 teams)
"""

from typing import Dict, Optional, Any


# Partner League team data
# Structure: team_name -> {id, logo, stadium, lat, lng, league, city}
PARTNER_TEAM_DATA: Dict[str, Dict[str, Any]] = {
    # ========== PIONEER LEAGUE (12 teams) ==========
    'Billings Mustangs': {
        'id': 'pioneer_billings',
        'bref_team_ids': {2024: '2c7424d3'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/c/cb/Billings_Mustangs_logo.png',
        'stadium': 'Dehler Park',
        'lat': 45.7833,
        'lng': -108.5007,
        'league': 'Pioneer League',
        'city': 'Billings, MT',
    },
    'Boise Hawks': {
        'id': 'pioneer_boise',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Memorial Stadium',
        'lat': 43.6150,
        'lng': -116.2023,
        'league': 'Pioneer League',
        'city': 'Boise, ID',
    },
    'Glacier Range Riders': {
        'id': 'pioneer_glacier',
        'bref_team_ids': {2024: '7feac6a5'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/1/10/Glacier_Range_Riders_logo.png',
        'stadium': 'Glacier Bank Park',
        'lat': 48.2058,
        'lng': -114.3167,
        'league': 'Pioneer League',
        'city': 'Kalispell, MT',
    },
    'Great Falls Voyagers': {
        'id': 'pioneer_great_falls',
        'bref_team_ids': {2024: '967db685'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/5/5c/Great_Falls_Voyagers_logo.png',
        'stadium': 'Centene Stadium',
        'lat': 47.4942,
        'lng': -111.2833,
        'league': 'Pioneer League',
        'city': 'Great Falls, MT',
    },
    'Idaho Falls Chukars': {
        'id': 'pioneer_idaho_falls',
        'bref_team_ids': {2024: '2fd78fb8'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/8/84/Idaho_Falls_Chukars_cap_logo.png',
        'stadium': 'Melaleuca Field',
        'lat': 43.4926,
        'lng': -112.0401,
        'league': 'Pioneer League',
        'city': 'Idaho Falls, ID',
    },
    'Long Beach Coast': {
        'id': 'pioneer_long_beach',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Blair Field',
        'lat': 33.8303,
        'lng': -118.1517,
        'league': 'Pioneer League',
        'city': 'Long Beach, CA',
    },
    'Missoula PaddleHeads': {
        'id': 'pioneer_missoula',
        'bref_team_ids': {2024: '455f3d7e'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/a/a7/Missoula_PaddleHeads_logo.png',
        'stadium': 'Ogren Park at Allegiance Field',
        'lat': 46.8422,
        'lng': -114.0197,
        'league': 'Pioneer League',
        'city': 'Missoula, MT',
    },
    'Modesto Roadsters': {
        'id': 'pioneer_modesto',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'John Thurman Field',
        'lat': 37.6391,
        'lng': -120.9969,
        'league': 'Pioneer League',
        'city': 'Modesto, CA',
    },
    'Oakland Ballers': {
        'id': 'pioneer_oakland',
        'bref_team_ids': {2024: 'cceedd0a'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/c/c6/Oakland_Ballers_insignia.svg',
        'stadium': 'Raimondi Park',
        'lat': 37.7983,
        'lng': -122.2633,
        'league': 'Pioneer League',
        'city': 'Oakland, CA',
    },
    'Ogden Raptors': {
        'id': 'pioneer_ogden',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Lindquist Field',
        'lat': 41.1939,
        'lng': -111.9700,
        'league': 'Pioneer League',
        'city': 'Ogden, UT',
    },
    'Yuba-Sutter High Wheelers': {
        'id': 'pioneer_yuba_sutter',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Bryant Field',
        'lat': 39.1457,
        'lng': -121.5908,
        'league': 'Pioneer League',
        'city': 'Marysville, CA',
    },
    'RedPocket Mobiles': {
        'id': 'pioneer_redpocket',
        'bref_team_ids': {},
        'logo': '',
        'stadium': '',
        'lat': 0,
        'lng': 0,
        'league': 'Pioneer League',
        'city': '',
    },

    # ========== ATLANTIC LEAGUE (10 teams) ==========
    'Lancaster Stormers': {
        'id': 'atlantic_lancaster',
        'bref_team_ids': {2024: '5465d7c4'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/0/08/Lancaster_Stormers_logo.png',
        'stadium': 'Clipper Magazine Stadium',
        'lat': 40.0433,
        'lng': -76.3064,
        'league': 'Atlantic League',
        'city': 'Lancaster, PA',
    },
    'Staten Island FerryHawks': {
        'id': 'atlantic_staten_island',
        'bref_team_ids': {2024: 'aa38bc8d'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/e/ed/Staten_Island_FerryHawks_logo.png',
        'stadium': 'Staten Island University Hospital Community Park',
        'lat': 40.6413,
        'lng': -74.0764,
        'league': 'Atlantic League',
        'city': 'Staten Island, NY',
    },
    'Long Island Ducks': {
        'id': 'atlantic_long_island',
        'bref_team_ids': {2024: 'f807ac8f'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/1/19/Long_Island_Ducks_logo.png',
        'stadium': 'Fairfield Properties Ballpark',
        'lat': 40.7579,
        'lng': -73.1723,
        'league': 'Atlantic League',
        'city': 'Central Islip, NY',
    },
    'York Revolution': {
        'id': 'atlantic_york',
        'bref_team_ids': {2024: '3c8834f3'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/3/3f/York_Revolution_Logo.png',
        'stadium': 'WellSpan Park',
        'lat': 39.9630,
        'lng': -76.7311,
        'league': 'Atlantic League',
        'city': 'York, PA',
    },
    'Southern Maryland Blue Crabs': {
        'id': 'atlantic_southern_maryland',
        'bref_team_ids': {2024: '3af408c1'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/f/fc/Southern_Maryland_Blue_Crabs_logo.png',
        'stadium': 'Regency Furniture Stadium',
        'lat': 38.5930,
        'lng': -76.9330,
        'league': 'Atlantic League',
        'city': 'Waldorf, MD',
    },
    'High Point Rockers': {
        'id': 'atlantic_high_point',
        'bref_team_ids': {2024: '3540f615'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/4/4f/High_Point_Rockers_logo.png',
        'stadium': 'Truist Point',
        'lat': 35.9707,
        'lng': -79.9959,
        'league': 'Atlantic League',
        'city': 'High Point, NC',
    },
    'Charleston Dirty Birds': {
        'id': 'atlantic_charleston',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'GoMart Ballpark',
        'lat': 38.3498,
        'lng': -81.6326,
        'league': 'Atlantic League',
        'city': 'Charleston, WV',
    },
    'Gastonia Ghost Peppers': {
        'id': 'atlantic_gastonia',
        'bref_team_ids': {2024: '1b605b9e'},
        'logo': '',
        'stadium': 'CaroMont Health Park',
        'lat': 35.2480,
        'lng': -81.1793,
        'league': 'Atlantic League',
        'city': 'Gastonia, NC',
    },
    'Hagerstown Flying Boxcars': {
        'id': 'atlantic_hagerstown',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Meritus Park',
        'lat': 39.6418,
        'lng': -77.7200,
        'league': 'Atlantic League',
        'city': 'Hagerstown, MD',
    },
    'Lexington Legends': {
        'id': 'atlantic_lexington',
        'bref_team_ids': {2024: '1ecf6f2f'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/7/7c/Lexington_Legends_logo.png',
        'stadium': 'Legends Field',
        'lat': 38.0406,
        'lng': -84.4856,
        'league': 'Atlantic League',
        'city': 'Lexington, KY',
    },

    # ========== AMERICAN ASSOCIATION (12 teams) ==========
    # Note: American Association teams have year-specific bref IDs since team IDs change each season
    'Fargo-Moorhead RedHawks': {
        'id': 'aa_fargo',
        'bref_team_ids': {2024: 'bfefd5db', 2019: 'df4c2924'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/4/40/Fargo-Moorhead_RedHawks_logo.png',
        'stadium': 'Newman Outdoor Field',
        'lat': 46.8624,
        'lng': -96.8311,
        'league': 'American Association',
        'city': 'Fargo, ND',
    },
    'St. Paul Saints': {
        'id': 'aa_st_paul',
        'bref_team_ids': {2019: '9629adfd'},  # 2021+ joined MiLB as Twins AAA affiliate
        'logo': 'https://upload.wikimedia.org/wikipedia/en/7/74/St._Paul_Saints_logo.svg',
        'stadium': 'CHS Field',
        'lat': 44.9533,
        'lng': -93.0933,
        'league': 'American Association',
        'city': 'St. Paul, MN',
    },
    'Cleburne Railroaders': {
        'id': 'aa_cleburne',
        'bref_team_ids': {2024: '0e7c9a26', 2019: '545ee0ab'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/2/2f/Cleburne_Railroaders_logo.png',
        'stadium': 'La Moderna Field',
        'lat': 32.3464,
        'lng': -97.3856,
        'league': 'American Association',
        'city': 'Cleburne, TX',
    },
    'Kansas City Monarchs': {
        'id': 'aa_kansas_city',
        'bref_team_ids': {2024: 'bdea85d4'},  # Monarchs name started 2021
        'logo': 'https://upload.wikimedia.org/wikipedia/en/6/64/Kansas_City_Monarchs_logo_%282021%29.png',
        'stadium': 'Legends Field',
        'lat': 39.1189,
        'lng': -94.8311,
        'league': 'American Association',
        'city': 'Kansas City, KS',
    },
    'Kansas City T-Bones': {
        'id': 'aa_kansas_city',
        'bref_team_ids': {2019: '487af3e8'},  # Pre-2021 name
        'logo': 'https://upload.wikimedia.org/wikipedia/en/6/64/Kansas_City_Monarchs_logo_%282021%29.png',
        'stadium': 'Legends Field',
        'lat': 39.1189,
        'lng': -94.8311,
        'league': 'American Association',
        'city': 'Kansas City, KS',
    },
    'Sioux Falls Canaries': {
        'id': 'aa_sioux_falls',
        'bref_team_ids': {2024: '4f6c1644', 2019: 'c56862de'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/3/3a/Sioux_Falls_Canaries_logo.png',
        'stadium': 'Sioux Falls Stadium',
        'lat': 43.5397,
        'lng': -96.7313,
        'league': 'American Association',
        'city': 'Sioux Falls, SD',
    },
    'Winnipeg Goldeyes': {
        'id': 'aa_winnipeg',
        'bref_team_ids': {2024: '6d3f6510', 2019: 'acc1663a'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/d/d7/Winnipeg_Goldeyes_logo.png',
        'stadium': 'Blue Cross Park',
        'lat': 49.8900,
        'lng': -97.1317,
        'league': 'American Association',
        'city': 'Winnipeg, MB',
    },
    'Lincoln Saltdogs': {
        'id': 'aa_lincoln',
        'bref_team_ids': {2024: 'c0b9a510', 2019: '8d79f99c'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/5/59/Lincoln_Saltdogs_logo.png',
        'stadium': 'Haymarket Park',
        'lat': 40.8297,
        'lng': -96.7064,
        'league': 'American Association',
        'city': 'Lincoln, NE',
    },
    'Chicago Dogs': {
        'id': 'aa_chicago',
        'bref_team_ids': {2024: '6200fe39', 2019: 'cbd8a4f1'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/0/0f/Chicago_Dogs_logo.png',
        'stadium': 'Impact Field',
        'lat': 42.0031,
        'lng': -87.9778,
        'league': 'American Association',
        'city': 'Rosemont, IL',
    },
    'Gary SouthShore RailCats': {
        'id': 'aa_gary',
        'bref_team_ids': {2024: '4c11417e', 2019: '6e67ce22'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/4/48/Gary_SouthShore_RailCats_logo.png',
        'stadium': 'U.S. Steel Yard',
        'lat': 41.6106,
        'lng': -87.3361,
        'league': 'American Association',
        'city': 'Gary, IN',
    },
    'Milwaukee Milkmen': {
        'id': 'aa_milwaukee',
        'bref_team_ids': {2024: '0a96f0c4', 2019: 'aba30380'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/1/1b/Milwaukee_Milkmen_logo.png',
        'stadium': 'Franklin Field',
        'lat': 42.8989,
        'lng': -88.0378,
        'league': 'American Association',
        'city': 'Franklin, WI',
    },
    'Sioux City Explorers': {
        'id': 'aa_sioux_city',
        'bref_team_ids': {2024: 'c1c8a8c7', 2019: '99127284'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/4/4a/Sioux_City_Explorers_logo.png',
        'stadium': 'Lewis and Clark Park',
        'lat': 42.4922,
        'lng': -96.4064,
        'league': 'American Association',
        'city': 'Sioux City, IA',
    },
    'Kane County Cougars': {
        'id': 'aa_kane_county',
        'bref_team_ids': {2024: '1d070839'},  # Joined AA in 2021
        'logo': 'https://upload.wikimedia.org/wikipedia/en/1/18/Kane_County_Cougars_logo.svg',
        'stadium': 'Northwestern Medicine Field',
        'lat': 41.8639,
        'lng': -88.2872,
        'league': 'American Association',
        'city': 'Geneva, IL',
    },
    'Lake Country DockHounds': {
        'id': 'aa_lake_country',
        'bref_team_ids': {2024: '69d93443'},  # Joined AA in 2022
        'logo': 'https://upload.wikimedia.org/wikipedia/en/8/8f/Lake_Country_DockHounds_logo.png',
        'stadium': 'Wisconsin Brewing Company Park',
        'lat': 43.0119,
        'lng': -88.2308,
        'league': 'American Association',
        'city': 'Oconomowoc, WI',
    },

    # ========== FRONTIER LEAGUE (18 teams) ==========
    'Brockton Rox': {
        'id': 'frontier_brockton',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Campanelli Stadium',
        'lat': 42.0834,
        'lng': -71.0183,
        'league': 'Frontier League',
        'city': 'Brockton, MA',
    },
    'Down East Bird Dawgs': {
        'id': 'frontier_down_east',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Grainger Stadium',
        'lat': 35.2668,
        'lng': -77.5816,
        'league': 'Frontier League',
        'city': 'Kinston, NC',
    },
    'Quebec Capitales': {
        'id': 'frontier_quebec',
        'bref_team_ids': {2024: 'ea239daf'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/c/cb/Quebec_Capitales_logo.png',
        'stadium': 'Stade Canac',
        'lat': 46.8139,
        'lng': -71.2256,
        'league': 'Frontier League',
        'city': 'Quebec City, QC',
    },
    'Trois-Rivières Aigles': {
        'id': 'frontier_trois_rivieres',
        'bref_team_ids': {2024: '9a518cb2'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/9/9f/Trois-Rivi%C3%A8res_Aigles_logo.png',
        'stadium': 'Stade Quillorama',
        'lat': 46.3500,
        'lng': -72.5500,
        'league': 'Frontier League',
        'city': 'Trois-Rivières, QC',
    },
    'Ottawa Titans': {
        'id': 'frontier_ottawa',
        'bref_team_ids': {2024: 'b734e91e'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/5/5f/Ottawa_Titans_logo.png',
        'stadium': 'Ottawa Stadium',
        'lat': 45.3041,
        'lng': -75.6167,
        'league': 'Frontier League',
        'city': 'Ottawa, ON',
    },
    'New York Boulders': {
        'id': 'frontier_new_york',
        'bref_team_ids': {2024: '55ded134'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/8/8d/New_York_Boulders_logo.png',
        'stadium': 'Clover Stadium',
        'lat': 41.0781,
        'lng': -74.0122,
        'league': 'Frontier League',
        'city': 'Pomona, NY',
    },
    'Tri-City ValleyCats': {
        'id': 'frontier_tri_city',
        'bref_team_ids': {2024: 'b8d5d1ba'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/a/ae/Tri-City_ValleyCats_logo.svg',
        'stadium': 'Joseph L. Bruno Stadium',
        'lat': 42.7284,
        'lng': -73.6918,
        'league': 'Frontier League',
        'city': 'Troy, NY',
    },
    'Sussex County Miners': {
        'id': 'frontier_sussex',
        'bref_team_ids': {2024: 'cb139218'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/4/4b/Sussex_County_Miners_logo.png',
        'stadium': 'Skylands Stadium',
        'lat': 41.1264,
        'lng': -74.5917,
        'league': 'Frontier League',
        'city': 'Augusta, NJ',
    },
    'Lake Erie Crushers': {
        'id': 'frontier_lake_erie',
        'bref_team_ids': {2024: 'dc6d8175'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/8/85/Lake_Erie_Crushers_logo.png',
        'stadium': 'Crushers Stadium',
        'lat': 41.4522,
        'lng': -82.0364,
        'league': 'Frontier League',
        'city': 'Avon, OH',
    },
    'Mississippi Mud Monsters': {
        'id': 'frontier_mississippi',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Trustmark Park',
        'lat': 32.2754,
        'lng': -90.1218,
        'league': 'Frontier League',
        'city': 'Pearl, MS',
    },
    'New Jersey Jackals': {
        'id': 'frontier_nj_jackals',
        'bref_team_ids': {},
        'logo': '',
        'stadium': 'Hinchcliffe Stadium',
        'lat': 40.9168,
        'lng': -74.1718,
        'league': 'Frontier League',
        'city': 'Paterson, NJ',
    },
    'Washington Wild Things': {
        'id': 'frontier_washington',
        'bref_team_ids': {2024: 'd6734aef'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/a/ab/Washington_Wild_Things_logo.png',
        'stadium': 'Wild Things Park',
        'lat': 40.1703,
        'lng': -80.2456,
        'league': 'Frontier League',
        'city': 'Washington, PA',
    },
    'Gateway Grizzlies': {
        'id': 'frontier_gateway',
        'bref_team_ids': {2024: '1984d5fe'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/9/99/Gateway_Grizzlies_logo.png',
        'stadium': 'Grizzlies Ballpark',
        'lat': 38.6008,
        'lng': -90.1569,
        'league': 'Frontier League',
        'city': 'Sauget, IL',
    },
    'Evansville Otters': {
        'id': 'frontier_evansville',
        'bref_team_ids': {2024: 'fbb9a140'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/d/d9/Evansville_Otters_logo.png',
        'stadium': 'Bosse Field',
        'lat': 37.9878,
        'lng': -87.5422,
        'league': 'Frontier League',
        'city': 'Evansville, IN',
    },
    'Florence Y\'alls': {
        'id': 'frontier_florence',
        'bref_team_ids': {2024: '69d6ec0b'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/f/f9/Florence_Y%27alls_logo.png',
        'stadium': 'Thomas More Stadium',
        'lat': 39.0033,
        'lng': -84.6475,
        'league': 'Frontier League',
        'city': 'Florence, KY',
    },
    'Joliet Slammers': {
        'id': 'frontier_joliet',
        'bref_team_ids': {2024: 'c604917a'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/d/df/Joliet_Slammers_logo.png',
        'stadium': 'Duly Health and Care Field',
        'lat': 41.5222,
        'lng': -88.1539,
        'league': 'Frontier League',
        'city': 'Joliet, IL',
    },
    'Schaumburg Boomers': {
        'id': 'frontier_schaumburg',
        'bref_team_ids': {2024: '39d301cb'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/e/e7/Schaumburg_Boomers_logo.png',
        'stadium': 'Wintrust Field',
        'lat': 42.0231,
        'lng': -88.0817,
        'league': 'Frontier League',
        'city': 'Schaumburg, IL',
    },
    'Windy City ThunderBolts': {
        'id': 'frontier_windy_city',
        'bref_team_ids': {2024: '2ee22689'},
        'logo': 'https://upload.wikimedia.org/wikipedia/en/a/a9/Windy_City_ThunderBolts_logo.png',
        'stadium': 'Ozinga Field',
        'lat': 41.5347,
        'lng': -87.6439,
        'league': 'Frontier League',
        'city': 'Crestwood, IL',
    },
}

# Team name aliases (alternate spellings and historical names)
PARTNER_TEAM_ALIASES: Dict[str, str] = {
    # Pioneer League
    'Oakland B\'s': 'Oakland Ballers',
    'Idaho Falls': 'Idaho Falls Chukars',
    'Missoula': 'Missoula PaddleHeads',
    'Great Falls': 'Great Falls Voyagers',
    'Glacier Range': 'Glacier Range Riders',
    'Billings': 'Billings Mustangs',
    'Northern Colorado': 'Northern Colorado Owlz',
    'NoCo Owlz': 'Northern Colorado Owlz',
    'Grand Junction': 'Grand Junction Rockies',

    # Atlantic League
    'Lancaster Barnstormers': 'Lancaster Stormers',
    'Lancaster': 'Lancaster Stormers',
    'Staten Island': 'Staten Island FerryHawks',
    'Long Island': 'Long Island Ducks',
    'York': 'York Revolution',
    'Southern Maryland': 'Southern Maryland Blue Crabs',
    'High Point': 'High Point Rockers',
    'Gastonia': 'Gastonia Ghost Peppers',
    'Gastonia Honey Hunters': 'Gastonia Ghost Peppers',
    'Gastonia Baseball Club': 'Gastonia Ghost Peppers',
    'Charleston': 'Charleston Dirty Birds',
    'Hagerstown': 'Hagerstown Flying Boxcars',
    'Lexington': 'Lexington Legends',

    # American Association
    'Fargo-Moorhead': 'Fargo-Moorhead RedHawks',
    'Fargo': 'Fargo-Moorhead RedHawks',
    'RedHawks': 'Fargo-Moorhead RedHawks',
    'St. Paul': 'St. Paul Saints',
    'Saint Paul Saints': 'St. Paul Saints',
    'Saints': 'St. Paul Saints',
    'Cleburne': 'Cleburne Railroaders',
    'Railroaders': 'Cleburne Railroaders',
    'Kansas City': 'Kansas City Monarchs',
    'KC Monarchs': 'Kansas City Monarchs',
    'Monarchs': 'Kansas City Monarchs',
    'Sioux Falls': 'Sioux Falls Canaries',
    'Canaries': 'Sioux Falls Canaries',
    'Winnipeg': 'Winnipeg Goldeyes',
    'Goldeyes': 'Winnipeg Goldeyes',
    'Lincoln': 'Lincoln Saltdogs',
    'Saltdogs': 'Lincoln Saltdogs',
    'Chicago': 'Chicago Dogs',
    'Dogs': 'Chicago Dogs',
    'Gary SouthShore': 'Gary SouthShore RailCats',
    'Gary': 'Gary SouthShore RailCats',
    'RailCats': 'Gary SouthShore RailCats',
    'Milwaukee': 'Milwaukee Milkmen',
    'Milkmen': 'Milwaukee Milkmen',
    'Sioux City': 'Sioux City Explorers',
    'Explorers': 'Sioux City Explorers',
    'Kane County': 'Kane County Cougars',
    'Cougars': 'Kane County Cougars',
    'Lake Country': 'Lake Country DockHounds',
    'DockHounds': 'Lake Country DockHounds',

    # Frontier League
    'Quebec': 'Quebec Capitales',
    'Capitales': 'Quebec Capitales',
    'Trois-Rivieres': 'Trois-Rivières Aigles',
    'Trois-Rivières': 'Trois-Rivières Aigles',
    'Aigles': 'Trois-Rivières Aigles',
    'Ottawa': 'Ottawa Titans',
    'Titans': 'Ottawa Titans',
    'New York': 'New York Boulders',
    'Boulders': 'New York Boulders',
    'Tri-City': 'Tri-City ValleyCats',
    'ValleyCats': 'Tri-City ValleyCats',
    'Sussex County': 'Sussex County Miners',
    'Miners': 'Sussex County Miners',
    'Lake Erie': 'Lake Erie Crushers',
    'Crushers': 'Lake Erie Crushers',
    'Washington': 'Washington Wild Things',
    'Wild Things': 'Washington Wild Things',
    'Gateway': 'Gateway Grizzlies',
    'Grizzlies': 'Gateway Grizzlies',
    'Evansville': 'Evansville Otters',
    'Otters': 'Evansville Otters',
    'Florence': 'Florence Y\'alls',
    'Y\'alls': 'Florence Y\'alls',
    'Joliet': 'Joliet Slammers',
    'Slammers': 'Joliet Slammers',
    'Schaumburg': 'Schaumburg Boomers',
    'Boomers': 'Schaumburg Boomers',
    'Windy City': 'Windy City ThunderBolts',
    'ThunderBolts': 'Windy City ThunderBolts',
    'Empire State': 'Empire State Greys',
    'Greys': 'Empire State Greys',
    'New England': 'New England Knockouts',
    'Knockouts': 'New England Knockouts',
}


def get_canonical_team_name(team_name: str) -> str:
    """Get canonical team name from alias or exact match."""
    if team_name in PARTNER_TEAM_DATA:
        return team_name
    return PARTNER_TEAM_ALIASES.get(team_name, team_name)


def get_partner_team_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Get team data for a Partner league team."""
    canonical = get_canonical_team_name(team_name)
    return PARTNER_TEAM_DATA.get(canonical)


def get_partner_team_id(team_name: str) -> Optional[str]:
    """Get team ID for a Partner league team."""
    data = get_partner_team_data(team_name)
    return data.get('id') if data else None


def get_bref_team_id(team_name: str, year: int) -> Optional[str]:
    """
    Get Baseball Reference team ID for a Partner league team in a specific year.

    Args:
        team_name: The team name (will be canonicalized)
        year: The year to look up (e.g., 2019, 2024)

    Returns:
        The 8-character bref team ID, or None if not found
    """
    data = get_partner_team_data(team_name)
    if not data:
        return None

    bref_team_ids = data.get('bref_team_ids', {})
    if not bref_team_ids:
        return None

    # Try exact year match first
    if year in bref_team_ids:
        return bref_team_ids[year]

    # Fall back to closest available year
    available_years = sorted(bref_team_ids.keys())
    if not available_years:
        return None

    # Use the most recent year that's <= requested year, or oldest if all are newer
    closest_year = None
    for y in available_years:
        if y <= year:
            closest_year = y
    if closest_year is None:
        closest_year = available_years[0]  # Use oldest available

    return bref_team_ids.get(closest_year)


def get_partner_logo(team_name: str) -> Optional[str]:
    """Get logo URL for a Partner league team."""
    data = get_partner_team_data(team_name)
    return data.get('logo') if data else None


def get_partner_stadium_locations() -> Dict[str, Dict[str, Any]]:
    """
    Get all Partner league stadium locations for map display.

    Returns dict of stadium_name -> location data
    """
    locations = {}
    seen_stadiums = set()

    for team_name, data in PARTNER_TEAM_DATA.items():
        stadium = data.get('stadium', '')
        if not stadium or stadium in seen_stadiums:
            continue
        seen_stadiums.add(stadium)

        locations[stadium] = {
            'lat': data.get('lat'),
            'lng': data.get('lng'),
            'stadium': stadium,
            'team': team_name,
            'league': data.get('league', 'Partner'),
            'level': 'Partner',
            'type': 'partner',
            'teamId': data.get('id'),
            'logo': data.get('logo'),
            'city': data.get('city', ''),
        }

    return locations


def get_all_partner_teams() -> Dict[str, Dict[str, Any]]:
    """Get all Partner league teams organized by league."""
    by_league = {
        'Pioneer League': [],
        'Atlantic League': [],
        'American Association': [],
        'Frontier League': [],
    }

    seen_ids = set()
    for team_name, data in PARTNER_TEAM_DATA.items():
        team_id = data.get('id')
        if team_id in seen_ids:
            continue
        seen_ids.add(team_id)

        league = data.get('league', 'Unknown')
        if league in by_league:
            by_league[league].append({
                'name': team_name,
                'id': team_id,
                'logo': data.get('logo'),
                'stadium': data.get('stadium'),
                'city': data.get('city'),
            })

    return by_league
