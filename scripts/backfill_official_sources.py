#!/usr/bin/env python3
"""Backfill official source URLs for scored XC Ski Labs profiles.

The ratings UI numbers the official source first. This migration only fills a
missing ``vitals.website`` and never overwrites an existing organizer URL.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RACE_DATA = ROOT / "race-data"

OFFICIAL_URLS = {
    "7-mila": "https://www.7-mila.se/",
    "alutaguse-maraton": "https://www.alutagusemaraton.ee/",
    "bessemerloppet": "https://www.bessemerloppet.se/",
    "bieg-podhalanski": "https://www.nowytarg.pl/miasto-nowy-targ/aktualnosci/xiii-bieg-podhalanski-17-stycznia-2026-r%2C2850",
    "blafjallagangan": "https://blafjallagangan.is/",
    "carpathian-ski-marathon": "https://klk.com.ua/",
    "etoile-des-saisies": "https://www.lessaisies.com/evenements/etoile-des-saisies/",
    "flyktningerennet": "https://flyktningerennet.no/",
    "grenaderlopet": "https://www.grenaderen.com/next/p/96737/hjem",
    "hafjell-ski-marathon": "https://hafjellskimarathon.no/",
    "jyvaskyla-ski-marathon": "https://jyvaskylaskimarathon.fi/",
    "kananaskis-ski-marathon": "https://www.foothillsnordic.ca/cookie-race",
    "kungsledenrannet": "https://www.kungsledenrannet.se/",
    "la-sgambeda": "https://www.lasgambeda.it/",
    "marathon-de-bessans": "https://www.marathondebessans.com/",
    "marathon-du-grand-bec": "https://www.marathondugrandbec.com/",
    "mt-ashwabay-summit": "https://ashwabaysummitskirace.com/",
    "neeruti-maraton": "https://www.estoloppet.ee/et/etapid?competition_id=458",
    "panorama-nordic-loppet": "https://www.panoramaresort.com/explore/nipika-panorama-loppet",
    "planoiras-volkslanglauf": "https://arosalenzerheide.swiss/de/Lenzerheide/Top-Events/Sport/Planoiras-Volkslanglauf",
    "pyeongchang-loppet": "https://skiclassics.com/events/challengers/pyeongchang-loppet/",
    "sisu-ski-fest": "https://www.sisuskifest.com/",
    "ski-de-she": "https://www.birkie.com/ski/events/ski-de-she/",
    "sumavsky-skimaraton": "https://www.skisumava.cz/ski",
    "tallinn-ski-marathon": "https://www.worldloppet.com/tallinn-ski-marathon/",
    "tamsalu-ski-marathon": "https://www.worldloppet.com/tamsalu-neeruti-maraton/",
    "thorleif-haugs-minnelop": "https://www.hauern.no/next/p/27881/hauern---thorleif-haugs-minnelop",
    "traverse-du-massacre": "https://www.ski-massif-jurassien.com/infos/traversee-du-massacre-01-03-2026/",
    "ushuaia-loppet": "https://www.ushuaialoppet.com/",
    "ushuaia-ski-marathon": "https://www.ushuaialoppet.com/",
    "valdres-skimaraton": "https://www.valdresskimaraton.no/",
    "vasaloppet-japan": "https://www.vasaloppet.jp/",
    "viru-maraton": "https://www.estoloppet.ee/en/etapid?competition_id=455",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    changed = []
    missing = []
    for path in sorted(RACE_DATA.glob("*.json")):
        if path.name == "_schema.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        race = data.get("race", data)
        if not race.get("nordic_lab_rating"):
            continue
        vitals = race.setdefault("vitals", {})
        if vitals.get("website") or vitals.get("official_website_url"):
            continue
        url = OFFICIAL_URLS.get(path.stem)
        if not url:
            missing.append(path.stem)
            continue
        changed.append(path.stem)
        if not args.check:
            vitals["website"] = url
            if "race" in data:
                data["race"] = race
            else:
                data = race
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for slug in changed:
        print(f"{'WOULD ADD' if args.check else 'ADDED'} {slug}")
    if missing:
        print("MISSING " + ", ".join(missing))
        return 1
    print(f"{'Would update' if args.check else 'Updated'} {len(changed)} profile(s); every scored profile has an official source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
