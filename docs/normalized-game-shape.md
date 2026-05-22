# Normalized Game Shape

Every parser can keep its source cache format, but processors should consume the
normalized adapter from `baseball_processor.normalization`.

## Top-Level Contract

`normalize_game(raw_game)` returns:

| Key | Shape | Notes |
| --- | --- | --- |
| `game_id` | string | Stable source-aware id such as `ncaa_pdf_YYYYMMDD_away_at_home_score_score`, `ncaa_api_<game_id>`, `milb_<game_pk>`, or `partner_<league>_<id>`. NCAA fallback ids include score and start time when available to avoid doubleheader collisions. |
| `source` | string | `ncaa`, `ncaa_api`, `milb`, or `partner` when available. |
| `basic_info` | object | Date, teams, scores, venue, source, level, and league. |
| `batting` | `{away: [], home: []}` | Rows with canonical stat keys plus original source keys. |
| `pitching` | `{away: [], home: []}` | Rows with canonical stat keys plus original source keys. |
| `game_notes` | object | Original notes, used for NCAA extra-base hit corrections. |
| `play_by_play` | object | Original play-by-play payload when present. |
| `raw` | object | Original raw game dictionary for source-specific drilldowns. |

## Row Keys

Batters should use canonical uppercase keys in processor code:

`AB`, `R`, `H`, `RBI`, `BB`, `SO`, `2B`, `3B`, `HR`, `SB`, `CS`, `HBP`, `SF`, `SH`.

Pitchers should use:

`IP`, `H`, `R`, `ER`, `BB`, `SO`, `HR`, `pitches`, `strikes`, `batters_faced`, `HBP`, `decision`.

The adapter accepts source aliases like `h`/`hits`, `k`/`so`/`strikeouts`,
`ip`/`innings_pitched`, and `bf`/`batters_faced`, then exposes one stable field
name to downstream code.

## Source Rules

- NCAA PDF and NCAA API records both normalize to `level: NCAA`; conference is
  derived from the home team when known.
- MiLB and Partner records resolve level/league through
  `resolve_level_and_league`.
- Missing numeric stats normalize to `0`, not missing values.
- Missing `batters_faced` means “unknown,” not “not a perfect game.” Rules that
  care about BF should only enforce exact BF when a source provided it.
