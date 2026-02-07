"""
Minor league baseball stadium data from MLB Stats API.
Includes MiLB venues with coordinates and team IDs for logos.
"""

# Custom logo overrides for defunct teams or when mlbstatic logos fail
# Map team_id -> custom logo URL (can be local file path or web URL)
# Example:
#   537: '/path/to/local/logo.png',           # Local file
#   538: 'https://example.com/logo.svg',      # Web URL
#   539: None,                                 # Force baseball emoji fallback
LOGO_OVERRIDES = {
    # Add defunct or problematic team logos here
    # team_id: 'path/to/logo.png' or 'https://url/to/logo.svg'
    248: 'https://content.sportslogos.net/logos/45/2750/full/rkv0i6rlqgd2pxmhlsd62eu41.gif',  # Savannah Sand Gnats (defunct 2016)
}

# Historical team logo overrides - for renamed/relocated teams
# Using mlbstatic.com URLs (more reliable than sportslogos.net which blocks hotlinking)
# Map old team name -> logo URL
HISTORICAL_TEAM_LOGOS = {
    # MiLB renamed/relocated teams - use successor team's mlbstatic logo
    'Akron Aeros': 'https://www.mlbstatic.com/team-logos/402.svg',  # Now Akron RubberDucks
    'Bowie Baysox': 'https://www.mlbstatic.com/team-logos/418.svg',  # Now Chesapeake Baysox
    'Reading Phillies': 'https://www.mlbstatic.com/team-logos/522.svg',  # Now Reading Fightin Phils
    'Buies Creek Astros': 'https://www.mlbstatic.com/team-logos/3712.svg',  # Now Fayetteville Woodpeckers
    'Savannah Sand Gnats': 'https://www.mlbstatic.com/team-logos/249.svg',  # Team relocated
    'Richmond Flying Squirrels': 'https://www.mlbstatic.com/team-logos/3410.svg',
    'Great Falls Voyagers': 'https://www.mlbstatic.com/team-logos/5004.svg',
}

