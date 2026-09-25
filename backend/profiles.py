"""
ClimateGuard India - Population Profiles & Heat Health Impact Engine
Computes profile-specific thermal vulnerability, exposure factors, and tailored bulletins.
"""

from typing import Dict, Any, List

PROFILES_DATA: Dict[str, Dict[str, Any]] = {
    "general_public": {
        "id": "general_public",
        "name": "General Public",
        "exposure_factor": 1.0,
        "sensitivity_factor": 1.0,
        "description": "Standard baseline public health advisory for adults in average physical condition.",
        "guidance": {
            "Low": {
                "exposure": "Normal (Routine daily activity)",
                "main_concern": "Gradual fluid loss during warm intervals",
                "possible_effects": "Mild thirst, minor afternoon lethargy",
                "recommended_action": "Drink 2 to 3 liters of water; wear light cotton clothing",
                "outdoor_travel": "Standard outdoor activity safe; observe basic sun protection",
                "peak_period": "1:00 PM – 3:30 PM"
            },
            "Caution": {
                "exposure": "Moderate (Increased ambient heat)",
                "main_concern": "Elevated sweat rate and fatigue",
                "possible_effects": "Dehydration, minor headache, fatigue",
                "recommended_action": "Carry water outdoors; take shaded rests during midday",
                "outdoor_travel": "Limit continuous unshaded exposure to under 60 minutes",
                "peak_period": "12:30 PM – 4:00 PM"
            },
            "Danger": {
                "exposure": "High (Strenuous thermal load)",
                "main_concern": "Heat exhaustion and impaired thermoregulation",
                "possible_effects": "Dizziness, profuse sweating, muscle cramps",
                "recommended_action": "Hydrate with ORS/electrolytes; seek air-cooled or shaded environments",
                "outdoor_travel": "Avoid unnecessary travel during peak afternoon sun",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Very High (Dangerous thermal stress)",
                "main_concern": "Heat stroke threshold exceeded during prolonged exposure",
                "possible_effects": "Nausea, rapid pulse, disorientation, severe dehydration",
                "recommended_action": "Remain indoors in ventilated/cooled rooms; check on neighbors",
                "outdoor_travel": "Strictly postpone non-essential outdoor excursions",
                "peak_period": "11:30 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "Critical (Emergency heat conditions)",
                "main_concern": "Life-threatening thermal collapse",
                "possible_effects": "Heat stroke, organ distress, fainting",
                "recommended_action": "Access emergency cooling centers; hydrate continuously; call 108 if unwell",
                "outdoor_travel": "Complete cessation of outdoor movement during sunlight hours",
                "peak_period": "11:00 AM – 5:00 PM"
            }
        }
    },
    "it_office": {
        "id": "it_office",
        "name": "IT / Office Worker",
        "exposure_factor": 0.65,
        "sensitivity_factor": 0.85,
        "description": "Predominantly indoor personnel with commute-time outdoor exposure and AC dependency.",
        "guidance": {
            "Low": {
                "exposure": "Low (Air-conditioned indoor environment)",
                "main_concern": "Dehydration masked by climate-controlled environments",
                "possible_effects": "Subtle dehydration, dry eyes, low concentration",
                "recommended_action": "Maintain scheduled fluid intake (water/green tea) at your desk",
                "outdoor_travel": "Commute unaffected by thermal stress",
                "peak_period": "1:00 PM – 3:00 PM"
            },
            "Caution": {
                "exposure": "Low to Moderate (Short commute transit)",
                "main_concern": "Sudden temperature transition from AC to outdoor heat",
                "possible_effects": "Thermal shock, lethargy during lunch or transit hours",
                "recommended_action": "Drink water before stepping outdoors; use sun umbrella/shades",
                "outdoor_travel": "Keep outdoor lunch walks short; prefer shaded routes",
                "peak_period": "12:30 PM – 3:30 PM"
            },
            "Danger": {
                "exposure": "Moderate (Commute exposure & power-cut risk)",
                "main_concern": "Heat stress during vehicular commute and transit walking",
                "possible_effects": "Headache, mental fatigue, dehydration, reduced cognitive focus",
                "recommended_action": "Hydrate with electrolyte fluids; ensure office ventilation backup",
                "outdoor_travel": "Travel early morning or post-4:30 PM; avoid bike travel in open sun",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Moderate (Indoor heat accumulation risk)",
                "main_concern": "Overheating in non-AC offices or public transport vehicles",
                "possible_effects": "Exhaustion, dizziness during transit, elevated stress",
                "recommended_action": "Request flexible remote work if transit involves non-AC public buses/trains",
                "outdoor_travel": "Strictly avoid two-wheeler/walking transit between 12 PM - 4 PM",
                "peak_period": "11:30 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "High during transit (Emergency thermal envelope)",
                "main_concern": "Severe transit heat stress and urban heat island trap",
                "possible_effects": "Dehydration headache, disorientation in uncooled vehicles",
                "recommended_action": "Enforce work-from-home advisory; maintain cooling indoors",
                "outdoor_travel": "No outdoor travel; transit vehicles turn into severe heat traps",
                "peak_period": "11:00 AM – 5:00 PM"
            }
        }
    },
    "outdoor_worker": {
        "id": "outdoor_worker",
        "name": "Outdoor Worker (Delivery / Transport / Vendors)",
        "exposure_factor": 1.6,
        "sensitivity_factor": 1.15,
        "description": "Continuous ambient solar exposure and physical movement on roads and public spaces.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Continuous outdoor movement)",
                "main_concern": "Cumulative perspiration throughout shift",
                "possible_effects": "Thirst, muscle fatigue after continuous riding/walking",
                "recommended_action": "Carry minimum 2L water flask; drink every 30 minutes",
                "outdoor_travel": "Safe with standard cotton head-covering",
                "peak_period": "1:00 PM – 3:30 PM"
            },
            "Caution": {
                "exposure": "High (Direct sun exposure on road)",
                "main_concern": "Accelerated dehydration and asphalt radiant heat",
                "possible_effects": "Heat cramps, dry mouth, slow reaction times",
                "recommended_action": "Mandatory 10-minute shade stops every hour; carry lemon salt water",
                "outdoor_travel": "Wear damp neck cloth, UV arm sleeves, and wide helmet visor",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Danger": {
                "exposure": "Very High (Severe pavement heat reflection)",
                "main_concern": "Heat exhaustion and motor coordination loss",
                "possible_effects": "Dizziness, muscle spasms, blurred vision, heavy perspiration",
                "recommended_action": "Shift deliveries to early morning/evening; take 15-min rest every 45 mins",
                "outdoor_travel": "Avoid continuous biking between 12 PM - 3:30 PM; use designated delivery kiosks",
                "peak_period": "11:30 AM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Severe (Life-threatening solar exposure)",
                "main_concern": "Imminent heat stroke and collapse on the road",
                "possible_effects": "Fainting, nausea, cessation of sweat, delirium",
                "recommended_action": "Employers must suspend outdoor deliveries 12 PM - 4 PM without pay penalty",
                "outdoor_travel": "Cessation of two-wheeler deliveries during peak sun hours",
                "peak_period": "11:00 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "Critical (Prohibitive outdoor conditions)",
                "main_concern": "Fatal heat trauma and severe systemic thermal injury",
                "possible_effects": "Heat stroke, loss of consciousness, kidney stress",
                "recommended_action": "Immediate suspension of all outdoor dispatch operations; seek cooling shelters",
                "outdoor_travel": "Zero outdoor transit; road surfaces exceed 55°C",
                "peak_period": "10:30 AM – 5:00 PM"
            }
        }
    },
    "construction_labor": {
        "id": "construction_labor",
        "name": "Construction / Labor Worker",
        "exposure_factor": 1.85,
        "sensitivity_factor": 1.25,
        "description": "Heavy physical exertion combined with direct solar radiation and industrial radiant surfaces.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Physical metabolic heat generation)",
                "main_concern": "Internal metabolic heat plus ambient temperature",
                "possible_effects": "Heavy sweat, physical fatigue, thirst",
                "recommended_action": "Mandatory water stations within 10 meters of work area",
                "outdoor_travel": "Standard PPE with breathable cotton undershirts",
                "peak_period": "12:30 PM – 3:30 PM"
            },
            "Caution": {
                "exposure": "High (Strenuous labor under sunlight)",
                "main_concern": "Electrolyte depletion and heavy muscle fatigue",
                "possible_effects": "Severe muscle cramps, reduced grip strength, headache",
                "recommended_action": "Enforce 15-min shaded break every hour; provide ORS/buttermilk at site",
                "outdoor_travel": "Erect temporary green tarpaulin shading over active work zones",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Danger": {
                "exposure": "Very High (Critical labor threshold)",
                "main_concern": "Heat exhaustion and occupational machinery accidents",
                "possible_effects": "Heat syncope (fainting), vomiting, disorientation",
                "recommended_action": "Reschedule heavy lifting to 6:00 AM - 11:00 AM; stop work 12 PM - 3:30 PM",
                "outdoor_travel": "Mandatory buddy-system to monitor co-workers for heat symptoms",
                "peak_period": "11:30 AM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Critical (Prohibited labor conditions)",
                "main_concern": "Rapid-onset heat stroke under physical workload",
                "possible_effects": "Hyperthermia (>40°C body temp), seizures, collapse",
                "recommended_action": "Mandatory labor holiday / shift work to night shifts (6 PM - 10 PM)",
                "outdoor_travel": "No rooftop, steel fixing, or unshaded masonry work permitted",
                "peak_period": "11:00 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "Life-Threatening (Severe emergency shutdown)",
                "main_concern": "Fatal exertional heat stroke",
                "possible_effects": "Coma, organ failure, cardiovascular breakdown",
                "recommended_action": "Legally enforced site closure; all personnel moved to cooling barracks",
                "outdoor_travel": "Absolute halt of all manual labor across the municipal district",
                "peak_period": "10:30 AM – 5:30 PM"
            }
        }
    },
    "student": {
        "id": "student",
        "name": "Student / Youth",
        "exposure_factor": 0.9,
        "sensitivity_factor": 1.1,
        "description": "School and college students with transit exposure, outdoor sports, and uncooled classrooms.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Classroom and playground activity)",
                "main_concern": "Dehydration during outdoor games and physical education",
                "possible_effects": "Thirst, tiredness, flushed skin after sports",
                "recommended_action": "Encourage regular water intake; refill bottles before PE classes",
                "outdoor_travel": "Normal school bus and walking transit safe",
                "peak_period": "1:00 PM – 3:00 PM"
            },
            "Caution": {
                "exposure": "Moderate to High (Afternoon school departure)",
                "main_concern": "Heat accumulation during afternoon school dismissal",
                "possible_effects": "Headache, lethargy, poor focus in uncooled classrooms",
                "recommended_action": "Move sports classes to indoor auditoriums or early morning",
                "outdoor_travel": "Ensure water availability on school buses; avoid waiting in unshaded bus stands",
                "peak_period": "12:00 PM – 3:30 PM"
            },
            "Danger": {
                "exposure": "High (Peak afternoon dispersal)",
                "main_concern": "Heat exhaustion in tin-roofed schools or unshaded playgrounds",
                "possible_effects": "Dizziness, fainting during morning assembly or playground games",
                "recommended_action": "Cancel outdoor sports and open-ground assemblies; advance school dismissal to 11:30 AM",
                "outdoor_travel": "Children must not walk home unshaded in afternoon sun",
                "peak_period": "11:30 AM – 3:30 PM"
            },
            "Extreme Danger": {
                "exposure": "Very High (Vulnerable youth physiology)",
                "main_concern": "Rapid core body heating due to higher body surface area to mass ratio",
                "possible_effects": "High fever, vomiting, severe dehydration, heat syncope",
                "recommended_action": "District education board should order schools closed or online classes",
                "outdoor_travel": "Keep students strictly indoors during daytime hours",
                "peak_period": "11:00 AM – 4:00 PM"
            },
            "Severe": {
                "exposure": "Severe (School emergency closure)",
                "main_concern": "Pediatric heat injury in high ambient temperatures",
                "possible_effects": "Loss of consciousness, heat delirium",
                "recommended_action": "Mandatory closure of all educational institutions and tuition centers",
                "outdoor_travel": "Children prohibited from open playgrounds and uncooled transit",
                "peak_period": "10:30 AM – 4:30 PM"
            }
        }
    },
    "pregnant": {
        "id": "pregnant",
        "name": "Pregnant Person",
        "exposure_factor": 0.8,
        "sensitivity_factor": 1.5,
        "description": "Elevated baseline body temperature, increased cardiovascular load, and high dehydration vulnerability.",
        "guidance": {
            "Low": {
                "exposure": "Moderate sensitivity (Maternal heat dissipation)",
                "main_concern": "Fluid balance and blood pressure fluctuations",
                "possible_effects": "Mild swelling in feet, fatigue, elevated thirst",
                "recommended_action": "Sip coconut water/water frequently; elevate feet during rest",
                "outdoor_travel": "Carry personal water bottle; walk in morning or late evening",
                "peak_period": "12:30 PM – 3:00 PM"
            },
            "Caution": {
                "exposure": "High sensitivity (Susceptible to heat strain)",
                "main_concern": "Dehydration precipitating Braxton-Hicks contractions or dizziness",
                "possible_effects": "Dizziness upon standing, excessive swelling, fatigue",
                "recommended_action": "Stay in cool, well-ventilated rooms; drink 3L fluids spread throughout the day",
                "outdoor_travel": "Avoid open outdoor transit between 12 PM - 3:30 PM",
                "peak_period": "12:00 PM – 3:30 PM"
            },
            "Danger": {
                "exposure": "Very High sensitivity (Maternal & fetal thermal load)",
                "main_concern": "Reduced amniotic fluid volume and heat exhaustion risk",
                "possible_effects": "Severe dizziness, palpitations, nausea, heat exhaustion",
                "recommended_action": "Remain in climate-controlled spaces; rest frequently; consult doctor if cramping occurs",
                "outdoor_travel": "Avoid all non-essential outdoor trips; use AC transportation only",
                "peak_period": "11:30 AM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Severe risk (Critical maternal heat precaution)",
                "main_concern": "Risk of premature labor or hyperthermia-induced maternal distress",
                "possible_effects": "Fainting, dehydration headache, maternal distress",
                "recommended_action": "Strict indoor rest with fans/coolers; continuous hydration; monitor fetal movement",
                "outdoor_travel": "Strict zero-exposure directive; medical travel only with AC vehicle",
                "peak_period": "11:00 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "Critical (Maternal emergency precautions)",
                "main_concern": "Systemic heat illness endangering maternal and fetal safety",
                "possible_effects": "Heat stroke, severe blood pressure drops, uterine irritability",
                "recommended_action": "Move to a municipal cooling shelter or hospital if home lacks cooling",
                "outdoor_travel": "Complete curfew for pregnant individuals; emergency contact on standby",
                "peak_period": "10:30 AM – 5:00 PM"
            }
        }
    },
    "elderly": {
        "id": "elderly",
        "name": "Elderly Person (60+ Years)",
        "exposure_factor": 0.75,
        "sensitivity_factor": 1.7,
        "description": "Blunted thirst response, diminished sweat gland efficiency, and prevalent cardiovascular comorbidities.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Reduced physiological reserve)",
                "main_concern": "Subconscious fluid deficit without active thirst sensation",
                "possible_effects": "Dry mouth, mild confusion, joint sluggishness",
                "recommended_action": "Drink water on a fixed hourly schedule rather than waiting for thirst",
                "outdoor_travel": "Perform morning walks before 9:00 AM or after 6:00 PM",
                "peak_period": "12:30 PM – 3:30 PM"
            },
            "Caution": {
                "exposure": "High (Cardiovascular compensation strain)",
                "main_concern": "Heart workload increases to circulate blood for skin cooling",
                "possible_effects": "Weakness, unsteady gait, elevated blood pressure or postural drops",
                "recommended_action": "Stay in shaded, cross-ventilated ground-floor rooms; keep sponge baths available",
                "outdoor_travel": "Avoid venturing outdoors during afternoon hours",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Danger": {
                "exposure": "Very High (Heat syncope and stroke danger)",
                "main_concern": "Thermoregulatory failure and medication interactions (diuretics/BP pills)",
                "possible_effects": "Confusion, slurred speech, heat cramps, loss of balance, fainting",
                "recommended_action": "Caregiver supervision required; sponge body with room-temp water; monitor BP",
                "outdoor_travel": "Strictly cancel all outdoor visits, temple trips, and market errands",
                "peak_period": "11:30 AM – 4:30 PM"
            },
            "Extreme Danger": {
                "exposure": "Severe (High mortality vulnerability zone)",
                "main_concern": "Classical non-exertional heat stroke and cardiovascular collapse",
                "possible_effects": "Hot dry skin without sweating, delirium, unconsciousness",
                "recommended_action": "Relocate to air-conditioned community cooling shelters; call emergency line immediately if confused",
                "outdoor_travel": "Zero outdoor exposure; keep windows shaded with wet curtains",
                "peak_period": "11:00 AM – 5:00 PM"
            },
            "Severe": {
                "exposure": "Critical Emergency (Extreme vulnerability)",
                "main_concern": "Fatal hyperthermia within 2-3 hours of uncooled indoor confinement",
                "possible_effects": "Coma, cardiovascular failure, multi-organ shock",
                "recommended_action": "Immediate medical intervention or transfer to hospital cooling ward",
                "outdoor_travel": "Life-threatening conditions outdoors and in unventilated rooms",
                "peak_period": "10:30 AM – 5:30 PM"
            }
        }
    },
    "child": {
        "id": "child",
        "name": "Infant & Young Child (Under 10)",
        "exposure_factor": 0.85,
        "sensitivity_factor": 1.6,
        "description": "Higher surface area to body weight ratio, immature sweating mechanism, and inability to self-regulate.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Fast metabolic water turnover)",
                "main_concern": "Dehydration from playtime without regular drink breaks",
                "possible_effects": "Irritability, flushed cheeks, dry lips",
                "recommended_action": "Offer water or breast milk/dilute fruit juices every 45 minutes",
                "outdoor_travel": "Avoid direct noon sun; dress in single-layer loose cotton",
                "peak_period": "1:00 PM – 3:00 PM"
            },
            "Caution": {
                "exposure": "High (Inability to communicate thirst early)",
                "main_concern": "Prickly heat rashes and rapid dehydration",
                "possible_effects": "Restlessness, crying without tears, decreased urination",
                "recommended_action": "Keep in cool indoor areas; sponge with lukewarm water if warm",
                "outdoor_travel": "Never leave a child unattended in a parked car even for 1 minute",
                "peak_period": "12:00 PM – 3:30 PM"
            },
            "Danger": {
                "exposure": "Very High (Pediatric heat exhaustion risk)",
                "main_concern": "Rapid rise in core body temperature (heats 3-5x faster than adult)",
                "possible_effects": "Fever-like body warmth, lethargy, vomiting, refusal to drink",
                "recommended_action": "Move to coolest room; give oral rehydration solution; contact pediatrician",
                "outdoor_travel": "Strictly cancel all outdoor play, stroller walks, and outings",
                "peak_period": "11:30 AM – 4:00 PM"
            },
            "Extreme Danger": {
                "exposure": "Severe (High-risk pediatric emergency)",
                "main_concern": "Pediatric heat stroke and febrile seizures",
                "possible_effects": "Seizures, unresponsive sleepiness, hot dry skin, rapid breathing",
                "recommended_action": "Emergency medical attention; apply wet towels to neck, armpits, and groin",
                "outdoor_travel": "No outdoor travel; keep indoor temperature below 28°C if possible",
                "peak_period": "11:00 AM – 4:30 PM"
            },
            "Severe": {
                "exposure": "Critical (Extreme pediatric danger)",
                "main_concern": "Acute hyperthermic organ injury",
                "possible_effects": "Unconsciousness, shock, breathing difficulties",
                "recommended_action": "Immediate hospitalization in pediatric emergency ward",
                "outdoor_travel": "Absolute indoor confinement with active temperature mitigation",
                "peak_period": "10:30 AM – 5:00 PM"
            }
        }
    },
    "chronic_conditions": {
        "id": "chronic_conditions",
        "name": "Person with Chronic Conditions (Heart/Kidney/Diabetes)",
        "exposure_factor": 0.8,
        "sensitivity_factor": 1.75,
        "description": "Compromised circulatory/renal function and prescription drug interactions under heat strain.",
        "guidance": {
            "Low": {
                "exposure": "Moderate (Baseline medication vulnerability)",
                "main_concern": "Fluid shifts altering medication concentration in bloodstream",
                "possible_effects": "Fatigue, mild swelling, blood sugar variability",
                "recommended_action": "Maintain doctor-approved fluid allowance; monitor daily weight",
                "outdoor_travel": "Avoid long walks during afternoon hours",
                "peak_period": "12:30 PM – 3:30 PM"
            },
            "Caution": {
                "exposure": "High (Renal and cardiovascular compensation)",
                "main_concern": "Diuretic medication leading to acute dehydration and low BP",
                "possible_effects": "Dizziness upon standing, irregular pulse, electrolyte imbalance",
                "recommended_action": "Check BP and glucose levels twice daily; consult doctor on fluid limits",
                "outdoor_travel": "Avoid all unshaded transit during midday heat",
                "peak_period": "12:00 PM – 4:00 PM"
            },
            "Danger": {
                "exposure": "Very High (Cardiorenal strain threshold)",
                "main_concern": "Acute kidney injury (prerenal azotemia) or heart strain",
                "possible_effects": "Severe weakness, reduced urine output, chest heaviness, confusion",
                "recommended_action": "Stay in cooled environment; do not adjust medication without doctor call",
                "outdoor_travel": "Strictly remain indoors; postpone all non-emergency visits",
                "peak_period": "11:30 AM – 4:30 PM"
            },
            "Extreme Danger": {
                "exposure": "Severe (High-risk decompensation zone)",
                "main_concern": "Cardiovascular collapse or acute renal failure triggered by heat",
                "possible_effects": "Arrhythmia, severe hypotension, fluid retention crisis, delirium",
                "recommended_action": "Caregiver monitoring; prepare to transfer to air-conditioned hospital ward",
                "outdoor_travel": "Zero exposure; medical transport with AC only",
                "peak_period": "11:00 AM – 5:00 PM"
            },
            "Severe": {
                "exposure": "Critical (Life-threatening decompensation)",
                "main_concern": "Multi-organ failure precipitated by extreme ambient heat",
                "possible_effects": "Cardiogenic shock, acute renal shutdown, coma",
                "recommended_action": "Immediate emergency hospitalization in monitored intensive care",
                "outdoor_travel": "Absolute indoor confinement with active temperature control",
                "peak_period": "10:30 AM – 5:30 PM"
            }
        }
    }
}


