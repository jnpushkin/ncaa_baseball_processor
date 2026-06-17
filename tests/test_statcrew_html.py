from parsers.statcrew_html import parse_statcrew_html


def test_parse_statcrew_html_batting_positions_and_metadata():
    html = """
    <html><body>
    <font size=3><b>
    2025 Virginia Baseball<br>
    Virginia at California<br>
    Mar 15, 2025 at Berkeley, CA (Stu Gordon Stadium)<br>
    </b></font>
    <table>
      <tr><td colspan=11><center><h4>Virginia 10 (11-6,2-3 ACC)</h4></center></td></tr>
      <tr><td>Player&nbsp;</td><td>ab</td><td>r</td><td>h</td><td>rbi</td><td>bb</td><td>so</td><td>po</td><td>a</td><td>lob</td><td>avg</td></tr>
      <tr><td>Aidan Teel cf&nbsp;</td><td>4</td><td>1</td><td>1</td><td>1</td><td>0</td><td>0</td><td>2</td><td>0</td><td>1</td><td>-</td></tr>
      <tr><td>Henry Ford rf/1b&nbsp;</td><td>4</td><td>1</td><td>2</td><td>3</td><td>1</td><td>0</td><td>3</td><td>0</td><td>0</td><td>-</td></tr>
      <tr><td>Totals</td><td>8</td><td>2</td><td>3</td><td>4</td><td>1</td><td>0</td><td>5</td><td>0</td><td>1</td><td></td></tr>
    </table>
    <table>
      <tr><td colspan=11><center><h4>California 8 (9-9,2-3 ACC)</h4></center></td></tr>
      <tr><td>Player&nbsp;</td><td>ab</td><td>r</td><td>h</td><td>rbi</td><td>bb</td><td>so</td><td>po</td><td>a</td><td>lob</td><td>avg</td></tr>
      <tr><td>Gwynn,S cf&nbsp;</td><td>6</td><td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>3</td><td>-</td></tr>
      <tr><td>Tayman,R dh&nbsp;</td><td>5</td><td>1</td><td>3</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>-</td></tr>
      <tr><td>Totals</td><td>11</td><td>1</td><td>4</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>3</td><td></td></tr>
    </table>
    </body></html>
    """

    parsed = parse_statcrew_html(html)

    assert parsed["metadata"]["date_yyyymmdd"] == "20250315"
    assert parsed["metadata"]["away_team"] == "Virginia"
    assert parsed["metadata"]["home_team"] == "California"
    assert parsed["metadata"]["away_team_score"] == 10
    assert parsed["metadata"]["home_team_score"] == 8
    assert parsed["box_score"]["away_batting"][1]["position"] == "rf/1b"
    assert parsed["box_score"]["home_batting"][0]["name"] == "Gwynn,S"
    assert parsed["box_score"]["home_batting"][0]["position"] == "cf"
    assert parsed["box_score"]["home_batting"][1]["name"] == "Tayman,R"
    assert parsed["box_score"]["home_batting"][1]["position"] == "dh"