# MiLB Stadium coordinates: venue_name -> (latitude, longitude, team_name, level, team_id, league_name)
MILB_STADIUM_DATA = {
    'ABC Supply Stadium': (42.496763, -89.0429539, 'Beloit Sky Carp', 'A+', 554, 'Midwest League'),
    'AT&T Field': (35.05449, -85.31384, 'Chattanooga Lookouts', 'AA', 498, 'Southern League'),
    'AdventHealth Stadium': (34.285832, -85.167211, 'Rome Emperors', 'A+', 432, 'South Atlantic League'),
    'Arthur W. Perdue Stadium': (38.369979, -75.530656, 'Delmarva Shorebirds', 'A', 548, 'Carolina League'),
    'Arvest Ballpark': (36.15968, -94.194624, 'Northwest Arkansas Naturals', 'AA', 1350, 'Texas League'),
    'Atrium Health Ballpark': (35.4968555, -80.6282677, 'Kannapolis Cannon Ballers', 'A', 487, 'Carolina League'),
    'AutoZone Park': (35.14297, -90.04924, 'Memphis Redbirds', 'AAA', 235, 'International League'),
    'Avista Stadium': (47.661351, -117.344426, 'Spokane Indians', 'A+', 486, 'Northwest League'),
    'Bank of the James Stadium': (37.3930099, -79.1661, 'Lynchburg Hillcats', 'A', 481, 'Carolina League'),
    'Banner Island Ballpark': (37.954863, -121.297357, 'Stockton Ports', 'A', 524, 'California League'),
    'BayCare Ballpark': (27.97159, -82.731714, 'Clearwater Threshers', 'A', 566, 'Florida State League'),
    'Blue Wahoos Stadium': (30.4048409, -87.2188349, 'Pensacola Blue Wahoos', 'AA', 4124, 'Southern League'),
    'Bowling Green Ballpark': (36.9957207, -86.4411401, 'Bowling Green Hot Rods', 'A+', 2498, 'South Atlantic League'),
    'CHS Field': (44.95089651, -93.08457526, 'St. Paul Saints', 'AAA', 1960, 'International League'),
    'Canal Park': (41.07739, -81.52185, 'Akron RubberDucks', 'AA', 402, 'Eastern League'),
    'Carilion Clinic Field': (37.2861162, -80.037161, 'Salem RidgeYaks', 'A', 414, 'Carolina League'),
    'Cheney Stadium': (47.237981, -122.497643, 'Tacoma Rainiers', 'AAA', 529, 'Pacific Coast League'),
    'Chickasaw Bricktown Ballpark': (35.46511, -97.50762, 'Oklahoma City Comets', 'AAA', 238, 'Pacific Coast League'),
    'Chukchansi Park': (36.73256, -119.79157, 'Fresno Grizzlies', 'A', 259, 'California League'),
    'Classic Auto Group Park': (41.6424351, -81.4367781, 'Lake County Captains', 'A+', 437, 'Midwest League'),
    'Clover Park': (27.3249268, -80.4068854, 'St. Lucie Mets', 'A', 507, 'Florida State League'),
    'Coca-Cola Park': (40.6253183, -75.4516154, 'Lehigh Valley IronPigs', 'AAA', 1410, 'International League'),
    'Constellation Field': (29.62275645, -95.64718344, 'Sugar Land Space Cowboys', 'AAA', 5434, 'Pacific Coast League'),
    'Coolray Field': (34.0409586, -83.9937909, 'Gwinnett Stripers', 'AAA', 431, 'International League'),
    'Covenant Health Park': (35.97248459516771, -83.91495041686319, 'Knoxville Smokies', 'AA', 553, 'Southern League'),
    'Day Air Ballpark': (39.764172, -84.185896, 'Dayton Dragons', 'A+', 459, 'Midwest League'),
    'Dell Diamond': (30.527463, -97.630397, 'Round Rock Express', 'AAA', 102, 'Pacific Coast League'),
    'Delta Dental Park': (43.6562399, -70.27873, 'Portland Sea Dogs', 'AA', 546, 'Eastern League'),
    'Delta Dental Stadium': (42.98115, -71.46653, 'New Hampshire Fisher Cats', 'AA', 463, 'Eastern League'),
    'Dickey-Stephens Park': (34.75513, -92.2725899, 'Arkansas Travelers', 'AA', 574, 'Texas League'),
    'Dow Diamond': (43.6089355, -84.2397878, 'Great Lakes Loons', 'A+', 456, 'Midwest League'),
    'Dozer Park': (40.68751, -89.59781, 'Peoria Chiefs', 'A+', 443, 'Midwest League'),
    'Dunkin\' Park': (41.77079, -72.6743078, 'Hartford Yard Goats', 'AA', 538, 'Eastern League'),
    'Durham Bulls Athletic Park': (35.99158, -78.90401, 'Durham Bulls', 'AAA', 234, 'International League'),
    'Equity Bank Park': (37.6813367, -97.3475531, 'Wichita Wind Surge', 'AA', 3898, 'Texas League'),
    'Excite Ballpark': (37.32128, -121.862286, 'San Jose Giants', 'A', 476, 'California League'),
    'FNB Field': (40.2568294, -76.8896522, 'Harrisburg Senators', 'AA', 547, 'Eastern League'),
    'Fifth Third Field': (41.64767, -83.53838, 'Toledo Mud Hens', 'AAA', 512, 'International League'),
    'Fifth Third Park': (34.9449402, -81.9359415, 'Hub City Spartanburgers', 'A+', 6324, 'South Atlantic League'),
    'First Horizon Park': (36.173218, -86.785171, 'Nashville Sounds', 'AAA', 556, 'International League'),
    'First National Bank Field': (36.07667, -79.79487, 'Greensboro Grasshoppers', 'A+', 477, 'South Atlantic League'),
    'FirstEnergy Stadium': (40.365558, -75.933816, 'Reading Fightin Phils', 'AA', 522, 'Eastern League'),
    'Fluor Field at the West End': (34.84297, -82.40893, 'Greenville Drive', 'A+', 428, 'South Atlantic League'),
    'Four Winds Field': (41.6704099, -86.25547, 'South Bend Cubs', 'A+', 550, 'Midwest League'),
    'Frawley Stadium': (39.731809, -75.564174, 'Wilmington Blue Rocks', 'A+', 426, 'South Atlantic League'),
    'Funko Field': (47.966664, -122.202786, 'Everett AquaSox', 'A+', 403, 'Northwest League'),
    'Gesa Stadium': (46.27032, -119.17079, 'Tri-City Dust Devils', 'A+', 460, 'Northwest League'),
    'Grainger Stadium': (35.27035945, -77.57396936, 'Down East Wood Ducks', 'A', 485, 'Carolina League'),
    'Grayson Stadium': (32.0502, -81.1019, 'Savannah Sand Gnats', 'A', 248, 'South Atlantic League'),  # Defunct 2016
    'Greater Nevada Field': (39.52812, -119.80901, 'Reno Aces', 'AAA', 2310, 'Pacific Coast League'),
    'Hammons Field': (37.21078, -93.2797, 'Springfield Cardinals', 'AA', 440, 'Texas League'),
    'Harbor Park': (36.84265, -76.27803, 'Norfolk Tides', 'AAA', 568, 'International League'),
    'Heritage Financial Park': (41.52638, -73.96109, 'Hudson Valley Renegades', 'A+', 537, 'South Atlantic League'),
    'Hillsboro Hops Ballpark': (45.554, -122.9085, 'Hillsboro Hops', 'A+', 419, 'Northwest League'),
    'Hodgetown': (35.2050189, -101.8339567, 'Amarillo Sod Poodles', 'AA', 5368, 'Texas League'),
    'Huntington Park': (39.96868, -83.01102, 'Columbus Clippers', 'AAA', 445, 'International League'),
    'Innovative Field': (43.158301, -77.619748, 'Rochester Red Wings', 'AAA', 534, 'International League'),
    'Isotopes Park': (35.06985, -106.62802, 'Albuquerque Isotopes', 'AAA', 342, 'Pacific Coast League'),
    'Jackie Robinson Ballpark': (29.20922, -81.01596, 'Daytona Tortugas', 'A', 450, 'Florida State League'),
    'Jackson Field': (42.73465, -84.5455999, 'Lansing Lugnuts', 'A+', 499, 'Midwest League'),
    'John Thurman Field': (37.622321, -121.000956, 'Modesto Nuts', 'A', 515, 'California League'),
    'Joseph P. Riley, Jr. Ballpark': (32.790421, -79.961332, 'Charleston RiverDogs', 'A', 233, 'Carolina League'),
    'Keesler Federal Park': (30.395421, -88.893217, 'Biloxi Shuckers', 'AA', 5015, 'Southern League'),
    'L.P. Frans Stadium': (35.747289, -81.3778848, 'Hickory Crawdads', 'A+', 448, 'South Atlantic League'),
    'LECOM Park': (27.48553, -82.57038, 'Bradenton Marauders', 'A', 3390, 'Florida State League'),
    'LMCU Ballpark': (43.040797, -85.65933, 'West Michigan Whitecaps', 'A+', 582, 'Midwest League'),
    'Las Vegas Ballpark': (36.152607, -115.329888, 'Las Vegas Aviators', 'AAA', 400, 'Pacific Coast League'),
    'Lee Health Sports Complex': (26.537803, -81.841973, 'Fort Myers Mighty Mussels', 'A', 509, 'Florida State League'),
    'LoanMart Field': (34.102721, -117.54792, 'Rancho Cucamonga Quakes', 'A', 526, 'California League'),
    'Louisville Slugger Field': (38.2557199, -85.74479, 'Louisville Bats', 'AAA', 416, 'International League'),
    'Maimonides Park': (40.57392, -73.98473, 'Brooklyn Cyclones', 'A+', 453, 'South Atlantic League'),
    'McCormick Field': (35.58668, -82.5501, 'Asheville Tourists', 'A+', 573, 'South Atlantic League'),
    'Melaleuca Field': (43.4926, -112.0408, 'Idaho Falls Chukars', 'Rookie', 571, 'Pioneer League'),
    'Mirabito Stadium': (42.1031199, -75.90379, 'Binghamton Rumble Ponies', 'AA', 505, 'Eastern League'),
    'Modern Woodmen Park': (41.51868, -90.58187, 'Quad Cities River Bandits', 'A+', 565, 'Midwest League'),
    'Momentum Bank Ballpark': (31.98835, -102.15482, 'Midland RockHounds', 'AA', 237, 'Texas League'),
    'Montgomery Riverwalk Stadium': (32.382298, -86.310592, 'Montgomery Biscuits', 'AA', 421, 'Southern League'),
    'NBT Bank Stadium': (43.079531, -76.165419, 'Syracuse Mets', 'AAA', 552, 'International League'),
    'Nelson Wolff Stadium': (29.40978, -98.60189, 'San Antonio Missions', 'AA', 510, 'Texas League'),
    'Neuroscience Group Field': (44.282871, -88.469427, 'Wisconsin Timber Rattlers', 'A+', 572, 'Midwest League'),
    'ONEOK Field': (36.1601215, -95.9888782, 'Tulsa Drillers', 'AA', 260, 'Texas League'),
    'Ontario Sports Empire Baseball Stadium': (34.0184639834586, -117.60331808557788, 'Ontario Tower Buzzers', 'A', 6482, 'California League'),
    'PK Park': (44.059012, -123.065482, 'Eugene Emeralds', 'A+', 461, 'Northwest League'),
    'PNC Field': (41.360672, -75.683676, 'Scranton/Wilkes-Barre RailRiders', 'AAA', 531, 'International League'),
    'Parkview Field': (41.07345, -85.14366, 'Fort Wayne TinCaps', 'A+', 584, 'Midwest League'),
    'Pelicans Ballpark': (33.711404, -78.88444, 'Myrtle Beach Pelicans', 'A', 521, 'Carolina League'),
    'Peoples Natural Gas Field': (40.473826, -78.394753, 'Altoona Curve', 'AA', 452, 'Eastern League'),
    'Polar Park': (42.25606, -71.80028, 'Worcester Red Sox', 'AAA', 533, 'International League'),
    'Prince George\'s Stadium': (38.946114, -76.709334, 'Chesapeake Baysox', 'AA', 418, 'Eastern League'),
    'Principal Park': (41.57998, -93.61619, 'Iowa Cubs', 'AAA', 451, 'International League'),
    'Publix Field at Joker Marchant Stadium': (28.074822, -81.9508415, 'Lakeland Flying Tigers', 'A', 570, 'Florida State League'),
    'Regions Field': (33.5077928, -86.8120366, 'Birmingham Barons', 'AA', 247, 'Southern League'),
    'Riders Field': (33.0984, -96.8197, 'Frisco RoughRiders', 'AA', 540, 'Texas League'),
    'Ripken Stadium': (39.5072, -76.1641, 'Aberdeen IronBirds', 'A+', 488, 'South Atlantic League'),
    'Roger Dean Chevrolet Stadium': (26.890957, -80.116365, 'Jupiter Hammerheads', 'A', 479, 'Florida State League'),
    'Rogers Field at Nat Bailey Stadium': (49.2431966, -123.1054384, 'Vancouver Canadians', 'A+', 435, 'Northwest League'),
    'SEGRA Stadium': (35.054357, -78.8851444, 'Fayetteville Woodpeckers', 'A', 3712, 'Carolina League'),
    'SRP Park': (33.4844619, -81.9764372, 'Augusta GreenJackets', 'A', 478, 'Carolina League'),
    'Sahlen Field': (42.880772, -78.873955, 'Buffalo Bisons', 'AAA', 422, 'International League'),
    'San Manuel Stadium': (34.097266, -117.296268, 'Inland Empire 66ers', 'A', 401, 'California League'),
    'Segra Park': (34.018317, -81.030958, 'Columbia Fireflies', 'A', 3705, 'Carolina League'),
    'ShoreTown Ballpark': (40.07495, -74.18846, 'Jersey Shore BlueClaws', 'A+', 427, 'South Atlantic League'),
    'Southwest University Park': (31.759277, -106.492526, 'El Paso Chihuahuas', 'AAA', 4904, 'Pacific Coast League'),
    'Sutter Health Park': (38.57994, -121.51246, 'Sacramento River Cats', 'AAA', 105, 'Pacific Coast League'),
    'Synovus Park': (32.4523727, -84.9939591, 'Columbus Clingstones', 'AA', 6325, 'Southern League'),
    'TD Ballpark': (27.9745812, -82.7913301, 'Dunedin Blue Jays', 'A', 424, 'Florida State League'),
    'TD Bank Ballpark': (40.56081907, -74.55328462, 'Somerset Patriots', 'AA', 1956, 'Eastern League'),
    'The Ballpark at America First Square': (40.549066970052124, -112.02301999999999, 'Salt Lake Bees', 'AAA', 561, 'Pacific Coast League'),
    'The Diamond': (33.654183, -117.3010675, 'Lake Elsinore Storm', 'A', 103, 'California League'),
    'Toyota Field': (34.6837403, -86.7274237, 'Rocket City Trash Pandas', 'AA', 559, 'Southern League'),
    'Truist Field': (35.22781, -80.84823, 'Charlotte Knights', 'AAA', 494, 'International League'),
    'Truist Stadium': (36.09182, -80.25527, 'Winston-Salem Dash', 'A+', 580, 'South Atlantic League'),
    'Trustmark Park': (32.274168, -90.147519, 'Mississippi Braves', 'AA', 430, 'Southern League'),
    'UPMC Park': (42.12706, -80.0803, 'Erie SeaWolves', 'AA', 106, 'Eastern League'),
    'Valley Strong Ballpark': (36.3320197, -119.3053325, 'Visalia Rawhide', 'A', 516, 'California League'),
    'Veterans Memorial Stadium': (41.96785, -91.68662, 'Cedar Rapids Kernels', 'A+', 492, 'Midwest League'),
    'Victory Field': (39.7657354, -86.1682918, 'Indianapolis Indians', 'AAA', 484, 'International League'),
    'Virginia Credit Union Stadium': (38.3181302, -77.5124029, 'Fredericksburg Nationals', 'A', 436, 'Carolina League'),
    'Vystar Ballpark': (30.32533, -81.64256, 'Jacksonville Jumbo Shrimp', 'AAA', 564, 'International League'),
    'Werner Park': (41.1510945, -96.1057988, 'Omaha Storm Chasers', 'AAA', 541, 'International League'),
    'Whataburger Field': (27.80995, -97.39941, 'Corpus Christi Hooks', 'AA', 482, 'Texas League'),
    'Yankee Complex Field 2': (27.978979741428514, -82.50706715487692, 'Tampa Tarpons', 'A', 587, 'Florida State League'),
}

# Reverse lookup: team_name -> league_name
MILB_TEAM_LEAGUES = {info[2]: info[5] for info in MILB_STADIUM_DATA.values()}

# Historic/renamed MiLB teams (from HISTORICAL_TEAM_LOGOS)
HISTORIC_MILB_TEAMS = set(HISTORICAL_TEAM_LOGOS.keys())


def get_logo_url(team_id: int) -> str:
    """Get team logo URL from team ID."""
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def get_milb_stadium_coords(venue_name: str) -> tuple:
    """Get coordinates for a MiLB venue."""
    return MILB_STADIUM_DATA.get(venue_name)


def find_stadium(venue_name: str) -> tuple:
    """
    Try to find a stadium by name in MiLB data.
    Returns tuple of (lat, lng, team, level, team_id, league) or None if not found.
    """
    if venue_name in MILB_STADIUM_DATA:
        return MILB_STADIUM_DATA[venue_name]

    venue_lower = venue_name.lower()
    for name, data in MILB_STADIUM_DATA.items():
        if name.lower() in venue_lower or venue_lower in name.lower():
            return data

    return None
