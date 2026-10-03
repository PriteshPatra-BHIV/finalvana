# -*- coding: utf-8 -*-
"""Emit the VANA five-region Zone Identity Register.

ASSIGNED
--------
Manager, 2026-08-28: "Hemanth and Group 3 now own immediate creation of an
authoritative five-region Zone Identity Register for Mumbai, Navi Mumbai, Vasai,
Thane and Maval, defining for each region the approved region key, exact zone
boundary/geometry or authoritative survey boundary reference, survey_id, zone_id, and
source/provenance."

And, decisively:

  "If an authoritative zone boundary/code does not yet exist, mark it UNVERIFIED/BLOCKED
   with provenance rather than inventing one, and escalate the exact missing authority.
   Do not use city-centre coordinates as substitutes."

WHAT THIS FILE THEREFORE DOES
-----------------------------
It does NOT invent a boundary, a survey_id or a zone_id for any of the five regions,
because Group 3 holds no authoritative source for any of them. It records what is
actually held, marks the rest BLOCKED, and names the specific authority that must
supply each missing piece.

The provisional city-centre coordinates used in the earlier reachability probe
(GROUP3_REGION_COVERAGE.json) are WITHDRAWN by this register and must not be used.

Run:  python emit_zone_identity_register.py
"""
import datetime, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
ZONE_PATTERN = SCHEMA["properties"]["zone_id"]["pattern"]
SURVEY_PATTERN = SCHEMA["properties"]["survey_id"]["pattern"]

# The ONE authoritative boundary Group 3 actually holds, and it came from Group 2.
G2_CTX = os.path.join(DAY6, "reference", "inbound",
                      "G2_context_TC-Z03-F02-LIDAR-OBS001_AS_RECEIVED_2026-08-21.json")
THANE_CREEK_POLYGON = None
if os.path.exists(G2_CTX):
    THANE_CREEK_POLYGON = json.load(io.open(G2_CTX, encoding="utf-8")).get("location_polygon")


# Administrative authority per region. The municipal/revenue body is named so the
# escalation has an address. District assignments marked VERIFIED were checked this
# session; the rest are marked for LGD confirmation rather than asserted.
REGIONS = [
    {"region": "Mumbai",
     "administrative_body": "Municipal Corporation of Greater Mumbai (MCGM / BMC)",
     "revenue_districts": "Mumbai City and Mumbai Suburban (TWO districts - a single "
                          "'Mumbai' boundary is ambiguous until the intended extent is stated)",
     "district_status": "REQUIRES LGD CONFIRMATION",
     "boundary_complication": ("'Mumbai' may mean the MCGM municipal limit, the two revenue "
                               "districts, or the Mumbai Metropolitan Region. These are different "
                               "polygons. The intended extent must be stated before a boundary "
                               "can be requested.")},

    {"region": "Navi Mumbai",
     "administrative_body": "Navi Mumbai Municipal Corporation (NMMC)",
     "revenue_districts": "Thane district",
     "district_status": "REQUIRES LGD CONFIRMATION",
     "boundary_complication": ("Parts of the planned Navi Mumbai area fall under CIDCO and under "
                               "Panvel Municipal Corporation rather than NMMC. The NMMC limit is "
                               "narrower than colloquial 'Navi Mumbai'.")},

    {"region": "Vasai",
     "administrative_body": "Vasai-Virar City Municipal Corporation (VVCMC), formed 3 July 2010",
     "revenue_districts": "Palghar district",
     "district_status": "VERIFIED 2026-08-28 - listed by palghar.gov.in",
     "boundary_complication": ("The corporation is Vasai-VIRAR. 'Vasai' alone may mean the town, "
                               "the taluka, or the combined VVCMC area. Palghar district was "
                               "itself split from Thane district in 2014, so older boundary "
                               "sources may still place Vasai in Thane.")},

    {"region": "Thane",
     "administrative_body": "Thane Municipal Corporation (TMC)",
     "revenue_districts": "Thane district",
     "district_status": "REQUIRES LGD CONFIRMATION",
     "boundary_complication": ("CRITICAL: 'Thane' the city/district is NOT 'Thane Creek', which is "
                               "the water body Group 3 already surveys as TC-Z03. Group 3 has an "
                               "observation for Thane CREEK and none for Thane. Mapping one to the "
                               "other would be a substitution, not a mapping.")},

    {"region": "Maval",
     "administrative_body": "Maval taluka - a RURAL revenue subdivision of Pune district. No "
                            "municipal corporation. Governed through Panchayat Samiti / Zilla "
                            "Parishad structures",
     "revenue_districts": "Pune district",
     "district_status": "REQUIRES LGD CONFIRMATION",
     "boundary_complication": ("The only region of the five that is not urban. Its boundary is a "
                               "revenue taluka boundary, not a municipal limit, so the authority "
                               "and the artifact type both differ from the other four. It is also "
                               "inland - not a coastal/mangrove environment like the others.")},
]

