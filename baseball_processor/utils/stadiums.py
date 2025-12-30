"""
Stadium data for NCAA Division I Baseball programs.
Includes stadium names and coordinates for mapping.
"""

# Stadium coordinates: team -> (latitude, longitude, stadium_name)
STADIUM_DATA = {
    # ACC
    'Boston College': (42.3355, -71.1685, 'Eddie Pellagrini Diamond'),
    'California': (37.8708, -122.2499, 'Stu Gordon Stadium'),  # Formerly Evans Diamond
    'Clemson': (34.6837, -82.8367, 'Doug Kingsmore Stadium'),
    'Duke': (35.9976, -78.9412, 'Durham Athletic Park'),
    'Florida State': (30.4383, -84.3040, 'Dick Howser Stadium'),
    'Georgia Tech': (33.7756, -84.3963, 'Russ Chandler Stadium'),
    'Louisville': (38.2189, -85.7587, 'Jim Patterson Stadium'),
    'Miami': (25.7211, -80.2832, 'Alex Rodriguez Park'),
    'NC State': (35.7872, -78.6963, 'Doak Field'),
    'North Carolina': (35.9132, -79.0558, 'Boshamer Stadium'),
    'Notre Dame': (41.6986, -86.2340, 'Frank Eck Stadium'),
    'Pittsburgh': (40.4456, -79.9574, 'Petersen Sports Complex'),
    'SMU': (32.8413, -96.7841, 'Jim and Janet Niver Field'),
    'Stanford': (37.4346, -122.1609, 'Sunken Diamond'),
    'Virginia': (38.0336, -78.5137, 'Davenport Field at Disharoon Park'),
    'Virginia Tech': (37.2296, -80.4139, 'English Field'),
    'Wake Forest': (36.1344, -80.2798, 'Gene Hooks Field'),

    # SEC
    'Alabama': (33.2084, -87.5505, 'Sewell-Thomas Stadium'),
    'Arkansas': (36.0674, -94.1803, 'Baum-Walker Stadium'),
    'Auburn': (32.6051, -85.4897, 'Samford Stadium'),
    'Florida': (29.6499, -82.3486, 'Condron Ballpark'),
    'Georgia': (33.9519, -83.3676, 'Foley Field'),
    'Kentucky': (38.0299, -84.5036, 'Kentucky Proud Park'),
    'LSU': (30.4112, -91.1819, 'Alex Box Stadium'),
    'Mississippi State': (33.4564, -88.7797, 'Dudy Noble Field'),
    'Missouri': (38.9467, -92.3279, 'Taylor Stadium'),
    'Oklahoma': (35.2226, -97.4395, 'L. Dale Mitchell Park'),
    'Ole Miss': (34.3668, -89.5347, 'Swayze Field'),
    'South Carolina': (33.9734, -81.0264, 'Carolina Stadium'),
    'Tennessee': (35.9567, -83.9294, 'Lindsey Nelson Stadium'),
    'Texas': (30.2836, -97.7321, 'UFCU Disch-Falk Field'),
    'Texas A&M': (30.6107, -96.3395, 'Olsen Field'),
    'Vanderbilt': (36.1437, -86.8133, 'Hawkins Field'),

    # Big 12
    'Arizona': (32.2286, -110.9479, 'Hi Corbett Field'),
    'Arizona State': (33.4450, -111.9567, 'Phoenix Municipal Stadium'),
    'Baylor': (31.5545, -97.1177, 'Baylor Ballpark'),
    'BYU': (40.2518, -111.6493, 'Larry H. Miller Field'),
    'Cincinnati': (39.1329, -84.5142, 'UC Baseball Stadium'),
    'Colorado': (40.0076, -105.2659, 'Folsom Field'),
    'Houston': (29.7199, -95.3422, 'Darryl & Lori Schroeder Park'),
    'Kansas': (38.9543, -95.2559, 'Hoglund Ballpark'),
    'Kansas State': (39.2014, -96.5847, 'Tointon Family Stadium'),
    'Oklahoma State': (36.1263, -97.0714, "O'Brate Stadium"),
    'TCU': (32.7095, -97.3679, 'Lupton Stadium'),
    'Texas Tech': (33.5899, -101.8744, 'Dan Law Field'),
    'UCF': (28.6024, -81.1976, 'John Euliano Park'),
    'Utah': (40.7649, -111.8421, 'America First Ballpark'),
    'West Virginia': (39.6295, -79.9559, 'Monongalia County Ballpark'),

    # Big Ten
    'Illinois': (40.1020, -88.2351, 'Illinois Field'),
    'Indiana': (39.1774, -86.5185, 'Bart Kaufman Field'),
    'Iowa': (41.6632, -91.5549, 'Duane Banks Field'),
    'Maryland': (38.9897, -76.9378, 'Shipley Field'),
    'Michigan': (42.2695, -83.7485, 'Ray Fisher Stadium'),
    'Michigan State': (42.7282, -84.4846, 'McLane Stadium'),
    'Minnesota': (44.9740, -93.2277, 'Siebert Field'),
    'Nebraska': (40.8202, -96.6880, 'Haymarket Park'),
    'Northwestern': (42.0565, -87.6753, 'Rocky Miller Park'),
    'Ohio State': (40.0074, -83.0259, 'Bill Davis Stadium'),
    'Oregon': (44.0582, -123.0681, 'PK Park'),
    'Penn State': (40.8148, -77.8567, 'Medlar Field'),
    'Purdue': (40.4349, -86.9196, 'Alexander Field'),
    'Rutgers': (40.5236, -74.4635, 'Bainton Field'),
    'UCLA': (34.0689, -118.4452, 'Jackie Robinson Stadium'),
    'USC': (34.0224, -118.2851, 'Dedeaux Field'),
    'Washington': (47.6507, -122.3015, 'Husky Ballpark'),

    # Pac-12
    'Oregon State': (44.5598, -123.2787, 'Goss Stadium'),
    'Washington State': (46.7324, -117.1631, 'Bailey-Brayton Field'),

    # WCC
    'Gonzaga': (47.6663, -117.4025, 'Patterson Baseball Complex'),
    'LMU': (33.9700, -118.4184, 'George C. Page Stadium'),
    'Pacific': (37.9815, -121.3109, 'Klein Family Field'),
    'Pepperdine': (34.0333, -118.7079, 'Eddy D. Field Stadium'),
    'Portland': (45.5714, -122.7282, 'Joe Etzel Field'),
    "Saint Mary's": (37.8404, -122.1065, 'Br. Ronald Gallagher Field'),
    'San Diego': (32.7720, -117.1905, 'John Cunningham Stadium'),
    'San Francisco': (37.7775, -122.4514, 'Dante Benedetti Diamond'),
    'San Francisco State': (37.7219, -122.4782, 'Maloney Field'),
    'Santa Clara': (37.3525, -121.9395, 'Stephen Schott Stadium'),
    'Seattle': (47.6062, -122.3321, 'Bannerwood Park'),

    # Mountain West
    'Air Force': (38.9968, -104.8614, 'Erdle Field'),
    'Fresno State': (36.8136, -119.7485, 'Pete Beiden Field'),
    'Grand Canyon': (33.5081, -112.1264, 'Brazell Field at GCU Ballpark'),
    'Nevada': (39.5460, -119.8139, 'William Peccole Park'),
    'New Mexico': (35.0844, -106.6504, 'Santa Ana Star Field'),
    'San Diego State': (32.7749, -117.0701, 'Tony Gwynn Stadium'),
    'San Jose State': (37.3382, -121.8863, 'San Jose Municipal Stadium'),
    'UNLV': (36.1072, -115.1398, 'Earl Wilson Stadium'),

    # Missouri Valley
    'Belmont': (36.1342, -86.7922, 'E. S. Rose Park'),
    'Bradley': (40.7023, -89.6067, 'Dozer Park'),
    'Evansville': (37.9716, -87.5711, 'Charles H. Braun Stadium'),
    'Illinois State': (40.5142, -88.9906, 'Duffy Bass Field'),
    'Indiana State': (39.4653, -87.4139, 'Sycamore Stadium'),
    'Murray State': (36.6121, -88.3191, 'Reagan Field'),
    'Southern Illinois': (37.7173, -89.2172, 'Itchy Jones Stadium'),
    'UIC': (41.8706, -87.6482, 'Les Miller Field'),
    'Valparaiso': (41.4597, -87.0512, 'Emory G. Bauer Field'),

    # Summit League
    'North Dakota State': (46.8958, -96.8003, 'Newman Outdoor Field'),
    'Northern Colorado': (40.4097, -104.6977, 'Jackson Field'),
    'Omaha': (41.2573, -96.0131, 'Tal Anderson Field'),
    'Oral Roberts': (36.0533, -95.9369, 'J. L. Johnson Stadium'),
    'South Dakota State': (44.3114, -96.7984, 'Erv Huether Field'),
    'St. Thomas': (44.9456, -93.1914, 'Koch Diamond'),

    # Big East
    'Butler': (39.8392, -86.1687, 'Bulldog Park'),
    'Creighton': (41.2619, -95.9315, 'Creighton Sports Complex'),
    'Georgetown': (38.9076, -77.0723, 'Shirley Povich Field'),
    'Seton Hall': (40.7435, -74.2389, "Owen T. Carroll Field"),
    "St. John's": (40.7213, -73.7949, 'Jack Kaiser Stadium'),
    'UConn': (41.8084, -72.2495, 'Elliot Ballpark'),
    'Villanova': (40.0345, -75.3376, 'Villanova Ballpark'),
    'Xavier': (39.1494, -84.4725, "J. Page Hayden Field"),

    # Sun Belt
    'Appalachian State': (36.2146, -81.6852, 'Jim and Bettie Smith Stadium'),
    'Arkansas State': (35.8418, -90.6750, 'Tomlinson Stadium'),
    'Coastal Carolina': (33.7962, -79.0101, 'Springs Brooks Stadium'),
    'Georgia Southern': (32.4196, -81.7866, 'J. I. Clements Stadium'),
    'Georgia State': (33.7490, -84.3880, 'Georgia State Baseball Complex'),
    'James Madison': (38.4496, -78.8689, 'Eagle Field'),
    'Louisiana': (30.2241, -92.0198, 'M. L. Tigue Moore Field'),
    'Louisiana-Monroe': (32.5293, -92.0764, 'Warhawk Field'),
    'Marshall': (38.4263, -82.4299, 'Jack Cook Field'),
    'Old Dominion': (36.8865, -76.3059, 'Bud Metheny Ballpark'),
    'South Alabama': (30.6965, -88.1780, 'Eddie Stanky Field'),
    'Southern Miss': (31.3271, -89.3350, 'Pete Taylor Park'),
    'Texas State': (29.8884, -97.9384, 'Bobcat Baseball Stadium'),
    'Troy': (31.7988, -85.9636, 'Riddle-Pace Field'),

    # Southern
    'ETSU': (36.3038, -82.3748, 'Thomas Stadium'),
    'Mercer': (32.8271, -83.6477, 'Claude Smith Field'),
    'Samford': (33.4644, -86.7915, 'Joe Lee Griffin Stadium'),
    'The Citadel': (32.7980, -79.9582, 'Joseph P. Riley Jr. Park'),
    'UNC Greensboro': (36.0665, -79.8103, 'UNCG Baseball Stadium'),
    'VMI': (37.7910, -79.4319, 'Gray-Minor Stadium'),
    'Western Carolina': (35.3077, -83.1854, 'Hennon Stadium'),
    'Wofford': (34.9512, -81.9362, 'Russell C. King Field'),

    # Northeast
    'Central Connecticut': (41.6880, -72.7795, 'Balf-Savin Field'),
    'Fairleigh Dickinson': (40.8629, -74.0797, 'Naimoli Family Baseball Complex'),
    'Le Moyne': (43.0481, -76.0680, 'Dick Rockwell Field'),
    'LIU': (40.6892, -73.9866, 'LIU Baseball Stadium'),
    'Mercyhurst': (42.0987, -80.0816, 'Mercyhurst Baseball Field'),
    'Stonehill': (42.1034, -71.1095, 'Lou Gorman Field'),
    'Wagner': (40.5795, -74.0988, 'Richmond County Bank Ballpark'),

    # Big West
    'Cal Poly': (35.3050, -120.6625, 'Robin Baggett Stadium'),
    'Cal State Fullerton': (33.8829, -117.8869, 'Goodwin Field'),
    'CSU Bakersfield': (35.3478, -119.1026, 'Hardt Field'),
    'CSUN': (34.2400, -118.5297, 'Matador Field'),
    'Hawaii': (21.2969, -157.8171, 'Les Murakami Stadium'),
    'Long Beach State': (33.7879, -118.1891, 'Blair Field'),
    'UC Davis': (38.5449, -121.7405, 'Dobbins Stadium'),
    'UC Irvine': (33.6461, -117.8426, 'Cicerone Field'),
    'UC Riverside': (33.9757, -117.3281, 'Riverside Sports Complex'),
    'UC San Diego': (32.8801, -117.2340, 'Triton Ballpark'),
    'UC Santa Barbara': (34.4140, -119.8489, 'Caesar Uyesaka Stadium'),

    # WAC
    'Abilene Christian': (32.4579, -99.7734, 'Crutcher Scott Field'),
    'California Baptist': (33.9330, -117.4256, 'James W. Totman Stadium'),
    'Sacramento State': (38.5629, -121.4252, 'John Smith Field'),
    'Tarleton State': (32.2227, -98.2178, 'Cecil Ballow Baseball Complex'),
    'UT Arlington': (32.7299, -97.1139, 'Clay Gould Ballpark'),
    'Utah Tech': (37.1041, -113.5681, 'Bruce Hurst Field'),
    'Utah Valley': (40.2969, -111.7130, 'UCCU Ballpark'),

    # American
    'Charlotte': (35.3079, -80.7337, 'Hayes Stadium'),
    'East Carolina': (35.6013, -77.3633, 'Clark-LeClair Stadium'),
    'FAU': (26.3796, -80.1042, 'FAU Baseball Stadium'),
    'Memphis': (35.1175, -89.9711, 'FedExPark'),
    'Rice': (29.7174, -95.4018, 'Reckling Park'),
    'Tulane': (29.9469, -90.1135, 'Greer Field'),
    'UAB': (33.5019, -86.8065, 'Jerry D. Young Memorial Field'),
    'USF': (28.0642, -82.4090, 'USF Baseball Stadium'),
    'UTSA': (29.5825, -98.6200, 'Roadrunner Field'),
    'Wichita State': (37.7208, -97.2931, 'Eck Stadium'),

    # MAC
    'Akron': (41.0765, -81.5116, 'Skeeles Field'),
    'Ball State': (40.2047, -85.4089, 'Ball Diamond'),
    'Bowling Green': (41.3784, -83.6270, 'Steller Field'),
    'Central Michigan': (43.5853, -84.7749, 'Theunissen Stadium'),
    'Eastern Michigan': (42.2505, -83.6239, 'Oestrike Stadium'),
    'Kent State': (41.1499, -81.3418, 'Schoonover Stadium'),
    'Miami (OH)': (39.5089, -84.7340, 'McKie Field'),
    'NIU': (41.9347, -88.7697, 'Ralph McKinzie Field'),
    'Ohio': (39.3246, -82.1018, 'Bob Wren Stadium'),
    'Toledo': (41.6576, -83.6145, 'Scott Park'),
    'UMass': (42.3876, -72.5301, 'Earl Lorden Field'),
    'Western Michigan': (42.2831, -85.6139, 'Robert J. Bobb Stadium'),

    # Patriot League
    'Army': (41.3915, -73.9656, 'Doubleday Field'),
    'Bucknell': (40.9548, -76.8867, 'Depew Field'),
    'Holy Cross': (42.2376, -71.8085, 'Hanover Insurance Park'),
    'Lafayette': (40.6973, -75.2104, 'Kamine Stadium'),
    'Lehigh': (40.6062, -75.3783, 'J. David Walker Field'),
    'Navy': (38.9847, -76.4891, 'Terwilliger Brothers Field'),

    # Ivy League
    'Brown': (41.8268, -71.3988, 'Murray Stadium'),
    'Columbia': (40.8688, -73.8858, 'Robertson Field at Satow Stadium'),
    'Cornell': (42.4445, -76.4388, 'Booth Field'),
    'Dartmouth': (43.7022, -72.2896, 'Red Rolfe Field'),
    'Harvard': (42.3665, -71.1277, "O'Donnell Field"),
    'Penn': (39.9503, -75.1909, 'Meiklejohn Stadium'),
    'Princeton': (40.3458, -74.6519, 'Bill Clarke Field'),
    'Yale': (41.3112, -72.9603, 'Yale Field'),

    # MAAC
    'Canisius': (42.9364, -78.8380, 'Demske Sports Complex'),
    'Fairfield': (41.2068, -73.2540, 'Alumni Diamond'),
    'Iona': (40.9312, -73.8286, 'City Park'),
    'Manhattan': (40.8903, -73.9022, 'Van Cortlandt Park'),
    'Marist': (41.7269, -73.9363, 'McCann Field'),
    'Merrimack': (42.7089, -71.1726, 'Warrior Field'),
    "Mount St. Mary's": (39.6982, -77.3344, 'E.T. Straw Family Stadium'),
    'Niagara': (43.1372, -79.0377, 'Bobo Field'),
    'Quinnipiac': (41.4194, -72.8932, 'QU Baseball Field'),
    'Rider': (40.2835, -74.7536, 'Sonny Pittaro Field'),
    'Sacred Heart': (41.2216, -73.2296, 'Pioneer Park'),
    "Saint Peter's": (40.7475, -74.0503, 'Joseph J. Jaroschak Field'),
    'Siena': (42.7186, -73.7517, 'Siena Field'),

    # Atlantic 10
    'Davidson': (35.5009, -80.8483, 'Wilson Field'),
    'Dayton': (39.7408, -84.1795, 'Woerner Field'),
    'Fordham': (40.8610, -73.8855, 'Houlihan Park'),
    'George Mason': (38.8316, -77.3076, 'Spuhler Field'),
    'George Washington': (38.9338, -77.1012, 'Tucker Field'),
    'La Salle': (40.0384, -75.1557, 'Hank DeVincent Field'),
    'Rhode Island': (41.4861, -71.5304, 'Bill Beck Field'),
    'Richmond': (37.5793, -77.5404, 'Pitt Field'),
    "Saint Joseph's": (39.9922, -75.2415, "Smithson Field"),
    'Saint Louis': (38.6359, -90.2249, 'Billiken Sports Center'),
    'St. Bonaventure': (42.0756, -78.4701, 'Fred Handler Park'),
    'VCU': (37.5500, -77.4528, 'The Diamond'),

    # Conference USA
    'Dallas Baptist': (32.7113, -96.9014, 'Horner Ballpark'),
    'Delaware': (39.6785, -75.7518, 'Bob Hannah Stadium'),
    'FIU': (25.7563, -80.3755, 'FIU Baseball Stadium'),
    'Jacksonville State': (33.8225, -85.7640, 'Jim Case Stadium'),
    'Kennesaw State': (34.0382, -84.5817, 'Stillwell Stadium'),
    'Liberty': (37.3527, -79.1722, 'Worthington Field'),
    'Louisiana Tech': (32.5290, -92.6479, 'J.C. Love Field'),
    'Middle Tennessee': (35.8492, -86.3686, 'Reese Smith Jr. Field'),
    'Missouri State': (37.2029, -93.2822, 'Hammons Field'),
    'New Mexico State': (32.2803, -106.7472, 'Presley Askew Field'),
    'Sam Houston': (30.7136, -95.5450, 'Don Sanders Stadium'),
    'WKU': (36.9857, -86.4560, 'Nick Denes Field'),

    # CAA
    'Campbell': (35.4185, -78.8499, 'Jim Perry Stadium'),
    'Charleston': (32.7833, -79.9370, 'Patriots Point'),
    'Elon': (36.1049, -79.5022, 'Latham Park'),
    'Hofstra': (40.7152, -73.6004, 'University Field'),
    'Monmouth': (40.2773, -74.0044, 'Monmouth Baseball Field'),
    'North Carolina A&T': (36.0726, -79.7728, 'War Memorial Stadium'),
    'Northeastern': (42.3398, -71.0892, 'Friedman Diamond'),
    'Stony Brook': (40.9126, -73.1234, 'Joe Nathan Field'),
    'Towson': (39.3932, -76.6119, 'John B. Schuerholz Park'),
    'UNC Wilmington': (34.2257, -77.8729, 'Brooks Field'),
    'William & Mary': (37.2707, -76.7142, 'Plumeri Park'),

    # Ohio Valley
    'Eastern Illinois': (39.4797, -88.1760, 'Coaches Stadium'),
    'Lindenwood': (38.7905, -90.5188, 'Lou Brock Sports Complex'),
    'Little Rock': (34.7277, -92.3387, 'Gary Hogan Field'),
    'Morehead State': (38.1867, -83.4382, 'Allen Field'),
    'SIU Edwardsville': (38.7930, -89.9984, 'Roy E. Lee Field'),
    'Southeast Missouri': (37.3111, -89.5515, 'Capaha Field'),
    'Southern Indiana': (37.9636, -87.6764, 'USI Baseball Field'),
    'Tennessee State': (36.1674, -86.8315, 'Meri-Weather Complex'),
    'Tennessee Tech': (36.1778, -85.5014, 'Bush Stadium'),
    'UT Martin': (36.3527, -88.8614, 'Skyhawk Field'),
    'Western Illinois': (40.4656, -90.6810, 'Alfred D. Boyer Stadium'),

    # ASUN
    'Austin Peay': (36.5346, -87.3514, 'Raymond C. Hand Park'),
    'Bellarmine': (38.2119, -85.6814, 'Knights Field'),
    'Central Arkansas': (35.0788, -92.4618, 'Bear Stadium'),
    'Eastern Kentucky': (37.7357, -84.2946, 'Turkey Hughes Field'),
    'FGCU': (26.4615, -81.7702, 'Swanson Stadium'),
    'Jacksonville': (30.3490, -81.6102, 'John Sessions Stadium'),
    'Lipscomb': (36.1152, -86.8074, 'Dugan Field'),
    'North Alabama': (34.8049, -87.6772, 'Mike Lane Field'),
    'North Florida': (30.2694, -81.5090, 'Harmon Stadium'),
    'Queens': (35.1879, -80.8284, 'Queens Sports Complex'),
    'Stetson': (29.0544, -81.3031, 'Melching Field'),
    'West Georgia': (33.5803, -85.0900, 'Gober Stadium'),

    # Southland
    'Houston Christian': (29.7234, -95.3449, 'Husky Field'),
    'Lamar': (30.0558, -94.0868, 'Vincent-Beck Stadium'),
    'McNeese': (30.2022, -93.2136, 'Cowboy Diamond'),
    'New Orleans': (30.0284, -90.0673, 'Maestri Field'),
    'Nicholls': (29.4499, -90.8196, 'Ben Meyer Diamond'),
    'Northwestern State': (31.7606, -93.1016, 'Brown-Stroud Field'),
    'Southeastern Louisiana': (30.5147, -90.4675, 'Alumni Field'),
    'Stephen F. Austin': (31.6189, -94.6559, 'Jaycees Field'),
    'Texas A&M-Corpus Christi': (27.7139, -97.3258, 'Chapman Field'),
    'UTRGV': (26.3058, -98.1739, 'UTRGV Baseball Stadium'),
    'UIW': (29.4630, -98.4675, 'Sullivan Field'),

    # Big South
    'Charleston Southern': (32.9786, -80.0606, 'CSU Softball Complex'),
    'Gardner-Webb': (35.2310, -81.6870, 'John Henry Moss Stadium'),
    'High Point': (35.9691, -79.9969, 'Williard Stadium'),
    'Longwood': (37.2961, -78.3953, 'Lancer Field'),
    'Presbyterian': (34.5079, -81.9099, 'PC Baseball Complex'),
    'Radford': (37.1349, -80.5583, 'Radford Baseball Stadium'),
    'UNC Asheville': (35.6163, -82.5668, 'Greenwood Field'),
    'USC Upstate': (34.9280, -81.9850, 'Harley Park'),
    'Winthrop': (34.9371, -81.0315, 'Winthrop Ballpark'),

    # Horizon League
    'Milwaukee': (43.0766, -87.8815, 'Henry Aaron Field'),
    'Northern Kentucky': (39.0344, -84.4650, 'Bill Aker Baseball Complex'),
    'Oakland': (42.6739, -83.2186, 'Oakland Baseball Field'),
    'PFW': (41.1150, -85.1089, 'Mastodon Field'),
    'Wright State': (39.7847, -84.0614, 'Nischwitz Stadium'),
    'Youngstown State': (41.1072, -80.6463, 'Eastwood Field'),

    # America East
    'Albany': (42.6866, -73.8232, 'Varsity Field'),
    'Binghamton': (42.0903, -75.9685, 'Bearcats Sports Complex'),
    'Bryant': (41.8469, -71.4591, 'Conaty Park'),
    'Maine': (44.8992, -68.6666, 'Mahaney Diamond'),
    'NJIT': (40.7424, -74.1793, 'Bears & Eagles Riverfront Stadium'),
    'UMBC': (39.2559, -76.7109, 'Alumni Field'),
    'UMass Lowell': (42.6559, -71.3249, 'LeLacheur Park'),

    # SWAC
    'Alabama A&M': (34.7834, -86.5686, 'Bulldog Field'),
    'Alabama State': (32.3643, -86.2956, 'Wheeler-Watkins Baseball Complex'),
    'Alcorn State': (31.8770, -91.1348, 'Foster Stadium'),
    'Arkansas-Pine Bluff': (34.2281, -92.0018, 'Torii Hunter Baseball Complex'),
    'Bethune-Cookman': (29.1957, -81.0460, 'Jackie Robinson Ballpark'),
    'Florida A&M': (30.4242, -84.2841, 'Moore-Kittles Field'),
    'Grambling State': (32.5249, -92.7147, 'Wilbert Ellis Field'),
    'Jackson State': (32.2961, -90.2048, 'Braddy Field'),
    'Mississippi Valley State': (33.4930, -90.3130, 'Magnolia Stadium'),
    'Prairie View A&M': (30.0925, -95.9878, 'Tankersley Field'),
    'Southern': (30.5192, -91.1903, 'Lee-Hines Field'),
    'Texas Southern': (29.7234, -95.3475, 'MacGregor Park'),

    # Additional missing teams
    'Coppin State': (39.3436, -76.6567, 'Coppin State Baseball Field'),
    'Delaware State': (39.1874, -75.5406, 'DSU Baseball Complex'),
    'Norfolk State': (36.8481, -76.2669, 'Marty L. Miller Field'),
}


