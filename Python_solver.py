# final_solver.py
# Author: Gulian Ibrahim
# Photospheria Hackathon - Entelect HackIT 2026
# Strategy: Phased unlock chain maximising species diversity,
# grid coverage and plant longevity across all four levels.

import json, os, math

GRASS=1; ROSE_BUSH=2; BLUE_MOSS=3; CRIMSON_VINE=4; DWARF_SUNFLOWER=5
LAVENDER=6; ORANGE_BLOSSOM=7; SILVER_FERN=8; GLOWCAP_FUNGUS=9
PURPLE_CANOPY=10; STONE_REED=11; OAK_TREE=12; EMBERROOT_TREE=13
WHITEVEIL=14; MOONPETAL_LILY=15; IRONTHORN_SHRUB=16; CRYSTAL_CACTUS=17
MIRE_BLOOM=18; RAZORGRASS=19; SKYVINE=20; GHOST_ORCHID=21
AMBER_FERN=22; THORNHEART=23; SPOREWOOD_TREE=24; SUNSHARD_BLOOM=25
ASHROOT_BRAMBLE=26; LIVING_TOPIARY=27; BLOODBLOOM=28
STARCAP_COLONY=29; PHOENIX_BLOOM=30; WORLDTREE=31

MAX_PER_TICK = 20

def parse_level(fp):
    with open(fp) as f: d = json.load(f)
    cell_map = {}
    for c in d.get("cells", []):
        cell_map[(c["row"], c["col"])] = {"terrain": c["terrain"], "soil": c["soil"]}
    seasons, events = {}, {}
    for cmd in d.get("commands", []):
        if cmd["type"] == "season":   seasons[cmd["tick"]] = cmd["season"]
        elif cmd["type"] == "event":  events[cmd["tick"]]  = cmd["event"]
    return {"rows": d["rows"], "cols": d["cols"], "ticks": d["ticks"],
            "animals": d.get("animals_enabled", False),
            "cell_map": cell_map, "seasons": seasons, "events": events}

def soil_cells(cell_map, rows, cols, soils={0,1}, bad_terrain={2,4}):
    out = []
    for r in range(rows):
        for c in range(cols):
            cell = cell_map.get((r,c), {"terrain":0,"soil":0})
            if cell["terrain"] not in bad_terrain and cell["soil"] in soils:
                out.append((r,c))
    return out

def water_adj(cell_map, rows, cols):
    water = {(r,c) for (r,c),v in cell_map.items() if v["terrain"]==1}
    seen, out = set(), []
    for r,c in water:
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr,nc=r+dr,c+dc
            if (nr,nc) in seen: continue
            cell=cell_map.get((nr,nc),{"terrain":0,"soil":0})
            if cell["terrain"] not in {1,2,4}:
                out.append((nr,nc)); seen.add((nr,nc))
    return out

def stone_adj(cell_map, rows, cols):
    stone = {(r,c) for (r,c),v in cell_map.items() if v["terrain"]==2}
    seen, out = set(), []
    for r,c in stone:
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr,nc=r+dr,c+dc
            if (nr,nc) in seen: continue
            cell=cell_map.get((nr,nc),{"terrain":0,"soil":0})
            if cell["terrain"] not in {2,4}:
                out.append((nr,nc)); seen.add((nr,nc))
    return out

def pick(cells, n, offset=0):
    if not cells or n<=0: return []
    if n>=len(cells): return list(cells)
    step = len(cells)/n
    return [cells[int((offset+i*step)%len(cells))] for i in range(n)]

def plant_batch(schedule, species, positions, start_tick, ticks_limit):
    t = start_tick
    for r,c in positions:
        while t in schedule and len(schedule[t])>=MAX_PER_TICK:
            t+=1
        if t>=ticks_limit: break
        schedule.setdefault(t,[]).append({"plant_index":species,"row":r,"col":c})
    return t