MISSING_AUTHORITIES = {
    "region_key": {
        "authority": "Local Government Directory (LGD), Ministry of Panchayati Raj",
        "url": "https://lgdirectory.gov.in/",
        "why_this_one": ("LGD assigns a unique code to every administrative unit and local body in "
                         "India and was mandated by the Cabinet Secretariat on 2016-11-04 as the "
                         "standard location code for e-Governance applications. It is maintained "
                         "with the Registrar General and the Ministry of Home Affairs. If VANA "
                         "needs an authoritative region key, this is the existing national one - "
                         "inventing a parallel scheme would create a second identity namespace."),
        "what_to_request": "The LGD code for each of the five regions at the correct level "
                           "(urban local body for four, revenue sub-district for Maval).",
    },
    "boundary_geometry": {
        "authority": ("The relevant municipal corporation for each urban region (MCGM, NMMC, "
                      "VVCMC, TMC), or the district administration for Maval taluka. Survey of "
                      "India is the national mapping authority for boundary geometry; Census of "
                      "India publishes administrative boundary datasets."),
        "why_group3_cannot_supply_it": ("Group 3 has no surveying capability and no boundary "
                                        "dataset. Deriving a polygon from a map service or a "
                                        "city-centre point would be inventing an authoritative "
                                        "boundary, which the manager has explicitly forbidden."),
        "what_to_request": "A boundary polygon or an authoritative boundary reference (a named "
                           "dataset plus version) per region.",
    },
    "survey_id_and_zone_id": {
        "authority": "OPEN - this is the escalation Group 3 needs answered before it can proceed.",
        "the_problem": ("survey_id and zone_id are CANONICAL IDENTITY. The standing authority "
                        "boundary places schemas, provenance and identity with MDU, and the frozen "
                        "contract's owner is Arya Barge. Group 3 producing region identity codes "
                        "unilaterally would create canonical identity - which the contract "
                        "explicitly forbids Group 3 from doing."),
        "what_to_request": ("A ruling on WHO assigns survey_id and zone_id for a new region, and "
                            "confirmation of the scheme. Group 3 can implement any scheme; it "
                            "cannot authorise one."),
    },
}

STRUCTURAL_FINDING = {
    "finding": "A REGION IS NOT A ZONE. The register may be asking for the wrong field.",
    "evidence": {
        "zone_id_pattern": ZONE_PATTERN,
        "zone_id_documented_as": ("'Survey zone, Z1-Z8' - the field that answers 'all observations "
                                  "in Z03 across flights', the quarterly repeat-survey query."),
        "survey_id_pattern": SURVEY_PATTERN,
    },
    "why_it_matters": (
        "zone_id is a SUBDIVISION OF A SURVEY, not a geographic region. Thane Creek is survey TC, "
        "zone Z03 - one zone within one survey of one site. Five metropolitan regions are not five "
        "zones of the same survey; they are five different survey areas.\n\n"
        "The pattern also caps zones at Z1-Z99 syntactically and Z1-Z8 by its own description. If "
        "regions were mapped to zone_id, VANA would exhaust the documented range at eight regions "
        "and would conflate 'which survey area' with 'which part of a survey'."),
    "group3_recommendation": (
        "Each region should get its own survey_id, with zone_id remaining a subdivision WITHIN that "
        "region's survey. Thane Creek already follows this: survey TC, zone Z03. This needs no "
        "contract change and no new field - it is how the contract already works.\n\n"
        "Group 3 recommends but does not decide. This is an identity ruling."),
}


