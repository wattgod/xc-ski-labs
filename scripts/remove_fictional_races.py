#!/usr/bin/env python3
"""
Remove races verified as FICTIONAL by Perplexity existence check.

These 128 profiles had zero web evidence of existing as real organized
cross-country ski races. Each was checked via Perplexity sonar-pro
searching for: official website, race results, news, Worldloppet/FIS
listings, social media, YouTube, and registration pages.

12 of these are duplicates/renames of real races we already have:
  bayerischer-wald-skimarathon → skadi-loppet
  dachstein-nordic-classic → dachsteinlauf (no profile yet)
  halvvasan → vasaloppet (renamed to Vasaloppet 45)
  jamtkraft-ski-marathon → craft-ski-marathon
  kainuu-ski-marathon → vuokatti-hiihto
  keskinada-loppet → gatineau-loppet (old name 1996-2008)
  kortvasan → discontinued Vasaloppet sub-event
  krkonossky-maraton → jizerska-50 (region)
  salpausselka-hiihto → finlandia-hiihto (same venue)
  suomen-hiihto → finlandia-hiihto
  traversee-de-la-haute-jura → transjurassienne
  yllas-pallas → yllas-levi-hiihto (trail running race, not XC)

Usage:
    python scripts/remove_fictional_races.py          # dry run
    python scripts/remove_fictional_races.py --delete  # actually delete
"""

import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "output"

FICTIONAL_SLUGS = [
    "akakura-xc-race",
    "akureyri-ski-marathon",
    "almaty-ski-marathon",
    "astana-ski-marathon",
    "backwoods-pursuit",
    "beito-ski-marathon",
    "beskydy-ski-marathon",
    "bezecka-30",
    "biatlon-romaniei-ski-marathon",
    "bieg-grunwaldzki",
    "bieg-gwarkow",
    "bjelasnica-ski-marathon",
    "bran-castle-ski-marathon",
    "bukovel-ski-marathon",
    "cairngorm-nordic-challenge",
    "cedars-ski-marathon",
    "cerro-catedral-nordic-race",
    "chapelco-nordic-race",
    "corralco-nordic-cup",
    "cradle-mountain-classic",
    "dachstein-nordic-classic",
    "daegwallyeong-snow-festival-race",
    "davos-nordic-marathon",
    "dizin-nordic-race",
    "dolomiti-ski-jazz",
    "egilsstadir-ski-marathon",
    "erciyes-ski-marathon",
    "falls-creek-hotham-crossing",
    "femund-ski-marathon",
    "foothills-nordic-loppet",
    "furano-ski-marathon",
    "gaustarennet",
    "glacier-nordic-races",
    "greina-ski-tour",
    "gudauri-ski-marathon",
    "gulmarg-nordic-ski-challenge",
    "hakkoda-ski-tour",
    "halsingeleden",
    "halvvasan",
    "harbin-ice-and-snow-ski-marathon",
    "harbin-ice-city-marathon",
    "hetta-vuontisjarvi",
    "highland-cross",
    "himos-loppet",
    "hotham-nordic-marathon",
    "ifrane-nordic-festival",
    "jackson-hole-nordic-marathon",
    "jamtkraft-ski-marathon",
    "jeongseon-alpine-cross-country",
    "jilin-city-ski-marathon",
    "jizni-cechy-loppet",
    "jokkmokk-winter-marathon",
    "kainuu-ski-marathon",
    "kamchatka-ski-marathon",
    "kamikawa-loppet",
    "kekes-ski-marathon",
    "keskinada-loppet",
    "keswick-to-barrow",
    "kincaid-classic",
    "kopaonik-nordic-race",
    "kortvasan",
    "kulakova-marathon",
    "kuopio-ski-marathon",
    "la-diable-nordic",
    "leavenworth-nordic-cup",
    "lithuanian-ski-marathon",
    "loppet-de-montreal",
    "loppet-festival-marathon",
    "lysebotn-sirdal",
    "maratonul-zapezii",
    "mont-sainte-anne-loppet",
    "mt-bachelor-nordic-marathon",
    "mt-hermon-nordic-race",
    "muju-taekwondo-ski-marathon",
    "nakkertok-loppet",
    "navrat-pod-lysou",
    "nayoro-citizen-ski-marathon",
    "oregon-nordic-invitational",
    "oregon-winterfest-nordic",
    "otaru-zenichi-loppet",
    "ounasvaara-ski-marathon",
    "perisher-nordic-festival",
    "piancavallo-nordic-marathon",
    "pitea-ski-marathon",
    "platak-nordic-race",
    "porvoo-ski-marathon",
    "pyeongchang-international-xc",
    "raubichi-ski-marathon",
    "romjulsrennet",
    "rovaniemi-arctic-ski-marathon",
    "rukajarvi-march",
    "saariselka-ski-marathon",
    "salpausselka-hiihto",
    "salzkammergut-langlauf",
    "sapporo-bankei-night-ski-race",
    "sapporo-moiwayama-classic",
    "sar-planina-marathon",
    "schwarzwald-skimarathon",
    "shizma-klassika",
    "sierra-de-guadarrama-ski-marathon",
    "silverton-ski-marathon",
    "ski-marathon-montreal",
    "ski-north-loppet",
    "steirische-langlauf-marathon",
    "stenfjellrunden",
    "suomen-hiihto",
    "suomi-hills-classic",
    "superior-nordic-marathon",
    "tarvisio-nordic-challenge",
    "tbilisi-bakuriani-challenge",
    "telemark-marathon",
    "three-rivers-classic",
    "timmins-gold-rush-loppet",
    "tokamachi-snow-marathon",
    "trans-lapland",
    "traversee-de-la-haute-jura",
    "tronfjell-rundt",
    "tug-hill-tourathon",
    "turoa-to-whakapapa-challenge",
    "ufa-marathon",
    "ulaanbaatar-nordic-ski-festival",
    "ulricehamn-ski-marathon",
    "valle-nevado-nordic-challenge",
    "wachau-ski-marathon",
    "wasa-ski-club-loppet",
    "whitehorse-loppet",
    "yakutsk-ski-marathon",
    "yllas-pallas",
    "zao-ski-marathon",
]


def main():
    delete = "--delete" in sys.argv

    deleted_profiles = 0
    deleted_outputs = 0
    missing = 0

    for slug in FICTIONAL_SLUGS:
        profile = RACE_DATA_DIR / f"{slug}.json"
        output = OUTPUT_DIR / slug

        if not profile.exists():
            missing += 1
            continue

        if delete:
            os.remove(profile)
            deleted_profiles += 1
            if output.exists():
                shutil.rmtree(output)
                deleted_outputs += 1
            print(f"  DELETED {slug}")
        else:
            exists_output = "+" if output.exists() else "-"
            print(f"  [DRY RUN] would delete {slug} (output: {exists_output})")

    mode = "DELETED" if delete else "DRY RUN"
    print(f"\n{'=' * 60}")
    print(f"{mode}: {deleted_profiles if delete else len(FICTIONAL_SLUGS)} profiles")
    if delete:
        print(f"Output dirs removed: {deleted_outputs}")
    print(f"Already missing: {missing}")
    print(f"Remaining profiles: {len(list(RACE_DATA_DIR.glob('*.json'))) - 1}")  # -1 for _schema.json


if __name__ == "__main__":
    main()