def generate(lv, ld):
    rows,cols,ticks = ld["rows"],ld["cols"],ld["ticks"]
    has_animals     = ld["animals"]
    events          = ld["events"]
    cm              = ld["cell_map"]
    total           = rows*cols

    rain_tick    = next((t for t,e in events.items() if e=="Rain"),        ticks)
    drought_tick = next((t for t,e in events.items() if e=="Drought"),     ticks)
    ash_tick     = next((t for t,e in events.items() if e=="Ash Eclipse"), ticks)

    s01   = soil_cells(cm, rows, cols, soils={0,1})
    wadj  = water_adj(cm, rows, cols)
    sadj  = stone_adj(cm, rows, cols)

    schedule = {}

    # ── LEVEL 1: 5 starters only (no animals, no events) ────────────────────
    if lv == 1:
        n = len(s01)
        # 4 Oak Trees at corners (shade radius 4 — keep them isolated)
        oaks = [s01[0], s01[n//4], s01[n//2], s01[3*n//4]] if n>=4 else s01[:1]
        oak_set = set(oaks)
        rest = [p for p in s01 if p not in oak_set]
        q = len(rest)//4
        for species, segment in [
            (OAK_TREE,        oaks),
            (GRASS,           rest[:q]),
            (ROSE_BUSH,       rest[q:2*q]),
            (LAVENDER,        rest[2*q:3*q]),
            (DWARF_SUNFLOWER, rest[3*q:]),
        ]:
            plant_batch(schedule, species, segment, 1, ticks)
        return schedule

    # ── LEVELS 2-4: phased unlock chain ─────────────────────────────────────
    # Seed counts: small enough to fit early, large enough to trigger thresholds
    # Animals trigger on COVERAGE so spread does the heavy lifting — plant seeds only.

    seed = max(20, min(200, total // 100))  # adaptive seed size per level size

    t = 1
    # Phase 1 — starters (trigger all core animals)
    for species, n_seeds, off in [
        (GRASS,           seed*4, 0),   # Loamcrawlers, Verdelopes need high Grass %
        (ROSE_BUSH,       seed*2, 1),   # Loamcrawlers (≥10 count), Grazeleths
        (LAVENDER,        seed*2, 2),   # Nectaris, Virexids
        (DWARF_SUNFLOWER, seed,   3),   # Solwings
        (OAK_TREE,        10,     4),   # Barkskips (≥8), Canorals (Trees≥10)
    ]:
        t = plant_batch(schedule, species, pick(s01, n_seeds, off), t, ticks)

    print(f"  Phase 1 ends ~tick {t}")

    # Phase 2 — Tier 1 unlocks (available once animals appear ~tick 30-50)
    t2 = min(t+1, max(30, t+1))
    for species, n_seeds, off in [
        (CRIMSON_VINE,    seed*3, 10),   # Nectaris|Canorals + Rose Bush > 0
        (ORANGE_BLOSSOM,  seed*2, 11),   # Nectaris|Solwings + Rose Bush > 2%
        (RAZORGRASS,      seed*2, 12),   # Verdelopes + Grass > 5%
        (STONE_REED,      min(seed, len(sadj)), 13),  # Virexids + stone adjacency
    ]:
        cells = sadj if species==STONE_REED else pick(s01, n_seeds, off)
        t2 = plant_batch(schedule, species, cells, t2, ticks)

    print(f"  Phase 2 ends ~tick {t2}")

    # Phase 3 — Tier 2 (Blue Moss triggers more chain ~tick 60)
    t3 = t2 + 1
    for species, n_seeds, off in [
        (BLUE_MOSS,       seed*3, 20),   # Loamcrawlers + Grass>3% + Rose>1%
        (IRONTHORN_SHRUB, seed*2, 21),   # Grazeleths + Rose>4%
        (SILVER_FERN,     seed*2, 22),   # Loamcrawlers|Grazeleths + Blue Moss>3%
        (MOONPETAL_LILY,  seed*2, 23),   # Nectaris + Lavender>4% + Blue Moss>2%
    ]:
        t3 = plant_batch(schedule, species, pick(s01,n_seeds,off), t3, ticks)

    print(f"  Phase 3 ends ~tick {t3}")

    # Phase 4 — Tier 3 (Purple Canopy Tree chain ~tick 100)
    t4 = t3 + 1
    for species, n_seeds, off in [
        (PURPLE_CANOPY,  8,      30),   # Blue Moss>1% + Crimson Vine>4%
        (SKYVINE,        seed*2, 31),   # Crimson Vine>4% + Purple Canopy≥3
        (THORNHEART,     seed*2, 32),   # Ironthorn>5% + Crimson Vine>3%
        (AMBER_FERN,     seed*2, 33),   # Silver Fern>6% + Loamcrawlers + no Monocryx
        (LIVING_TOPIARY, seed,   34),   # Silver Fern>4% + Purple Canopy≥3 + Canorals
    ]:
        t4 = plant_batch(schedule, species, pick(s01,n_seeds,off), t4, ticks)

    print(f"  Phase 4 ends ~tick {t4}")

    # Phase 5 — Mycelium chain + Rhizorends unlocks (~tick 130)
    t5 = t4 + 1
    for species, n_seeds, off in [
        (GLOWCAP_FUNGUS,  seed*3, 40),  # Loamcrawlers + dead_matter>5%
        (WHITEVEIL,       seed*3, 41),  # Glowcap>5% + Loamcrawlers|Rhizorends
        (GHOST_ORCHID,    seed*2, 42),  # Glowcap>3% + Moonpetal>3%
        (BLOODBLOOM,      seed*2, 43),  # Crimson Vine>5% + Rhizorends
        (STARCAP_COLONY,  seed*2, 44),  # Whiteveil>5% + Glowcap>3% + Ghost>1%
        (SUNSHARD_BLOOM,  seed*2, 45),  # Orange>2% + Moonpetal>4% + Nectaris + Solwings
    ]:
        t5 = plant_batch(schedule, species, pick(s01,n_seeds,off), t5, ticks)

    print(f"  Phase 5 ends ~tick {t5}")

    # Phase 6 — Tree chain (Emberroot, Sporewood, Worldtree ~tick 180)
    t6 = t5 + 1
    for species, n_seeds, off in [
        (EMBERROOT_TREE, seed*2, 50),  # Whiteveil>5% + Purple Canopy≥4
        (SPOREWOOD_TREE, 6,      51),  # Whiteveil>3% + Purple Canopy≥4
        (WORLDTREE,      6,      52),  # Oak≥6 + Purple Canopy≥6 + Sporewood≥4 + Barkskips
    ]:
        t6 = plant_batch(schedule, species, pick(s01,n_seeds,off), t6, ticks)

    print(f"  Phase 6 ends ~tick {t6}")

    # Phase 7 — Event-gated plants
    t7 = t6 + 1

    if drought_tick < ticks:
        ct = max(drought_tick+1, t7)
        t7 = plant_batch(schedule, CRYSTAL_CACTUS,
                         pick(s01, seed*2, 60), ct, ticks)
        print(f"  Crystal Cactus @ tick {ct}")

    if rain_tick < ticks and wadj:
        rt = max(rain_tick+1, t7)
        t7 = plant_batch(schedule, MIRE_BLOOM,
                         wadj[:seed*2], rt, ticks)
        print(f"  Mire Bloom @ tick {rt}")

    if True:  # Ashroot needs Emberroot alive + burnt soil ≥20
        at = max(t6+30, t7)
        t7 = plant_batch(schedule, ASHROOT_BRAMBLE,
                         pick(s01, seed*2, 70), at, ticks)
        print(f"  Ashroot Bramble @ tick {at}")

    if ash_tick < ticks:
        pt = max(ash_tick+1, t7+30)
        t7 = plant_batch(schedule, PHOENIX_BLOOM,
                         pick(s01, seed*2, 71), pt, ticks)
        print(f"  Phoenix Bloom @ tick {pt}")

    # Final fill — pack unplanted cells with diverse species for coverage
    planted = {(a["row"],a["col"]) for acts in schedule.values() for a in acts}
    unplanted = [p for p in s01 if p not in planted]
    fill = [GRASS,ROSE_BUSH,LAVENDER,CRIMSON_VINE,BLUE_MOSS,
            ORANGE_BLOSSOM,SILVER_FERN,RAZORGRASS,SKYVINE,
            IRONTHORN_SHRUB,THORNHEART,MOONPETAL_LILY,
            GLOWCAP_FUNGUS,WHITEVEIL,GHOST_ORCHID]
    ft = max(t7+1, 1)
    for i,(r,c) in enumerate(unplanted):
        s = fill[i%len(fill)]
        while ft in schedule and len(schedule[ft])>=MAX_PER_TICK: ft+=1
        if ft>=ticks: break
        schedule.setdefault(ft,[]).append({"plant_index":s,"row":r,"col":c})

    print(f"  Fill ends ~tick {ft} ({len(unplanted)} cells)")
    return schedule

def to_json(schedule):
    return {"actions":[{"tick":t,"plants":p} for t,p in sorted(schedule.items()) if p]}

def solve(fp, lv):
    out = f"solution_level{lv}.json"
    print(f"\n{'='*58}\n  LEVEL {lv}\n{'='*58}")
    ld = parse_level(fp)
    print(f"  {ld['rows']}x{ld['cols']} | {ld['ticks']} ticks | animals={ld['animals']}")
    print(f"  Events: {ld['events']}")
    sched = generate(lv, ld)
    sol   = to_json(sched)
    total = sum(len(t["plants"]) for t in sol["actions"])
    species = len({p["plant_index"] for t in sol["actions"] for p in t["plants"]})
    with open(out,"w") as f: json.dump(sol, f, indent=2)
    print(f"  Actions: {total} | Species: {species} | Written: {out}")
    return out, total, species

def main():
    print("="*58)
    print("  PHOTOSPHERIA - Final Solver | Gulian Ibrahim")
    print("  Entelect HackIT 2026")
    print("="*58)
    results=[]
    for n in [1,2,3,4]:
        fp=f"{n}.json"
        if os.path.exists(fp):
            results.append(solve(fp,n))
    print(f"\n{'='*58}\n  DONE\n{'='*58}")
    for o,c,s in results:
        print(f"  {o}: {c} actions, {s} species")

if __name__=="__main__":
    main()