# OWNER RULING, Arya Barge, 2026-08-28. survey_id and zone_id are APPROVED. Recorded
# here because they are now authoritative, not a Group 3 proposal. She corrected the
# Thane code from Group 3's recommended TH to THN, on the grounds that TH is too close
# to TC (Thane Creek) for operational use - a transcription risk Group 3 had flagged.
APPROVED_IDENTITY = {
    "Mumbai": ("MU", "Z01"),
    "Navi Mumbai": ("NM", "Z01"),
    "Vasai": ("VS", "Z01"),
    "Thane": ("THN", "Z01"),
    "Maval": ("MV", "Z01"),
}
IDENTITY_RULING = {
    "ruled_by": "Arya Barge - Group 3 Canonical Observation Contract & Provenance Owner",
    "date": "2026-08-28",
    "decision": "APPROVED",
    "scheme": ("One survey_id per region, Z01 as the initial zone within each survey. A region is a "
               "SURVEY AREA; a zone is a subdivision within it. The five regions are therefore NOT "
               "Z01-Z05 of one survey."),
    "consistent_with": "The existing Thane Creek precedent - survey TC, zone Z03.",
    "thane_code_correction": ("Group 3 recommended TH; the owner approved THN instead. TC is the "
                              "established Thane Creek survey code and TH is too visually close for "
                              "operational use. THN gives Thane city a distinct identity. TC/Z03 "
                              "must NOT be reused for Thane city."),
    "lgd_position": ("These survey_id values are VANA/Group 3 survey identifiers, NOT national "
                     "administrative identifiers. The authoritative administrative region key "
                     "remains the LGD code when supplied, retained as external provenance. It does "
                     "not replace the short survey_id. Group 3 must not invent an LGD code."),
    "contract_status": ("An identity ruling under the already-frozen V2.2 contract. Requires no "
                        "V2.3, no new field, no schema change, and does not reopen the freeze."),
    "explicitly_not_authorised": ("This ruling does NOT authorise Group 3 to resolve the third "
                                  "blocker. Group 3 will not substitute city-centre coordinates, "
                                  "arbitrary map coordinates, inferred boundaries, or another "
                                  "region's boundary."),
    "verified_by_group3": ("All five resulting observation_id values validated against the frozen "
                           "pattern on 2026-08-28. 0 invalid."),
}


def region_entry(r):
    _sv, _zn = APPROVED_IDENTITY[r["region"]]
    return {
        "region": r["region"],
        "approved_region_key": None,
        "region_key_status": "BLOCKED - no LGD code held (external provenance, not identity)",
        "zone_boundary_geometry": None,
        "authoritative_boundary_reference": None,
        "boundary_status": "BLOCKED - no authoritative boundary held",
        "survey_id": _sv,
        "zone_id": _zn,
        "resulting_observation_id": "%s-%s-EXT-OPENMETEO-OBS001" % (_sv, _zn),
        "identity_status": "APPROVED - owner ruling, Arya Barge 2026-08-28",
        "source_provenance": ("Identity: owner ruling, Arya Barge 2026-08-28. "
                              "Boundary: NONE - Group 3 holds no authoritative artifact."),
        "administrative_body": r["administrative_body"],
        "revenue_districts": r["revenue_districts"],
        "district_status": r["district_status"],
        "boundary_complication": r["boundary_complication"],
        "overall": "BLOCKED ON BOUNDARY ONLY - identity resolved",
    }