def test_parse_modern_sidearm_composite_batting_and_pitching():
    html = """
    <html><body>
    <aside class="game-details">
      <h3>Game Details</h3>
      <div>Date</div><div>04/18/2026</div>
      <div>Start</div><div>2:06 PM</div>
      <div>Time</div><div>2:34</div>
      <div>Attendance</div><div>476</div>
      <div>Site</div><div>Berkeley, CA (Evans Diamond at Stu Gordon Stadium)</div>
      <div>Umpires</div><div>Home Plate: Darren Hyman First: AJ Lostaglio Second Base: Sam Burch Third Base: Tim Rosso</div>
    </aside>
    <table>
      <caption>Team Score By Innings</caption>
      <thead><tr><th>Team</th><th>1</th><th>2</th><th>R</th><th>H</th><th>E</th></tr></thead>
      <tbody>
        <tr><td><span class="hide-on-large-down">Louisville</span></td><td>0</td><td>5</td><td>5</td><td>9</td><td>1</td></tr>
        <tr><td><span class="hide-on-large-down">California</span></td><td>6</td><td>X</td><td>6</td><td>9</td><td>1</td></tr>
      </tbody>
    </table>
    <table>
      <caption>Louisville 5 - Composite Stats</caption>
      <tr><th>POS</th><th>Player</th><th>AB</th><th>R</th><th>H</th><th>RBI</th><th>2B</th><th>3B</th><th>HR</th><th>BB</th><th>SB</th><th>CS</th><th>HBP</th><th>SH</th><th>SF</th><th>SO</th><th>KL</th><th>GDP</th><th>PO</th><th>A</th></tr>
      <tr><td>PR</td><td>PR Campbell, Kyle</td><td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
      <tr><td></td><td>Totals</td><td>0</td><td>5</td><td>9</td><td>5</td><td>0</td><td>0</td><td>1</td><td>1</td><td>2</td><td>0</td><td>0</td><td>1</td><td>1</td><td>8</td><td>1</td><td>0</td><td>24</td><td>12</td></tr>
    </table>
    <table>
      <caption>California 6 Composite Stats</caption>
      <tr><th>POS</th><th>Player</th><th>AB</th><th>R</th><th>H</th><th>RBI</th><th>2B</th><th>3B</th><th>HR</th><th>BB</th><th>SB</th><th>CS</th><th>HBP</th><th>SH</th><th>SF</th><th>SO</th><th>KL</th><th>GDP</th><th>PO</th><th>A</th></tr>
      <tr><td>1b</td><td><span>1b</span> Murillo, Daniel
        <td>3</td><td>2</td><td>3</td><td>4</td><td>0</td><td>0</td><td>2</td><td>0</td><td>0</td><td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>10</td><td>0</td>
      </td></tr>
      <tr><td></td><td>Totals</td><td>32</td><td>6</td><td>9</td><td>5</td><td>1</td><td>0</td><td>2</td><td>2</td><td>0</td><td>1</td><td>2</td><td>0</td><td>0</td><td>5</td><td>3</td><td>1</td><td>27</td><td>11</td></tr>
    </table>
    <table>
      <caption>Louisville - Pitching Stats</caption>
      <tr><th>Player</th><th>IP</th><th>H</th><th>R</th><th>ER</th><th>BB</th><th>SO</th><th>WP</th><th>BK</th><th>HBP</th><th>IBB</th><th>AB</th><th>BF</th><th>FO</th><th>GO</th><th>NP</th></tr>
      <tr><td>Eberle, Ethan (L, 3-3)</td><td>5.0</td><td>7</td><td>5</td><td>5</td><td>1</td><td>1</td><td>0</td><td>0</td><td>2</td><td>0</td><td>21</td><td>24</td><td>3</td><td>10</td><td>80</td></tr>
    </table>
    <table>
      <caption>California - Pitching Stats</caption>
      <tr><th>Player</th><th>IP</th><th>H</th><th>R</th><th>ER</th><th>BB</th><th>SO</th><th>WP</th><th>BK</th><th>HBP</th><th>IBB</th><th>AB</th><th>BF</th><th>FO</th><th>GO</th><th>NP</th></tr>
      <tr><td>Eddy, Gavin (W, 6-2)</td><td>8.0</td><td>7</td><td>4</td><td>3</td><td>1</td><td>7</td><td>0</td><td>0</td><td>0</td><td>1</td><td>29</td><td>32</td><td>7</td><td>9</td><td>109</td></tr>
    </table>
    </body></html>
    """

    parsed = parse_statcrew_html(html)

    assert parsed["metadata"]["date_yyyymmdd"] == "20260418"
    assert parsed["metadata"]["attendance"] == 476
    assert parsed["metadata"]["away_team"] == "Louisville"
    assert parsed["metadata"]["home_team"] == "California"
    assert parsed["box_score"]["line_score"]["home_innings"] == [6, 0]

    assert parsed["box_score"]["away_batting"][0]["name"] == "Kyle Campbell"
    assert parsed["box_score"]["away_batting"][0]["position"] == "pr"
    assert parsed["box_score"]["away_batting"][0]["runs"] == 1

    murillo = parsed["box_score"]["home_batting"][0]
    assert murillo["name"] == "Daniel Murillo"
    assert murillo["home_runs"] == 2
    assert murillo["hit_by_pitch"] == 1

    assert parsed["box_score"]["away_pitching"][0]["name"] == "Ethan Eberle"
    assert parsed["box_score"]["away_pitching"][0]["loss"] is True
    assert parsed["box_score"]["away_pitching"][0]["batters_faced"] == 24
    assert parsed["box_score"]["home_pitching"][0]["win"] is True
    assert parsed["box_score"]["home_pitching"][0]["pitches"] == 109