def get_all_profiles() -> List[Dict[str, Any]]:
    """Return list of all registered population profiles."""
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "exposure_factor": p["exposure_factor"],
            "sensitivity_factor": p["sensitivity_factor"]
        }
        for p in PROFILES_DATA.values()
    ]


def calculate_profile_impact(
    wbgt: float,
    temp: float,
    rh: float,
    profile_id: str = "general_public"
) -> Dict[str, Any]:
    """
    Computes a deterministic, rule-based profile-specific heat exposure and impact assessment.
    
    Formula:
    base_weight = 1 (Low) to 5 (Severe)
    raw_score = base_weight * exposure_factor * sensitivity_factor
    
    Impact Levels:
    raw_score < 2.0  -> LOW (Green)
    2.0 <= < 3.5    -> MODERATE (Yellow)
    3.5 <= < 5.5    -> HIGH (Orange)
    5.5 <= < 8.0    -> VERY HIGH (Red)
    >= 8.0          -> CRITICAL (Dark Red)
    """
    profile = PROFILES_DATA.get(profile_id, PROFILES_DATA["general_public"])

    # Environmental risk baseline from WBGT
    if wbgt < 28.0:
        cat = "Low"
        weight = 1
    elif wbgt < 30.0:
        cat = "Caution"
        weight = 2
    elif wbgt < 32.0:
        cat = "Danger"
        weight = 3
    elif wbgt <= 35.0:
        cat = "Extreme Danger"
        weight = 4
    else:
        cat = "Severe"
        weight = 5

    # Deterministic profile impact calculation
    exposure = profile["exposure_factor"]
    sensitivity = profile["sensitivity_factor"]
    raw_score = round(weight * exposure * sensitivity, 2)

    # Classify profile impact level
    if raw_score < 2.0:
        impact_level = "LOW"
        impact_color = "#10b981"
        badge_class = "risk-low"
    elif raw_score < 3.5:
        impact_level = "MODERATE"
        impact_color = "#f59e0b"
        badge_class = "risk-caution"
    elif raw_score < 5.5:
        impact_level = "HIGH"
        impact_color = "#f97316"
        badge_class = "risk-danger"
    elif raw_score < 8.0:
        impact_level = "VERY HIGH"
        impact_color = "#ef4444"
        badge_class = "risk-extreme"
    else:
        impact_level = "CRITICAL"
        impact_color = "#991b1b"
        badge_class = "risk-severe"

    # Specific bulletin guidance for current environmental category
    guidance = profile["guidance"].get(cat, profile["guidance"]["Caution"])

    return {
        "profile_id": profile["id"],
        "profile_name": profile["name"],
        "environmental_category": cat,
        "environmental_weight": weight,
        "profile_score": raw_score,
        "impact_level": impact_level,
        "impact_color": impact_color,
        "badge_class": badge_class,
        "exposure_factor": exposure,
        "sensitivity_factor": sensitivity,
        "bulletin": {
            "exposure": guidance["exposure"],
            "main_concern": guidance["main_concern"],
            "possible_effects": guidance["possible_effects"],
            "recommended_action": guidance["recommended_action"],
            "outdoor_travel": guidance["outdoor_travel"],
            "peak_period": guidance["peak_period"]
        },
        "disclaimer": "Illustrative profile vulnerability score for decision support; not a clinical medical prediction."
    }