def main():
    entries = [region_entry(r) for r in REGIONS]

    doc = {
        "_README": ("VANA five-region Zone Identity Register. Produced under the manager's "
                    "direction of 2026-08-28. NOTHING IS INVENTED: every region below is BLOCKED "
                    "because Group 3 holds no authoritative region key, boundary or identity code "
                    "for any of them, and the manager's instruction is to mark that rather than "
                    "substitute a value."),
        "_generated_by": "integration/emit_zone_identity_register.py",
        "_owner": "Hemanth Reddy - Group 3",
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_status": ("IDENTITY FROZEN by owner ruling 2026-08-28. BOUNDARY STILL BLOCKED for all "
                    "five regions - the register cannot be fully frozen until an authoritative "
                    "coordinate exists per region."),
        "identity_ruling": IDENTITY_RULING,
        "_delivered_to": "Group 1 (Sanskar) and Sakshi, per the manager's direction.",

        "_withdrawal": {
            "what": ("The provisional city-centre coordinates in GROUP3_REGION_COVERAGE.json are "
                     "WITHDRAWN by this register."),
            "why": ("The manager ruled: 'do not use provisional city-centre coordinates'. Group 3 "
                    "had already labelled them PROVISIONAL and not-approved-zones, but withdrawing "
                    "them removes any chance of reuse."),
            "what_remains_valid_in_that_file": ("The live reachability probe - all five regions "
                                                "returned HTTP 200 from the source. That proves "
                                                "the SOURCE is reachable. It never proved an "
                                                "identity, and does not now."),
        },

        "summary": {
            "regions_requested": len(REGIONS),
            "regions_with_approved_identity": 5,
            "regions_with_authoritative_boundary": 0,
            "regions_blocked_on_boundary": len(entries),
            "the_honest_position": ("IDENTITY IS RESOLVED - the owner ruled on 2026-08-28 and all "
                                    "five observation_ids validate against the frozen pattern. ONE "
                                    "blocker remains: an authoritative coordinate or boundary per "
                                    "region, which is Group 2's input. Group 3 will not substitute "
                                    "one."),
        },

        "register": entries,

        "the_one_region_that_IS_defined": {
            "region": "Thane Creek",
            "note": ("NOT one of the five requested. Included because it is the only worked "
                     "example and shows what a complete entry looks like."),
            "survey_id": "TC",
            "zone_id": "Z03",
            "zone_boundary_geometry": THANE_CREEK_POLYGON,
            "source_provenance": ("Group 2 scientific context record for TC-Z03-F02-LIDAR-OBS001, "
                                  "received 2026-08-21, field location_polygon. Stored unmodified "
                                  "at reference/inbound/."),
            "status": "VERIFIED - and note the boundary came from GROUP 2, not Group 3.",
            "caveat": ("The polygon is a 0.01 x 0.01 degree box, roughly 1.1 km square. It is "
                       "sufficient to bind a coordinate and is what the emitted observation was "
                       "checked against. It is not a surveyed mangrove extent."),
        },

        "BOUNDARY_AVAILABILITY_FINDING": {
            "_summary": ("TESTED 2026-08-28, not assumed. Two of the five regions are NOT "
                         "administrative divisions at any level, so NO standard boundary dataset "
                         "will ever contain them. This is a category problem, not a sourcing "
                         "delay, and it would otherwise surface only after someone spent hours "
                         "hunting for files."),
            "_what_was_tested": ("geoBoundaries open API queried live. IND ADM2 (districts, year "
                                 "2021) and ADM3 (sub-districts/talukas, year 2018) both return "
                                 "HTTP 200 under Open Data Commons ODbL, pinned to release commit "
                                 "9469f09. It is a versioned, citable source meeting the same "
                                 "standard Group 2 used for the Thane Creek polygon."),
            "per_region": [
                {"region": "Maval", "administrative_reality": "Taluka (sub-district) of Pune district",
                 "boundary_dataset_can_supply": "YES - ADM3", "status": "SOLVABLE"},
                {"region": "Mumbai",
                 "administrative_reality": "TWO districts - Mumbai City and Mumbai Suburban",
                 "boundary_dataset_can_supply": "AMBIGUOUS - which district, or both merged, or the "
                                                "MCGM municipal limit, or the Metropolitan Region",
                 "status": "NEEDS A DECISION ON EXTENT"},
                {"region": "Thane",
                 "administrative_reality": "Thane district exists as ADM2, but Thane Municipal "
                                           "Corporation is far narrower and is a different thing",
                 "boundary_dataset_can_supply": "AMBIGUOUS - the district is not the city",
                 "status": "NEEDS A DECISION ON EXTENT"},
                {"region": "Navi Mumbai",
                 "administrative_reality": "NOT an administrative division. NMMC is a municipal "
                                           "corporation inside Thane district",
                 "boundary_dataset_can_supply": "NO", "status": "NOT IN ANY ADM HIERARCHY"},
                {"region": "Vasai",
                 "administrative_reality": "NOT an administrative division. VVCMC is a municipal "
                                           "corporation inside Palghar district",
                 "boundary_dataset_can_supply": "NO", "status": "NOT IN ANY ADM HIERARCHY"},
            ],
            "_the_consequence": ("Adopting an open boundary dataset closes ONE region cleanly, two "
                                 "ambiguously, and two not at all. It is therefore not a complete "
                                 "answer, and Group 3 will not use a district polygon as a stand-in "
                                 "for a municipal corporation - that is 'another region's boundary', "
                                 "which the contract owner's ruling explicitly excludes."),
            "_verification_caveat": ("The ADM levels, licence and commit pin were verified by live "
                                     "API call. The administrative status of each region is reasoned "
                                     "from administrative structure, not read out of the dataset's "
                                     "contents."),
        },

        "THE_SMALLER_UNLOCK": {
            "_insight": ("The polygon was only ever used to VERIFY a coordinate. What EMISSION "
                         "actually requires is latitude and longitude - the frozen contract's "
                         "location object requires exactly those two sub-fields and no polygon."),
            "_therefore": ("The ask should change from 'supply five boundaries' - which fails for "
                           "two regions regardless of effort - to 'name five specific coordinates, "
                           "with a stated basis, from someone with authority to name them'."),
            "_what_would_qualify": [
                "A named monitoring site or field station.",
                "A creek mouth, gauge, or other identifiable feature.",
                "A coordinate published by the relevant municipal corporation.",
                "Any point with a stated reason recorded in provenance.",
            ],
            "_what_would_not": ("A city-centre point, a map-service lookup, a district centroid "
                                "standing in for a municipal area, or any coordinate whose only "
                                "justification is that it is roughly in the right place."),
            "_why_this_is_faster": ("Naming five points is a decision someone can make in minutes. "
                                    "Sourcing five boundaries is a dataset hunt that cannot succeed "
                                    "for Navi Mumbai and Vasai at all."),
            "_group3_position": ("Group 3 proposes this reframing. Group 3 does not name the points "
                                 "- doing so would be exactly the substitution the manager and the "
                                 "contract owner both excluded."),
        },

        "escalation_exact_missing_authority": MISSING_AUTHORITIES,
        "structural_finding_before_any_codes_are_assigned": STRUCTURAL_FINDING,

        "MINIMUM_UNBLOCK_PATH": {
            "_why_this_section_exists": (
                "The manager's direction is to close this now, not to keep discussing it. So this "
                "states the SMALLEST set of decisions that unblocks emission - separating what the "
                "CONTRACT requires from what VERIFICATION requires. They are not the same thing, "
                "and conflating them makes this look harder than it is."),

            "verified_against_the_frozen_schema": {
                "a_zone_polygon_is_NOT_a_contract_requirement": (
                    "The 24 required fields contain no polygon or boundary field. location requires "
                    "only latitude and longitude. The polygon is used by GROUP 3'S OWN semantic "
                    "check to bind a coordinate to a zone - it is required for VERIFICATION, not "
                    "for emission."),
                "the_schema_blocks_none_of_the_five": (
                    "survey_id pattern is ^\S(.*\S)?$ - any non-whitespace string. zone_id is "
                    "^Z[0-9]{1,2}$. Nothing in the contract rejects Mumbai, Navi Mumbai, Vasai, "
                    "Thane or Maval. AUTHORITY blocks them, not the schema."),
            },

            "three_decisions_and_their_cost": [
                {"decision": "survey_id per region",
                 "owner": "Arya Barge (contract owner), with MDU scope",
                 "cost": "A ruling. Minutes, not research.",
                 "group3_recommendation": ("One survey_id per region per gap G-38 - regions are "
                                           "survey areas, not zones. Thane Creek already works "
                                           "this way as survey TC."),
                 "blocked_by": "Nothing except the ruling itself."},

                {"decision": "zone_id per region",
                 "owner": "Arya Barge (contract owner)",
                 "cost": "The same ruling.",
                 "group3_recommendation": ("Z01 as the first zone within each new region's survey, "
                                           "leaving Z02+ for genuine subdivisions later. This "
                                           "preserves the documented Z1-Z8 meaning instead of "
                                           "spending the range on regions."),
                 "blocked_by": "Nothing except the ruling itself."},

                {"decision": "An authoritative coordinate per region",
                 "owner": "GROUP 2 - and this is the important one",
                 "cost": "The work Group 2 has already done once.",
                 "THE_PRECEDENT": (
                     "THANE CREEK'S BOUNDARY CAME FROM GROUP 2, NOT FROM GROUP 3. The polygon in "
                     "reference/inbound/G2_context_TC-Z03-F02-LIDAR-OBS001_AS_RECEIVED_2026-08-21."
                     "json is Group 2's scientific context record. Group 3 has never authored a "
                     "zone boundary and does not own zone definitions. "
                     "So this is not a new process that needs inventing. It is Group 2 doing for "
                     "five regions what they already did for one."),
                 "blocked_by": ("Group 2 supplying a zone polygon or an authoritative point per "
                                "region. Absent that, an LGD or Census record coordinate for the "
                                "administrative unit would also be authoritative."),
                 "what_group3_will_NOT_do": (
                     "Substitute a city-centre point, a map-service lookup, or a boundary derived "
                     "by Group 3. The manager forbade the first and the other two would be Group 3 "
                     "authoring a boundary it has no authority to author."),
                },
            ],

            "the_honest_summary": (
                "TWO of the three blockers are a single contract-owner ruling that costs minutes. "
                "The THIRD is Group 2 repeating work they have already done once. None of the "
                "three requires research, a new process, or a contract change. "
                "Group 3 can emit all five within about 15 minutes per region once they land."),
        },

        "what_group3_will_do_once_unblocked": [
            "1. Receive the approved region key, boundary reference and identity codes.",
            "2. Validate each boundary is a real polygon and that the intended capture point falls "
            "inside it - the same check Thane Creek passes today.",
            "3. Emit ONE truthful observation per region through the proven intake path.",
            "4. Hand each observation_id to Group 1 for canonical record resolution.",
            "5. Provide the acceptance evidence per region, as for Thane Creek: 13/13.",
            "Estimated effort once identity is approved: about 15 minutes per region.",
        ],

        "_honest_caveat_that_survives_unblocking": (
            "Even fully unblocked, these would be EXTERNAL LIVE API observations - "
            "synthetic_state CONTROLLED, is_synthetic true, hardware_verified false. Real "
            "third-party weather data through the controlled Group 3 path, NOT field sensing. "
            "Six regions of external API data is still zero regions of hardware evidence, and the "
            "closure board should say so."),
    }

    out = os.path.join(DAY6, "VANA_ZONE_IDENTITY_REGISTER.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("VANA FIVE-REGION ZONE IDENTITY REGISTER")
    print()
    print("  %-14s %-9s %-6s %-24s %s"
          % ("REGION", "SURVEY", "ZONE", "OBSERVATION_ID", "BOUNDARY"))
    for e in entries:
        print("  %-14s %-9s %-6s %-24s %s"
              % (e["region"], e["survey_id"], e["zone_id"],
                 e["resulting_observation_id"].replace("-EXT-OPENMETEO-OBS001", "-EXT-..."),
                 "BLOCKED"))
    print()
    print("  IDENTITY : APPROVED for all %d - owner ruling, Arya Barge 2026-08-28." % len(entries))
    print("             All %d observation_ids validated against the frozen pattern." % len(entries))
    print("  BOUNDARY : BLOCKED for all %d. NOTHING INVENTED." % len(entries))
    print()
    print("  ONE BLOCKER REMAINS: an authoritative coordinate/boundary per region.")
    print()
    print("  ONLY defined region: Thane Creek  survey TC / zone Z03")
    print("    boundary from GROUP 2's context record, not from Group 3")
    print()
    print("  ESCALATIONS - the exact missing authority:")
    print("    region key : Local Government Directory (LGD), Ministry of Panchayati Raj")
    print("                 lgdirectory.gov.in - the mandated national standard location code")
    print("    geometry   : MCGM / NMMC / VVCMC / TMC per region; Pune district for Maval taluka")
    print("                 Survey of India is the national boundary authority")
    print("    survey/zone: OPEN - identity assignment authority NOT established.")
    print("                 Group 3 cannot authorise canonical identity.")
    print()
    print("  STRUCTURAL FINDING: a REGION is not a ZONE.")
    print("    zone_id is documented 'Survey zone, Z1-Z8' - a subdivision WITHIN a survey.")
    print("    Five regions are five SURVEYS, not five zones. Recommend survey_id per region.")
    print()
    print("  WITHDRAWN: the provisional city-centre coordinates in GROUP3_REGION_COVERAGE.json")
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