# NCAA Team Logos using ESPN team IDs
# URL pattern: https://a.espncdn.com/i/teamlogos/ncaa/500/{id}.png
NCAA_TEAM_LOGOS = {
    # ACC
    'Boston College': 103,
    'California': 25,
    'Clemson': 228,
    'Duke': 150,
    'Florida State': 52,
    'Georgia Tech': 59,
    'Louisville': 97,
    'Miami': 2390,
    'NC State': 152,
    'North Carolina': 153,
    'Notre Dame': 87,
    'Pittsburgh': 221,
    'SMU': 2567,
    'Stanford': 24,
    'Virginia': 258,
    'Virginia Tech': 259,
    'Wake Forest': 154,

    # SEC
    'Alabama': 333,
    'Arkansas': 8,
    'Auburn': 2,
    'Florida': 57,
    'Georgia': 61,
    'Kentucky': 96,
    'LSU': 99,
    'Mississippi State': 344,
    'Missouri': 142,
    'Oklahoma': 201,
    'Ole Miss': 145,
    'South Carolina': 2579,
    'Tennessee': 2633,
    'Texas': 251,
    'Texas A&M': 245,
    'Vanderbilt': 238,

    # Big 12
    'Arizona': 12,
    'Arizona State': 9,
    'Baylor': 239,
    'BYU': 252,
    'Cincinnati': 2132,
    'Colorado': 38,
    'Houston': 248,
    'Kansas': 2305,
    'Kansas State': 2306,
    'Oklahoma State': 197,
    'TCU': 2628,
    'Texas Tech': 2641,
    'UCF': 2116,
    'Utah': 254,
    'West Virginia': 277,

    # Big Ten
    'Illinois': 356,
    'Indiana': 84,
    'Iowa': 2294,
    'Maryland': 120,
    'Michigan': 130,
    'Michigan State': 127,
    'Minnesota': 135,
    'Nebraska': 158,
    'Northwestern': 77,
    'Ohio State': 194,
    'Oregon': 2483,
    'Penn State': 213,
    'Purdue': 2509,
    'Rutgers': 164,
    'UCLA': 26,
    'USC': 30,
    'Washington': 264,

    # Pac-12
    'Oregon State': 204,
    'Washington State': 265,

    # WCC
    'Gonzaga': 2250,
    'LMU': 2350,
    'Pacific': 279,
    'Pepperdine': 2492,
    'Portland': 2507,
    "Saint Mary's": 2608,
    'San Diego': 2612,
    'San Francisco': 2608,
    'Santa Clara': 2541,

    # Mountain West
    'Air Force': 2005,
    'Fresno State': 278,
    'Grand Canyon': 2253,
    'Nevada': 2440,
    'New Mexico': 167,
    'San Diego State': 21,
    'San Jose State': 23,
    'UNLV': 2439,

    # Missouri Valley
    'Belmont': 2057,
    'Bradley': 2080,
    'Evansville': 339,
    'Illinois State': 2287,
    'Indiana State': 282,
    'Murray State': 93,
    'Southern Illinois': 79,
    'UIC': 82,
    'Valparaiso': 2674,

    # Summit League
    'North Dakota State': 2449,
    'Northern Colorado': 2458,
    'Omaha': 2437,
    'Oral Roberts': 198,
    'South Dakota State': 2571,
    'St. Thomas': 2900,

    # Big East
    'Butler': 2086,
    'Creighton': 156,
    'Georgetown': 46,
    'Seton Hall': 2550,
    "St. John's": 2599,
    'UConn': 41,
    'Villanova': 222,
    'Xavier': 2752,

    # Sun Belt
    'Appalachian State': 2026,
    'Arkansas State': 2032,
    'Coastal Carolina': 324,
    'Georgia Southern': 290,
    'Georgia State': 2247,
    'James Madison': 256,
    'Louisiana': 309,
    'Louisiana-Monroe': 2433,
    'Marshall': 276,
    'Old Dominion': 295,
    'South Alabama': 6,
    'Southern Miss': 2572,
    'Texas State': 326,
    'Troy': 2653,

    # Southern
    'ETSU': 2193,
    'Mercer': 2382,
    'Samford': 2534,
    'The Citadel': 2643,
    'UNC Greensboro': 2430,
    'VMI': 2678,
    'Western Carolina': 2717,
    'Wofford': 2747,

    # Northeast
    'Central Connecticut': 2115,
    'Fairleigh Dickinson': 161,
    'Le Moyne': 2329,
    'LIU': 2344,
    'Mercyhurst': 2372,
    'Stonehill': 2926,
    'Wagner': 2681,

    # Big West
    'Cal Poly': 13,
    'Cal State Fullerton': 2239,
    'CSU Bakersfield': 2934,
    'CSUN': 2463,
    'Hawaii': 62,
    'Long Beach State': 299,
    'UC Davis': 302,
    'UC Irvine': 300,
    'UC Riverside': 27,
    'UC San Diego': 28,
    'UC Santa Barbara': 2540,

    # WAC
    'Abilene Christian': 2000,
    'California Baptist': 16541,
    'Sacramento State': 16,
    'Tarleton State': 2466,
    'UT Arlington': 250,
    'Utah Tech': 3137,
    'Utah Valley': 3084,

    # American
    'Charlotte': 2429,
    'East Carolina': 151,
    'FAU': 2226,
    'Memphis': 235,
    'Rice': 242,
    'Tulane': 2655,
    'UAB': 5,
    'USF': 58,
    'UTSA': 2636,
    'Wichita State': 2724,

    # MAC
    'Akron': 2006,
    'Ball State': 2050,
    'Bowling Green': 189,
    'Central Michigan': 2117,
    'Eastern Michigan': 2199,
    'Kent State': 2309,
    'Miami (OH)': 193,
    'NIU': 2459,
    'Ohio': 195,
    'Toledo': 2649,
    'UMass': 113,
    'Western Michigan': 2711,

    # Patriot League
    'Army': 349,
    'Bucknell': 2083,
    'Holy Cross': 107,
    'Lafayette': 322,
    'Lehigh': 2329,
    'Navy': 2426,

    # Ivy League
    'Brown': 225,
    'Columbia': 171,
    'Cornell': 172,
    'Dartmouth': 159,
    'Harvard': 108,
    'Penn': 219,
    'Princeton': 163,
    'Yale': 43,

    # Atlantic 10
    'Davidson': 2166,
    'Dayton': 2168,
    'Fordham': 2230,
    'George Mason': 2244,
    'George Washington': 45,
    'La Salle': 2325,
    'Rhode Island': 227,
    'Richmond': 257,
    "Saint Joseph's": 2603,
    'Saint Louis': 139,
    'St. Bonaventure': 179,
    'VCU': 2670,

    # Conference USA
    'Dallas Baptist': 2162,
    'Delaware': 48,
    'FIU': 2229,
    'Jacksonville State': 55,
    'Kennesaw State': 338,
    'Liberty': 2335,
    'Louisiana Tech': 2348,
    'Middle Tennessee': 2393,
    'Missouri State': 2623,
    'New Mexico State': 166,
    'Sam Houston': 2534,
    'WKU': 98,

    # CAA
    'Campbell': 2097,
    'Charleston': 232,
    'Elon': 2210,
    'Hofstra': 2275,
    'Monmouth': 2405,
    'North Carolina A&T': 2448,
    'Northeastern': 111,
    'Stony Brook': 2619,
    'Towson': 119,
    'UNC Wilmington': 350,
    'William & Mary': 2729,

    # Ohio Valley
    'Eastern Illinois': 2197,
    'Lindenwood': 2815,
    'Little Rock': 2031,
    'Morehead State': 2413,
    'SIU Edwardsville': 2565,
    'Southeast Missouri': 2546,
    'Southern Indiana': 6916,
    'Tennessee State': 2634,
    'Tennessee Tech': 2635,
    'UT Martin': 2630,
    'Western Illinois': 2710,

    # ASUN
    'Austin Peay': 2046,
    'Bellarmine': 91,
    'Central Arkansas': 2110,
    'Eastern Kentucky': 2198,
    'FGCU': 526,
    'Jacksonville': 294,
    'Lipscomb': 288,
    'North Alabama': 2453,
    'North Florida': 2454,
    'Queens': 2761,
    'Stetson': 56,
    'West Georgia': 20049,

    # Southland
    'Houston Christian': 2277,
    'Lamar': 2320,
    'McNeese': 2377,
    'New Orleans': 2443,
    'Nicholls': 2447,
    'Northwestern State': 2464,
    'Southeastern Louisiana': 2545,
    'Stephen F. Austin': 2617,
    'Texas A&M-Corpus Christi': 357,
    'UTRGV': 292,
    'UIW': 2916,

    # Big South
    'Charleston Southern': 2127,
    'Gardner-Webb': 2241,
    'High Point': 2272,
    'Longwood': 2344,
    'Presbyterian': 2506,
    'Radford': 2520,
    'UNC Asheville': 2427,
    'USC Upstate': 2908,
    'Winthrop': 2745,

    # Horizon League
    'Milwaukee': 270,
    'Northern Kentucky': 94,
    'Oakland': 2473,
    'PFW': 2870,
    'Wright State': 2750,
    'Youngstown State': 2754,

    # America East
    'Albany': 399,
    'Binghamton': 2066,
    'Bryant': 2803,
    'Maine': 311,
    'NJIT': 2885,
    'UMBC': 2378,
    'UMass Lowell': 2349,

    # SWAC
    'Alabama A&M': 2010,
    'Alabama State': 2011,
    'Alcorn State': 2016,
    'Arkansas-Pine Bluff': 2029,
    'Bethune-Cookman': 2065,
    'Florida A&M': 50,
    'Grambling State': 2755,
    'Jackson State': 2296,
    'Mississippi Valley State': 2400,
    'Prairie View A&M': 2504,
    'Southern': 2582,
    'Texas Southern': 2640,

    # Additional teams
    'Coppin State': 2154,
    'Delaware State': 2169,
    'Norfolk State': 2450,
    'San Francisco State': 2614,
}


def get_ncaa_logo_url(team: str) -> str:
    """Get ESPN logo URL for an NCAA team.

    Args:
        team: Team name

    Returns:
        ESPN logo URL or empty string if not found
    """
    espn_id = NCAA_TEAM_LOGOS.get(team)
    if espn_id:
        return f'https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png'
    return ''


def get_stadium_info(team: str) -> tuple:
    """Get stadium info for a team.

    Returns:
        Tuple of (lat, lng, stadium_name) or None if not found
    """
    return STADIUM_DATA.get(team)


def get_all_stadiums() -> dict:
    """Get all stadium data."""
    return STADIUM_DATA
