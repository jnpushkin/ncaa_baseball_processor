"""Tests for independent/partner league parsers."""

import json

from parsers import partner_leagues
from parsers.partner_leagues import parse_pioneer_html


def test_pioneer_artifact_urls_and_paths(tmp_path):
    urls = partner_leagues.pioneer_boxscore_urls("20260520_6ela")
    paths = partner_leagues.pioneer_artifact_paths("20260520_6ela", output_dir=tmp_path)

    assert urls == {
        "boxscore": "https://www.pioneerleague.com/sports/bsb/2026/boxscores/20260520_6ela.xml",
        "print": "https://www.pioneerleague.com/sports/bsb/2026/boxscores/20260520_6ela.xml?dec=printer-decorator",
        "coach_view": "https://www.pioneerleague.com/sports/bsb/2026/boxscores/20260520_6ela.xml?tmpl=bsxml-monospace-template",
    }
    assert paths["print_pdf"] == tmp_path / "pioneer" / "2026" / "20260520_6ela.print.pdf"
    assert paths["print_html"] == tmp_path / "pioneer" / "2026" / "20260520_6ela.print.html"


def test_process_cached_pioneer_game_downloads_source_artifact_metadata(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    artifact_dir = tmp_path / "artifacts"
    cache_dir.mkdir()
    cache_file = cache_dir / "pioneer_20260520_6ela.json"
    cache_file.write_text(
        json.dumps(
            {
                "metadata": {
                    "source": "partner",
                    "game_code": "20260520_6ela",
                    "away_team": "Missoula PaddleHeads",
                    "home_team": "Oakland Ballers",
                },
                "box_score": {},
            }
        ),
        encoding="utf-8",
    )

    def fake_download(game_code, year=None, output_dir=None, **kwargs):
        paths = partner_leagues.pioneer_artifact_paths(game_code, year, output_dir)
        paths["print_pdf"].parent.mkdir(parents=True, exist_ok=True)
        paths["print_pdf"].write_bytes(b"%PDF-1.4\n")
        paths["print_html"].write_text("<html>print</html>", encoding="utf-8")
        return {
            "artifacts": {
                "print_pdf": str(paths["print_pdf"]),
                "print_html": str(paths["print_html"]),
            }
        }

    monkeypatch.setattr(partner_leagues, "download_pioneer_boxscore_artifacts", fake_download)

    game = partner_leagues.process_partner_game(
        "20260520_6ela",
        "pioneer",
        cache_dir,
        enrich_with_bref_ids=False,
        download_artifacts=True,
        artifact_dir=artifact_dir,
    )

    artifacts = game["metadata"]["source_artifacts"]
    assert artifacts["files"]["print_pdf"].endswith("20260520_6ela.print.pdf")
    assert "printer-decorator" in artifacts["urls"]["print"]

    saved = json.loads(cache_file.read_text(encoding="utf-8"))
    assert saved["metadata"]["source_artifacts"]["files"]["print_html"].endswith("20260520_6ela.print.html")


def test_pioneer_html_merges_batting_summaries_and_pitching_columns():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Missoula PaddleHeads vs. Oakland Ballers - Box Score - 5/20/2026">
      </head>
      <body>
        <table>
          <tr><th>Final</th><th>R</th><th>H</th><th>E</th></tr>
          <tr><th>Missoula PaddleHeads</th><td>8</td><td>10</td><td>0</td></tr>
          <tr><th>Oakland Ballers</th><td>13</td><td>11</td><td>1</td></tr>
        </table>
        <section id="boxscore-tabpanel">
          <div class="stats-box half">
            <table>
              <tr><th>Hitters</th><th>AB</th><th>R</th><th>H</th><th>RBI</th><th>BB</th><th>SO</th><th>LOB</th><th>AVG</th></tr>
              <tr><th><span>rf</span><a>Enzo Apodaca</a></th><td>4</td><td>2</td><td>3</td><td>4</td><td>0</td><td>1</td><td>0</td><td>.571</td></tr>
              <tr><th><span>3b</span><a>Xavier Casserilla</a></th><td>5</td><td>2</td><td>2</td><td>1</td><td>0</td><td>2</td><td>3</td><td>.300</td></tr>
            </table>
            <div class="stats-summary">
              <div class="caption">Batting</div>
              <div><strong>2B:</strong><span>Xavier Casserilla</span></div>
              <div><strong>HR:</strong><span>Enzo Apodaca (2)</span></div>
            </div>
          </div>
          <div class="stats-box half">
            <table>
              <tr><th>Hitters</th><th>AB</th><th>R</th><th>H</th><th>RBI</th><th>BB</th><th>SO</th><th>LOB</th><th>AVG</th></tr>
              <tr><th><span>cf</span><a>T.J. McKenzie</a></th><td>3</td><td>4</td><td>3</td><td>6</td><td>1</td><td>0</td><td>0</td><td>.571</td></tr>
              <tr><th><span>rf</span><a>Noah Blythe</a></th><td>4</td><td>2</td><td>1</td><td>3</td><td>1</td><td>3</td><td>0</td><td>.143</td></tr>
              <tr><th><span>3b</span><a>Jake Allgeyer</a></th><td>4</td><td>0</td><td>2</td><td>1</td><td>1</td><td>1</td><td>0</td><td>.429</td></tr>
              <tr><th><span>ss</span><a>Tremayne Cobb</a></th><td>5</td><td>1</td><td>3</td><td>0</td><td>0</td><td>0</td><td>0</td><td>.500</td></tr>
            </table>
            <div class="stats-summary">
              <div class="caption">Batting</div>
              <div><strong>2B:</strong><span>Jake Allgeyer (2)</span></div>
              <div><strong>HR:</strong><span>Noah Blythe, T.J. McKenzie (3)</span></div>
              <div><strong>SB:</strong><span>Tremayne Cobb (2)</span></div>
            </div>
          </div>
          <div class="stats-box half">
            <table>
              <tr><th>Pitchers</th><th>IP</th><th>H</th><th>R</th><th>ER</th><th>BB</th><th>SO</th><th>HR</th><th>WP</th><th>BF</th><th>AB</th><th>NP</th><th>ERA</th></tr>
              <tr><th>Jaren Jackson</th><td>2.1</td><td>4</td><td>5</td><td>5</td><td>3</td><td>3</td><td>1</td><td>1</td><td>14</td><td>11</td><td>67</td><td>19.29</td></tr>
            </table>
          </div>
          <div class="stats-box half">
            <table>
              <tr><th>Pitchers</th><th>IP</th><th>H</th><th>R</th><th>ER</th><th>BB</th><th>SO</th><th>HR</th><th>WP</th><th>BF</th><th>AB</th><th>NP</th><th>ERA</th></tr>
              <tr><th>Aidan Risse</th><td>3.0</td><td>7</td><td>6</td><td>6</td><td>2</td><td>1</td><td>2</td><td>0</td><td>16</td><td>14</td><td>68</td><td>18.00</td></tr>
            </table>
          </div>
        </section>
      </body>
    </html>
    """

    game = parse_pioneer_html(html, "20260520_6ela")

    assert game["metadata"]["away_team"] == "Missoula PaddleHeads"
    assert game["metadata"]["home_team"] == "Oakland Ballers"
    assert game["metadata"]["away_team_score"] == 8
    assert game["metadata"]["home_team_score"] == 13

    away_batters = {row["name"]: row for row in game["box_score"]["away_batting"]}
    home_batters = {row["name"]: row for row in game["box_score"]["home_batting"]}
    assert away_batters["Enzo Apodaca"]["hr"] == 2
    assert away_batters["Xavier Casserilla"]["doubles"] == 1
    assert home_batters["T.J. McKenzie"]["hr"] == 3
    assert home_batters["Noah Blythe"]["hr"] == 1
    assert home_batters["Jake Allgeyer"]["doubles"] == 2
    assert home_batters["Tremayne Cobb"]["sb"] == 2

    assert game["game_notes"]["home_runs"] == [
        "Enzo Apodaca (2)",
        "Noah Blythe",
        "T.J. McKenzie (3)",
    ]
    assert game["box_score"]["away_pitching"][0]["hr"] == 1
    assert game["box_score"]["away_pitching"][0]["bf"] == 14
    assert game["box_score"]["away_pitching"][0]["np"] == 67