def test_parse_modern_sidearm_play_by_play_tables():
    html = """
    <html><body>
      <section id="play-by-play">
        <div id="inning-all">
          <table class="sidearm-table play-by-play">
            <caption>Louisville - Top of 1st</caption>
            <thead><tr><th>Play Description</th><th>LOU</th><th>CAL</th></tr></thead>
            <tbody>
              <tr><td>Rose,Zion singled through the left side (1-0 B).</td><td>0</td><td>0</td></tr>
            </tbody>
          </table>
          <table class="sidearm-table play-by-play">
            <caption>California - Bottom of 1st</caption>
            <thead><tr><th>Play Description</th><th>LOU</th><th>CAL</th></tr></thead>
            <tbody>
              <tr><td>Murillo,Daniel homered to center field, 2RBI (0-0); Kenady,Jett scored.</td><td>1</td><td>3</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </body></html>
    """

    parsed = parse_statcrew_html(html)

    assert parsed["play_by_play"][1]["top"][0]["description"].startswith("Rose,Zion singled")
    assert parsed["play_by_play"][1]["top"][0]["pitch_count"] == "1-0 B"
    assert parsed["play_by_play"][1]["bottom"][0]["rbi"] == 2
    assert parsed["play_by_play"][1]["bottom"][0]["home_score"] == 3


def test_parse_legacy_statcrew_pitching_team_header_and_decision():
    html = """
    <html><body>
    <table>
      <tr><td>Player</td><td>ab</td><td>r</td><td>h</td><td>rbi</td><td>bb</td><td>so</td><td>po</td><td>a</td><td>lob</td></tr>
      <tr><td>Example Batter rf</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
      <tr><td>Totals</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
    </table>
    <table>
      <tr><td>Player</td><td>ab</td><td>r</td><td>h</td><td>rbi</td><td>bb</td><td>so</td><td>po</td><td>a</td><td>lob</td></tr>
      <tr><td>Other Batter cf</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
      <tr><td>Totals</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
    </table>
    <table>
      <tr><td>VMI</td><td>ip</td><td>h</td><td>r</td><td>er</td><td>bb</td><td>so</td><td>wp</td><td>bk</td><td>hbp</td><td>ibb</td><td>ab</td><td>bf</td><td>fo</td><td>go</td><td>np</td></tr>
      <tr><td>Brandon Barbery W,1-0</td><td>5.0</td><td>6</td><td>3</td><td>1</td><td>1</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>22</td><td>23</td><td>8</td><td>6</td><td>79</td></tr>
      <tr><td>Brandon Barbery W,1-0</td><td>5.0</td><td>6</td><td>3</td><td>1</td><td>1</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>22</td><td>23</td><td>8</td><td>6</td><td>79</td></tr>
    </table>
    <table>
      <tr><td>Virginia</td><td>ip</td><td>h</td><td>r</td><td>er</td><td>bb</td><td>so</td><td>wp</td><td>bk</td><td>hbp</td><td>ibb</td><td>ab</td><td>bf</td><td>fo</td><td>go</td><td>np</td></tr>
      <tr><td>McGarry, G. L,0-1</td><td>0.2</td><td>2</td><td>5</td><td>5</td><td>3</td><td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>4</td><td>7</td><td>1</td><td>1</td><td>38</td></tr>
    </table>
    </body></html>
    """

    parsed = parse_statcrew_html(html)

    assert len(parsed["box_score"]["away_pitching"]) == 1
    barbery = parsed["box_score"]["away_pitching"][0]
    assert barbery["name"] == "Brandon Barbery"
    assert barbery["win"] is True
    assert barbery["batters_faced"] == 23
    assert parsed["box_score"]["home_pitching"][0]["name"] == "G. McGarry"
    assert parsed["box_score"]["home_pitching"][0]["loss"] is True
