"""
Professional baseball stadium data from MLB Stats API.
Includes MLB and MiLB venues with coordinates and team IDs for logos.
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
    # MLB renamed teams - use current team's mlbstatic logo
    'Cleveland Indians': 'https://www.mlbstatic.com/team-logos/114.svg',  # Now Guardians
    'Oakland Athletics': 'https://www.mlbstatic.com/team-logos/133.svg',  # Now in Sacramento
    'Oakland A\'s': 'https://www.mlbstatic.com/team-logos/133.svg',
    'Los Angeles Angels of Anaheim': 'https://www.mlbstatic.com/team-logos/108.svg',  # Now LA Angels
    'Anaheim Angels': 'https://www.mlbstatic.com/team-logos/108.svg',
    'California Angels': 'https://www.mlbstatic.com/team-logos/108.svg',
    'Florida Marlins': 'https://www.mlbstatic.com/team-logos/146.svg',  # Now Miami Marlins
    'Montreal Expos': 'https://www.mlbstatic.com/team-logos/120.svg',  # Now Washington Nationals
    'Tampa Bay Devil Rays': 'https://www.mlbstatic.com/team-logos/139.svg',  # Now Rays
    # MiLB renamed/relocated teams - use successor team's mlbstatic logo
    'Akron Aeros': 'https://www.mlbstatic.com/team-logos/402.svg',  # Now Akron RubberDucks
    'Bowie Baysox': 'https://www.mlbstatic.com/team-logos/418.svg',  # Now Chesapeake Baysox
    'Reading Phillies': 'https://www.mlbstatic.com/team-logos/522.svg',  # Now Reading Fightin Phils
    'Buies Creek Astros': 'https://www.mlbstatic.com/team-logos/3712.svg',  # Now Fayetteville Woodpeckers
    'Savannah Sand Gnats': 'https://www.mlbstatic.com/team-logos/249.svg',  # Team relocated
    'Richmond Flying Squirrels': 'https://www.mlbstatic.com/team-logos/3410.svg',
    'Great Falls Voyagers': 'https://www.mlbstatic.com/team-logos/5004.svg',
}

# MLB Stadium coordinates: venue_name -> (latitude, longitude, team_name, level, team_id)
MLB_STADIUM_DATA = {
    'American Family Field': (43.02838, -87.97099, 'Milwaukee Brewers', 'MLB', 158),
    'Angel Stadium': (33.80019044, -117.8823996, 'Los Angeles Angels', 'MLB', 108),
    'Busch Stadium': (38.62256667, -90.19286667, 'St. Louis Cardinals', 'MLB', 138),
    'Chase Field': (33.445302, -112.066687, 'Arizona Diamondbacks', 'MLB', 109),
    'Citi Field': (40.75753012, -73.84559155, 'New York Mets', 'MLB', 121),
    'Citizens Bank Park': (39.90539086, -75.16716957, 'Philadelphia Phillies', 'MLB', 143),
    'Comerica Park': (42.3391151, -83.048695, 'Detroit Tigers', 'MLB', 116),
    'Coors Field': (39.756042, -104.994136, 'Colorado Rockies', 'MLB', 115),
    'Daikin Park': (29.756967, -95.355509, 'Houston Astros', 'MLB', 117),
    'Dodger Stadium': (34.07368, -118.24053, 'Los Angeles Dodgers', 'MLB', 119),
    'Fenway Park': (42.346456, -71.097441, 'Boston Red Sox', 'MLB', 111),
    'George M. Steinbrenner Field': (27.97997, -82.50702, 'Tampa Bay Rays', 'MLB', 139),
    'Globe Life Field': (32.747299, -97.081818, 'Texas Rangers', 'MLB', 140),
    'Great American Ball Park': (39.097389, -84.506611, 'Cincinnati Reds', 'MLB', 113),
    'Kauffman Stadium': (39.051567, -94.480483, 'Kansas City Royals', 'MLB', 118),
    'Nationals Park': (38.872861, -77.007501, 'Washington Nationals', 'MLB', 120),
    'Oracle Park': (37.778383, -122.389448, 'San Francisco Giants', 'MLB', 137),
    'Oriole Park at Camden Yards': (39.283787, -76.621689, 'Baltimore Orioles', 'MLB', 110),
    'PNC Park': (40.446904, -80.005753, 'Pittsburgh Pirates', 'MLB', 134),
    'Petco Park': (32.707861, -117.157278, 'San Diego Padres', 'MLB', 135),
    'Progressive Field': (41.495861, -81.685255, 'Cleveland Guardians', 'MLB', 114),
    'Rate Field': (41.83, -87.634167, 'Chicago White Sox', 'MLB', 145),
    'Rogers Centre': (43.64155, -79.38915, 'Toronto Blue Jays', 'MLB', 141),
    'Sutter Health Park': (38.57994, -121.51246, 'Athletics', 'MLB', 133),
    'T-Mobile Park': (47.591333, -122.33251, 'Seattle Mariners', 'MLB', 136),
    'Target Field': (44.981829, -93.277891, 'Minnesota Twins', 'MLB', 142),
    'Truist Park': (33.890672, -84.467641, 'Atlanta Braves', 'MLB', 144),
    'Wrigley Field': (41.948171, -87.655503, 'Chicago Cubs', 'MLB', 112),
    'Yankee Stadium': (40.82919482, -73.9264977, 'New York Yankees', 'MLB', 147),
    'loanDepot park': (25.77796236, -80.21951795, 'Miami Marlins', 'MLB', 146),
}

# MiLB Stadium coordinates: venue_name -> (latitude, longitude, team_name, level, team_id)
MILB_STADIUM_DATA = {
    'ABC Supply Stadium': (42.496763, -89.0429539, 'Beloit Sky Carp', 'A+', 554),
    'AT&T Field': (35.05449, -85.31384, 'Chattanooga Lookouts', 'AA', 498),
    'AdventHealth Stadium': (34.285832, -85.167211, 'Rome Emperors', 'A+', 432),
    'Arthur W. Perdue Stadium': (38.369979, -75.530656, 'Delmarva Shorebirds', 'A', 548),
    'Arvest Ballpark': (36.15968, -94.194624, 'Northwest Arkansas Naturals', 'AA', 1350),
    'Atrium Health Ballpark': (35.4968555, -80.6282677, 'Kannapolis Cannon Ballers', 'A', 487),
    'AutoZone Park': (35.14297, -90.04924, 'Memphis Redbirds', 'AAA', 235),
    'Avista Stadium': (47.661351, -117.344426, 'Spokane Indians', 'A+', 486),
    'Bank of the James Stadium': (37.3930099, -79.1661, 'Lynchburg Hillcats', 'A', 481),
    'Banner Island Ballpark': (37.954863, -121.297357, 'Stockton Ports', 'A', 524),
    'BayCare Ballpark': (27.97159, -82.731714, 'Clearwater Threshers', 'A', 566),
    'Blue Wahoos Stadium': (30.4048409, -87.2188349, 'Pensacola Blue Wahoos', 'AA', 4124),
    'Bowling Green Ballpark': (36.9957207, -86.4411401, 'Bowling Green Hot Rods', 'A+', 2498),
    'CHS Field': (44.95089651, -93.08457526, 'St. Paul Saints', 'AAA', 1960),
    'Canal Park': (41.07739, -81.52185, 'Akron RubberDucks', 'AA', 402),
    'Carilion Clinic Field': (37.2861162, -80.037161, 'Salem RidgeYaks', 'A', 414),
    'Cheney Stadium': (47.237981, -122.497643, 'Tacoma Rainiers', 'AAA', 529),
    'Chickasaw Bricktown Ballpark': (35.46511, -97.50762, 'Oklahoma City Comets', 'AAA', 238),
    'Chukchansi Park': (36.73256, -119.79157, 'Fresno Grizzlies', 'A', 259),
    'Classic Auto Group Park': (41.6424351, -81.4367781, 'Lake County Captains', 'A+', 437),
    'Clover Park': (27.3249268, -80.4068854, 'St. Lucie Mets', 'A', 507),
    'Coca-Cola Park': (40.6253183, -75.4516154, 'Lehigh Valley IronPigs', 'AAA', 1410),
    'Constellation Field': (29.62275645, -95.64718344, 'Sugar Land Space Cowboys', 'AAA', 5434),
    'Coolray Field': (34.0409586, -83.9937909, 'Gwinnett Stripers', 'AAA', 431),
    'Covenant Health Park': (35.97248459516771, -83.91495041686319, 'Knoxville Smokies', 'AA', 553),
    'Day Air Ballpark': (39.764172, -84.185896, 'Dayton Dragons', 'A+', 459),
    'Dell Diamond': (30.527463, -97.630397, 'Round Rock Express', 'AAA', 102),
    'Delta Dental Park': (43.6562399, -70.27873, 'Portland Sea Dogs', 'AA', 546),
    'Delta Dental Stadium': (42.98115, -71.46653, 'New Hampshire Fisher Cats', 'AA', 463),
    'Dickey-Stephens Park': (34.75513, -92.2725899, 'Arkansas Travelers', 'AA', 574),
    'Dow Diamond': (43.6089355, -84.2397878, 'Great Lakes Loons', 'A+', 456),
    'Dozer Park': (40.68751, -89.59781, 'Peoria Chiefs', 'A+', 443),
    'Dunkin\' Park': (41.77079, -72.6743078, 'Hartford Yard Goats', 'AA', 538),
    'Durham Bulls Athletic Park': (35.99158, -78.90401, 'Durham Bulls', 'AAA', 234),
    'Equity Bank Park': (37.6813367, -97.3475531, 'Wichita Wind Surge', 'AA', 3898),
    'Excite Ballpark': (37.32128, -121.862286, 'San Jose Giants', 'A', 476),
    'FNB Field': (40.2568294, -76.8896522, 'Harrisburg Senators', 'AA', 547),
    'Fifth Third Field': (41.64767, -83.53838, 'Toledo Mud Hens', 'AAA', 512),
    'Fifth Third Park': (34.9449402, -81.9359415, 'Hub City Spartanburgers', 'A+', 6324),
    'First Horizon Park': (36.173218, -86.785171, 'Nashville Sounds', 'AAA', 556),
    'First National Bank Field': (36.07667, -79.79487, 'Greensboro Grasshoppers', 'A+', 477),
    'FirstEnergy Stadium': (40.365558, -75.933816, 'Reading Fightin Phils', 'AA', 522),
    'Fluor Field at the West End': (34.84297, -82.40893, 'Greenville Drive', 'A+', 428),
    'Four Winds Field': (41.6704099, -86.25547, 'South Bend Cubs', 'A+', 550),
    'Frawley Stadium': (39.731809, -75.564174, 'Wilmington Blue Rocks', 'A+', 426),
    'Funko Field': (47.966664, -122.202786, 'Everett AquaSox', 'A+', 403),
    'Gesa Stadium': (46.27032, -119.17079, 'Tri-City Dust Devils', 'A+', 460),
    'Grainger Stadium': (35.27035945, -77.57396936, 'Down East Wood Ducks', 'A', 485),
    'Grayson Stadium': (32.0502, -81.1019, 'Savannah Sand Gnats', 'A', 248),  # Defunct 2016
    'Greater Nevada Field': (39.52812, -119.80901, 'Reno Aces', 'AAA', 2310),
    'Hammons Field': (37.21078, -93.2797, 'Springfield Cardinals', 'AA', 440),
    'Harbor Park': (36.84265, -76.27803, 'Norfolk Tides', 'AAA', 568),
    'Heritage Financial Park': (41.52638, -73.96109, 'Hudson Valley Renegades', 'A+', 537),
    'Hillsboro Hops Ballpark': (45.554, -122.9085, 'Hillsboro Hops', 'A+', 419),
    'Hodgetown': (35.2050189, -101.8339567, 'Amarillo Sod Poodles', 'AA', 5368),
    'Huntington Park': (39.96868, -83.01102, 'Columbus Clippers', 'AAA', 445),
    'Innovative Field': (43.158301, -77.619748, 'Rochester Red Wings', 'AAA', 534),
    'Isotopes Park': (35.06985, -106.62802, 'Albuquerque Isotopes', 'AAA', 342),
    'Jackie Robinson Ballpark': (29.20922, -81.01596, 'Daytona Tortugas', 'A', 450),
    'Jackson Field': (42.73465, -84.5455999, 'Lansing Lugnuts', 'A+', 499),
    'John Thurman Field': (37.622321, -121.000956, 'Modesto Nuts', 'A', 515),
    'Joseph P. Riley, Jr. Ballpark': (32.790421, -79.961332, 'Charleston RiverDogs', 'A', 233),
    'Keesler Federal Park': (30.395421, -88.893217, 'Biloxi Shuckers', 'AA', 5015),
    'L.P. Frans Stadium': (35.747289, -81.3778848, 'Hickory Crawdads', 'A', 448),
    'LECOM Park': (27.48553, -82.57038, 'Bradenton Marauders', 'A', 3390),
    'LMCU Ballpark': (43.040797, -85.65933, 'West Michigan Whitecaps', 'A+', 582),
    'Las Vegas Ballpark': (36.152607, -115.329888, 'Las Vegas Aviators', 'AAA', 400),
    'Lee Health Sports Complex': (26.537803, -81.841973, 'Fort Myers Mighty Mussels', 'A', 509),
    'LoanMart Field': (34.102721, -117.54792, 'Rancho Cucamonga Quakes', 'A', 526),
    'Louisville Slugger Field': (38.2557199, -85.74479, 'Louisville Bats', 'AAA', 416),
    'Maimonides Park': (40.57392, -73.98473, 'Brooklyn Cyclones', 'A+', 453),
    'McCormick Field': (35.58668, -82.5501, 'Asheville Tourists', 'A+', 573),
    'Melaleuca Field': (43.4926, -112.0408, 'Idaho Falls Chukars', 'Rookie', 571),  # Pioneer League (now independent)
    'Mirabito Stadium': (42.1031199, -75.90379, 'Binghamton Rumble Ponies', 'AA', 505),
    'Modern Woodmen Park': (41.51868, -90.58187, 'Quad Cities River Bandits', 'A+', 565),
    'Momentum Bank Ballpark': (31.98835, -102.15482, 'Midland RockHounds', 'AA', 237),
    'Montgomery Riverwalk Stadium': (32.382298, -86.310592, 'Montgomery Biscuits', 'AA', 421),
    'NBT Bank Stadium': (43.079531, -76.165419, 'Syracuse Mets', 'AAA', 552),
    'Nelson Wolff Stadium': (29.40978, -98.60189, 'San Antonio Missions', 'AA', 510),
    'Neuroscience Group Field': (44.282871, -88.469427, 'Wisconsin Timber Rattlers', 'A+', 572),
    'ONEOK Field': (36.1601215, -95.9888782, 'Tulsa Drillers', 'AA', 260),
    'Ontario Sports Empire Baseball Stadium': (34.0184639834586, -117.60331808557788, 'Ontario Tower Buzzers', 'A', 6482),
    'PK Park': (44.059012, -123.065482, 'Eugene Emeralds', 'A+', 461),
    'PNC Field': (41.360672, -75.683676, 'Scranton/Wilkes-Barre RailRiders', 'AAA', 531),
    'Parkview Field': (41.07345, -85.14366, 'Fort Wayne TinCaps', 'A+', 584),
    'Pelicans Ballpark': (33.711404, -78.88444, 'Myrtle Beach Pelicans', 'A', 521),
    'Peoples Natural Gas Field': (40.473826, -78.394753, 'Altoona Curve', 'AA', 452),
    'Polar Park': (42.25606, -71.80028, 'Worcester Red Sox', 'AAA', 533),
    'Prince George\'s Stadium': (38.946114, -76.709334, 'Chesapeake Baysox', 'AA', 418),
    'Principal Park': (41.57998, -93.61619, 'Iowa Cubs', 'AAA', 451),
    'Publix Field at Joker Marchant Stadium': (28.074822, -81.9508415, 'Lakeland Flying Tigers', 'A', 570),
    'Regions Field': (33.5077928, -86.8120366, 'Birmingham Barons', 'AA', 247),
    'Riders Field': (33.0984, -96.8197, 'Frisco RoughRiders', 'AA', 540),
    'Ripken Stadium': (39.5072, -76.1641, 'Aberdeen IronBirds', 'A+', 488),
    'Roger Dean Chevrolet Stadium': (26.890957, -80.116365, 'Jupiter Hammerheads', 'A', 479),
    'Rogers Field at Nat Bailey Stadium': (49.2431966, -123.1054384, 'Vancouver Canadians', 'A+', 435),
    'SEGRA Stadium': (35.054357, -78.8851444, 'Fayetteville Woodpeckers', 'A', 3712),
    'SRP Park': (33.4844619, -81.9764372, 'Augusta GreenJackets', 'A', 478),
    'Sahlen Field': (42.880772, -78.873955, 'Buffalo Bisons', 'AAA', 422),
    'San Manuel Stadium': (34.097266, -117.296268, 'Inland Empire 66ers', 'A', 401),
    'Segra Park': (34.018317, -81.030958, 'Columbia Fireflies', 'A', 3705),
    'ShoreTown Ballpark': (40.07495, -74.18846, 'Jersey Shore BlueClaws', 'A+', 427),
    'Southwest University Park': (31.759277, -106.492526, 'El Paso Chihuahuas', 'AAA', 4904),
    'Sutter Health Park': (38.57994, -121.51246, 'Sacramento River Cats', 'AAA', 105),
    'Synovus Park': (32.4523727, -84.9939591, 'Columbus Clingstones', 'AA', 6325),
    'TD Ballpark': (27.9745812, -82.7913301, 'Dunedin Blue Jays', 'A', 424),
    'TD Bank Ballpark': (40.56081907, -74.55328462, 'Somerset Patriots', 'AA', 1956),
    'The Ballpark at America First Square': (40.549066970052124, -112.02301999999999, 'Salt Lake Bees', 'AAA', 561),
    'The Diamond': (33.654183, -117.3010675, 'Lake Elsinore Storm', 'A', 103),
    'Toyota Field': (34.6837403, -86.7274237, 'Rocket City Trash Pandas', 'AA', 559),
    'Truist Field': (35.22781, -80.84823, 'Charlotte Knights', 'AAA', 494),
    'Truist Stadium': (36.09182, -80.25527, 'Winston-Salem Dash', 'A+', 580),
    'Trustmark Park': (32.274168, -90.147519, 'Mississippi Braves', 'AA', 430),
    'UPMC Park': (42.12706, -80.0803, 'Erie SeaWolves', 'AA', 106),
    'Valley Strong Ballpark': (36.3320197, -119.3053325, 'Visalia Rawhide', 'A', 516),
    'Veterans Memorial Stadium': (41.96785, -91.68662, 'Cedar Rapids Kernels', 'A+', 492),
    'Victory Field': (39.7657354, -86.1682918, 'Indianapolis Indians', 'AAA', 484),
    'Virginia Credit Union Stadium': (38.3181302, -77.5124029, 'Fredericksburg Nationals', 'A', 436),
    'Vystar Ballpark': (30.32533, -81.64256, 'Jacksonville Jumbo Shrimp', 'AAA', 564),
    'Werner Park': (41.1510945, -96.1057988, 'Omaha Storm Chasers', 'AAA', 541),
    'Whataburger Field': (27.80995, -97.39941, 'Corpus Christi Hooks', 'AA', 482),
    'Yankee Complex Field 2': (27.978979741428514, -82.50706715487692, 'Tampa Tarpons', 'A', 587),
}


def get_logo_url(team_id: int) -> str:
    """Get team logo URL from team ID."""
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def get_milb_stadium_coords(venue_name: str) -> tuple:
    """Get coordinates for a MiLB venue."""
    return MILB_STADIUM_DATA.get(venue_name)


def get_mlb_stadium_coords(venue_name: str) -> tuple:
    """Get coordinates for an MLB venue."""
    return MLB_STADIUM_DATA.get(venue_name)


def find_stadium(venue_name: str) -> tuple:
    """
    Try to find a stadium by name in both MLB and MiLB data.
    Returns tuple of (lat, lng, team, level, team_id) or None if not found.
    """
    if venue_name in MLB_STADIUM_DATA:
        return MLB_STADIUM_DATA[venue_name]
    
    if venue_name in MILB_STADIUM_DATA:
        return MILB_STADIUM_DATA[venue_name]
    
    venue_lower = venue_name.lower()
    for name, data in MLB_STADIUM_DATA.items():
        if name.lower() in venue_lower or venue_lower in name.lower():
            return data
    for name, data in MILB_STADIUM_DATA.items():
        if name.lower() in venue_lower or venue_lower in name.lower():
            return data
    
    return None
